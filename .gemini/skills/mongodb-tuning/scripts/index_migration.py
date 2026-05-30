"""
MongoDB Index Migration and Management

Safe creation, monitoring, and rollback of indexes in production.

For Lessley database maintenance and performance tuning.

Usage:
    python index_migration.py --action create-all --mongodb-uri mongodb://mongo:27017
    python index_migration.py --action list-indexes
    python index_migration.py --action analyze-query --query store_id
"""

import logging
import argparse
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

from pymongo import MongoClient
from pymongo.errors import OperationFailure


logger = logging.getLogger(__name__)


class MongoIndexManager:
    """Manage MongoDB indexes for production environments."""
    
    def __init__(self, mongodb_uri: str, db_name: str = "lessley"):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[db_name]
    
    # =========================================================================
    # Index Definitions: Production Indexes for Lessley
    # =========================================================================
    
    INDEXES = {
        "deals": [
            {
                "name": "idx_store_active_deals",
                "keys": [("store_id", 1), ("valid_until", -1)],
                "options": {
                    "background": True,
                    "unique": False
                },
                "reason": "Query: all active deals for a store, sorted by expiry"
            },
            {
                "name": "idx_deal_list_view",
                "keys": [("store_id", 1), ("deal_name", 1), ("discount_value", 1)],
                "options": {
                    "background": True,
                    "unique": False
                },
                "reason": "Covered query: mobile app list view (no document lookup needed)"
            },
            {
                "name": "idx_deal_category",
                "keys": [("category", 1), ("popularity", -1)],
                "options": {
                    "background": True,
                    "unique": False
                },
                "reason": "Browse deals by category, sorted by popularity"
            }
        ],
        "stores": [
            {
                "name": "idx_store_location",
                "keys": [("location", "2dsphere")],
                "options": {
                    "background": True,
                    "unique": False
                },
                "reason": "Geospatial query: find stores within radius"
            },
            {
                "name": "idx_store_chain",
                "keys": [("chain_id", 1), ("branch_id", 1)],
                "options": {
                    "background": True,
                    "unique": False
                },
                "reason": "Find all branches of a chain"
            }
        ],
        "users": [
            {
                "name": "idx_user_email",
                "keys": [("email", 1)],
                "options": {
                    "background": True,
                    "unique": True,
                    "sparse": True
                },
                "reason": "Unique email constraint + fast user lookup by email"
            },
            {
                "name": "idx_user_clubs",
                "keys": [("clubs.name", 1)],
                "options": {
                    "background": True,
                    "unique": False
                },
                "reason": "Find users with specific club membership"
            },
            {
                "name": "idx_user_updated",
                "keys": [("updated_at", -1)],
                "options": {
                    "background": True,
                    "unique": False
                },
                "reason": "Recent user updates, for audit/sync"
            }
        ],
        "analytics": [
            {
                "name": "idx_analytics_user",
                "keys": [("user_id", 1)],
                "options": {
                    "background": True,
                    "unique": False
                },
                "reason": "Fast analytics lookup by user"
            },
            {
                "name": "idx_analytics_updated",
                "keys": [("updated_at", -1)],
                "options": {
                    "background": True,
                    "unique": False
                },
                "reason": "Recent analytics updates for recomputation"
            }
        ]
    }
    
    # =========================================================================
    # Index Creation
    # =========================================================================
    
    def create_all_indexes(self) -> Dict[str, Dict[str, bool]]:
        """
        Create all production indexes defined in INDEXES.
        
        Returns:
            {collection: {index_name: success}}
        """
        results = {}
        
        for collection_name, indexes in self.INDEXES.items():
            results[collection_name] = {}
            
            for index_def in indexes:
                success = self._create_index(collection_name, index_def)
                results[collection_name][index_def["name"]] = success
        
        return results
    
    def _create_index(self, collection_name: str, index_def: Dict[str, Any]) -> bool:
        """Create a single index with error handling."""
        
        try:
            collection = self.db[collection_name]
            
            index_name = index_def["name"]
            keys = index_def["keys"]
            options = index_def.get("options", {})
            reason = index_def.get("reason", "")
            
            logger.info(f"Creating index '{index_name}' on {collection_name}...")
            logger.info(f"  Keys: {keys}")
            logger.info(f"  Reason: {reason}")
            
            # Check if index already exists
            existing_indexes = {idx["name"]: idx for idx in collection.list_indexes()}
            
            if index_name in existing_indexes:
                logger.info(f"  Index already exists (skipped)")
                return True
            
            # Create index with background option
            collection.create_index(keys, name=index_name, **options)
            
            logger.info(f"  ✓ Index created successfully")
            return True
        
        except OperationFailure as e:
            logger.error(f"  ✗ Failed to create index: {e}")
            return False
    
    # =========================================================================
    # Index Inspection
    # =========================================================================
    
    def list_all_indexes(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all indexes across all collections."""
        
        results = {}
        
        for collection_name in self.INDEXES.keys():
            indexes = self.list_collection_indexes(collection_name)
            results[collection_name] = indexes
        
        return results
    
    def list_collection_indexes(self, collection_name: str) -> List[Dict[str, Any]]:
        """List all indexes on a specific collection."""
        
        try:
            collection = self.db[collection_name]
            
            indexes = []
            for index_info in collection.list_indexes():
                indexes.append({
                    "name": index_info.get("name"),
                    "keys": index_info.get("key"),
                    "size_bytes": index_info.get("size", "unknown"),
                    "unique": index_info.get("unique", False)
                })
            
            return indexes
        
        except Exception as e:
            logger.error(f"Error listing indexes for {collection_name}: {e}")
            return []
    
    def show_index_details(self, collection_name: str):
        """Pretty-print index details."""
        
        indexes = self.list_collection_indexes(collection_name)
        
        print(f"\n{'='*70}")
        print(f"Indexes for collection: {collection_name}")
        print(f"{'='*70}")
        
        if not indexes:
            print("No indexes found")
            return
        
        for idx in indexes:
            print(f"\nIndex: {idx['name']}")
            print(f"  Keys: {idx['keys']}")
            print(f"  Size: {idx['size_bytes']} bytes")
            print(f"  Unique: {idx['unique']}")
    
    # =========================================================================
    # Index Analysis (using profiling)
    # =========================================================================
    
    def enable_profiling(self, slow_ms: int = 100):
        """
        Enable MongoDB profiling to capture slow queries.
        
        Args:
            slow_ms: Threshold in milliseconds for "slow" queries
        """
        
        try:
            self.db.set_profiling_level(1, slow_ms=slow_ms)
            logger.info(f"Profiling enabled (slow_ms={slow_ms})")
        except Exception as e:
            logger.error(f"Failed to enable profiling: {e}")
    
    def analyze_index_usage(self) -> Dict[str, int]:
        """
        Analyze which indexes are being used (requires profiling enabled).
        
        Returns:
            {index_name: usage_count}
        """
        
        try:
            profile_collection = self.db.system.profile
            
            pipeline = [
                {
                    "$match": {
                        "execStats.executionStages.indexName": {"$exists": True}
                    }
                },
                {
                    "$group": {
                        "_id": "$execStats.executionStages.indexName",
                        "count": {"$sum": 1}
                    }
                },
                {
                    "$sort": {"count": -1}
                }
            ]
            
            results = {}
            for result in profile_collection.aggregate(pipeline):
                index_name = result.get("_id", "unknown")
                usage_count = result.get("count", 0)
                results[index_name] = usage_count
            
            return results
        
        except Exception as e:
            logger.error(f"Error analyzing index usage: {e}")
            return {}
    
    # =========================================================================
    # Index Optimization & Cleanup
    # =========================================================================
    
    def find_unused_indexes(self) -> List[str]:
        """Identify indexes that are not being used (requires profiling data)."""
        
        used = self.analyze_index_usage()
        
        all_indexes = self.list_all_indexes()
        unused = []
        
        for collection_name, indexes in all_indexes.items():
            for idx in indexes:
                if idx["name"] not in used and idx["name"] != "_id_":
                    unused.append(f"{collection_name}.{idx['name']}")
        
        return unused
    
    def drop_index(self, collection_name: str, index_name: str) -> bool:
        """
        Safely drop an index.
        
        Args:
            collection_name: Collection to drop from
            index_name: Name of index to drop
        
        Returns:
            True if dropped successfully
        """
        
        try:
            if index_name == "_id_":
                logger.error("Cannot drop _id index")
                return False
            
            collection = self.db[collection_name]
            collection.drop_index(index_name)
            logger.info(f"Dropped index: {collection_name}.{index_name}")
            return True
        
        except OperationFailure as e:
            logger.error(f"Failed to drop index: {e}")
            return False
    
    # =========================================================================
    # Cleanup & Utilities
    # =========================================================================
    
    def reindex_collection(self, collection_name: str) -> bool:
        """
        Rebuild all indexes for a collection (useful after data migration).
        
        Warning: This can lock the collection for a while.
        """
        
        try:
            collection = self.db[collection_name]
            logger.info(f"Reindexing collection: {collection_name}")
            collection.reindex()
            logger.info(f"Reindexing complete")
            return True
        
        except Exception as e:
            logger.error(f"Reindexing failed: {e}")
            return False
    
    def close(self):
        """Close MongoDB connection."""
        self.client.close()


# ============================================================================
# CLI & Main
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="MongoDB Index Management")
    parser.add_argument("--mongodb-uri", default="mongodb://localhost:27017", help="MongoDB URI")
    parser.add_argument("--mongodb-db", default="lessley", help="Database name")
    
    subparsers = parser.add_subparsers(dest="action")
    
    # Action: create-all
    subparsers.add_parser("create-all", help="Create all production indexes")
    
    # Action: list-indexes
    list_parser = subparsers.add_parser("list-indexes", help="List all indexes")
    list_parser.add_argument("--collection", help="Specific collection (optional)")
    
    # Action: analyze-usage
    subparsers.add_parser("analyze-usage", help="Analyze index usage (requires profiling)")
    
    # Action: find-unused
    subparsers.add_parser("find-unused", help="Find unused indexes")
    
    # Action: drop
    drop_parser = subparsers.add_parser("drop", help="Drop an index")
    drop_parser.add_argument("collection", help="Collection name")
    drop_parser.add_argument("index", help="Index name")
    
    args = parser.parse_args()
    
    manager = MongoIndexManager(args.mongodb_uri, args.mongodb_db)
    
    try:
        if args.action == "create-all":
            results = manager.create_all_indexes()
            print(json.dumps(results, indent=2))
        
        elif args.action == "list-indexes":
            if args.collection:
                manager.show_index_details(args.collection)
            else:
                all_indexes = manager.list_all_indexes()
                print(json.dumps(all_indexes, indent=2, default=str))
        
        elif args.action == "analyze-usage":
            usage = manager.analyze_index_usage()
            print(json.dumps(usage, indent=2))
        
        elif args.action == "find-unused":
            unused = manager.find_unused_indexes()
            for idx in unused:
                print(f"Unused: {idx}")
        
        elif args.action == "drop":
            manager.drop_index(args.collection, args.index)
    
    finally:
        manager.close()
