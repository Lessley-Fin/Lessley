import logging
from typing import Dict, List
import pandas as pd

from .utils.data_frame_builder import DataFrameBuilder
from .utils.normalize_rows import normalize_amount_spent, normalize_merchant_name
from models.transaction import Transaction
from models.db.entities import Deal, Store, Club
from routers.responses import (
    TransactionInsightSchema,
    MissedStoreDiscountSchema,
    MissedStoreSchema,
)

from services.mcc_service import MccService
from config.constants import LIMITS

logger = logging.getLogger(__name__)


class ProcessingCoreService:
    def __init__(self, mcc_service: MccService):
        self.mcc_service = mcc_service  # Inject the MCC service dependency
        self._deals_dict: Dict[str, List[Deal]] = {}  # {store_id: [deals]}
        self._stores_dict: Dict[str, Store] = {}  # {store_id: store}
        self._stores_by_mcc: Dict[int, List[Store]] = {}  # {mcc_code: [stores]}
        self._clubs_dict: Dict[str, Club] = {}  # {club_id: club}
        self._deals_loaded = False

    def get_top_spending_categories(
        self, transactions: list[Transaction], limit: int = LIMITS.TOP_CATEGORIES
    ) -> list[Transaction]:
        """
        Analyzes raw Open Finance JSON transactions and returns the top spending categories by total spend.

        Sorts by transaction count first, then by amount (both descending).

        Args:
            transactions: List of Transaction objects
            limit: Number of top categories to return (default: 20)

        Returns:
            List of Transaction objects with category, total_count, and total_amount
            [
                {"category": "FOOD_&_DRINKS - GROCERIES", "total_count": 15, "total_amount": 350.50},
                {"category": "TRANSPORT", "total_count": 8, "total_amount": 200.00}
            ]
        """
        if not transactions:
            return []

        return (
            DataFrameBuilder(transactions)
            .extract_columns(
                [
                    "category.main",
                    "category.sub",
                    "categoryCode",
                    "amount.chargedAmount.amount",
                    "amount.originalAmount.amount",
                ]
            )
            # Create concatenated category name (main + sub if exists)
            .apply_row_logic(
                "category",
                lambda row: (
                    row["category.sub"] if pd.notna(row.get("category.sub")) and row.get("category.sub") else "N/A"
                ),
            )
            # Calculate amount_spent with fallback logic
            .apply_row_logic("amount_spent", normalize_amount_spent)
            # Group by category: count transactions and sum amounts
            .group_and_aggregate(
                group_by="category",
                aggregations={
                    "total_count": ("amount_spent", "count"),
                    "total_amount": ("amount_spent", "sum"),
                    "mcc_codes": ("categoryCode", lambda x: list(x.dropna().unique())),
                },
                sort_by=["total_count", "total_amount"],
                ascending=[False, False],
            )
            # Limit and convert to list of dicts
            .limit_and_convert(limit)
        )

    def get_top_spending_accounts(
        self,
        transactions: list[Transaction],
        flat_columns: list[str] = None,
        group_by_column: str = "accountId",
        ascending: bool = False,
        limit: int = LIMITS.TOP_ACCOUNTS,
    ) -> list[Transaction]:
        """
        Analyzes raw Open Finance JSON transactions and returns the top accounts by total spend.

        Sorts by transaction count first, then by amount (both descending by default).

        Args:
            transactions: Dictionary containing transaction items
            flat_columns: List of columns to extract (default: standard account columns)
            group_by_column: Column name to group by (default: "accountId")
            ascending: Sort order (default: False = descending)
            limit: Number of top accounts to return (default: 10)

        Returns:
            List of Transaction objects with accountId, accountNumber, total_count, and total_amount
            [
                Transaction(accountId="123", accountNumber="****1234", total_count=50, total_amount=5000.00),
                Transaction(accountId="456", accountNumber="****5678", total_count=30, total_amount=3000.00)
            ]
        """
        if not transactions:
            return []

        # Set default columns if not provided
        if flat_columns is None:
            flat_columns = [
                "accountId",
                "accountNumber",
                "amount.chargedAmount.amount",
                "amount.originalAmount.amount",
            ]

        return (
            DataFrameBuilder(transactions)
            .extract_columns(flat_columns)
            # Calculate amount_spent with fallback logic
            .apply_row_logic("amount_spent", normalize_amount_spent)
            # Group by account: count transactions and sum amounts, also preserve account details
            .group_and_aggregate(
                group_by=group_by_column,
                aggregations={
                    "accountNumber": ("accountNumber", "first"),
                    "total_count": ("amount_spent", "count"),
                    "total_amount": ("amount_spent", "sum"),
                },
                sort_by=["total_count", "total_amount"],
                ascending=[ascending, ascending],
            )
            # Limit and convert to list of dicts
            .limit_and_convert(limit)
        )

    def get_top_spending_stores(
        self,
        transactions: list[Transaction],
        limit: int = LIMITS.TOP_STORES,
    ) -> list[Transaction]:
        """
        INFRASTRUCTURE: Analyzes transactions and returns stores with nested accounts.

        Creates hierarchical structure:
        - Groups by normalized merchant name
        - Calculates totals per merchant and per account
        - Accounts sorted by amount within each merchant (descending)
        - Merchants sorted by count then amount (both descending)

        Args:
            transactions: Dictionary containing transaction items
            limit: Number of top merchants to return (default: 50)

        Returns:
            List of nested Transaction objects:
            [
                Transaction(merchantName="STARBUCKS", total_count=10, total_amount=500.50, items=[...]),
                Transaction(merchantName="COFFEE SHOP", total_count=8, total_amount=400.00, items=[...])
            ]
        if not transactions:
            return []
                    "items": [
                        {"accountNumber": "****1234", "total_count": 6, "total_amount": 300.00},
                        {"accountNumber": "****5678", "total_count": 4, "total_amount": 200.50}
                    ]
                }
            ]
        """
        if not transactions:
            return []

        flat_columns = [
            "merchantName",
            "accountNumber",
            "amount.chargedAmount.amount",
            "amount.originalAmount.amount",
        ]

        return (
            DataFrameBuilder(transactions)
            .extract_columns(flat_columns)
            .apply_row_logic("amount_spent", normalize_amount_spent)
            .apply_row_logic("normalized_merchantName", normalize_merchant_name)
            # Group by merchant and account: count transactions and sum amounts
            .group_and_aggregate(
                group_by=["normalized_merchantName", "accountNumber"],
                aggregations={
                    "transaction_count": ("amount_spent", "count"),
                    "transaction_amount": ("amount_spent", "sum"),
                },
                sort_by=["transaction_count", "transaction_amount"],
                ascending=[False, False],
            )
            # Build nested structure
            # .limit_and_convert(limit)
            .build_nested_structure(
                primary_key="normalized_merchantName",
                secondary_key="accountNumber",
                count_col="transaction_count",
                amount_col="transaction_amount",
                limit=limit,
            )
        )

    async def _load_deals_and_stores_async(self) -> None:
        """
        Pre-load deals, stores, and clubs from MongoDB into memory dictionaries for efficient lookups.
        Indexes stores by: store_id and MCC codes.
        Indexes deals by: store_id.
        """
        if self._deals_loaded:
            logger.debug("Deals and stores already loaded, skipping reload")
            return

        logger.info("Loading deals, stores, and clubs from MongoDB...")
        try:
            # Load all stores
            stores_list = await Store.find_all().to_list()
            self._stores_dict = {store.store_id: store for store in stores_list}

            # Index stores by MCC codes for fast lookup
            for store in stores_list:
                for mcc_code in store.metadata.mcc_codes:
                    if mcc_code not in self._stores_by_mcc:
                        self._stores_by_mcc[mcc_code] = []
                    self._stores_by_mcc[mcc_code].append(store)

            logger.info(
                "Stores loaded and indexed",
                extra={
                    "reason": "Data preparation for missed savings analysis",
                    "extra_data": {
                        "store_count": len(self._stores_dict),
                        "mcc_unique_codes": len(self._stores_by_mcc),
                    },
                },
            )

            # Load all deals
            deals_list = await Deal.find_all().to_list()
            for deal in deals_list:
                if deal.store_id not in self._deals_dict:
                    self._deals_dict[deal.store_id] = []
                self._deals_dict[deal.store_id].append(deal)

            logger.info(
                "Deals loaded and indexed",
                extra={
                    "reason": "Data preparation for missed savings analysis",
                    "extra_data": {
                        "deal_count": len(deals_list),
                        "stores_with_deals": len(self._deals_dict),
                    },
                },
            )

            # Load all clubs
            clubs_list = await Club.find_all().to_list()
            self._clubs_dict = {club.club_id: club for club in clubs_list}

            logger.info(
                "Clubs loaded",
                extra={
                    "reason": "Data preparation for missed savings analysis",
                    "extra_data": {"club_count": len(self._clubs_dict)},
                },
            )

            self._deals_loaded = True
        except Exception as e:
            logger.error(
                f"Error loading deals and stores from MongoDB: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Database query failed",
                    "extra_data": {"error_type": type(e).__name__},
                },
            )
            raise

    def _has_active_deal(self, store_id: str) -> bool:
        """
        Check if a store has any active deals.

        Args:
            store_id: The store ID to check

        Returns:
            True if store has active deals, False otherwise
        """
        return store_id in self._deals_dict and len(self._deals_dict[store_id]) > 0

    def _find_alternative_stores_by_mcc(
        self, mcc_code: str | int, exclude_store_id: str = None
    ) -> Dict[str, List[Store]]:
        """
        Find alternative stores with active deals for a given MCC code.
        Groups stores by club.

        Args:
            mcc_code: The MCC code to search for
            exclude_store_id: Store ID to exclude from results (the original merchant)

        Returns:
            Dictionary mapping club_id -> list of stores with deals (max 10 per club)
        """
        if not mcc_code:
            return {}

        try:
            mcc_int = int(mcc_code)
        except (ValueError, TypeError):
            logger.debug(
                f"Invalid MCC code for alternative store search: {mcc_code}",
                extra={
                    "reason": "Data validation",
                    "extra_data": {"mcc_code": str(mcc_code)},
                },
            )
            return {}

        # Find all stores with this MCC code
        stores_with_mcc = self._stores_by_mcc.get(mcc_int, [])

        # Filter to only stores with active deals, excluding the original merchant
        alternative_stores = [
            store
            for store in stores_with_mcc
            if store.store_id != exclude_store_id and self._has_active_deal(store.store_id)
        ]

        if not alternative_stores:
            return {}

        # Group alternative stores by club (max 10 per club)
        stores_by_club: Dict[str, List[Store]] = {}
        for club_id, club in self._clubs_dict.items():
            club_stores = [store for store in alternative_stores if store.store_id in (club.stores or [])]
            if club_stores:
                # Cap at 10 stores per club
                stores_by_club[club_id] = club_stores[:10]

        return stores_by_club

    def _build_missed_store_discount_schemas(
        self, stores_by_club: Dict[str, List[Store]]
    ) -> List[MissedStoreDiscountSchema]:
        """
        Build MissedStoreDiscountSchema objects from stores grouped by club.

        Args:
            stores_by_club: Dictionary mapping club_id -> list of Store objects

        Returns:
            List of MissedStoreDiscountSchema objects
        """
        missed_store_discounts = []

        for club_id, stores in stores_by_club.items():
            club = self._clubs_dict.get(club_id)
            if not club:
                continue

            missed_stores = [MissedStoreSchema(store_id=store.store_id, store_name=store.name) for store in stores]

            if missed_stores:
                missed_store_discounts.append(
                    MissedStoreDiscountSchema(
                        club_id=club_id,
                        missed_store=missed_stores,
                        store_count=len(missed_stores),
                    )
                )

        return missed_store_discounts

    async def calculate_missed_savings_async(self, transactions: list[Transaction]) -> list[TransactionInsightSchema]:
        """
        Analyzes user transactions to identify missed savings opportunities.
        For each transaction, finds deals available for stores matching the transaction's MCC code.

        Algorithm:
        1. Load deals, stores, clubs from MongoDB (one-time, cached)
        2. For each transaction with MCC code X:
           a. Find all stores with MCC code X that have active deals
           b. had_discount = true if any deal exists for MCC X
           c. Group alternative stores by club (max 10 per club)
           d. Build and return TransactionInsightSchema

        Args:
            transactions: List of transaction objects to analyze

        Returns:
            List of TransactionInsightSchema objects with missed savings analysis
        """
        start_count = len(transactions)
        logger.info(
            "Missed savings analysis started",
            extra={
                "reason": "Batch transaction processing",
                "extra_data": {"transaction_count": start_count},
            },
        )

        if not transactions:
            return []

        try:
            # Load data once (cached after first load)
            await self._load_deals_and_stores_async()

            insights: List[TransactionInsightSchema] = []
            processed_count = 0
            with_deals_found = 0
            alternatives_found = 0

            for transaction in transactions:
                # Skip transactions with missing critical data
                if not transaction.id or not transaction.categoryCode:
                    logger.debug(
                        "Skipping transaction with missing data",
                        extra={
                            "reason": "Data validation",
                            "extra_data": {
                                "has_id": transaction.id is not None,
                                "has_mcc": transaction.categoryCode is not None,
                            },
                        },
                    )
                    continue

                processed_count += 1

                # Find all stores with matching MCC that have active deals
                stores_by_club = self._find_alternative_stores_by_mcc(transaction.categoryCode)
                had_discount = len(stores_by_club) > 0
                missed_stores_list: List[MissedStoreDiscountSchema] = []

                # Build missed store discount schemas
                if stores_by_club:
                    missed_stores_list = self._build_missed_store_discount_schemas(stores_by_club)
                    with_deals_found += 1
                    alternatives_found += sum(schema.store_count for schema in missed_stores_list)

                # Build transaction insight
                insight = TransactionInsightSchema(
                    transaction_id=transaction.id,
                    had_discount=had_discount,
                    missed_store_discont=missed_stores_list,
                    store_name=transaction.merchantName or "N/A",
                    mcc_code=transaction.categoryCode,
                    mcc_description=(
                        transaction.category.sub if transaction.category and transaction.category.sub else "N/A"
                    ),
                    amount=(
                        transaction.amount.chargedAmount.amount
                        if transaction.amount
                        and transaction.amount.chargedAmount
                        and transaction.amount.chargedAmount.amount is not None
                        else (
                            transaction.amount.originalAmount.amount
                            if transaction.amount
                            and transaction.amount.originalAmount
                            and transaction.amount.originalAmount.amount is not None
                            else 0.0
                        )
                    ),
                )
                insights.append(insight)

            logger.info(
                "Missed savings analysis completed",
                extra={
                    "reason": "Batch processing complete",
                    "extra_data": {
                        "transaction_count": start_count,
                        "processed_count": processed_count,
                        "transactions_with_deals": with_deals_found,
                        "total_alternative_stores": alternatives_found,
                        "insights_returned": len(insights),
                    },
                },
            )

            return insights

        except Exception as e:
            logger.error(
                f"Error in calculate_missed_savings_async: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Service execution failure",
                    "extra_data": {
                        "transaction_count": len(transactions),
                        "error_type": type(e).__name__,
                    },
                },
            )
            raise
