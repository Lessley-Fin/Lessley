import pandas as pd

from services.mcc_service import MccService


class InsightsService:
    def __init__(self, mcc_service: MccService):
        self.mcc_service = mcc_service  # Inject the MCC service dependency

    def get_top_spending_categories(
        self, transactions: dict, limit: int = 3
    ) -> list[dict]:
        """
        Analyzes raw Open Finance JSON transactions and returns the top spending categories by total spend.

        Args:
            transactions: Dictionary containing transaction items
            limit: Number of top categories to return (default: 3)

        Returns:
            List of dictionaries with category and amount_spent
        """
        if not transactions or "items" not in transactions:
            return []

        # 1. Load the raw JSON array into a Pandas DataFrame
        df = pd.json_normalize(transactions["items"])

        # 2. Extract the main category, sub category and the charged amount
        analysis_df = df[
            [
                "category.main",
                "category.sub",
                "categoryCode",
                "amount.chargedAmount.amount",
            ]
        ].copy()

        # 3. Create concatenated category name (main + sub if sub exists)
        analysis_df["category"] = analysis_df.apply(
            lambda row: (
                f"{row['category.main']} - {row['category.sub']}"
                if pd.notna(row["category.sub"]) and row["category.sub"]
                else row["category.main"]
            ),
            axis=1,
        )
        analysis_df["category"] = analysis_df["category"].fillna("Uncategorized")

        # 4. Expenses are negative (e.g., -326). We want the absolute value to calculate total spend.
        analysis_df["amount_spent"] = analysis_df["amount.chargedAmount.amount"].abs()

        # 5. Group by the category, sum the amounts, and sort descending
        top_categories = (
            analysis_df.groupby("category")["amount_spent"]
            .sum()
            .reset_index()
            .sort_values(by="amount_spent", ascending=False)
        )

        # 6. Take the top N and convert back to a standard Python dictionary list
        top_n = top_categories.head(limit).to_dict(orient="records")

        return top_n

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
            flat_columns: List of columns to extract (optional, for compatibility)
            group_by_column: Column name to group by (default: "accountId")
            ascending: Sort order (default: False = descending)
            limit: Number of top accounts to return (default: 3)

        Returns:
            List of dictionaries with accountId, accountNumber, and amount_spent
        """
        if not transactions or "items" not in transactions:
            return []

        # STEP 1: Flatten nested JSON structure into a flat DataFrame
        # pd.json_normalize converts nested JSON (like amount.chargedAmount.amount)
        # into flat columns with dot notation (amount.chargedAmount.amount becomes a column name)
        df = pd.json_normalize(transactions["items"])

        # STEP 2: Select only the columns we need
        # .copy() creates a new DataFrame so we don't modify the original
        # We extract: accountId (group key), accountNumber (for display), and amount fields (for calculation)
        analysis_df = df[
            [
                "accountId",
                "accountNumber",
                "amount.chargedAmount.amount",
                "amount.originalAmount.amount",
            ]
        ].copy()

        # STEP 3: Create amount_spent column with fallback logic
        # For each row:
        # - Use chargedAmount if it exists and is not empty
        # - Fall back to originalAmount if chargedAmount is missing/empty
        # - Default to 0 if both are missing
        # abs() gives us positive values (expenses are stored as negative numbers)
        analysis_df["amount_spent"] = analysis_df.apply(
            lambda row: (
                abs(row["amount.chargedAmount.amount"])
                if pd.notna(row["amount.chargedAmount.amount"])
                and row["amount.chargedAmount.amount"] != ""
                else (
                    abs(row["amount.originalAmount.amount"])
                    if pd.notna(row["amount.originalAmount.amount"])
                    and row["amount.originalAmount.amount"] != ""
                    else 0
                )
            ),
            axis=1,
        )

        # STEP 4: Group by accountId and aggregate
        # .groupby() partitions the data by accountId so each account is one group
        # For each group, we need to preserve accountNumber (use 'first' since all rows with same accountId have same accountNumber)
        # and sum up all the amount_spent values
        top_accounts = (
            analysis_df.groupby(group_by_column, as_index=False)
            .agg(
                {
                    "accountNumber": "first",  # Get the first accountNumber (they're all the same per account)
                    "amount_spent": "sum",  # Sum all transactions for this account
                }
            )
            .sort_values(by="amount_spent", ascending=ascending)
        )

        # STEP 5: Select top N results and convert to list of dictionaries
        # .head(limit) keeps only the top N rows (ordered by amount_spent from step 4)
        # .to_dict(orient="records") converts each row into a dictionary
        return top_accounts.head(limit).to_dict(orient="records")
