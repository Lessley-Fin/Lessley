# Idempotency Patterns for Distributed Systems

## The Problem: Duplicate Message Delivery

In a distributed system, RabbitMQ can deliver the same message multiple times due to:

1. **Network blips**: Message delivered, ack sent, but ack gets lost. RabbitMQ resends.
2. **Broker restart**: Consumer acked, but broker crashed before persisting the ack. On recovery, message redelivers.
3. **Consumer crash + recovery**: Unacked message stays in queue, another instance picks it up.

**Without idempotency**: Duplicate messages create duplicate database records, confusing users and breaking business logic.

## Definition: Idempotency

**Idempotent operation**: Processing the same message 1 time or 100 times produces identical state.

```
f(x) = f(f(x)) = f(f(f(x))) = ...  (same final state)
```

---

## Strategy 1: Unique Identifier + Upsert

This is the **recommended pattern** for Lessley (Scraper, Personalization).

### Step 1: Extract or Generate Unique ID

Identify fields in the message that uniquely represent the work to be done.

**Example: Scraper Job**

```python
def generate_scrape_id(job_payload):
    """
    Unique ID for a scrape job: hash of (url, product_id, batch_date)
    
    Same job scraped on different dates = different IDs (desired).
    Same job re-delivered today = same ID (deduplicated).
    """
    stable_key = {
        "url": job_payload["url"],
        "product_id": job_payload["product_id"],
        "batch_date": job_payload["batch_date"],
    }
    import hashlib
    return hashlib.sha256(
        json.dumps(stable_key, sort_keys=True).encode()
    ).hexdigest()
```

**Example: Personalization Job**

```python
def generate_personalization_id(job_payload):
    """
    Unique ID for a user's personalized content.
    
    Same user, same content type, same day = same ID.
    Re-delivered within the same day = deduplicated.
    """
    stable_key = {
        "user_id": job_payload["user_id"],
        "content_type": job_payload["content_type"],
        "date": job_payload["date"],
    }
    import hashlib
    return hashlib.sha256(
        json.dumps(stable_key, sort_keys=True).encode()
    ).hexdigest()
```

**Key Principle**: Use fields that change when the work *actually* changes, exclude fields that change on every delivery (timestamps, queue metadata).

### Step 2: Upsert to Database

Use MongoDB's `update_one(..., upsert=True)` to insert-or-update in one atomic operation.

```python
def idempotent_upsert(db_collection, unique_id, scraped_data):
    """
    Insert new doc if ID doesn't exist.
    Update existing doc if ID exists.
    Either way, end state is the same.
    """
    db_collection.update_one(
        {"_id": unique_id},          # ← Filter: find by unique ID
        {"$set": scraped_data},       # ← Update: set all fields
        upsert=True                   # ← Upsert: insert if not found
    )
    # Result: always exactly one doc with that _id
```

### Step 3: Verify Idempotency in Tests

```python
def test_idempotent_duplicate_delivery(db, queue):
    """
    Publish the same job twice.
    Verify only one database record exists.
    """
    job_payload = {
        "url": "https://example.com/product/123",
        "product_id": "123",
        "batch_date": "2025-05-28",
    }
    
    # Publish twice
    publish_to_queue(queue, job_payload)
    publish_to_queue(queue, job_payload)
    
    # Process both messages
    consumer.process()
    consumer.process()
    
    # Verify: only one record in database
    unique_id = generate_scrape_id(job_payload)
    docs = list(db.deals.find({"_id": unique_id}))
    
    assert len(docs) == 1, "Expected 1 doc, got {len(docs)}"
    assert docs[0]["scraped_data"]["price"] == job_payload["price"]
```

---

## Strategy 2: Idempotency Key Header

Alternative pattern: Client provides an idempotency key in message metadata.

```python
# Publisher side
def publish_job(queue, job_payload, idempotency_key):
    queue.publish(
        body=job_payload,
        properties=pika.BasicProperties(
            correlation_id=idempotency_key,
            # ... other properties
        )
    )

# Consumer side
def on_message(ch, method, properties, body):
    idempotency_key = properties.correlation_id
    
    # Record this key as "processed"
    db.idempotent_log.update_one(
        {"_id": idempotency_key},
        {"$set": {"processed_at": datetime.now()}},
        upsert=True
    )
    
    # Check if already processed
    if db.idempotent_log.find_one({"_id": idempotency_key, "result": {"$exists": True}}):
        logger.info(f"Duplicate detected: {idempotency_key}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return
    
    # Process...
    result = do_work(body)
    
    # Store result
    db.idempotent_log.update_one(
        {"_id": idempotency_key},
        {"$set": {"result": result}}
    )
    
    ch.basic_ack(delivery_tag=method.delivery_tag)
```

**Pros**: Works for any job type, explicit tracking.
**Cons**: Requires extra database collection, more overhead.

---

## Strategy 3: Conditional Inserts with Database Constraints

Use database uniqueness constraints to prevent duplicates at the database level.

```python
# MongoDB schema with unique constraint
db.create_collection("deals", validator={
    "bsonType": "object",
    "properties": {
        "_id": {"bsonType": "string"},  # unique_id from payload
        "url": {"bsonType": "string"},
        "product_id": {"bsonType": "string"},
        "price": {"bsonType": "double"},
    }
})

# Create unique index
db.deals.create_index([("url", 1), ("product_id", 1)], unique=True)

# Consumer tries to insert; if duplicate, exception is caught
def on_message(ch, method, properties, body):
    try:
        result = process_payload(body)
        db.deals.insert_one(result)  # ← Throws DuplicateKeyError if exists
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except pymongo.errors.DuplicateKeyError:
        logger.info("Duplicate message, skipping insert")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
```

**Pros**: Simple, leverages database constraints.
**Cons**: Less flexible (can't update existing records), requires careful index design.

---

## Strategy 4: Event Sourcing (Advanced)

Store every message event immutably, then build projections from events.

```python
# Store every message delivery
db.events.insert_one({
    "event_id": unique_id,
    "message_hash": hash(payload),
    "timestamp": datetime.now(),
    "worker": hostname,
    "status": "success"
})

# Projection: build read-friendly "deals" view from events
def rebuild_deals_projection():
    events = db.events.find({"event_type": "scrape_completed"})
    for event in events:
        deal_id = event["deal_id"]
        latest_event = db.events.find_one(
            {"deal_id": deal_id},
            sort=[("timestamp", -1)]
        )
        db.deals.update_one(
            {"_id": deal_id},
            {"$set": latest_event["data"]},
            upsert=True
        )
```

**Pros**: Complete audit trail, flexible rebuilding.
**Cons**: Complex, slower (extra read phase).

---

## Choosing the Right Strategy

| Strategy | Use Case | Complexity | Storage |
|----------|----------|-----------|---------|
| **Unique ID + Upsert** | Standard jobs (Scraper, Personalization) | Low | Low |
| **Idempotency Key** | External API integration, high audit requirement | Medium | Medium |
| **Constraint-based** | Simple inserts, no updates | Low | Low |
| **Event Sourcing** | Complex domain, need full history, advanced | High | High |

**Lessley Recommendation**: Use **Strategy 1 (Unique ID + Upsert)** for Scraper and Personalization workers.

---

## Monitoring Idempotency

### Deduplicated Message Rate

```
rate(lessley_idempotent_duplicates_total[5m])
```

Expected: Low deduplication rate (~1-5%) unless broker is restarting frequently.

### Alert Rules

```yaml
- alert: HighDuplicationRate
  expr: rate(lessley_idempotent_duplicates_total[5m]) > 0.1
  for: 10m
  annotations:
    summary: "High message duplication detected ({{ $value }}/sec)"
    hint: "Check RabbitMQ stability and broker logs"
```

---

## Testing Idempotency

```python
import pytest

@pytest.mark.parametrize("delivery_count", [1, 5, 10, 100])
def test_multiple_deliveries(db, queue, delivery_count):
    """Verify identical result after N duplicate deliveries."""
    
    job = {
        "url": "https://store.example.com/item/abc",
        "product_id": "abc",
        "price": 99.99,
    }
    
    unique_id = generate_id(job)
    
    # Publish and process N times
    for _ in range(delivery_count):
        publish_to_queue(queue, job)
        consumer.process()
    
    # Verify: exactly one record with correct data
    doc = db.deals.find_one({"_id": unique_id})
    assert doc is not None
    assert doc["price"] == 99.99
    assert len(list(db.deals.find({"_id": unique_id}))) == 1
```

---

## References

- [MongoDB Upsert Documentation](https://docs.mongodb.com/manual/reference/method/db.collection.updateOne/)
- [Idempotency Best Practices](https://www.stripe.com/blog/idempotency)
- [Event Sourcing Pattern](https://martinfowler.com/eaaDev/EventSourcing.html)
