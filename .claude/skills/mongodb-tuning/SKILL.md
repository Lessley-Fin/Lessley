---
name: mongodb-tuning
description: 'Implement ACID transactions and advanced indexing for MongoDB at scale. Use when: ensuring data consistency across multi-document updates (user wallet + savings), designing query-specific indexes (compound, covered, geospatial), or optimizing API Gateway response times.'
argument-hint: 'mongodb-tuning for transaction and indexing patterns'
user-invocable: true
---

# Advanced MongoDB Tuning: Safety & Speed

Supporting Lessley's "Hybrid Read-Optimized" architecture at scale requires two critical capabilities: **data safety** through ACID transactions and **lightning-fast queries** through strategic indexing.

## When to Use

- Implementing multi-step user profile updates (club cards, wallet state)
- Building optimizer functions that recalculate user savings atomically
- Designing queries for the API Gateway that must complete in <100ms
- Creating geospatial queries for location-based deal discovery
- Migrating indexes in production without locking the database

---

## Pattern 1: Multi-Document Transactions (ACID Safety)

**Goal**: Guarantee data consistency when multiple writes must succeed or fail together.

### Problem: Corrupted State Without Transactions

```
User adds "Hever" club card:
  1. Update USERS.clubs array ✓
  2. Recalculate savings in ANALYTICS ✗ (crashes)
  
Result: User has club card in profile, but optimizer doesn't recognize benefits
        → Incorrect discount calculations, data inconsistency
```

### Solution: ClientSession Transactions

```python
from pymongo import MongoClient
from pymongo.errors import OperationFailure

def add_club_card_safely(client: MongoClient, user_id: str, club_name: str) -> bool:
    """
    Atomically add club card to user profile and recalculate savings.
    
    Either BOTH succeed, or BOTH roll back.
    """
    session = client.start_session()
    
    try:
        session.start_transaction()
        
        db = client.lessley
        
        # Step 1: Add club card to user profile
        db.users.update_one(
            {"_id": user_id},
            {"$push": {"clubs": {"name": club_name, "added_at": datetime.now()}}},
            session=session
        )
        
        # Step 2: Recalculate savings for this club
        user = db.users.find_one({"_id": user_id}, session=session)
        new_savings = calculate_savings(user, club_name)
        
        db.analytics.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "savings": new_savings,
                    "last_updated": datetime.now(),
                    "club_count": len(user["clubs"])
                }
            },
            upsert=True,
            session=session
        )
        
        # Commit: both writes succeed
        session.commit_transaction()
        return True
    
    except OperationFailure as e:
        # Rollback: neither write persists
        session.abort_transaction()
        logger.error(f"Transaction failed, rolled back: {e}")
        return False
    
    finally:
        session.end_session()
```

### Key Points

- **ClientSession**: Container for transaction context
- **start_transaction()**: Begin atomic scope
- **session= parameter**: Pass to all DB operations in transaction
- **commit_transaction()**: All writes persisted together
- **abort_transaction()**: All writes discarded on error

### Retry Logic for Transient Failures

```python
def add_club_card_with_retry(client: MongoClient, user_id: str, club_name: str, max_retries: int = 3):
    """Retry transaction on transient failures (network blips, temporary locks)."""
    
    for attempt in range(max_retries):
        try:
            if add_club_card_safely(client, user_id, club_name):
                return True
        except pymongo.errors.ServerSelectionTimeout:
            if attempt < max_retries - 1:
                logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(0.5 * (2 ** attempt))  # Exponential backoff
            else:
                raise
    
    return False
```

---

## Pattern 2: Wise Indexing Strategies

> **The collections this database actually has.** `deals`, `stores`, `clubs` and `mccs` are
> shared: the scraping pipeline writes them and the Gateway, Personalization and
> deal-optimizer all read them directly. There is no projected read model. History lives in
> `deals_current` (one head row per deal, filtered on `status: "active"`) and the append-only
> `deal_versions`. Identity is `users`, written by ASP.NET Identity, so **its fields are
> PascalCase** (`NormalizedEmail`, `Clubs`, `Tags`) unlike everything else.
>
> A deal document carries `store_id`, `source_id`, `club_id`, `title`, `deal_type`,
> `scraped_at`, and the nested `discount_logic` / `constraints`. It has no `valid_until`,
> `deal_name`, `discount_value` or `popularity` — index against what is stored, and check
> `scripts/index_migration.py`, which mirrors the indexes the application really creates.

### Strategy 2a: Compound Indexes (Query-Specific)

**Use Case**: "Get the live deals for a store" — served from the versioned head collection,
which is the only one carrying a lifecycle.

```python
def create_compound_index(db):
    """
    Compound index matching the head-collection query.

    Query: db.deals_current.find({
        store_id: "019d2090...",
        status: "active"
    })
    """

    db.deals_current.create_index(
        [("store_id", 1), ("status", 1)],
        name="idx_current_store_status",
        background=True  # ← Don't lock the database
    )
```

**Index Design**:
- `store_id: 1` (ascending) — Equality filter
- `status: 1` — Second equality filter, so the index answers both

Equality fields come first; a range or sort field goes last (ESR: Equality, Sort, Range).

**Result**: Index instantly finds matching documents without collection scan.

---

### Strategy 2b: Covered Queries (No Document Access)

**Use Case**: Mobile app needs quick list of deal names and discounts (no full documents)

```python
def create_covered_query_index(db):
    """
    Index includes all fields needed by the query.
    MongoDB returns results directly from index (in RAM), never touches disk.
    
    Query: db.deals.find(
        {store_id: "019d2090..."},
        {_id: 1, title: 1, deal_type: 1}  # Only these fields
    )
    """

    # Include all fields the query needs
    db.deals.create_index(
        [
            ("store_id", 1),   # Filter
            ("title", 1),      # Projected field
            ("deal_type", 1)   # Projected field
        ],
        name="idx_deal_card_view",
        background=True
    )
```

**Benefit**: Sub-millisecond response times for frontend.

---

### Strategy 2c: Geospatial Indexes (2dsphere)

> **Not applicable to this database yet.** `stores` carries no coordinates — its `metadata`
> holds `image_urls`, `mcc_codes` and `store_url`. Creating the index below today would
> index a field that does not exist. Keep the pattern for when location is scraped.

**Use Case**: "Find the best deals within 5km of my location"

```python
def create_geospatial_index(db):
    """
    2dsphere index enables radius queries on store coordinates.
    
    Data format:
    {
        "store_id": "store-123",
        "location": {
            "type": "Point",
            "coordinates": [lon, lat]  # Note: [lon, lat], not [lat, lon]
        }
    }
    """
    
    db.stores.create_index(
        [("location", "2dsphere")],
        name="idx_store_location",
        background=True
    )
    
    # Query: find stores within 5km radius
    stores = db.stores.find({
        "location": {
            "$near": {
                "$geometry": {
                    "type": "Point",
                    "coordinates": [-73.97, 40.77]  # [lon, lat]
                },
                "$maxDistance": 5000  # meters
            }
        }
    })
```

---

### Strategy 2d: Background Index Creation (No Lock)

**Always use `background=True`** to avoid blocking database during index build.

```python
# BAD: Locks database, blocks all traffic during index creation
db.deals.create_index([("store_id", 1)])

# GOOD: Builds in background, traffic continues
db.deals.create_index(
    [("store_id", 1)],
    background=True
)
```

---

## Index Lifecycle & Monitoring

### View Existing Indexes

```python
def list_indexes(db, collection_name: str):
    """List all indexes on a collection."""
    
    for index_info in db[collection_name].list_indexes():
        print(f"Name: {index_info['name']}")
        print(f"Keys: {index_info['key']}")
        print(f"Size: {index_info.get('size', 'N/A')} bytes")
        print()
```

### Remove Unused Indexes

```python
def remove_index(db, collection_name: str, index_name: str):
    """Remove an index (e.g., after performance optimization reveals it's redundant)."""
    
    try:
        db[collection_name].drop_index(index_name)
        logger.info(f"Dropped index: {index_name}")
    except pymongo.errors.OperationFailure as e:
        logger.error(f"Cannot drop index: {e}")
```

### Monitor Index Performance

```python
def analyze_index_usage(db, collection_name: str):
    """Analyze which indexes are being used (requires profiling enabled)."""
    
    pipeline = [
        {"$match": {"ns": f"lessley.{collection_name}"}},
        {"$group": {
            "_id": "$execStats.executionStages.indexName",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    results = list(db.system.profile.aggregate(pipeline))
    
    for result in results:
        print(f"Index: {result['_id']}, Usage: {result['count']} times")
```

---

## Example Code

See the reference implementations:
- [transaction_example.py](./scripts/transaction_example.py) — Python ClientSession pattern for Lessley.Personalization
- [transaction_example.cs](./scripts/transaction_example.cs) — C# MongoDB.Driver pattern for Lessley.Gateway.Api
- [index_migration.py](./scripts/index_migration.py) — Safe index creation and monitoring script

---

## Integration Checklist

### Transactions
- [ ] User profile updates wrapped in ClientSession
- [ ] Optimizer recalculations use start_transaction()
- [ ] Retry logic handles transient failures
- [ ] Rollback tested for each transaction
- [ ] Logs include transaction status (committed/aborted)

### Indexing
- [ ] Compound indexes match query patterns (store_id + valid_until)
- [ ] Covered query indexes for frontend list views
- [ ] Geospatial index created for location-based queries (if feature exists)
- [ ] All index creation uses `background=True`
- [ ] Index monitoring dashboard in Grafana

### Performance
- [ ] API Gateway response time < 100ms (measured in Grafana)
- [ ] Collection scans eliminated (0 scans in profiling)
- [ ] Database lock contention < 1% (monitored)

---

## Reference Docs

- [Transactions Guide](./references/transactions-guide.md) — ClientSession lifecycle, error handling, isolation levels
- [Indexing Strategies](./references/indexing-strategies.md) — Deep dive on compound, covered, sparse, unique indexes
- [Performance Tuning](./references/performance-tuning.md) — Profiling, query analysis, Grafana monitoring, migration strategies

---

## Related Skills

- **RabbitMQ Resilience**: For message-driven updates that write to MongoDB
- **Grafana Monitoring**: For real-time query performance dashboards
- **Data Migration**: For safe index rollout across production replicas
