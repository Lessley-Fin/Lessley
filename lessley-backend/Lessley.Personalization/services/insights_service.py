import pandas as pd

from services.mcc_service import get_mcc_service


class InsightsService:
    def __init__(self):
        self.mcc_service = get_mcc_service()  # Inject the MCC service dependency

    def get_top_3_spending_categories(self, transactions: dict) -> list[dict]:
        """
        Analyzes raw Open Finance JSON transactions and returns the top 3 categories by total spend.
        """
        if not transactions or "items" not in transactions:
            return []

        # 1. Load the raw JSON array into a Pandas DataFrame
        df = pd.json_normalize(transactions["items"])

        # 2. Extract the main category and the charged amount
        # (pd.json_normalize flattens nested JSON, so 'category.main' becomes the column name)
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

        # 4 . Expenses are negative (e.g., -326). We want the absolute value to calculate total spend.
        analysis_df["amount_spent"] = analysis_df["amount.chargedAmount.amount"].abs()

        # 4. Group by the category, sum the amounts, and sort descending
        top_categories = (
            analysis_df.groupby("category")["amount_spent"]
            .sum()
            .reset_index()
            .sort_values(by="amount_spent", ascending=False)
        )

        # 5. Take the top 3 and convert back to a standard Python dictionary list
        top_3 = top_categories.head(3).to_dict(orient="records")

        return top_3

    def get_top_spending_categories(self, transactions: dict) -> list[dict]:
        """
        Analyzes raw Open Finance JSON transactions and returns the top 3 categories by total spend.
        """
        if not transactions or "items" not in transactions:
            return []

        # 1. Load the raw JSON array into a Pandas DataFrame
        df = pd.json_normalize(transactions["items"])

        # 2. Extract the main category and the charged amount
        # (pd.json_normalize flattens nested JSON, so 'category.main' becomes the column name)
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

        # 4 . Expenses are negative (e.g., -326). We want the absolute value to calculate total spend.
        analysis_df["amount_spent"] = analysis_df["amount.chargedAmount.amount"].abs()

        # 4. Group by the category, sum the amounts, and sort descending
        top_categories = (
            analysis_df.groupby("category")["amount_spent"]
            .sum()
            .reset_index()
            .sort_values(by="amount_spent", ascending=False)
        )

        # 5. Take the top 3 and convert back to a standard Python dictionary list
        top_3 = top_categories.to_dict(orient="records")

        return top_3


# Dependency Injection provider function
def get_insights_service():
    return InsightsService()
