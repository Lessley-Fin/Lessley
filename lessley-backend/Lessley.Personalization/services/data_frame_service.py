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

    def to_nested_list(self, primary_key: str, nested_key_name: str = "items", limit: int = None) -> List[Dict]:
        """
        Transforms a flat grouped dataframe into a nested dictionary structure.
        Example: Groups by 'category', nests the rest under 'items'.
        """
        if self.df.empty:
            return []

        print(f"DataFrame before nesting: {self.df.head()}")
        if limit is not None:
            self.df = self.df.head(limit)

        # Group by the primary key, and convert all other columns into a list of dictionaries
        nested_series = self.df.groupby(primary_key).apply(
            lambda x: x.drop(columns=[primary_key]).to_dict(orient="records")
        )

        # Convert the resulting pandas Series back into a clean list of dictionaries
        nested_list = [{primary_key: key, nested_key_name: values} for key, values in nested_series.items()]

        return nested_list
