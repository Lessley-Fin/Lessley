# Dead Letter Exchange (DLX) Setup & Configuration

## Overview

A Dead Letter Exchange (DLX) is an automatic routing mechanism that isolates messages that cannot be processed. When a consumer calls `basic_nack(..., requeue=False)`, the message is routed to the DLX instead of being re-queued, preventing poisoned messages from clogging the main queue.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Main Queue: scraper.jobs                                        │
│ (consumer processes messages, publishes ack/nack)               │
└─────────┬───────────────────────────────────────────────────────┘
          │
          ├─ ack → message removed from queue (success)
          │
          ├─ nack(requeue=True) → message goes back to end of queue
          │
          └─ nack(requeue=False) → message sent to DLX
                                     │
                ┌────────────────────┴──────────────┐
                │                                   │
        ┌───────▼──────────────┐        ┌───────────▼──────────┐
        │ DLX Exchange         │        │ DLX Queue            │
        │ (dlx.scraper.jobs)   │──────→ │ (dlx.scraper.jobs)   │
        └──────────────────────┘        │                      │
                                        │ (messages remain     │
                                        │  until manually      │
                                        │  inspected/handled)  │
                                        └──────────────────────┘
                                                    │
                                                    │
                                            (offline inspection)
                                        (reprocess, log, alert)
```

---

## Configuration in Docker & Docker Compose

### RabbitMQ with DLX Support

**Dockerfile** (lessley-cd/Dockerfile or similar):

```dockerfile
FROM rabbitmq:3.12-management-alpine

# Enable management plugin for dashboard
RUN rabbitmq-plugins enable rabbitmq_management

# Optional: Set default user
ENV RABBITMQ_DEFAULT_USER=rabbitmq
ENV RABBITMQ_DEFAULT_PASS=secretpassword

EXPOSE 5672 15672
```

### docker-compose.yaml

```yaml
version: "3.8"

services:
  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    container_name: lessley-rabbitmq
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER:-rabbitmq}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD:-rabbitmq}
    ports:
      - "5672:5672"    # AMQP port
      - "15672:15672"  # Management UI
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
      - ./rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf:ro

volumes:
  rabbitmq_data:
```

---

## Queue & Exchange Declarations

### Programmatic Setup (Consumer Startup)

```python
import pika

def setup_dlx(channel: pika.adapters.blocking_connection.BlockingChannel):
    """
    Declare main queue, DLX, and routing.
    
    Idempotent: Safe to call multiple times.
    """
    
    # ─────────────────────────────────────────────────────────────
    # 1. Declare DLX Exchange (where poisoned messages go)
    # ─────────────────────────────────────────────────────────────
    
    channel.exchange_declare(
        exchange="dlx.scraper",      # DLX exchange name
        exchange_type="direct",      # Use "direct" for 1-to-1 routing
        durable=True,                # Persist across restarts
        auto_delete=False,           # Don't auto-delete
    )
    
    # ─────────────────────────────────────────────────────────────
    # 2. Declare DLX Queue (holds poisoned messages)
    # ─────────────────────────────────────────────────────────────
    
    channel.queue_declare(
        queue="dlx.scraper.jobs",    # DLX queue name
        durable=True,
        auto_delete=False,
        arguments={
            # Optional: expire messages after 7 days
            "x-message-ttl": 7 * 24 * 60 * 60 * 1000,  # milliseconds
        }
    )
    
    # ─────────────────────────────────────────────────────────────
    # 3. Bind DLX Queue to DLX Exchange
    # ─────────────────────────────────────────────────────────────
    
    channel.queue_bind(
        queue="dlx.scraper.jobs",
        exchange="dlx.scraper",
        routing_key="jobs",          # Routing key
    )
    
    # ─────────────────────────────────────────────────────────────
    # 4. Declare Main Exchange
    # ─────────────────────────────────────────────────────────────
    
    channel.exchange_declare(
        exchange="scraper",
        exchange_type="direct",
        durable=True,
        auto_delete=False,
    )
    
    # ─────────────────────────────────────────────────────────────
    # 5. Declare Main Queue (with DLX configured)
    # ─────────────────────────────────────────────────────────────
    
    channel.queue_declare(
        queue="scraper.jobs",
        durable=True,
        auto_delete=False,
        arguments={
            # ← Configure the DLX
            "x-dead-letter-exchange": "dlx.scraper",  # Route nacked msgs here
            "x-dead-letter-routing-key": "jobs",      # With this routing key
            
            # Optional: expire messages after 24 hours (TTL)
            "x-message-ttl": 24 * 60 * 60 * 1000,
            
            # Optional: max message count
            "x-max-length": 100000,
        }
    )
    
    # ─────────────────────────────────────────────────────────────
    # 6. Bind Main Queue to Main Exchange
    # ─────────────────────────────────────────────────────────────
    
    channel.queue_bind(
        queue="scraper.jobs",
        exchange="scraper",
        routing_key="jobs",
    )
    
    print("DLX configured: scraper.jobs → dlx.scraper → dlx.scraper.jobs")
```

---

## Consumer Implementation

### Reject Logic

```python
def on_message(ch, method, properties, body):
    delivery_tag = method.delivery_tag
    
    try:
        # Validate payload
        payload = json.loads(body.decode('utf-8'))
    except json.JSONDecodeError as e:
        logger.error(f"Malformed JSON in message: {e}")
        # Nack without requeue → routes to DLX
        ch.basic_nack(delivery_tag=delivery_tag, requeue=False)
        return
    
    try:
        # Validate schema
        validate_scraper_schema(payload)
    except ValueError as e:
        logger.error(f"Invalid schema: {e}")
        # Nack without requeue → routes to DLX
        ch.basic_nack(delivery_tag=delivery_tag, requeue=False)
        return
    
    try:
        # Process
        result = scrape(payload)
        mongodb.insert(result)
        ch.basic_ack(delivery_tag=delivery_tag)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        # Nack with requeue → back to main queue
        ch.basic_nack(delivery_tag=delivery_tag, requeue=True)
```

---

## Inspection & Recovery

### View Messages in DLX Queue

```python
from pika import BlockingConnection, ConnectionParameters, BasicProperties

def inspect_dlx_queue(rabbitmq_host: str, queue_name: str = "dlx.scraper.jobs"):
    """
    Non-destructive: peek at messages without consuming them.
    """
    conn = BlockingConnection(ConnectionParameters(host=rabbitmq_host))
    channel = conn.channel()
    
    # Passive declaration (don't create, just check)
    queue_info = channel.queue_declare(queue=queue_name, passive=True)
    
    print(f"DLX Queue: {queue_name}")
    print(f"  Message count: {queue_info.method.message_count}")
    print(f"  Consumer count: {queue_info.method.consumer_count}")
    
    # Get first message WITHOUT consuming (ack=False keeps it in queue)
    method, properties, body = channel.basic_get(queue=queue_name, auto_ack=False)
    
    if method:
        print(f"\nFirst message in DLX:")
        print(f"  Delivery tag: {method.delivery_tag}")
        print(f"  Redelivered: {method.redelivered}")
        print(f"  Content-Type: {properties.content_type}")
        print(f"  Body: {body.decode('utf-8', errors='replace')}")
        
        # Return the message to the queue (don't ack or nack)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    else:
        print("DLX queue is empty")
    
    conn.close()
```

### Reprocess Messages from DLX

```python
def reprocess_dlx_message(rabbitmq_host: str, queue_name: str = "dlx.scraper.jobs"):
    """
    After fixing the issue, reprocess messages from DLX.
    """
    conn = BlockingConnection(ConnectionParameters(host=rabbitmq_host))
    channel = conn.channel()
    
    method, properties, body = channel.basic_get(queue=queue_name, auto_ack=False)
    
    if method:
        # Republish to main queue
        channel.basic_publish(
            exchange="scraper",
            routing_key="jobs",
            body=body,
            properties=BasicProperties(
                content_type=properties.content_type,
                delivery_mode=2,  # Persistent
            )
        )
        
        # Ack the DLX message (remove from DLX)
        channel.basic_ack(delivery_tag=method.delivery_tag)
        
        print(f"Message republished to main queue")
    
    conn.close()
```

---

## Grafana Monitoring

### Dashboard Setup

Create a Grafana panel with the following PromQL query to monitor DLX queue depth:

```promql
rabbitmq_queue_messages_unacked{queue="dlx.scraper.jobs"}
+ rabbitmq_queue_messages_ready{queue="dlx.scraper.jobs"}
```

This sums unacked + ready messages in the DLX queue.

### Alert Rules

```yaml
groups:
  - name: lessley_dlx_alerts
    rules:
      - alert: DLXQueueNotEmpty
        expr: |
          (
            rabbitmq_queue_messages_unacked{queue=~"dlx\\..*"}
            + rabbitmq_queue_messages_ready{queue=~"dlx\\..*"}
          ) > 0
        for: 5m
        annotations:
          summary: "DLX queue {{ $labels.queue }} has messages"
          description: |
            Dead Letter Queue detected messages.
            Check logs for schema changes in upstream services.
          runbook: "https://wiki.lessley.local/dlx-runbook"
      
      - alert: DLXQueueAccumulating
        expr: |
          rate(
            rabbitmq_queue_messages_ready{queue=~"dlx\\..*"}[5m]
          ) > 0.1
        for: 30m
        annotations:
          summary: "DLX queue {{ $labels.queue }} is accumulating (>0.1 msgs/sec)"
          description: "Sustained failure rate in poison message handling"
```

---

## RabbitMQ Management UI

### Access Dashboard

- **URL**: `http://localhost:15672`
- **Username**: `rabbitmq`
- **Password**: `rabbitmq` (or from env var)

### Inspect Queues

1. Click **Queues** tab
2. Find `dlx.scraper.jobs`
3. View message count, consumer info
4. Click queue name for details:
   - Message rate (in/out)
   - Bindings
   - Purge option (delete all messages, caution!)

### Republish from Management UI

1. Go to queue details
2. Click **Get messages** (with auto-ack disabled)
3. Copy message body
4. Click **Publish message** on main exchange
5. Paste body, publish

---

## Typical Failure Scenarios & Solutions

### Scenario 1: Retail Website Changed DOM Structure

**Symptom**: All messages in DLX queue with "XPath not found" errors.

```
dlx.scraper.jobs: 50 messages
```

**Solution**:

1. Inspect DLX messages to identify the DOM change
2. Update XPath/CSS selector in Scraper code
3. Deploy new version
4. Reprocess DLX messages:

```python
reprocess_dlx_message("rabbitmq-host", "dlx.scraper.jobs")
```

### Scenario 2: Schema Mismatch After Upgrade

**Symptom**: Publisher upgraded and sends new field format. Consumers haven't deployed yet.

**Solution**:

1. Update consumer schema validation to accept both old and new formats
2. Deploy consumer
3. Reprocess DLX

### Scenario 3: DLX Queue Fills Up

**Symptom**: DLX queue has thousands of messages, not being inspected.

**Prevention**:

- Set up Grafana alerts to notify when DLX > 100 messages
- Configure TTL (`x-message-ttl`) to auto-expire old DLX messages
- Schedule weekly DLX queue review

---

## Environment Variables

```bash
# .env or deploy config
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=rabbitmq
RABBITMQ_PASSWORD=secretpass

# DLX Configuration
RABBITMQ_DLX_EXCHANGE=dlx.scraper
RABBITMQ_DLX_QUEUE=dlx.scraper.jobs
RABBITMQ_MAIN_EXCHANGE=scraper
RABBITMQ_MAIN_QUEUE=scraper.jobs

# Message TTL (milliseconds)
RABBITMQ_MESSAGE_TTL=86400000  # 24 hours
RABBITMQ_DLX_MESSAGE_TTL=604800000  # 7 days

# QoS
RABBITMQ_PREFETCH_COUNT=10
```

---

## References

- [RabbitMQ Dead Letter Exchange Docs](https://www.rabbitmq.com/docs/dlx)
- [Pika Queue Declare Arguments](https://pika.readthedocs.io/en/stable/modules/adapters/blocking_connection.html#pika.adapters.blocking_connection.BlockingChannel.queue_declare)
- [RabbitMQ Management Plugin](https://www.rabbitmq.com/docs/management)
- [Prometheus RabbitMQ Exporter](https://github.com/prometheus-community/rabbitmq_exporter)
