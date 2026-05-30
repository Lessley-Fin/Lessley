# MongoDB Transactions: ACID Guarantees & ClientSession Lifecycle

## Overview

MongoDB transactions provide ACID (Atomicity, Consistency, Isolation, Durability) guarantees for multi-document writes. When you need to update multiple collections or documents and guarantee consistency, transactions are essential.

## When to Use Transactions

✅ **Use transactions for**:
- User profile updates + analytics synchronization
- Club card addition + savings recalculation
- Schema migrations affecting multiple collections
- Complex business logic requiring "all-or-nothing" semantics

❌ **Avoid transactions for**:
- Single-document writes (MongoDB is atomic by default)
- Read-only queries
- Simple inserts to a single collection
- High-throughput scenarios where transaction overhead matters

---

## ACID Properties

| Property | Meaning | Example |
|----------|---------|---------|
| **Atomicity** | All operations succeed or all fail | Add club card + recalculate savings: both or neither |
| **Consistency** | Database moves from valid state to valid state | No partially updated documents |
| **Isolation** | Concurrent transactions don't interfere | Other clients don't see uncommitted changes |
| **Durability** | Committed data survives crashes | After commit_transaction(), data is safe |

---

## ClientSession Lifecycle

```
┌──────────────────────────────────────┐
│ client.start_session()               │
│ (Create session context)             │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│ session.start_transaction()          │
│ (Begin atomic scope)                 │
└──────────────┬───────────────────────┘
               │
        ┌──────────────┐
        │ Phase: ACTIVE
        │ (Add operations)
        │
        │ db.users.update_one(..., session=session)
        │ db.analytics.update_one(..., session=session)
        │ db.deals.insert_one(..., session=session)
        └──────────────┐
               │
        ┌──────▼──────────────────────┐
        │ Decision Point:              │
        │ All success? No errors?      │
        └──────┬───────────────┬───────┘
               │               │
    [YES]      │               │      [NO / ERROR]
               │               │
    ┌──────────▼─┐       ┌─────▼──────────┐
    │ commit     │       │ abort          │
    │ transaction│       │ transaction    │
    └──────┬─────┘       └────┬───────────┘
           │                  │
    ┌──────▼──────────────────▼─────────────┐
    │ session.end_session()                 │
    │ (Clean up resources)                  │
    └───────────────────────────────────────┘
```

---

## Python Implementation: Step by Step

### Step 1: Create Session

```python
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
session = client.start_session()
```

### Step 2: Start Transaction

```python
session.start_transaction()
```

At this point, the session is in "ACTIVE" state. All operations within this session are part of the transaction.

### Step 3: Perform Operations (with session parameter)

```python
db = client.lessley
users_collection = db.users
analytics_collection = db.analytics

# ← All write operations MUST include session=session
users_collection.update_one(
    {"_id": "user-123"},
    {"$push": {"clubs": {"name": "hever"}}},
    session=session  # ← CRITICAL: attach to session
)

analytics_collection.update_one(
    {"user_id": "user-123"},
    {"$set": {"total_savings": 150}},
    upsert=True,
    session=session  # ← CRITICAL: attach to session
)
```

**Critical**: Every operation must include `session=session`. Operations without the session parameter bypass the transaction.

### Step 4: Commit or Abort

```python
try:
    # If we reach here, all operations succeeded
    session.commit_transaction()
    print("Transaction committed")
except Exception as e:
    # If any operation failed or threw an exception
    session.abort_transaction()
    print(f"Transaction aborted: {e}")
finally:
    session.end_session()
```

---

## Isolation Levels

MongoDB supports two isolation levels for transactions:

### Default: "snapshot" Isolation

```python
session.start_transaction()
```

**Semantics**:
- Transaction reads from a snapshot of data taken at transaction start
- Other concurrent transactions don't see uncommitted changes
- Serializable isolation (strongest guarantee)

### Performance Note

Snapshot isolation ensures strong consistency but has performance cost:
- Don't use for high-frequency operations (e.g., counters on hot keys)
- Suitable for occasional complex updates (user profile, analytics)

---

## Error Handling & Retry Logic

### Transient Errors (Retry)

```python
from pymongo.errors import ServerSelectionTimeout, OperationFailure
import time

max_retries = 3

for attempt in range(max_retries):
    session = client.start_session()
    
    try:
        session.start_transaction()
        
        # ... perform operations ...
        
        session.commit_transaction()
        break  # Success
    
    except ServerSelectionTimeout as e:
        # Network blip: retry with backoff
        session.abort_transaction()
        
        if attempt < max_retries - 1:
            backoff = 0.5 * (2 ** attempt)
            time.sleep(backoff)
        else:
            raise
    
    except OperationFailure as e:
        # Logical error: don't retry
        session.abort_transaction()
        raise
    
    finally:
        session.end_session()
```

### Error Classification

| Error | Type | Action |
|-------|------|--------|
| ServerSelectionTimeout | Transient (network) | **Retry** with backoff |
| NotWritablePrimary | Transient (replication) | **Retry** |
| WriteConflict | Transient (concurrent writes) | **Retry** |
| ValidationError | Permanent (schema mismatch) | **Don't retry**, log & alert |
| DuplicateKeyError | Permanent (unique constraint) | **Don't retry**, handle gracefully |

---

## Common Pitfalls

### ❌ Pitfall 1: Forgetting session= in Operations

```python
# BAD: Operation is NOT part of transaction
session.start_transaction()
db.users.update_one({"_id": user_id}, {"$set": {"name": "new"}})  # ← No session!
session.commit_transaction()
```

**Result**: Update is not part of transaction; rollback won't affect it.

**Fix**:
```python
db.users.update_one({"_id": user_id}, {"$set": {"name": "new"}}, session=session)
```

---

### ❌ Pitfall 2: Long-Running Transactions

```python
# BAD: Transaction holds locks for 30+ seconds
session.start_transaction()

data = db.deals.find_one({"_id": deal_id}, session=session)
time.sleep(30)  # Simulate slow processing
db.deals.update_one({"_id": deal_id}, {"$set": {"processed": True}}, session=session)

session.commit_transaction()
```

**Result**: Other concurrent transactions are blocked for 30 seconds.

**Fix**: Do expensive computations *outside* the transaction.

```python
data = db.deals.find_one({"_id": deal_id})  # ← Outside transaction
processed_result = expensive_computation(data)  # ← Outside transaction

session.start_transaction()
db.deals.update_one({"_id": deal_id}, {"$set": {"result": processed_result}}, session=session)
session.commit_transaction()
```

---

### ❌ Pitfall 3: Not Calling end_session()

```python
# BAD: Session leaks
session = client.start_session()
session.start_transaction()
# ... some error happens ...
# Forgot to call end_session()
```

**Result**: Sessions exhaust connection pool; subsequent requests timeout.

**Fix**: Always call end_session() (use try/finally or context manager).

```python
# GOOD: Guaranteed cleanup
try:
    session.start_transaction()
    # ... operations ...
    session.commit_transaction()
finally:
    session.end_session()
```

---

## C# Implementation (MongoDB.Driver)

```csharp
using MongoDB.Driver;

// Setup
var client = new MongoClient("mongodb://localhost:27017");
var database = client.GetDatabase("lessley");

// Create session
using (var session = client.StartSession())
{
    session.StartTransaction();
    
    try
    {
        var usersCollection = database.GetCollection<BsonDocument>("users");
        var analyticsCollection = database.GetCollection<BsonDocument>("analytics");
        
        // Operation 1
        usersCollection.UpdateOne(
            session,
            Builders<BsonDocument>.Filter.Eq("_id", userId),
            Builders<BsonDocument>.Update.Push("clubs", "hever")
        );
        
        // Operation 2
        analyticsCollection.UpdateOne(
            session,
            Builders<BsonDocument>.Filter.Eq("user_id", userId),
            Builders<BsonDocument>.Update.Set("total_savings", 150),
            new UpdateOptions { IsUpsert = true }
        );
        
        session.CommitTransaction();
    }
    catch (Exception ex)
    {
        session.AbortTransaction();
        throw;
    }
}  // end_session() called automatically by using()
```

---

## Monitoring & Debugging

### View Active Transactions

```
// In MongoDB shell
db.currentOp({op: "insert|update|delete", client_s: {$exists: true}})
```

### Check Transaction Isolation

```python
# In Python code
session.options.transaction_options
# Returns: ReadConcern, WriteConcern, ReadPreference settings
```

### Logs

Enable transaction tracing in mongod:
```
--logComponentVerbosity=transaction:2
```

---

## Performance Tuning

### Transaction Timeout

By default, MongoDB kills transactions after 60 minutes. For shorter transactions, set explicitly:

```python
from pymongo.read_preferences import ReadPreference
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

session = client.start_session(
    read_preference=ReadPreference.PRIMARY,
    write_concern=WriteConcern(w=1),
    read_concern=ReadConcern(level="snapshot")
)
```

### Optimize for Latency

1. **Minimize transaction scope**: Only wrap operations that *must* be atomic
2. **Pre-compute outside**: Calculate values before transaction starts
3. **Batch operations**: Combine multiple updates into one transaction where possible
4. **Use indexes**: Ensure queries within transactions are indexed

---

## References

- [MongoDB Transactions Documentation](https://docs.mongodb.com/manual/core/transactions/)
- [PyMongo ClientSession](https://pymongo.readthedocs.io/en/stable/api/pymongo/client_session.html)
- [MongoDB.Driver Transactions (.NET)](https://www.mongodb.com/docs/drivers/csharp/current/fundamentals/transactions/)
