# RabbitMQ Message Acknowledgments: Ack/Nack Lifecycle

## Overview

RabbitMQ uses acknowledgments to guarantee message delivery. When a consumer receives a message, it must signal back to the broker that processing succeeded (ack) or failed (nack). Without this feedback, RabbitMQ doesn't know whether to mark the message as delivered or redeliver it.

## Key Concepts

### Auto-Acknowledge vs. Manual Acknowledge

| Mode | Setting | Behavior | When to Use |
|------|---------|----------|------------|
| **Auto-Ack** | `auto_ack=True` | Consumer acks immediately upon receipt (before processing) | ❌ **Never** for critical systems—data loss risk |
| **Manual Ack** | `auto_ack=False` | Consumer explicitly calls `basic_ack()` after success | ✅ **Always** for distributed workers |

### Why Manual Ack is Essential

1. **Crash Recovery**: If worker dies mid-task, the connection drops. Unacked messages automatically re-queue.
2. **Atomicity**: The consumer controls *when* the ack is sent—only after safely committing to persistent storage (MongoDB).
3. **Retry Logic**: Failed messages don't disappear; they stay in the queue for another worker.

## Message Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. Message in Queue (undelivered)                                   │
│    RabbitMQ: "Waiting to send this to a worker"                     │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ├─ Worker connects with auto_ack=False
                 │
┌────────────────▼────────────────────────────────────────────────────┐
│ 2. Message Delivered to Consumer (unacked)                          │
│    RabbitMQ: "Sent to worker. If no ack in N seconds, redeliver"    │
│    MongoDB: (not yet written)                                        │
└────────────────┬────────────────────────────────────────────────────┘
                 │
         ┌───────┴────────┐
         │                │
    HAPPY PATH        CRASH SCENARIO
    (normal flow)     (failure case)
         │                │
    [Process OK]      [Process Fails]
    [DB Commit]       [Crash/OOM/Exception]
         │                │
    ┌────▼────┐      ┌────▼────────────────┐
    │ ack()   │      │ Connection drops    │
    └────┬────┘      │ (no ack ever sent)  │
         │           └────┬────────────────┘
         │                │
    ┌────▼──────────────────────────────────┐
    │ 3. Consumer Notifies RabbitMQ          │
    │ - ack: "Success, remove from queue"   │
    │ - nack: "Failed, requeue or DLX"      │
    └────┬──────────────────────────────────┘
         │
    ┌────▼──────────────────┐
    │ 4. Message Terminal   │
    │ State (delivered,     │
    │ requeued, or          │
    │ dead-lettered)        │
    └───────────────────────┘
```

## Acknowledgment Types

### 1. Basic Ack (Success)

```python
channel.basic_ack(delivery_tag=method.delivery_tag)
```

**Semantics**:
- Consumer signals: "I successfully processed this message"
- RabbitMQ action: Remove message from queue (no retry)
- MongoDB: Must have committed before ack

**Timing**:
- Call ONLY after persistent storage confirms write
- Example: After `mongodb.insert_one()` returns without error

---

### 2. Basic Nack with Requeue=True (Retryable Error)

```python
channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
```

**Semantics**:
- Consumer signals: "I failed, but another worker might succeed"
- RabbitMQ action: Requeue message to end of queue (or dead letter if prefetch is high)
- Use case: Temporary errors (network timeout, DB connection loss)

**Retry Behavior**:
- Message goes back to queue with delivery_count += 1
- Another worker consumes it
- If all workers consistently fail, the queue backs up (alert in Grafana)

---

### 3. Basic Nack with Requeue=False (Dead Letter Exchange)

```python
channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
```

**Semantics**:
- Consumer signals: "This message is poisoned; don't retry"
- RabbitMQ action: Route to Dead Letter Exchange (DLX) for isolation
- Use case: Permanent errors (malformed JSON, invalid structure)

**DLX Routing**:
- Message bypasses main queue
- Lands in `dlx.poisoned` queue (configured at infrastructure level)
- Operator inspects failed message later (debugging)

---

## Practical Example: Error Handling

```python
def on_message(ch, method, properties, body):
    delivery_tag = method.delivery_tag
    
    try:
        # 1. Parse and validate
        payload = json.loads(body)
        validate_schema(payload)
        
        # 2. Process
        result = process_job(payload)
        
        # 3. Commit to persistent storage
        db.collection.insert_one(result)
        
        # 4. Acknowledge success
        ch.basic_ack(delivery_tag=delivery_tag)
        logger.info("Message ack'd")
    
    except json.JSONDecodeError as e:
        # Malformed JSON: permanent error
        logger.error(f"Invalid JSON: {e}")
        ch.basic_nack(delivery_tag=delivery_tag, requeue=False)
        # → Routes to DLX
    
    except ValueError as e:
        # Schema validation: permanent error
        logger.error(f"Invalid schema: {e}")
        ch.basic_nack(delivery_tag=delivery_tag, requeue=False)
        # → Routes to DLX
    
    except pymongo.errors.ServerSelectionTimeout as e:
        # Database unavailable: temporary error
        logger.error(f"DB connection timeout: {e}")
        ch.basic_nack(delivery_tag=delivery_tag, requeue=True)
        # → Requeue to main queue
    
    except Exception as e:
        # Unexpected error: assume retryable
        logger.error(f"Unexpected error: {e}", exc_info=True)
        ch.basic_nack(delivery_tag=delivery_tag, requeue=True)
        # → Requeue to main queue
```

---

## QoS (Quality of Service)

### Prefetch Count

```python
channel.basic_qos(prefetch_count=10)
```

**Meaning**:
- Worker can hold max 10 unacked messages at a time
- After acking one, RabbitMQ delivers the next

**Tuning**:
- `prefetch_count=1`: Conservative, processes one message at a time (slow but safe)
- `prefetch_count=10`: Balanced, handles multiple messages without overwhelming
- `prefetch_count=100`: Aggressive, high throughput but risky if crashes are frequent

**Interaction with Nack**:
- If all 10 messages are stuck waiting for ack/nack, RabbitMQ stops delivering
- Use `basic_nack(..., requeue=True)` to unblock the queue

---

## Monitoring: Unacked Message Count

### Grafana Dashboard Query

```
rabbitmq_queue_messages_unacked{queue="scraper.jobs"}
```

**What It Means**:
- Count of messages delivered but not yet ack'd/nack'd
- If this grows over time → workers are slow or crashing
- If this stays at 0 → all messages are ack'd quickly (good)

### Alert Rules

```yaml
- alert: UnackedMessagesAccumulating
  expr: rabbitmq_queue_messages_unacked > 1000
  for: 5m
  annotations:
    summary: "Queue {{ $labels.queue }} has {{ $value }} unacked messages"
```

---

## Common Mistakes

### ❌ Mistake 1: Auto-Ack in Production

```python
# BAD: Never do this for critical systems
channel.basic_consume(
    queue=config.queue_name,
    auto_ack=True,  # ← Ack happens immediately, before processing
    on_message_callback=callback
)
```

**Why it fails**: If callback crashes after ack, message is lost forever.

---

### ❌ Mistake 2: Ack Before Commit

```python
# BAD: Message appears delivered, but data isn't in DB yet
def process(ch, method, properties, body):
    result = parse_message(body)
    ch.basic_ack(delivery_tag=method.delivery_tag)  # ← ACK TOO EARLY!
    
    db.insert(result)  # ← Crash here → data lost, message gone
```

**Why it fails**: RabbitMQ considers message gone, but database never received it.

---

### ✅ Correct Pattern

```python
# GOOD: Ack only after successful commit
def process(ch, method, properties, body):
    result = parse_message(body)
    
    db.insert(result)  # ← Commit first
    
    ch.basic_ack(delivery_tag=method.delivery_tag)  # ← Ack last
    # If crash happens before this line, DB commit is undone
    # (or if using transactions, the whole operation is atomic)
```

---

## References

- [RabbitMQ Consumer Acknowledgments](https://www.rabbitmq.com/docs/confirms)
- [RabbitMQ Dead Letter Exchanges](https://www.rabbitmq.com/docs/dlx)
- [Pika Python: Basic Consume](https://pika.readthedocs.io/en/stable/modules/adapters/blocking.html)
