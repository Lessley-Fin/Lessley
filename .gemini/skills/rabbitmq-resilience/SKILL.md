---
name: rabbitmq-resilience
description: 'Implement fault-tolerant RabbitMQ consumers for distributed systems. Use when: building Python workers (Scraper, Personalization) that must survive crashes, handle duplicate messages, and gracefully reject malformed payloads without data loss.'
argument-hint: 'rabbitmq-resilience for consumer pattern guidance'
user-invocable: true
---

# Advanced Event-Driven Architecture: RabbitMQ Resilience

Building a distributed system means preparing for failure. This skill covers three critical patterns for implementing robust RabbitMQ consumers in Python that prevent data loss, avoid infinite loops, and safely isolate poisoned messages.

## When to Use

- Implementing new worker services (Scraper, Personalization consumers)
- Debugging message loss or duplicate processing in existing workers
- Setting up Dead Letter Exchanges (DLX) for failed jobs
- Ensuring idempotency across service restarts
- Handling network blips and broker restarts gracefully

## Core Patterns at a Glance

| Pattern | Problem | Solution |
|---------|---------|----------|
| **Manual Ack/Nack** | Process crash loses unacknowledged messages | Only ack after successful DB commit; message re-queues on crash |
| **Idempotency** | Network blips deliver duplicate messages | Use unique identifiers + upsert to deduplicate safely |
| **Dead Letter Exchange** | Poisoned (malformed) messages clog the queue | Nack with requeue=False → DLX routes to isolated queue |

---

## Pattern 1: Manual Acknowledgments (Ack/Nack)

**Goal**: Ensure RabbitMQ re-queues messages if the worker crashes before processing completes.

### Implementation Steps

1. **Disable auto-acknowledge in consumer setup**
   - Set `auto_ack=False` (default) when creating the channel and binding the consumer
   - This forces explicit ack/nack after each message

2. **Process the message and commit to MongoDB atomically**
   - Parse and validate the payload
   - Perform business logic (e.g., scrape data, enrich records)
   - Write results to MongoDB in a single transaction

3. **Send acknowledgment only after successful commit**
   ```python
   try:
       result = process_message(payload)
       mongodb.insert_or_update(result)  # Commit to DB
       channel.basic_ack(delivery_tag=method.delivery_tag)
   except Exception as e:
       channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
   ```

4. **Monitor for unacknowledged messages in Grafana**
   - Track queue depth and consumer status
   - Alert if unacked messages accumulate (indicates stalled workers)

**Result**: If the Python process dies mid-task, the connection drops, and RabbitMQ assumes the message failed. It automatically re-queues for another available worker—no manual recovery needed.

---

## Pattern 2: Idempotency (Repeated Messages)

**Goal**: Process the same message twice and get the same state as processing it once.

### Implementation Steps

1. **Extract or generate a unique identifier for the payload**
   - Hash the message content (e.g., deal ID, scraper URL, batch hash)
   - Store this as a unique constraint or document ID in MongoDB

2. **Use MongoDB upsert to deduplicate**
   ```python
   unique_id = hash_payload(payload)
   result = {
       "_id": unique_id,
       "data": parse_payload(payload),
       "processed_at": datetime.now(),
   }
   mongodb.deals.update_one(
       {"_id": unique_id},
       {"$set": result},
       upsert=True
   )
   channel.basic_ack(delivery_tag=method.delivery_tag)
   ```

3. **Test with intentional duplicates**
   - Publish the same message to the queue twice
   - Verify MongoDB contains exactly one record (not two)
   - Confirm both acks are processed cleanly

**Result**: Network blips or broker restarts re-deliver the same message, but your database sees it as an idempotent operation. The client UI shows one deal, not two duplicates.

---

## Pattern 3: Rejections & Dead Letter Exchanges (DLX)

**Goal**: Isolate permanently failed messages (malformed payloads, invalid JSON) without blocking the main pipeline.

### Implementation Steps

1. **Configure Dead Letter Exchange at infrastructure level**
   - Define in `docker-compose.yaml` or deployment environment variables:
     ```yaml
     RABBITMQ_DLX_EXCHANGE: "dlx.main"
     RABBITMQ_DLX_QUEUE: "dlx.poisoned"
     ```
   - Bind the main consumer queue with `x-dead-letter-exchange: dlx.main`

2. **Detect and reject malformed messages in consumer**
   - Validate JSON, DOM structure, required fields
   - If validation fails, nack with `requeue=False`:
     ```python
     try:
         payload = json.loads(msg)
         validate_structure(payload)
     except (json.JSONDecodeError, ValueError) as e:
         logger.error(f"Malformed payload: {e}")
         channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
         return
     ```

3. **Monitor DLX queue in Grafana**
   - Set up dashboard panel for `dlx.poisoned` queue depth
   - Create alert if DLX queue grows (indicates upstream format changes)

4. **Inspect failed messages offline**
   - Query `dlx.poisoned` queue (don't consume yet)
   - Extract payload, analyze why validation failed
   - Update consumer logic or notify the scraping team if the target site's DOM changed

**Result**: A single malformed message doesn't crash the worker or clog the main queue. It safely lands in the DLX for later inspection and remediation.

---

## Example: Complete Consumer Template

See [resilient_consumer.py](./scripts/resilient_consumer.py) for a full working example combining all three patterns.

Key code sections:
- Callback with manual ack/nack
- Idempotent upsert logic
- Malformed message rejection
- Structured logging context

---

## Integration Checklist

- [ ] Consumer uses `auto_ack=False`
- [ ] Message processing + DB commit wrapped in try/except
- [ ] Ack sent only after successful commit
- [ ] Unique identifier extracted from payload
- [ ] MongoDB upsert (not insert) for deduplication
- [ ] Malformed payloads trigger nack with `requeue=False`
- [ ] DLX queue configured at infrastructure level
- [ ] Grafana dashboards monitor queue depth and DLX
- [ ] Logging includes correlation ID and structured context

---

## Reference Docs

- [RabbitMQ Message Acknowledgments](./references/rabbitmq-ack-nack.md) — Detailed semantics of ack/nack lifecycle
- [Idempotency Patterns](./references/idempotency-patterns.md) — Strategies for unique identifier generation and MongoDB upsert
- [Dead Letter Exchange Setup](./references/dlx-setup.md) — Infrastructure config examples and monitoring

---

## Related Skills

- **Python 3.13 Service Setup**: For venv, dependency management, and structured logging
- **Grafana Monitoring**: For dashboard creation and alerting on queue metrics
- **MongoDB Transactions**: For multi-document ACID guarantees in upserts
