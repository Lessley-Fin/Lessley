import pandas as pd
from typing import Callable, Optional, Dict, List, Any, Union


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
        # existing_cols = [col for col in columns if col in self.df.columns]
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
        group_by: Union[str, List[str]],
        aggregations: Dict[str, tuple],
        sort_by: Union[str, List[str]] = None,
        ascending: Union[bool, List[bool]] = False,
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
        self.df = self.df.groupby(group_by, as_index=False).agg(**aggregations)

        if sort_by is not None:
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

    def build_nested_structure(
        self,
        primary_key: str,
        secondary_key: str,
        count_col: str,
        amount_col: str,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        STEP: Creates a hierarchical structure where:
        - Primary key groups with aggregated counts/amounts
        - Secondary key items nested under each primary group
        - Items sorted by amount within each group (descending)
        - Groups sorted by count then amount (both descending)

        Args:
            primary_key: Column name for top-level grouping (e.g., "merchantName")
            secondary_key: Column name for nested items (e.g., "accountNumber")
            count_col: Column name for transaction count
            amount_col: Column name for total amount
            limit: Maximum number of primary groups to return

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
        if self.df.empty:
            return []

        nested_structure = {}

        # Build nested dict from flat grouped data
        for _, row in self.df.iterrows():
            primary_value = row[primary_key]
            secondary_value = row[secondary_key]
            count_value = row[count_col]
            amount_value = row[amount_col]

            # Initialize primary group if not exists
            if primary_value not in nested_structure:
                nested_structure[primary_value] = {
                    primary_key: primary_value,
                    "total_count": 0,
                    "total_amount": 0.0,
                    "items": [],
                }

            # Accumulate totals
            nested_structure[primary_value]["total_count"] += count_value
            nested_structure[primary_value]["total_amount"] += amount_value

            # Add secondary item
            nested_structure[primary_value]["items"].append(
                {
                    secondary_key: secondary_value,
                    "total_count": count_value,
                    "total_amount": amount_value,
                }
            )

        # Sort items within each group by amount (descending)
        for group_data in nested_structure.values():
            group_data["items"].sort(key=lambda x: x["total_amount"], reverse=True)

        # Convert to list and sort groups by total_count then total_amount (both descending)
        result = list(nested_structure.values())
        result.sort(key=lambda x: (x["total_count"], x["total_amount"]), reverse=True)

        # Apply limit
        if limit is not None:
            result = result[:limit]

        return result
