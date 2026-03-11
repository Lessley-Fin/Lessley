import pandas as pd
from .data_frame_service import DataFrameBuilder
from .utils import calc_amount_spent, clean_merchant_name

from services.mcc_service import MccService


class ProcessingCoreService:
    def __init__(self, mcc_service: MccService):
        self.mcc_service = mcc_service  # Inject the MCC service dependency

    def get_top_spending_categories(self, transactions: dict, limit: int = 20) -> list[dict]:
        """
        Analyzes raw Open Finance JSON transactions and returns the top spending categories by total spend.

        Sorts by transaction count first, then by amount (both descending).

        Args:
            transactions: Dictionary containing transaction items
            limit: Number of top categories to return (default: 20)

        Returns:
            List of dictionaries with category, total_count, and total_amount
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
                    (
                        f"{row['category.main']} - {row['category.sub']}"
                        if pd.notna(row["category.sub"]) and row["category.sub"]
                        else row["category.main"]
                    )
                    or "Uncategorized"
                ),
            )
            # Calculate amount_spent with fallback logic
            .apply_row_logic("amount_spent", calc_amount_spent)
            # Group by category: count transactions and sum amounts
            .group_and_aggregate(
                group_by="category",
                aggregations={
                    "total_count": ("amount_spent", "count"),
                    "total_amount": ("amount_spent", "sum"),
                },
                sort_by=["total_count", "total_amount"],
                ascending=[False, False],
            )
            # Limit and convert to list of dicts
            .limit_and_convert(limit)
        )

    def get_top_spending_accounts(
        self,
        transactions: dict,
        flat_columns: list[str] = None,
        group_by_column: str = "accountId",
        ascending: bool = False,
        limit: int = 10,
    ) -> list[dict]:
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
            List of dictionaries with accountId, accountNumber, total_count, and total_amount
            [
                {"accountId": "123", "accountNumber": "****1234", "total_count": 50, "total_amount": 5000.00},
                {"accountId": "456", "accountNumber": "****5678", "total_count": 30, "total_amount": 3000.00}
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
            .apply_row_logic("amount_spent", calc_amount_spent)
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
        transactions: dict,
        limit: int = 50,
    ) -> list[dict]:
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
            List of nested dictionaries:
            [
                {
                    "merchantName": "STARBUCKS",
                    "total_count": 10,
                    "total_amount": 500.50,
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
            .apply_row_logic("amount_spent", calc_amount_spent)
            .apply_row_logic("normalized_merchantName", clean_merchant_name)
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
