"""
MongoDB Transaction Example (Python)

Demonstrates ACID transactions using pymongo ClientSession.

For Lessley.Personalization and analytics services.

Usage:
    from transaction_example import PersonalizationTransactions
    
    tx = PersonalizationTransactions(mongodb_uri="mongodb://mongo:27017/lessley")
    success = tx.add_club_card("user-123", "hever", {
        "phone": "0543334422",
        "email": "user@example.com"
    })
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import time

from pymongo import MongoClient
from pymongo.errors import OperationFailure, ServerSelectionTimeout
from pymongo.client_session import ClientSession


logger = logging.getLogger(__name__)


class PersonalizationTransactions:
    """Manage multi-document transactions for user profile and analytics updates."""
    
    def __init__(self, mongodb_uri: str, db_name: str = "lessley", max_retries: int = 3):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[db_name]
        self.max_retries = max_retries
    
    # =========================================================================
    # Transaction 1: Add Club Card (Atomicity: profile + analytics)
    # =========================================================================
    
    def add_club_card(
        self,
        user_id: str,
        club_name: str,
        club_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a club card to user profile and atomically recalculate savings.
        
        If either step fails, both are rolled back.
        
        Args:
            user_id: User document ID
            club_name: Name of club (e.g., "hever", "hightechzone")
            club_metadata: Optional metadata (phone, email, etc.)
        
        Returns:
            True if transaction committed, False if rolled back
        """
        
        for attempt in range(self.max_retries):
            session = self.client.start_session()
            
            try:
                session.start_transaction()
                
                # ─────────────────────────────────────────────────────────────
                # Step 1: Add club card to user profile
                # ─────────────────────────────────────────────────────────────
                
                club_record = {
                    "name": club_name,
                    "metadata": club_metadata or {},
                    "added_at": datetime.now(),
                    "status": "active"
                }
                
                result = self.db.users.update_one(
                    {"_id": user_id},
                    {
                        "$push": {"clubs": club_record},
                        "$inc": {"club_count": 1},
                        "$set": {"updated_at": datetime.now()}
                    },
                    session=session
                )
                
                if result.matched_count == 0:
                    logger.warning(f"User not found: {user_id}")
                    session.abort_transaction()
                    return False
                
                logger.info(f"Added club card '{club_name}' to user {user_id}")
                
                # ─────────────────────────────────────────────────────────────
                # Step 2: Fetch updated user and recalculate savings
                # ─────────────────────────────────────────────────────────────
                
                updated_user = self.db.users.find_one(
                    {"_id": user_id},
                    session=session
                )
                
                if not updated_user:
                    logger.error(f"User disappeared mid-transaction: {user_id}")
                    session.abort_transaction()
                    return False
                
                # Calculate new savings based on all clubs
                new_savings = self._calculate_user_savings(updated_user)
                
                # ─────────────────────────────────────────────────────────────
                # Step 3: Update analytics collection
                # ─────────────────────────────────────────────────────────────
                
                self.db.analytics.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "total_savings": new_savings,
                            "club_count": len(updated_user.get("clubs", [])),
                            "last_club_added": club_name,
                            "updated_at": datetime.now()
                        }
                    },
                    upsert=True,
                    session=session
                )
                
                logger.info(f"Updated analytics: savings={new_savings}, clubs={len(updated_user['clubs'])}")
                
                # ─────────────────────────────────────────────────────────────
                # Commit: all three operations succeed together
                # ─────────────────────────────────────────────────────────────
                
                session.commit_transaction()
                logger.info(f"Transaction committed for user {user_id}")
                return True
            
            except ServerSelectionTimeout as e:
                # Transient network error: retry with exponential backoff
                if attempt < self.max_retries - 1:
                    backoff = 0.5 * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed (network error), retrying in {backoff}s...")
                    time.sleep(backoff)
                else:
                    logger.error(f"Transaction failed after {self.max_retries} retries (network error)")
                    raise
            
            except OperationFailure as e:
                # Logical error: don't retry
                logger.error(f"Transaction failed (logical error): {e}")
                session.abort_transaction()
                return False
            
            finally:
                session.end_session()
        
        return False
    
    # =========================================================================
    # Transaction 2: Update Savings with Multi-Step Recalculation
    # =========================================================================
    
    def recalculate_user_savings(self, user_id: str) -> Optional[float]:
        """
        Atomically recalculate user savings across all clubs and update both
        users and analytics collections.
        
        Returns:
            New savings amount, or None if transaction failed
        """
        
        session = self.client.start_session()
        
        try:
            session.start_transaction()
            
            # Step 1: Fetch current user state
            user = self.db.users.find_one({"_id": user_id}, session=session)
            
            if not user:
                logger.warning(f"User not found for savings recalculation: {user_id}")
                session.abort_transaction()
                return None
            
            # Step 2: Calculate savings
            new_savings = self._calculate_user_savings(user)
            
            # Step 3: Update users collection
            self.db.users.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "estimated_savings": new_savings,
                        "savings_calculated_at": datetime.now()
                    }
                },
                session=session
            )
            
            # Step 4: Update analytics
            self.db.analytics.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "total_savings": new_savings,
                        "updated_at": datetime.now()
                    }
                },
                upsert=True,
                session=session
            )
            
            # Step 5: Log the recalculation event
            self.db.savings_log.insert_one(
                {
                    "user_id": user_id,
                    "savings": new_savings,
                    "club_count": len(user.get("clubs", [])),
                    "timestamp": datetime.now()
                },
                session=session
            )
            
            session.commit_transaction()
            logger.info(f"Savings recalculated and committed for user {user_id}: ${new_savings:.2f}")
            return new_savings
        
        except OperationFailure as e:
            logger.error(f"Savings recalculation failed: {e}")
            session.abort_transaction()
            return None
        
        finally:
            session.end_session()
    
    # =========================================================================
    # Transaction 3: Batch User Migration with Atomicity
    # =========================================================================
    
    def migrate_user_to_v2_schema(self, user_id: str) -> bool:
        """
        Atomically migrate a user to new schema version, updating
        multiple related collections.
        
        Returns True if migration committed, False if rolled back.
        """
        
        session = self.client.start_session()
        
        try:
            session.start_transaction()
            
            # Step 1: Update user to v2 schema
            self.db.users.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "schema_version": 2,
                        "migrated_at": datetime.now()
                    },
                    "$unset": {"legacy_field": 1}  # Remove old field
                },
                session=session
            )
            
            # Step 2: Create analytics record if missing
            self.db.analytics.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "schema_version": 2,
                        "migrated_at": datetime.now()
                    }
                },
                upsert=True,
                session=session
            )
            
            # Step 3: Mark migration in audit log
            self.db.audit_log.insert_one(
                {
                    "action": "schema_migration",
                    "user_id": user_id,
                    "from_version": 1,
                    "to_version": 2,
                    "timestamp": datetime.now()
                },
                session=session
            )
            
            session.commit_transaction()
            logger.info(f"User {user_id} migrated to v2 schema")
            return True
        
        except OperationFailure as e:
            logger.error(f"Migration failed: {e}")
            session.abort_transaction()
            return False
        
        finally:
            session.end_session()
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _calculate_user_savings(self, user: Dict[str, Any]) -> float:
        """
        Calculate total savings from all club memberships.
        
        This is a simplified example; in production, fetch from a
        pricing/discount rules table.
        """
        
        clubs = user.get("clubs", [])
        
        # Stub: assume each club grants $10/month base + some variance
        base_per_club = 10.0
        total = base_per_club * len(clubs)
        
        # In production, this would call:
        # - discount_engine.calculate_savings_for_clubs(clubs)
        # - Which queries deal history and applies real rates
        
        return total
    
    def close(self):
        """Close MongoDB connection."""
        self.client.close()


# ============================================================================
# CLI & Testing
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="MongoDB Transaction Examples")
    parser.add_argument("--mongodb-uri", default="mongodb://localhost:27017", help="MongoDB URI")
    parser.add_argument("--mongodb-db", default="lessley", help="Database name")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # Command: add-club
    add_club_parser = subparsers.add_parser("add-club", help="Add club card to user")
    add_club_parser.add_argument("user_id", help="User ID")
    add_club_parser.add_argument("club_name", help="Club name")
    
    # Command: recalculate-savings
    recalc_parser = subparsers.add_parser("recalculate-savings", help="Recalculate user savings")
    recalc_parser.add_argument("user_id", help="User ID")
    
    args = parser.parse_args()
    
    tx = PersonalizationTransactions(
        mongodb_uri=args.mongodb_uri,
        db_name=args.mongodb_db
    )
    
    try:
        if args.command == "add-club":
            success = tx.add_club_card(args.user_id, args.club_name)
            print(f"Transaction: {'committed' if success else 'rolled back'}")
        
        elif args.command == "recalculate-savings":
            savings = tx.recalculate_user_savings(args.user_id)
            print(f"New savings: ${savings:.2f}" if savings else "Transaction failed")
    
    finally:
        tx.close()
