# MongoDB Indexing Strategies: Speed & Consistency

## The Cost of Index Misses

Without proper indexing, MongoDB performs **collection scans**: it reads every document on disk to find matches.

```
Collection Scan (BAD):
┌─────────────────────────────────────────┐
│ Read 1M documents from disk             │
│ Check each: store_id == "store-123"?    │
│ Return matches                          │
│ Time: 5-10 seconds                      │
└─────────────────────────────────────────┘

Indexed Query (GOOD):
┌─────────────────────────────────────────┐
│ Look up index B-tree: O(log N)          │
│ Direct access to matching documents     │
│ Time: <100ms                            │
└─────────────────────────────────────────┘
```

API Gateway can't afford collection scans. Every query must hit an index.

---

## Index Types

### 1. Single-Field Index

**Simplest index**: Speed up queries on one field.

```python
db.deals.create_index([("store_id", 1)])
```

**Use case**: If you frequently query by `store_id` alone.

**Limitation**: Doesn't help if you query `store_id + valid_until` together.

---

### 2. Compound Index (Most Important)

**Compound indexes** speed up queries with multiple filter/sort conditions.

#### Rule: Equality → Range → Sort (ERS)

When designing a compound index, follow this order:

1. **Equality fields**: Filters that match exactly (e.g., `store_id == "store-123"`)
2. **Range fields**: Filters with ranges (e.g., `valid_until > now`)
3. **Sort fields**: Fields used for sorting

#### Example: Query

```python
# Query: Get active deals for a store, newest first
db.deals.find({
    "store_id": "store-123",        # Equality
    "valid_until": {$gt: now}       # Range
}).sort({"valid_until": -1})        # Sort
```

#### Index Design (ERS order)

```python
db.deals.create_index([
    ("store_id", 1),           # Equality (ascending)
    ("valid_until", -1)        # Range + Sort (descending for sort)
])
```

**Why this order**:
- Index first narrows by store
- Then narrows by valid_until range
- Results are already sorted (no sort overhead)

#### Counter-example (Wrong Order)

```python
# WRONG: Range before Equality
db.deals.create_index([
    ("valid_until", -1),       # Range first ✗
    ("store_id", 1)            # Equality second ✗
])
```

This index is less efficient because MongoDB has to scan *all* documents with `valid_until > now`, then filter by `store_id`.

---

### 3. Covered Queries (Index-Only)

**Covered queries** return results directly from the index without reading any documents.

**Requirement**: Index must include all fields the query needs to return.

#### Example: Mobile App Deal List

```python
# Query: Get deal names and discounts for a store
db.deals.find(
    {"store_id": "store-123"},
    {"_id": 1, "deal_name": 1, "discount_value": 1}  # Projection
)
```

#### Index Design (includes all projected fields)

```python
db.deals.create_index([
    ("store_id", 1),
    ("deal_name", 1),
    ("discount_value", 1)
])
```

**Benefit**: MongoDB reads the index and returns results in **<1ms**. Never touches the actual documents.

**Check if query is covered**:

```
explain = db.deals.find(...).explain()
print(explain["executionStats"]["executionStages"]["stage"])
# Output: "COLLSCAN" = collection scan (BAD)
#         "IXSCAN"  = index scan (GOOD)
#         "COVERED" = covered query (BEST)
```

---

### 4. Unique Index

**Unique indexes** enforce uniqueness and speed up lookups.

```python
db.users.create_index([("email", 1)], unique=True, sparse=True)
```

**Benefits**:
- Email lookup is fast: O(log N)
- Duplicates are prevented
- Constraint enforced by database (not application)

**sparse=True**: Allow multiple NULL values (emails).

---

### 5. Sparse Index

**Sparse indexes** only index documents that have the field.

```python
db.users.create_index([("phone", 1)], sparse=True)
```

**Use case**: Optional fields (not all users have a phone number).

**Benefit**: Index smaller in memory.

---

### 6. Geospatial Index (2dsphere)

**2dsphere indexes** enable location-based queries.

#### Data Format (GeoJSON)

```python
db.stores.insert_one({
    "store_id": "store-123",
    "location": {
        "type": "Point",
        "coordinates": [-73.97, 40.77]  # [longitude, latitude]
    }
})
```

**Note**: GeoJSON uses [lon, lat], not [lat, lon].

#### Index Creation

```python
db.stores.create_index([("location", "2dsphere")])
```

#### Radius Query

```python
# Find stores within 5km of my location
db.stores.find({
    "location": {
        "$near": {
            "$geometry": {
                "type": "Point",
                "coordinates": [-73.97, 40.77]
            },
            "$maxDistance": 5000  # meters
        }
    }
})
```

**Benefit**: Near-instant location-based queries, even with thousands of stores.

---

### 7. Text Index (Full-Text Search)

For searching deal descriptions or store names.

```python
db.deals.create_index([("description", "text"), ("name", "text")])

# Query
db.deals.find({"$text": {"$search": "organic coffee"}})
```

---

## Index Best Practices

### ✅ Background Index Creation (Always!)

```python
db.deals.create_index(
    [("store_id", 1), ("valid_until", -1)],
    background=True  # ← Don't lock the database
)
```

**Why**: Without `background=True`, MongoDB locks the collection during index build, blocking all traffic.

### ✅ Analyze Queries Before Indexing

```python
# See how many documents are scanned
explain = db.deals.find({"store_id": "store-123"}).explain()

examined = explain["executionStats"]["totalDocsExamined"]
returned = explain["executionStats"]["nReturned"]

efficiency = returned / examined
print(f"Index efficiency: {efficiency:.1%}")
# Goal: efficiency close to 100%
```

### ✅ Monitor Index Size

```python
# Check index memory usage
for idx in db.deals.list_indexes():
    print(f"{idx['name']}: {idx.get('size', 'unknown')} bytes")
```

Large indexes consume RAM; tune or remove if unused.

### ❌ Avoid Over-Indexing

Each index:
- Consumes memory (especially with large documents)
- Slows down writes (every insert updates all indexes)
- Needs maintenance

**Rule**: Create indexes for your actual queries, not hypothetical ones.

### ❌ Avoid Redundant Indexes

```python
# BAD: Redundant indexes
db.deals.create_index([("store_id", 1)])
db.deals.create_index([("store_id", 1), ("valid_until", -1)])
```

The second index supersedes the first. Drop the single-field index.

---

## Index Naming Convention

```python
# Pattern: idx_<collection>_<fields>_<type>
db.deals.create_index([("store_id", 1), ("valid_until", -1)], name="idx_deals_store_active")
db.stores.create_index([("location", "2dsphere")], name="idx_stores_geo")
```

Clear names make maintenance easier.

---

## Migration: Adding Indexes to Large Collections

### Safe Strategy (No Downtime)

1. **Build index in background** while traffic continues:
   ```python
   db.deals.create_index([("store_id", 1)], background=True)
   ```

2. **Monitor progress** (on replica set, builds in parallel):
   ```
   # In MongoDB shell
   db.currentOp({op: "createIndexes"})
   ```

3. **Verify index exists**:
   ```python
   index_names = [idx["name"] for idx in db.deals.list_indexes()]
   assert "idx_deals_store_id" in index_names
   ```

### Fallback: Remove if Slow

If index build blocks traffic too much:
```python
db.deals.drop_index("idx_deals_store_id")
```

---

## Performance Tuning Examples

### Scenario: API Gateway is Slow

**Problem**: 
```
Query: db.deals.find({store_id: "store-123"})
Time: 3 seconds
```

**Investigation**:
```python
explain = db.deals.find({"store_id": "store-123"}).explain()
print(explain["executionStats"]["executionStages"]["stage"])
# Output: COLLSCAN ← Scanning entire collection!
```

**Solution**: Create compound index
```python
db.deals.create_index([("store_id", 1), ("valid_until", -1)], background=True)
```

**Result**: Same query now <100ms.

---

### Scenario: Mobile App Crashes on List View

**Problem**: Loading deal list times out, app freezes.

**Root cause**: Queries are looking up documents from disk.

**Solution**: Create covered query index
```python
# Query only needs: deal_name, discount_value
db.deals.create_index(
    [("store_id", 1), ("deal_name", 1), ("discount_value", 1)],
    background=True
)
```

**Result**: List returns in <1ms, app responsive.

---

### Scenario: Location-Based Discovery Feature

**Problem**: "Find deals near me" feature is slow.

**Solution**: Create geospatial index
```python
db.stores.create_index([("location", "2dsphere")], background=True)
```

**Result**: Radius queries now instant.

---

## Index Monitoring

### Grafana Query: Index Hit Rate

```promql
rate(mongodb_indexCounters_hits[5m]) /
(rate(mongodb_indexCounters_hits[5m]) + rate(mongodb_indexCounters_misses[5m]))
```

**Target**: >95% hit rate.

### Grafana Query: Collection Scans

```promql
rate(mongodb_query_executor_scanned_objects[5m])
```

**Target**: Should be 0 or near-zero (means queries aren't using indexes).

---

## References

- [MongoDB Indexes](https://docs.mongodb.com/manual/indexes/)
- [Compound Indexes](https://docs.mongodb.com/manual/core/index-compound/)
- [Geospatial Indexes](https://docs.mongodb.com/manual/core/geospatial-indexes/)
- [Use Indexes to Sort Query Results](https://docs.mongodb.com/manual/tutorial/sort-results-with-indexes/)
