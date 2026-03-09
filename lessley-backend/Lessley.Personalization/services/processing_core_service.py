import pandas as pd
from typing import Callable, Optional, Dict, List, Any

from services.mcc_service import MccService


class DataFrameBuilder:
    """
    Generic DataFrame processing builder that allows composing operations in a fluent style.
    This eliminates code duplication and provides reusable building blocks.
    """
    
    def __init__(self, data: Any):
        """Initialize with raw data (list, dict, or already a DataFrame)"""
        self.df = None
        if isinstance(data, pd.DataFrame):
            self.df = data
        elif isinstance(data, list):
            self.df = pd.json_normalize(data)
        elif isinstance(data, dict):
            # Handle dict with "items" key or raw dict
            items = data.get("items", [data])
            self.df = pd.json_normalize(items)
        else:
            raise ValueError("Data must be a DataFrame, list, or dict")
    
    def extract_columns(self, columns: List[str]) -> "DataFrameBuilder":
        """
        STEP: Extract specific columns and create a copy to avoid modifying original.
        
        Args:
            columns: List of column names to extract
            
        Returns:
            Self for method chaining
        """
        self.df = self.df[columns].copy()
        return self
    
    def apply_row_logic(self, new_column: str, logic: Callable) -> "DataFrameBuilder":
        """
        STEP: Apply custom lambda/function logic to each row and create new column.
        
        Args:
            new_column: Name of the new column to create
            logic: Callable that takes a row and returns a value
                  Example: lambda row: abs(row["amount"]) if row["amount"] else 0
        
        Returns:
            Self for method chaining
        """
        self.df[new_column] = self.df.apply(logic, axis=1)
        return self
    
    def group_and_aggregate(
        self,
        group_by: str,
        aggregations: Dict[str, str],
        sort_by: str = None,
        ascending: bool = False,
    ) -> "DataFrameBuilder":
        """
        STEP: Group by column, apply aggregations, and sort results.
        
        Args:
            group_by: Column name to group by
            aggregations: Dict mapping column names to aggregation functions
                         Example: {"amount": "sum", "account": "first", "type": "first"}
                         Valid functions: "sum", "mean", "first", "last", "count", "max", "min"
            sort_by: Column to sort by (default: first aggregation column)
            ascending: Sort order (default: False = descending)
        
        Returns:
            Self for method chaining
        """
        self.df = (
            self.df.groupby(group_by, as_index=False)
            .agg(aggregations)
        )
        
        if sort_by is None:
            # Default to first aggregation column if not specified
            sort_by = list(aggregations.keys())[0]
        
        self.df = self.df.sort_values(by=sort_by, ascending=ascending)
        return self
    
    def limit_and_convert(self, limit: Optional[int] = None) -> List[Dict]:
        """
        STEP: Take top N rows and convert to list of dictionaries.
        
        Args:
            limit: Number of rows to keep (None = keep all)
        
        Returns:
            List of dictionaries (one dict per row)
        """
        if limit is not None:
            self.df = self.df.head(limit)
        
        return self.df.to_dict(orient="records")


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
            .extract_columns([
                "category.main",
                "category.sub",
                "categoryCode",
                "amount.chargedAmount.amount",
                "amount.originalAmount.amount",
            ])
            # Create concatenated category name (main + sub if exists)
            .apply_row_logic(
                "category",
                lambda row: (
                    f"{row['category.main']} - {row['category.sub']}"
                    if pd.notna(row["category.sub"]) and row["category.sub"]
                    else row["category.main"]
                ) or "Uncategorized"
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
                )
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
                )
            )
            # Group by account and aggregate
            .group_and_aggregate(
                group_by=group_by_column,
                aggregations={
                    "accountNumber": "first",
                    "amount_spent": "sum",
                },
                sort_by="amount_spent",
                ascending=ascending,
            )
            # Limit and convert to list of dicts
            .limit_and_convert(limit)
        )
