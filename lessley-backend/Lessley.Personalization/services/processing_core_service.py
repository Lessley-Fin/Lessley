import pandas as pd
from .data_frame_service import DataFrameBuilder
from .utils import calc_amount_spent, clean_merchant_name

from services.mcc_service import MccService


class ProcessingCoreService:
    def __init__(self, mcc_service: MccService):
        self.mcc_service = mcc_service  # Inject the MCC service dependency

    def get_top_spending_categories(self, transactions: dict, limit: int = 3) -> list[dict]:
        """
        Analyzes raw Open Finance JSON transactions and returns the top spending categories by total spend.

        Args:
            transactions: Dictionary containing transaction items
            limit: Number of top categories to return (default: 3)

        Returns:
            List of dictionaries with category and amount_spent
        """
        if not transactions:
            return []

        # BUILDING BLOCK PIPELINE:
        # 1. Normalize JSON → 2. Extract columns → 3. Create category name → 4. Calculate amounts → 5. Group & aggregate → 6. Limit & convert

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
            .apply_row_logic(
                "amount_spent",
                lambda row: (
                    abs(row["amount.chargedAmount.amount"])
                    if pd.notna(row["amount.chargedAmount.amount"]) and row["amount.chargedAmount.amount"] != ""
                    else (
                        abs(row["amount.originalAmount.amount"])
                        if pd.notna(row["amount.originalAmount.amount"]) and row["amount.originalAmount.amount"] != ""
                        else 0
                    )
                ),
            )
            # Group by category and sum amounts
            .group_and_aggregate(
                group_by="category",
                aggregations={"amount_spent": "sum"},
                sort_by="amount_spent",
                ascending=False,
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
        limit: int = 3,
    ) -> list[dict]:
        """
        Analyzes raw Open Finance JSON transactions and returns the top accounts by total spend,
        including accountNumber in the result.

        Uses chargedAmount if available, falls back to originalAmount if chargedAmount is null/empty,
        otherwise defaults to 0.

        Args:
            transactions: Dictionary containing transaction items
            flat_columns: List of columns to extract (default: standard account columns)
            group_by_column: Column name to group by (default: "accountId")
            ascending: Sort order (default: False = descending)
            limit: Number of top accounts to return (default: 3)

        Returns:
            List of dictionaries with accountId, accountNumber, and amount_spent
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

        # BUILDING BLOCK PIPELINE:
        # 1. Normalize JSON → 2. Extract columns → 3. Calculate amounts → 4. Group & aggregate → 5. Limit & convert

        return (
            DataFrameBuilder(transactions)
            .extract_columns(flat_columns)
            # Calculate amount_spent with fallback logic
            .apply_row_logic(
                "amount_spent",
                lambda row: (
                    abs(row["amount.chargedAmount.amount"])
                    if pd.notna(row["amount.chargedAmount.amount"]) and row["amount.chargedAmount.amount"] != ""
                    else (
                        abs(row["amount.originalAmount.amount"])
                        if pd.notna(row["amount.originalAmount.amount"]) and row["amount.originalAmount.amount"] != ""
                        else 0
                    )
                ),
            )
            # Group by account and aggregate
            .group_and_aggregate(
                group_by=group_by_column,
                aggregations={
                    "accountNumber": "first",
                    "providerId": "first",
                    "type": "first",
                    "amount_spent": "sum",
                },
                sort_by="amount_spent",
                ascending=ascending,
            )
            # Limit and convert to list of dicts
            .limit_and_convert(limit)
        )

    def get_top_spending_stores(
        self,
        transactions: dict,
    ) -> list[dict]:
        """
        Analyzes raw Open Finance JSON transactions and returns the top accounts by total spend,
        including accountNumber in the result.

        Uses chargedAmount if available, falls back to originalAmount if chargedAmount is null/empty,
        otherwise defaults to 0.

        Args:
            transactions: Dictionary containing transaction items
            group_by_column: Column name to group by (default: "merchantName")
            ascending: Sort order (default: False = descending)
            limit: Number of top accounts to return (default: 15)

        Returns:
            List of dictionaries with merchantName, accountNumber, and amount_spent
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
            .group_and_aggregate(
                group_by=["normalized_merchantName", "accountNumber"],
                aggregations={
                    "transaction_count": ("amount_spent", "size"),
                    "total_spent": ("amount_spent", "sum"),
                },
                sort_by=["transaction_count", "total_spent"],
                ascending=[False, False],
            )
            # .limit_and_convert(30)
            .to_nested_list("normalized_merchantName", "accountNumber", 15)
        )
