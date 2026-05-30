"""
Resilient RabbitMQ Consumer Template

Demonstrates all three patterns:
1. Manual Acknowledgments (ack/nack)
2. Idempotency (unique ID + upsert)
3. Dead Letter Exchange (nack with requeue=False for malformed messages)

For Lessley Scraper and Personalization workers.
Usage:
    python resilient_consumer.py \
        --rabbitmq-host localhost \
        --queue scraper.jobs \
        --mongodb-uri mongodb://mongo:27017/lessley
"""

import json
import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, Callable
from functools import wraps

import pika
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError


# ============================================================================
# Configuration
# ============================================================================

class ConsumerConfig:
    """Central configuration for consumer behavior."""
    
    def __init__(
        self,
        rabbitmq_host: str = "localhost",
        rabbitmq_port: int = 5672,
        rabbitmq_user: str = "guest",
        rabbitmq_password: str = "guest",
        queue_name: str = "default.queue",
        mongodb_uri: str = "mongodb://localhost:27017",
        mongodb_db: str = "lessley",
        prefetch_count: int = 10,
    ):
        self.rabbitmq_host = rabbitmq_host
        self.rabbitmq_port = rabbitmq_port
        self.rabbitmq_user = rabbitmq_user
        self.rabbitmq_password = rabbitmq_password
        self.queue_name = queue_name
        self.mongodb_uri = mongodb_uri
        self.mongodb_db = mongodb_db
        self.prefetch_count = prefetch_count  # QoS: max unacked messages per consumer


# ============================================================================
# Logging with Structured Context
# ============================================================================

class StructuredLogger:
    """Logger with correlation ID and message metadata."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._context = {}
    
    def set_context(self, **kwargs):
        """Set structured context (e.g., correlation_id, message_id)."""
        self._context.update(kwargs)
    
    def clear_context(self):
        """Clear structured context after message processing."""
        self._context.clear()
    
    def _format_message(self, msg: str) -> str:
        """Prepend context to log message."""
        if self._context:
            context_str = " | ".join(f"{k}={v}" for k, v in self._context.items())
            return f"[{context_str}] {msg}"
        return msg
    
    def info(self, msg: str):
        self.logger.info(self._format_message(msg))
    
    def error(self, msg: str, exc_info=False):
        self.logger.error(self._format_message(msg), exc_info=exc_info)
    
    def warning(self, msg: str):
        self.logger.warning(self._format_message(msg))


logger = StructuredLogger(__name__)


# ============================================================================
# Pattern 1 & 2: Message Processing with Ack/Nack + Idempotency
# ============================================================================

def generate_unique_id(payload: Dict[str, Any]) -> str:
    """
    Generate deterministic unique ID from payload.
    
    For Scraper: hash of (url, product_id, timestamp_day)
    For Personalization: hash of (user_id, content_hash)
    
    Must be stable across retries so idempotent upsert works.
    """
    # Extract stable fields (exclude timestamps that change on retry)
    stable_key = json.dumps(
        {
            "url": payload.get("url"),
            "product_id": payload.get("product_id"),
            "batch_id": payload.get("batch_id"),
        },
        sort_keys=True,
    )
    return hashlib.sha256(stable_key.encode()).hexdigest()


def process_message(payload: Dict[str, Any], logger_ctx: StructuredLogger) -> Dict[str, Any]:
    """
    Business logic: parse, validate, and transform payload.
    
    Raises:
        ValueError: If payload structure is invalid (hard error).
        json.JSONDecodeError: If JSON is malformed.
    """
    # Validate required fields
    required_fields = ["url", "product_id"]
    for field in required_fields:
        if field not in payload:
            raise ValueError(f"Missing required field: {field}")
    
    logger_ctx.info(f"Processing payload: url={payload['url']}, product_id={payload['product_id']}")
    
    # Example: scraper result (replace with actual scraping logic)
    result = {
        "product_id": payload["product_id"],
        "url": payload["url"],
        "title": payload.get("title", "N/A"),
        "price": payload.get("price", 0),
        "scraped_at": datetime.now().isoformat(),
    }
    
    logger_ctx.info("Payload processed successfully")
    return result


# ============================================================================
# Pattern 2: Idempotent Upsert to MongoDB
# ============================================================================

def idempotent_upsert(
    collection,
    unique_id: str,
    data: Dict[str, Any],
    logger_ctx: StructuredLogger,
) -> bool:
    """
    Insert or update document with upsert.
    
    Returns True on success, False if duplicate was detected (already processed).
    """
    try:
        document = {
            "_id": unique_id,
            "data": data,
            "processed_at": datetime.now().isoformat(),
        }
        
        result = collection.update_one(
            {"_id": unique_id},
            {"$set": document},
            upsert=True,
        )
        
        if result.upserted_id:
            logger_ctx.info(f"New document inserted: {unique_id}")
        else:
            logger_ctx.info(f"Document already exists (duplicate detected): {unique_id}")
        
        return True
    except Exception as e:
        logger_ctx.error(f"MongoDB upsert failed: {e}", exc_info=True)
        return False


# ============================================================================
# Pattern 3: Message Validation & Dead Letter Exchange
# ============================================================================

def validate_payload(payload_str: str) -> Dict[str, Any]:
    """
    Parse and validate JSON payload.
    
    Raises:
        json.JSONDecodeError: If JSON is malformed.
        ValueError: If structure is invalid (poisoned message).
    """
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Malformed JSON in message body: {e.msg}",
            e.doc,
            e.pos,
        )
    
    if not isinstance(payload, dict):
        raise ValueError("Message payload must be a JSON object")
    
    return payload


# ============================================================================
# Consumer Callback: Orchestrates All Patterns
# ============================================================================

def create_message_callback(
    mongodb_client: MongoClient,
    config: ConsumerConfig,
    logger_ctx: StructuredLogger,
) -> Callable:
    """
    Factory function: returns the callback that processes each message.
    
    Callback implements:
    1. Manual ack/nack (never auto-acknowledge)
    2. Idempotent upsert to MongoDB
    3. Reject malformed payloads with requeue=False (→ DLX)
    """
    
    db = mongodb_client[config.mongodb_db]
    collection = db["deals"]  # or "personalization", etc.
    
    def on_message_received(ch, method, properties, body: bytes):
        """
        Callback invoked when message arrives from RabbitMQ.
        
        Args:
            ch: Channel object (for ack/nack)
            method: Method object (contains delivery_tag)
            properties: Message properties
            body: Message body (bytes)
        """
        delivery_tag = method.delivery_tag
        correlation_id = properties.correlation_id or "unknown"
        
        # Set structured context for this message
        logger_ctx.set_context(
            correlation_id=correlation_id,
            queue=config.queue_name,
            delivery_tag=delivery_tag,
        )
        
        logger_ctx.info("Message received from RabbitMQ")
        
        try:
            # ─────────────────────────────────────────────────────────────
            # Step 1: Validate & Parse JSON (Pattern 3: DLX for malformed)
            # ─────────────────────────────────────────────────────────────
            
            payload = validate_payload(body.decode("utf-8"))
            logger_ctx.info("Payload validated and parsed")
            
        except (json.JSONDecodeError, ValueError) as e:
            # Malformed payload: nack with requeue=False
            # RabbitMQ will route to Dead Letter Exchange (DLX)
            logger_ctx.error(f"Malformed payload: {e}")
            ch.basic_nack(delivery_tag=delivery_tag, requeue=False)
            logger_ctx.info("Message nack'd (requeue=False) → routed to DLX")
            return
        
        try:
            # ─────────────────────────────────────────────────────────────
            # Step 2: Generate Unique ID & Process (Pattern 2: Idempotency)
            # ─────────────────────────────────────────────────────────────
            
            unique_id = generate_unique_id(payload)
            logger_ctx.set_context(unique_id=unique_id)
            
            result = process_message(payload, logger_ctx)
            
            # ─────────────────────────────────────────────────────────────
            # Step 3: Atomic Commit to MongoDB
            # ─────────────────────────────────────────────────────────────
            
            success = idempotent_upsert(
                collection,
                unique_id=unique_id,
                data=result,
                logger_ctx=logger_ctx,
            )
            
            if not success:
                raise Exception("MongoDB upsert failed")
            
            # ─────────────────────────────────────────────────────────────
            # Step 4: Acknowledge to RabbitMQ (Pattern 1: Manual Ack)
            # ─────────────────────────────────────────────────────────────
            # Only reach here if all steps succeed. If process crashes before
            # this line, the connection drops and message stays in queue.
            
            ch.basic_ack(delivery_tag=delivery_tag)
            logger_ctx.info("Message processed and ack'd successfully")
        
        except Exception as e:
            # Unexpected error (not malformed JSON, but processing failed)
            # Nack with requeue=True so another worker tries again
            logger_ctx.error(f"Processing failed (retryable error): {e}", exc_info=True)
            ch.basic_nack(delivery_tag=delivery_tag, requeue=True)
            logger_ctx.info("Message nack'd (requeue=True) → back to queue")
        
        finally:
            # Clean up structured context for next message
            logger_ctx.clear_context()
    
    return on_message_received


# ============================================================================
# Consumer Setup & Lifecycle
# ============================================================================

def setup_consumer(config: ConsumerConfig) -> tuple:
    """
    Initialize RabbitMQ channel, MongoDB connection, and register callback.
    
    Returns:
        (connection, channel, mongodb_client)
    """
    
    # RabbitMQ Connection
    credentials = pika.PlainCredentials(config.rabbitmq_user, config.rabbitmq_password)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=config.rabbitmq_host,
            port=config.rabbitmq_port,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
        )
    )
    
    channel = connection.channel()
    
    # QoS: Don't fetch more than prefetch_count unacked messages
    # This prevents one slow worker from consuming all messages
    channel.basic_qos(prefetch_count=config.prefetch_count)
    
    # Declare queue (idempotent; fails silently if already exists)
    channel.queue_declare(queue=config.queue_name, durable=True)
    
    logger.info(f"RabbitMQ connected: queue={config.queue_name}, prefetch={config.prefetch_count}")
    
    # MongoDB Connection
    mongodb_client = MongoClient(config.mongodb_uri)
    logger.info(f"MongoDB connected: {config.mongodb_uri}")
    
    return connection, channel, mongodb_client


def start_consuming(config: ConsumerConfig):
    """
    Main consumer loop: connect and start processing messages.
    """
    
    connection, channel, mongodb_client = setup_consumer(config)
    logger_ctx = StructuredLogger(__name__)
    
    # Create and register callback
    callback = create_message_callback(mongodb_client, config, logger_ctx)
    channel.basic_consume(queue=config.queue_name, on_message_callback=callback)
    
    logger.info(f"Started consuming from queue: {config.queue_name}")
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")
    finally:
        channel.stop_consuming()
        connection.close()
        mongodb_client.close()
        logger.info("Consumer shutdown complete")


# ============================================================================
# CLI & Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Resilient RabbitMQ Consumer")
    parser.add_argument("--rabbitmq-host", default="localhost", help="RabbitMQ host")
    parser.add_argument("--rabbitmq-port", type=int, default=5672, help="RabbitMQ port")
    parser.add_argument("--queue", required=True, help="Queue name to consume from")
    parser.add_argument("--mongodb-uri", default="mongodb://localhost:27017", help="MongoDB URI")
    parser.add_argument("--mongodb-db", default="lessley", help="MongoDB database name")
    parser.add_argument("--prefetch-count", type=int, default=10, help="Max unacked messages per worker")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )
    
    config = ConsumerConfig(
        rabbitmq_host=args.rabbitmq_host,
        rabbitmq_port=args.rabbitmq_port,
        queue_name=args.queue,
        mongodb_uri=args.mongodb_uri,
        mongodb_db=args.mongodb_db,
        prefetch_count=args.prefetch_count,
    )
    
    start_consuming(config)
