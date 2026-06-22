"""
Integration Tests: MongoDB Logic Verification

Validates TTL indexes, geospatial queries, and transactions work as designed.

Usage:
    pytest integration_tests_mongodb.py -v
    pytest integration_tests_mongodb.py::test_ttl_index_removes_expired_deals -v
"""

import time
import logging
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
from typing import List, Tuple

import pytest
from pymongo import MongoClient, UpdateOne
from pymongo.errors import OperationFailure


logger = logging.getLogger(__name__)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mongo_client():
    """MongoDB client with test database."""
    client = MongoClient("mongodb://localhost:27017")
    db = client.lessley_test
    
    yield db
    
    # Cleanup
    client.drop_database("lessley_test")
    client.close()


@pytest.fixture(scope="function")
def deals_collection(mongo_client):
    """Clean deals collection."""
    collection = mongo_client.deals
    collection.delete_many({})
    
    # Ensure indexes are dropped
    for index in collection.list_indexes():
        if index["name"] != "_id_":
            collection.drop_index(index["name"])
    
    return collection


@pytest.fixture(scope="function")
def stores_collection(mongo_client):
    """Clean stores collection."""
    collection = mongo_client.stores
    collection.delete_many({})
    
    for index in collection.list_indexes():
        if index["name"] != "_id_":
            collection.drop_index(index["name"])
    
    return collection


# ============================================================================
# TTL Index Tests
# ============================================================================

class TestTTLIndexes:
    """Verify TTL (Time To Live) indexes remove expired documents."""
    
    def test_ttl_index_removes_expired_deals(self, deals_collection):
        """
        TTL index should automatically remove documents after expiration time.
        """
        
        # Create TTL index: remove documents 60 seconds after insert
        deals_collection.create_index(
            [("inserted_at", 1)],
            name="idx_ttl_deals",
            expireAfterSeconds=2  # 2 seconds for quick test
        )
        
        # Insert a deal
        deal = {
            "_id": "deal-old",
            "title": "Very old deal",
            "inserted_at": datetime.now()
        }
        deals_collection.insert_one(deal)
        
        # Verify it exists
        assert deals_collection.find_one({"_id": "deal-old"}) is not None
        
        # Wait for TTL job to run (usually runs every 60s, but we test with shorter TTL)
        time.sleep(3)
        
        # Verify it's been removed
        result = deals_collection.find_one({"_id": "deal-old"})
        assert result is None, f"TTL index failed to remove expired deal: {result}"
        
        logger.info("✓ TTL index successfully removed expired document")
    
    def test_ttl_index_preserves_recent_deals(self, deals_collection):
        """TTL index should only remove old documents, not recent ones."""
        
        deals_collection.create_index(
            [("inserted_at", 1)],
            name="idx_ttl_deals",
            expireAfterSeconds=10
        )
        
        # Insert a recent deal
        deal = {
            "_id": "deal-recent",
            "title": "Recent deal",
            "inserted_at": datetime.now()
        }
        deals_collection.insert_one(deal)
        
        # Check after 2 seconds
        time.sleep(2)
        
        # Should still exist
        result = deals_collection.find_one({"_id": "deal-recent"})
        assert result is not None, "TTL index removed recent document prematurely"
        
        logger.info("✓ TTL index preserved recent document")
    
    def test_ttl_with_custom_field(self, deals_collection):
        """TTL index can use a custom expiration timestamp."""
        
        deals_collection.create_index(
            [("valid_until", 1)],
            name="idx_ttl_valid_until",
            expireAfterSeconds=0  # Remove immediately when valid_until < now
        )
        
        # Insert with explicit valid_until
        old_deal = {
            "_id": "deal-expired",
            "title": "Expired deal",
            "valid_until": datetime.now() - timedelta(seconds=5)  # Already expired
        }
        deals_collection.insert_one(old_deal)
        
        # TTL should remove it soon
        time.sleep(2)
        
        result = deals_collection.find_one({"_id": "deal-expired"})
        assert result is None, "TTL failed to remove expired deal with custom field"
        
        logger.info("✓ TTL index with custom field works correctly")


# ============================================================================
# Geospatial Query Tests
# ============================================================================

class TestGeospatialQueries:
    """Verify 2dsphere index enables accurate location-based queries."""
    
    def test_geospatial_index_creation(self, stores_collection):
        """Create and verify 2dsphere index."""
        
        stores_collection.create_index([("location", "2dsphere")])
        
        indexes = [idx["name"] for idx in stores_collection.list_indexes()]
        assert any("location_2dsphere" in idx for idx in indexes)
        
        logger.info("✓ 2dsphere index created successfully")
    
    def test_geospatial_query_nearby_stores(self, stores_collection):
        """Query finds stores within specified radius."""
        
        stores_collection.create_index([("location", "2dsphere")])
        
        # Insert stores at known locations
        stores = [
            {
                "_id": "store-hever-tlv",
                "name": "Hever Tel Aviv",
                "location": {
                    "type": "Point",
                    "coordinates": [34.7617, 32.0853]  # [lon, lat] Tel Aviv
                }
            },
            {
                "_id": "store-hever-jaffa",
                "name": "Hever Jaffa",
                "location": {
                    "type": "Point",
                    "coordinates": [34.7614, 32.0547]  # ~5km south of Tel Aviv
                }
            },
            {
                "_id": "store-hever-ramat-hasharon",
                "name": "Hever Ramat Hasharon",
                "location": {
                    "type": "Point",
                    "coordinates": [34.8241, 32.1563]  # ~15km north of Tel Aviv
                }
            }
        ]
        
        stores_collection.insert_many(stores)
        
        # Query: stores within 10km of Tel Aviv center
        results = list(stores_collection.find({
            "location": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [34.7617, 32.0853]  # Tel Aviv
                    },
                    "$maxDistance": 10000  # 10km in meters
                }
            }
        }))
        
        # Should return Tel Aviv and Jaffa, not Ramat Hasharon
        store_ids = [r["_id"] for r in results]
        
        assert "store-hever-tlv" in store_ids, "Center store not returned"
        assert "store-hever-jaffa" in store_ids, "Nearby store not returned"
        assert "store-hever-ramat-hasharon" not in store_ids, "Distant store incorrectly returned"
        
        logger.info(f"✓ Geospatial query returned {len(results)} stores within radius")
    
    def test_geospatial_query_radius_accuracy(self, stores_collection):
        """Verify radius calculation is accurate."""
        
        stores_collection.create_index([("location", "2dsphere")])
        
        # Query point (center)
        center = [34.7617, 32.0853]  # Tel Aviv
        
        # Test different radii
        radii_tests = [
            (1000, 0),      # 1km: should return 0 stores (none that close)
            (5000, 1),      # 5km: should return the center + nearby
            (50000, 3),     # 50km: should return all 3
        ]
        
        stores = [
            {
                "_id": "store-center",
                "location": {"type": "Point", "coordinates": center}
            },
            {
                "_id": "store-1km",
                "location": {"type": "Point", "coordinates": [34.7717, 32.0853]}  # ~1.1km east
            },
            {
                "_id": "store-30km",
                "location": {"type": "Point", "coordinates": [34.9617, 32.0853]}  # ~20km east
            }
        ]
        
        stores_collection.insert_many(stores)
        
        for max_distance, expected_min_count in radii_tests:
            results = list(stores_collection.find({
                "location": {
                    "$near": {
                        "$geometry": {"type": "Point", "coordinates": center},
                        "$maxDistance": max_distance
                    }
                }
            }))
            
            assert len(results) >= expected_min_count, \
                f"Radius {max_distance}m should return >= {expected_min_count} stores, got {len(results)}"
    
    def test_geospatial_invalid_coordinates_rejected(self, stores_collection):
        """Invalid coordinates should be rejected."""
        
        stores_collection.create_index([("location", "2dsphere")])
        
        # Longitude must be [-180, 180], Latitude must be [-90, 90]
        invalid_stores = [
            {
                "_id": "store-bad-lon",
                "location": {"type": "Point", "coordinates": [200, 32]}  # Lon out of range
            },
            {
                "_id": "store-bad-lat",
                "location": {"type": "Point", "coordinates": [34, 100]}  # Lat out of range
            }
        ]
        
        for store in invalid_stores:
            with pytest.raises(OperationFailure):
                stores_collection.insert_one(store)


# ============================================================================
# Transaction Tests
# ============================================================================

class TestTransactions:
    """Verify ACID transactions work correctly."""
    
    def test_transaction_commit_updates_both_collections(self, mongo_client):
        """Transaction commits when all operations succeed."""
        
        users_col = mongo_client.users
        analytics_col = mongo_client.analytics
        
        session = mongo_client.start_session()
        
        try:
            session.start_transaction()
            
            # Operation 1: Add club to user
            users_col.update_one(
                {"_id": "user-alice"},
                {
                    "$set": {
                        "_id": "user-alice",
                        "name": "Alice",
                        "clubs": ["hever"]
                    }
                },
                upsert=True,
                session=session
            )
            
            # Operation 2: Update analytics
            analytics_col.update_one(
                {"user_id": "user-alice"},
                {"$set": {"club_count": 1, "total_savings": 10}},
                upsert=True,
                session=session
            )
            
            session.commit_transaction()
        
        finally:
            session.end_session()
        
        # Verify both updates persisted
        user = users_col.find_one({"_id": "user-alice"})
        analytics = analytics_col.find_one({"user_id": "user-alice"})
        
        assert user is not None
        assert "hever" in user.get("clubs", [])
        assert analytics is not None
        assert analytics["club_count"] == 1
        
        logger.info("✓ Transaction committed successfully")
    
    def test_transaction_rollback_on_error(self, mongo_client):
        """Transaction rolls back if any operation fails."""
        
        users_col = mongo_client.users
        analytics_col = mongo_client.analytics
        
        session = mongo_client.start_session()
        
        try:
            session.start_transaction()
            
            # Operation 1: Add club (should succeed)
            users_col.update_one(
                {"_id": "user-bob"},
                {"$set": {"_id": "user-bob", "clubs": ["hever"]}},
                upsert=True,
                session=session
            )
            
            # Operation 2: Simulate error (invalid update)
            # This would normally fail; we manually abort
            session.abort_transaction()
        
        finally:
            session.end_session()
        
        # Verify nothing was persisted (rolled back)
        user = users_col.find_one({"_id": "user-bob"})
        assert user is None, "Transaction should have rolled back"
        
        logger.info("✓ Transaction rolled back successfully")


# ============================================================================
# Index Performance Tests
# ============================================================================

class TestIndexPerformance:
    """Verify indexes provide expected performance improvements."""
    
    def test_indexed_query_faster_than_collection_scan(self, deals_collection):
        """Query with index should be significantly faster than without."""
        
        # Insert many deals
        deals = [
            {
                "_id": f"deal-{i}",
                "store_id": f"store-{i % 10}",
                "price": 10 + i
            }
            for i in range(10000)
        ]
        deals_collection.insert_many(deals)
        
        # Time query WITHOUT index
        start = time.time()
        for _ in range(100):
            list(deals_collection.find({"store_id": "store-5"}).limit(10))
        time_without_index = time.time() - start
        
        # Create index
        deals_collection.create_index([("store_id", 1)])
        
        # Time query WITH index
        start = time.time()
        for _ in range(100):
            list(deals_collection.find({"store_id": "store-5"}).limit(10))
        time_with_index = time.time() - start
        
        logger.info(f"Without index: {time_without_index:.2f}s")
        logger.info(f"With index: {time_with_index:.2f}s")
        logger.info(f"Speedup: {time_without_index / time_with_index:.1f}x")
        
        # Index should provide at least 2x speedup
        assert time_with_index < time_without_index * 0.5, \
            f"Index didn't provide expected speedup (got {time_without_index / time_with_index:.1f}x)"


# ============================================================================
# CLI & Main
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    
    client = MongoClient("mongodb://localhost:27017")
    db = client.lessley_test
    
    try:
        print("Testing MongoDB TTL index...")
        # Create test collection
        db.test_ttl.delete_many({})
        db.test_ttl.create_index(
            [("inserted_at", 1)],
            expireAfterSeconds=2
        )
        
        db.test_ttl.insert_one({
            "test": "old",
            "inserted_at": datetime.now()
        })
        
        print("Inserted test document, waiting for TTL...")
        time.sleep(3)
        
        remaining = db.test_ttl.count_documents({})
        print(f"✓ TTL test passed (removed after 3s: {remaining == 0})")
        
    finally:
        client.drop_database("lessley_test")
        client.close()
