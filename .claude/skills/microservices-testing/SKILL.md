---
name: microservices-testing
description: 'Test distributed systems across service boundaries. Use when: validating data contracts between Python/Node.js/C# services (Scraper ↔ Optimizer ↔ Personalization), testing MongoDB TTL and geospatial queries, simulating full Daily Night Routine workflows, or chaos-testing resilience.'
argument-hint: 'microservices-testing for contract, integration, e2e, or chaos test patterns'
user-invocable: true
---

# Comprehensive Testing Strategy for Microservices

Lessley's distributed architecture demands testing beyond traditional monolithic approaches. You must verify service contracts, database behavior, message flows, and resilience across multiple languages (Python, Node.js, C#) and failure modes.

## When to Use

- **Before integrating** Python Scraper with Node.js Optimizer: verify JSON payload contracts
- **Validating MongoDB logic**: confirm TTL indexes drop expired deals, geospatial queries work correctly
- **Testing the Daily Night Routine**: end-to-end workflow from Scraper.finish → Personalize.hotdeal
- **Resilience validation**: verify message safety when services crash and recover
- **Regression detection**: catch breaking changes in service APIs

---

## Layer 1: Contract Testing (Service Boundary Verification)

**Goal**: Ensure Python Scraper publishes exactly what Node.js Optimizer and Personalization expect.

### The Problem

```
Python Scraper publishes:
{
  "store_id": "store-123",
  "deals": [{"url": "...", "price": 99.99}]
}

Node.js Optimizer expects:
{
  "store_id": "store-123",
  "deals": [{"url": "...", "price": "99.99"}]  // ← STRING, not number!
}

Result: Type mismatch, silent data corruption
```

### Solution: Pact-Based Contract Testing

```python
# 1. Python Scraper defines its contract (what it publishes)
# 2. Node.js Optimizer defines its contract (what it consumes)
# 3. Verify they match before deployment
```

### Implementation

```python
# contract_tests.py: Verify Scraper output matches Optimizer input

def test_scraper_publishes_valid_deal_batch():
    """
    Scraper publishes Scraper.finish event.
    Verify structure matches Optimizer's consumer contract.
    """
    
    payload = {
        "batch_id": "batch-001",
        "timestamp": datetime.now().isoformat(),
        "scraped_deals": [
            {
                "url": "https://store.com/deal",
                "store_id": "store-123",
                "title": "50% off",
                "price": 99.99,       # ← Must be NUMBER
                "category": "food"
            }
        ]
    }
    
    # Verify schema matches Optimizer's contract
    validate_against_optimizer_schema(payload)
    
    # Publish and verify
    publish_to_rabbitmq("scraper.finish", payload)
    
    # Optimizer consumes and validates
    consumed = consume_from_rabbitmq("scraper.finish")
    assert consumed["scraped_deals"][0]["price"] == 99.99  # ← Not a string
```

### Complete Example

See [contract_tests.py](./scripts/contract_tests.py) for:
- Shared schema definitions (YAML)
- Python publisher validation
- Node.js consumer validation
- Mismatch detection and reporting

---

## Layer 2: Integration Testing (Database Logic)

**Goal**: Verify MongoDB operations work as designed (TTL, geospatial, transactions).

### The Problem

```
Assumptions made:
- TTL indexes drop deals older than 7 days
- Geospatial queries return correct radius
- Transactions roll back on error

Reality:
- TTL job didn't run (misconfigured)
- Radius calculation is off by 10%
- Transaction left partial data
```

### Solution: Database Integration Tests

```python
def test_ttl_index_removes_expired_deals():
    """Verify TTL index actually removes old deals."""
    
    # Insert a deal with old timestamp
    old_deal = {
        "_id": "deal-old",
        "expires_at": datetime.now() - timedelta(days=8),
        "title": "Very old deal"
    }
    db.deals.insert_one(old_deal)
    
    # TTL index should remove it within 60 seconds
    db.deals.create_index(
        [("expires_at", 1)],
        expireAfterSeconds=0
    )
    
    time.sleep(65)  # Wait for TTL job
    
    # Verify it's gone
    result = db.deals.find_one({"_id": "deal-old"})
    assert result is None, "TTL index failed to remove expired deal"
```

### Geospatial Test

```python
def test_geospatial_query_returns_nearby_stores():
    """Verify 2dsphere index returns correct radius."""
    
    # Create stores at known distances
    stores = [
        {
            "_id": "store-near",
            "location": {
                "type": "Point",
                "coordinates": [-73.97, 40.77]  # [lon, lat]
            }
        },
        {
            "_id": "store-far",
            "location": {
                "type": "Point",
                "coordinates": [-73.97, 40.87]  # ~11km north
            }
        }
    ]
    
    db.stores.insert_many(stores)
    db.stores.create_index([("location", "2dsphere")])
    
    # Query for stores within 5km
    results = list(db.stores.find({
        "location": {
            "$near": {
                "$geometry": {
                    "type": "Point",
                    "coordinates": [-73.97, 40.77]
                },
                "$maxDistance": 5000  # 5km in meters
            }
        }
    }))
    
    # Only near store should be returned
    assert len(results) == 1
    assert results[0]["_id"] == "store-near"
```

### Complete Example

See [integration_tests_mongodb.py](./scripts/integration_tests_mongodb.py) for:
- TTL index validation
- Geospatial radius accuracy
- Transaction rollback verification
- Index performance benchmarks

---

## Layer 3: End-to-End Message Flow Testing

**Goal**: Simulate the complete Daily Night Routine: Scraper finishes → Personalization consumes → Hotdeal published.

### The Workflow

```
1. Mock Scraper finishes job (insert deals into MongoDB)
2. Publish Scraper.finish event to RabbitMQ
3. Personalization service consumes Scraper.finish
4. Personalization recalculates user savings
5. Personalization publishes Personalize.hotdeal
6. Verify hotdeal reached API Gateway
```

### Implementation

```python
def test_full_daily_night_routine():
    """
    End-to-end: Scraper.finish → Personalization → Personalize.hotdeal
    """
    
    # Step 1: Mock scraped deals in MongoDB
    deals = [
        {
            "_id": "deal-1",
            "store_id": "store-123",
            "title": "50% coffee",
            "price": 2.50,
            "valid_until": datetime.now() + timedelta(days=7)
        }
    ]
    db.deals.insert_many(deals)
    
    # Step 2: Publish Scraper.finish event
    event = {
        "batch_id": "batch-night-001",
        "timestamp": datetime.now().isoformat(),
        "deals_scraped": 1,
        "status": "success"
    }
    
    rabbitmq_channel.basic_publish(
        exchange="scraper",
        routing_key="finish",
        body=json.dumps(event).encode()
    )
    
    # Step 3: Personalization consumes and processes
    # (In real test, this runs in background; we poll for result)
    
    time.sleep(2)  # Wait for processing
    
    # Step 4: Verify Personalize.hotdeal was published
    personalize_message = rabbitmq_channel.basic_get(
        queue="personalization.hotdeal"
    )
    
    assert personalize_message is not None
    payload = json.loads(personalize_message[2])
    
    assert payload["user_id"] in ["user-1", "user-2", ...]
    assert payload["deal_title"] == "50% coffee"
    assert payload["savings_estimate"] > 0
    
    # Step 5: Verify API Gateway received it
    # (Mock Gateway subscriber)
    gateway_received = list(db.gateway_notifications.find({
        "type": "hotdeal"
    }))
    
    assert len(gateway_received) > 0
```

### Complete Example

See [e2e_message_flow_tests.py](./scripts/e2e_message_flow_tests.py) for:
- Multi-service orchestration
- Message consumption verification
- Database state assertions
- Timeout and failure handling

---

## Layer 4: Chaos Testing (Resilience Verification)

**Goal**: Verify system survives deliberate failures without data loss.

### Scenarios

#### Scenario 1: Optimizer Crashes During Scrape

```python
def test_optimizer_crash_recovers_safely():
    """
    1. Start publishing Scraper events
    2. Optimizer crashes mid-stream
    3. Restart Optimizer
    4. Verify all events are consumed, no loss
    """
    
    # Step 1: Start publishing events
    for i in range(100):
        event = {"batch_id": f"batch-{i}", "deals": [...]}
        rabbitmq_channel.basic_publish(
            exchange="scraper",
            routing_key="finish",
            body=json.dumps(event).encode()
        )
    
    time.sleep(1)
    
    # Step 2: Kill Optimizer process
    optimizer_process.kill()
    
    # Verify messages are still in queue (not lost)
    queue_info = rabbitmq_channel.queue_declare(
        queue="optimizer.jobs",
        passive=True
    )
    unacked = queue_info.method.message_count
    
    assert unacked > 0, "Messages were lost!"
    
    # Step 3: Restart Optimizer
    optimizer_process = start_optimizer_service()
    
    time.sleep(5)  # Wait for recovery
    
    # Step 4: Verify all events processed
    processed_count = db.optimizer_processed_batches.count_documents({})
    
    assert processed_count == 100, f"Only {processed_count}/100 batches processed"
```

#### Scenario 2: MongoDB Connection Fails, Then Recovers

```python
def test_database_failure_recovery():
    """Verify system queues writes during DB outage."""
    
    # Start normal operation
    db.deals.insert_one({"_id": "deal-1", "price": 50})
    
    # Simulate DB connection failure
    mongodb_port = 27017
    block_port(mongodb_port)  # Network-level block
    
    # Try to write (should fail gracefully)
    try:
        db.deals.insert_one({"_id": "deal-2", "price": 60})
    except pymongo.errors.ServerSelectionTimeout:
        pass  # Expected
    
    # Restore connection
    unblock_port(mongodb_port)
    
    time.sleep(2)
    
    # Verify retry logic caught up
    deals = list(db.deals.find({"_id": {"$in": ["deal-1", "deal-2"]}}))
    assert len(deals) >= 1, "Writes were lost after recovery"
```

### Complete Example

See [chaos_tests.py](./scripts/chaos_tests.py) for:
- Service kill/restart patterns
- Network failure simulation
- Message queue overflow testing
- Data loss verification
- Recovery time measurement

---

## Test Organization

```
tests/
├── conftest.py                          # Shared fixtures
├── contract/
│   ├── scraper_to_optimizer.py         # Python → Node.js contracts
│   ├── scraper_to_personalization.py   # Python → Python contracts
│   └── schemas/                         # Shared schema definitions
├── integration/
│   ├── mongodb_ttl_tests.py
│   ├── mongodb_geo_tests.py
│   └── transaction_tests.py
├── e2e/
│   ├── daily_night_routine_tests.py
│   └── user_experience_flow_tests.py
├── chaos/
│   ├── optimizer_failure_tests.py
│   ├── database_failure_tests.py
│   └── network_failure_tests.py
└── conftest.py                          # Docker container fixtures
```

---

## Running Tests

### All Tests
```bash
pytest tests/ -v
```

### By Layer
```bash
pytest tests/contract/ -v     # Contract tests only
pytest tests/integration/ -v  # Database tests only
pytest tests/e2e/ -v         # Message flow tests only
pytest tests/chaos/ -v        # Resilience tests only
```

### With Coverage
```bash
pytest tests/ --cov=services --cov-report=html
```

---

## CI/CD Integration

### Pre-Deployment Checklist
- ✅ All contract tests pass (no schema mismatches)
- ✅ All integration tests pass (DB logic verified)
- ✅ E2E Daily Night Routine succeeds
- ✅ Chaos tests show recovery within SLA (recovery time < 30s)

### Example GitHub Actions
```yaml
- name: Run Contract Tests
  run: pytest tests/contract/ -v

- name: Run Integration Tests
  run: pytest tests/integration/ -v --cov

- name: Run E2E Tests
  run: pytest tests/e2e/ -v

- name: Run Chaos Tests
  run: pytest tests/chaos/ -v -x  # Stop on first failure
```

---

## Integration Checklist

- [ ] Contract test schemas defined (shared across services)
- [ ] Database tests verify TTL index behavior
- [ ] Geospatial queries tested at multiple radii
- [ ] E2E Daily Night Routine test automated
- [ ] Optimizer crash/recovery tested
- [ ] MongoDB failure/recovery tested
- [ ] Network partition tested (messages queue up safely)
- [ ] Message loss detection in place
- [ ] Recovery time measured and alerts set
- [ ] All tests pass in CI/CD before deployment

---

## Reference Docs

- [Contract Testing Guide](./references/contract-testing.md) — Pact patterns, schema versioning, cross-language validation
- [Integration Testing Guide](./references/integration-testing-mongodb.md) — TTL, geospatial, transactions, performance
- [E2E Testing Guide](./references/e2e-testing.md) — Orchestration, message flow, assertion patterns
- [Chaos Testing Guide](./references/chaos-testing.md) — Failure injection, observability, recovery SLA

---

## Related Skills

- **MongoDB Tuning**: For database queries being validated
- **RabbitMQ Resilience**: For message contract validation and recovery testing
- **Grafana Monitoring**: For observing test runs and chaos experiments
