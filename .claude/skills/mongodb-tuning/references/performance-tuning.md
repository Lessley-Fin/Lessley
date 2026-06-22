# MongoDB Performance Tuning: Profiling, Monitoring & Optimization

## Query Profiling: Find Slow Queries

### Enable Profiling

```python
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client.lessley

# Level 1: Profile slow queries (>100ms)
db.set_profiling_level(1, slow_ms=100)
```

**Profiling levels**:
- 0 = Off (no profiling)
- 1 = Log slow queries only
- 2 = Log all queries (production risk: performance overhead)

### Query the Profile Collection

```python
# Find all slow queries in the last hour
import time
from datetime import datetime, timedelta

one_hour_ago = time.time() - 3600

slow_queries = db.system.profile.find({
    "millis": {"$gt": 100},  # Queries slower than 100ms
    "ts": {"$gt": datetime.now() - timedelta(hours=1)}
}).sort("millis", -1)

for query in slow_queries:
    print(f"Query: {query.get('command', {})}")
    print(f"Duration: {query['millis']}ms")
    print(f"Docs examined: {query['nExamined']}")
    print(f"Docs returned: {query['nMatched']}")
    print()
```

### Efficiency Metric

```python
efficiency = nMatched / nExamined

# GOOD:   efficiency > 0.9  (90% of examined docs matched)
# OKAY:   efficiency > 0.5  (50% of examined docs matched)
# BAD:    efficiency < 0.1  (1% of examined docs matched) ← collection scan
```

---

## Explain: Deep Dive into Query Execution

### Basic Explain

```python
explain = db.deals.find({"store_id": "store-123"}).explain()

print(f"Stage: {explain['executionStats']['executionStages']['stage']}")
# COLLSCAN = collection scan (BAD)
# IXSCAN   = index scan (GOOD)
# COVERED  = index-only (BEST)

print(f"Docs examined: {explain['executionStats']['totalDocsExamined']}")
print(f"Docs returned: {explain['executionStats']['nReturned']}")
```

### Verbose Explain

```python
explain = db.deals.find({"store_id": "store-123"}).explain()

stages = explain['executionStats']['executionStages']

def print_stage(stage, indent=0):
    prefix = "  " * indent
    stage_name = stage.get('stage')
    print(f"{prefix}{stage_name}: {stage.get('nReturned', '?')} docs")
    
    if "executionStages" in stage:
        print_stage(stage["executionStages"], indent + 1)

print_stage(stages)
```

---

## Common Query Patterns & Optimization

### Pattern 1: Filtering by Store (Most Common)

```python
# Query
db.deals.find({"store_id": "store-123"})

# Without index: COLLSCAN (slow)
# With index:   IXSCAN (fast)

# Index needed:
db.deals.create_index([("store_id", 1)])
```

---

### Pattern 2: Active Deals for a Store

```python
# Query
db.deals.find({
    "store_id": "store-123",
    "valid_until": {"$gt": datetime.now()}
}).sort({"valid_until": -1})

# Compound index required:
db.deals.create_index([
    ("store_id", 1),
    ("valid_until", -1)
])
```

---

### Pattern 3: Nearby Stores

```python
# Query
db.stores.find({
    "location": {
        "$near": {
            "$geometry": {
                "type": "Point",
                "coordinates": [-73.97, 40.77]
            },
            "$maxDistance": 5000
        }
    }
})

# Geospatial index required:
db.stores.create_index([("location", "2dsphere")])
```

---

## Write Performance Tuning

### Bulk Insert Optimization

```python
from pymongo import InsertOne

# BAD: One insert at a time
for deal in deals:
    db.deals.insert_one(deal)  # 1000 round trips to database

# GOOD: Bulk insert
requests = [InsertOne(deal) for deal in deals]
db.deals.bulk_write(requests)  # 1 round trip
```

**Benefit**: 100-1000x faster for bulk operations.

---

### Batch Updates with Transactions

```python
from pymongo import UpdateOne

session = client.start_session()

try:
    session.start_transaction()
    
    requests = [
        UpdateOne(
            {"_id": deal_id},
            {"$set": {"processed": True}},
            session=session
        )
        for deal_id in deal_ids
    ]
    
    db.deals.bulk_write(requests)
    
    session.commit_transaction()
finally:
    session.end_session()
```

---

## Connection Pooling & Thread Safety

### Configure Connection Pool

```python
client = MongoClient(
    "mongodb://localhost:27017",
    maxPoolSize=50,      # Max connections to keep open
    minPoolSize=10,      # Min connections to maintain
    maxIdleTimeMS=60000  # Close idle connections after 60s
)
```

**Tuning**:
- `maxPoolSize=50`: For API Gateway serving 100s of concurrent requests
- `minPoolSize=10`: Keep warm connections ready
- `maxIdleTimeMS`: Balance memory vs connection re-creation overhead

### Thread-Safe Access

```python
# GOOD: Single client, shared across threads
client = MongoClient(...)
db = client.lessley

# In each thread:
deals = db.deals.find_one(...)  # Thread-safe

# BAD: Creating a new client per thread (connection leak!)
# Don't do this in a loop:
for _ in range(100):
    client = MongoClient(...)  # Leak!
```

---

## Server-Side Optimization

### Disable Profiling in Production

```python
db.set_profiling_level(0)  # Turn off profiling
```

Profiling has overhead; only enable for troubleshooting.

### Enable Compression

In MongoDB configuration:

```yaml
net:
  compression:
    compressors: snappy
```

Reduces network bandwidth for large documents.

### Cache Warm-Up

Pre-load frequently accessed indexes into memory:

```python
# Run this after database starts
db.deals.find({"store_id": "top-store"}).hint([("store_id", 1)]).limit(1000)
db.stores.find({}).hint([("location", "2dsphere")]).limit(100)
```

---

## Replica Set Replication Lag

### Monitor Replication Status

```python
status = client.admin.command("replSetGetStatus")

for member in status["members"]:
    print(f"Node: {member['name']}")
    print(f"  State: {member['stateStr']}")
    print(f"  Lag: {member.get('optimeDate', 'N/A')}")
```

### Optimize for Replica Lag

**Problem**: Secondary replicas lag, reads see stale data.

**Solution**: Use read preference

```python
from pymongo.read_preferences import ReadPreference

# Read from primary only (consistent, but slower)
db = client.get_database(read_preference=ReadPreference.PRIMARY)

# Read from secondary (faster, but potentially stale)
db = client.get_database(read_preference=ReadPreference.SECONDARY)

# Read from closest replica (fastest)
db = client.get_database(read_preference=ReadPreference.NEAREST)
```

---

## Grafana Monitoring

### Key Metrics

```promql
# Query latency
histogram_quantile(0.95, rate(mongodb_operation_latency_us_bucket[5m])) / 1000

# Throughput
rate(mongodb_op_counters_total[5m])

# Connection count
mongodb_connections{state="current"}

# Index efficiency
rate(mongodb_indexCounters_hits[5m]) / 
(rate(mongodb_indexCounters_hits[5m]) + rate(mongodb_indexCounters_misses[5m]))

# Collection scan rate (should be zero)
rate(mongodb_query_executor_scanned_objects[5m])

# Memory usage
mongodb_memory{type="resident"} / 1024 / 1024  # Convert to MB
```

### Alert Rules

```yaml
groups:
  - name: mongodb_alerts
    rules:
      - alert: SlowQueries
        expr: histogram_quantile(0.95, rate(mongodb_operation_latency_us_bucket[5m])) > 100000000  # 100ms
        for: 5m
        annotations:
          summary: "MongoDB p95 latency > 100ms"
      
      - alert: HighCollectionScanRate
        expr: rate(mongodb_query_executor_scanned_objects[5m]) > 1000
        for: 10m
        annotations:
          summary: "Collection scans detected (missing indexes)"
      
      - alert: LowIndexHitRate
        expr: |
          rate(mongodb_indexCounters_hits[5m]) /
          (rate(mongodb_indexCounters_hits[5m]) + rate(mongodb_indexCounters_misses[5m]))
          < 0.9
        for: 10m
        annotations:
          summary: "Index hit rate < 90%"
      
      - alert: ReplicationLag
        expr: mongodb_replication_lag_seconds > 10
        for: 5m
        annotations:
          summary: "Secondary replication lag > 10 seconds"
```

---

## Migration: Reshaping Data for Performance

### Scenario: Denormalization for Speed

**Problem**: Queries need to fetch user clubs + calculate savings (slow joins).

**Solution**: Denormalize into read-optimized format

```python
# Before: Normalized (requires joins)
users = {
    "_id": "user-123",
    "name": "Alice",
    "club_ids": ["club-1", "club-2"]
}

clubs = {
    "_id": "club-1",
    "name": "hever",
    "discount": 0.15
}

# After: Denormalized (query is fast)
users_optimized = {
    "_id": "user-123",
    "name": "Alice",
    "clubs": [
        {"name": "hever", "discount": 0.15},
        {"name": "hightechzone", "discount": 0.20}
    ],
    "total_discount": 0.35,
    "savings_estimated": 150
}
```

**Trade-off**: Larger documents, but queries are instant and don't require joins.

### Batch Migration

```python
def migrate_to_denormalized():
    session = client.start_session()
    
    try:
        session.start_transaction()
        
        for user in db.users.find({}, session=session):
            # Fetch clubs
            clubs = list(db.clubs.find(
                {"_id": {"$in": user["club_ids"]}},
                session=session
            ))
            
            # Denormalize
            club_data = [
                {"name": c["name"], "discount": c["discount"]}
                for c in clubs
            ]
            
            # Update user document
            db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"clubs": club_data}},
                session=session
            )
        
        session.commit_transaction()
    finally:
        session.end_session()

migrate_to_denormalized()
```

---

## References

- [MongoDB Explain Output](https://docs.mongodb.com/manual/reference/explain-results/)
- [Performance Best Practices](https://docs.mongodb.com/manual/administration/analyzing-mongodb-performance/)
- [Profiler](https://docs.mongodb.com/manual/tutorial/manage-the-database-profiler/)
- [Connection String Options](https://docs.mongodb.com/manual/reference/connection-string/)
