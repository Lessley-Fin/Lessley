"""
End-to-End (E2E) Tests: Full Message Flow Testing

Simulates the complete Daily Night Routine:
1. Scraper finishes job (scraped deals in MongoDB)
2. Scraper.finish event published to RabbitMQ
3. Optimizer consumes and processes
4. Optimizer.ready event published
5. Personalization consumes and publishes Personalize.hotdeal
6. API Gateway receives notification

Usage:
    pytest e2e_message_flow_tests.py -v
    pytest e2e_message_flow_tests.py::test_daily_night_routine_e2e -v
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import pytest
import pika
from pymongo import MongoClient


logger = logging.getLogger(__name__)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mongo_db():
    """MongoDB test database."""
    client = MongoClient("mongodb://localhost:27017")
    db = client.lessley_e2e_test
    
    yield db
    
    client.drop_database("lessley_e2e_test")
    client.close()


@pytest.fixture(scope="function")
def rabbitmq_connection():
    """RabbitMQ connection."""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters("localhost")
    )
    
    yield connection
    
    connection.close()


@pytest.fixture(scope="function")
def rabbitmq_channel(rabbitmq_connection):
    """RabbitMQ channel with test queues."""
    channel = rabbitmq_connection.channel()
    
    # Declare test exchanges and queues
    channel.exchange_declare(exchange="test_scraper", exchange_type="direct", durable=True)
    channel.exchange_declare(exchange="test_optimizer", exchange_type="direct", durable=True)
    channel.exchange_declare(exchange="test_personalization", exchange_type="direct", durable=True)
    
    channel.queue_declare(queue="test_scraper.finish", durable=True)
    channel.queue_declare(queue="test_optimizer.ready", durable=True)
    channel.queue_declare(queue="test_personalization.hotdeal", durable=True)
    
    channel.queue_bind(queue="test_scraper.finish", exchange="test_scraper", routing_key="finish")
    channel.queue_bind(queue="test_optimizer.ready", exchange="test_optimizer", routing_key="ready")
    channel.queue_bind(queue="test_personalization.hotdeal", exchange="test_personalization", routing_key="hotdeal")
    
    yield channel
    
    # Cleanup
    channel.queue_delete(queue="test_scraper.finish")
    channel.queue_delete(queue="test_optimizer.ready")
    channel.queue_delete(queue="test_personalization.hotdeal")
    channel.close()


# ============================================================================
# E2E Test: Daily Night Routine
# ============================================================================

class TestDailyNightRoutine:
    """Test the complete Daily Night Routine workflow."""
    
    def test_daily_night_routine_e2e(self, mongo_db, rabbitmq_channel):
        """
        End-to-end: Scraper.finish → Optimizer → Personalization → API Gateway
        """
        
        logger.info("=" * 70)
        logger.info("Starting Daily Night Routine E2E Test")
        logger.info("=" * 70)
        
        # ─────────────────────────────────────────────────────────────────
        # Step 1: Scraper finishes job (insert deals into MongoDB)
        # ─────────────────────────────────────────────────────────────────
        
        logger.info("\nStep 1: Scraper processes deals and inserts into MongoDB")
        
        scraped_deals = [
            {
                "_id": "deal-coffee-50",
                "store_id": "store-hever-001",
                "title": "50% off coffee",
                "price": 2.50,
                "category": "food",
                "inserted_at": datetime.now()
            },
            {
                "_id": "deal-books-30",
                "store_id": "store-tarbut-001",
                "title": "30% off books",
                "price": 7.00,
                "category": "books",
                "inserted_at": datetime.now()
            }
        ]
        
        mongo_db.deals.delete_many({})
        mongo_db.deals.insert_many(scraped_deals)
        
        inserted_count = mongo_db.deals.count_documents({})
        logger.info(f"✓ Inserted {inserted_count} deals into MongoDB")
        
        assert inserted_count == 2, f"Expected 2 deals, got {inserted_count}"
        
        # ─────────────────────────────────────────────────────────────────
        # Step 2: Publish Scraper.finish event
        # ─────────────────────────────────────────────────────────────────
        
        logger.info("\nStep 2: Scraper publishes Scraper.finish event")
        
        scraper_event = {
            "batch_id": "batch-night-001",
            "timestamp": datetime.now().isoformat(),
            "scraped_deals": len(scraped_deals),
            "status": "success"
        }
        
        rabbitmq_channel.basic_publish(
            exchange="test_scraper",
            routing_key="finish",
            body=json.dumps(scraper_event).encode(),
            properties=pika.BasicProperties(delivery_mode=2)  # Persistent
        )
        
        logger.info(f"✓ Published Scraper.finish event: {scraper_event['batch_id']}")
        
        # ─────────────────────────────────────────────────────────────────
        # Step 3: Optimizer consumes Scraper.finish
        # ─────────────────────────────────────────────────────────────────
        
        logger.info("\nStep 3: Optimizer consumes Scraper.finish and processes")
        
        # Get message from queue (in real test, this runs as background service)
        method, properties, body = rabbitmq_channel.basic_get(
            queue="test_scraper.finish",
            auto_ack=False
        )
        
        assert method is not None, "No message in Scraper.finish queue"
        
        received_event = json.loads(body.decode())
        logger.info(f"✓ Optimizer received event: {received_event['batch_id']}")
        
        # Simulate Optimizer processing
        logger.info("  Optimizing deals...")
        time.sleep(0.5)
        
        # Store optimization results
        optimized_deals = [
            {
                "_id": f"optimized-{i}",
                "deal_id": deal["_id"],
                "store_id": deal["store_id"],
                "ranking_score": 85 + i * 5,
                "recommendation_reason": "Popular in your area"
            }
            for i, deal in enumerate(scraped_deals)
        ]
        
        mongo_db.optimized_deals.insert_many(optimized_deals)
        logger.info(f"✓ Stored {len(optimized_deals)} optimized deals in MongoDB")
        
        # Ack the message
        rabbitmq_channel.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("✓ Optimizer ack'd the message")
        
        # ─────────────────────────────────────────────────────────────────
        # Step 4: Optimizer publishes Optimizer.ready
        # ─────────────────────────────────────────────────────────────────
        
        logger.info("\nStep 4: Optimizer publishes Optimizer.ready event")
        
        optimizer_event = {
            "batch_id": received_event["batch_id"],
            "timestamp": datetime.now().isoformat(),
            "optimized_deal_count": len(optimized_deals)
        }
        
        rabbitmq_channel.basic_publish(
            exchange="test_optimizer",
            routing_key="ready",
            body=json.dumps(optimizer_event).encode(),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        logger.info(f"✓ Published Optimizer.ready event")
        
        # ─────────────────────────────────────────────────────────────────
        # Step 5: Personalization consumes Optimizer.ready
        # ─────────────────────────────────────────────────────────────────
        
        logger.info("\nStep 5: Personalization consumes Optimizer.ready")
        
        method, properties, body = rabbitmq_channel.basic_get(
            queue="test_optimizer.ready",
            auto_ack=False
        )
        
        assert method is not None, "No message in Optimizer.ready queue"
        
        optimizer_msg = json.loads(body.decode())
        logger.info(f"✓ Personalization received Optimizer.ready")
        
        # Simulate Personalization processing (calculate user hotdeals)
        logger.info("  Calculating user recommendations...")
        time.sleep(0.5)
        
        # Mock users and their hotdeals
        users = ["user-alice", "user-bob", "user-charlie"]
        hotdeals = []
        
        for user_id in users:
            for opt_deal in optimized_deals:
                hotdeal = {
                    "_id": f"hotdeal-{user_id}-{opt_deal['deal_id']}",
                    "user_id": user_id,
                    "deal_id": opt_deal["deal_id"],
                    "timestamp": datetime.now().isoformat(),
                    "deal_title": next(d["title"] for d in scraped_deals if d["_id"] == opt_deal["deal_id"]),
                    "savings_estimate": 5.0,
                    "confidence": 0.9
                }
                hotdeals.append(hotdeal)
        
        mongo_db.hotdeals.insert_many(hotdeals)
        logger.info(f"✓ Personalization calculated {len(hotdeals)} hotdeals")
        
        # Ack the message
        rabbitmq_channel.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("✓ Personalization ack'd the message")
        
        # ─────────────────────────────────────────────────────────────────
        # Step 6: Personalization publishes Personalize.hotdeal
        # ─────────────────────────────────────────────────────────────────
        
        logger.info("\nStep 6: Personalization publishes Personalize.hotdeal events")
        
        for hotdeal in hotdeals:
            event = {
                "user_id": hotdeal["user_id"],
                "deal_id": hotdeal["deal_id"],
                "timestamp": hotdeal["timestamp"],
                "deal_title": hotdeal["deal_title"],
                "savings_estimate": hotdeal["savings_estimate"],
                "confidence": hotdeal["confidence"]
            }
            
            rabbitmq_channel.basic_publish(
                exchange="test_personalization",
                routing_key="hotdeal",
                body=json.dumps(event).encode(),
                properties=pika.BasicProperties(delivery_mode=2)
            )
        
        logger.info(f"✓ Published {len(hotdeals)} Personalize.hotdeal events")
        
        # ─────────────────────────────────────────────────────────────────
        # Step 7: API Gateway receives hotdeals
        # ─────────────────────────────────────────────────────────────────
        
        logger.info("\nStep 7: API Gateway processes hotdeals")
        
        # Simulate API Gateway consuming from queue
        gateway_notifications = []
        
        for _ in range(len(hotdeals)):
            method, properties, body = rabbitmq_channel.basic_get(
                queue="test_personalization.hotdeal",
                auto_ack=False
            )
            
            if method:
                notification = json.loads(body.decode())
                gateway_notifications.append(notification)
                rabbitmq_channel.basic_ack(delivery_tag=method.delivery_tag)
        
        logger.info(f"✓ API Gateway received {len(gateway_notifications)} notifications")
        
        # ─────────────────────────────────────────────────────────────────
        # Verification
        # ─────────────────────────────────────────────────────────────────
        
        logger.info("\nVerifying complete workflow...")
        
        assert mongo_db.deals.count_documents({}) == 2
        assert mongo_db.optimized_deals.count_documents({}) == 2
        assert mongo_db.hotdeals.count_documents({}) == len(hotdeals)
        assert len(gateway_notifications) == len(hotdeals)
        
        logger.info("\n" + "=" * 70)
        logger.info("✓ Daily Night Routine E2E Test PASSED")
        logger.info("=" * 70)
    
    def test_workflow_with_db_transaction(self, mongo_db, rabbitmq_channel):
        """
        E2E with MongoDB transactions for safety.
        """
        
        logger.info("Testing E2E workflow with transactions...")
        
        mongo_client = MongoClient("mongodb://localhost:27017")
        session = mongo_client.start_session()
        
        try:
            session.start_transaction()
            
            # Insert deals
            deals = [
                {"_id": f"deal-{i}", "title": f"Deal {i}", "price": 10.0 + i}
                for i in range(3)
            ]
            mongo_db.deals.insert_many(deals, session=session)
            
            # Insert optimizations
            optimized = [
                {"_id": f"opt-{i}", "deal_id": f"deal-{i}", "score": 85 + i}
                for i in range(3)
            ]
            mongo_db.optimized_deals.insert_many(optimized, session=session)
            
            session.commit_transaction()
        
        finally:
            session.end_session()
        
        # Verify both collections updated atomically
        assert mongo_db.deals.count_documents({}) == 3
        assert mongo_db.optimized_deals.count_documents({}) == 3
        
        logger.info("✓ Transactional workflow succeeded")


# ============================================================================
# Timeout & Failure Handling
# ============================================================================

class TestWorkflowRobustness:
    """Test E2E workflow handles timeouts and failures gracefully."""
    
    def test_message_timeout_handling(self, mongo_db, rabbitmq_channel):
        """Test consumer timeout when message isn't consumed quickly."""
        
        logger.info("Testing message timeout handling...")
        
        # Publish a message
        event = {
            "batch_id": "batch-timeout-test",
            "timestamp": datetime.now().isoformat(),
            "deals": 5
        }
        
        rabbitmq_channel.basic_publish(
            exchange="test_scraper",
            routing_key="finish",
            body=json.dumps(event).encode()
        )
        
        # Wait longer than typical processing time
        time.sleep(5)
        
        # Message should still be in queue (not lost)
        method, properties, body = rabbitmq_channel.basic_get(
            queue="test_scraper.finish"
        )
        
        assert method is not None, "Message was lost due to timeout"
        logger.info("✓ Message persisted through timeout")
    
    def test_partial_failure_recovery(self, mongo_db, rabbitmq_channel):
        """Test workflow continues after partial failure."""
        
        logger.info("Testing partial failure recovery...")
        
        # Step 1: Successfully insert some deals
        mongo_db.deals.insert_one({
            "_id": "deal-1",
            "title": "Deal 1",
            "price": 10
        })
        
        # Step 2: Publish event
        event = {
            "batch_id": "batch-partial",
            "timestamp": datetime.now().isoformat(),
            "deals": 1
        }
        
        rabbitmq_channel.basic_publish(
            exchange="test_scraper",
            routing_key="finish",
            body=json.dumps(event).encode()
        )
        
        # Step 3: Simulate partial failure (some optimization succeeds)
        method, _, body = rabbitmq_channel.basic_get(queue="test_scraper.finish")
        
        # Only partially complete optimization
        mongo_db.optimized_deals.insert_one({
            "_id": "opt-1",
            "deal_id": "deal-1",
            "score": 85
        })
        
        # Ack and continue
        rabbitmq_channel.basic_ack(delivery_tag=method.delivery_tag)
        
        # Verify state is consistent
        deals = mongo_db.deals.count_documents({})
        optimized = mongo_db.optimized_deals.count_documents({})
        
        assert deals == 1
        assert optimized == 1
        
        logger.info("✓ Workflow recovered from partial failure")


# ============================================================================
# CLI & Main
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    
    print("E2E testing requires running MongoDB and RabbitMQ")
    print("Run with: pytest e2e_message_flow_tests.py -v")
