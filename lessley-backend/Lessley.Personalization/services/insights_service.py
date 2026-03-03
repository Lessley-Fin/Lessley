import pandas as pd


class InsightsService:
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
        analysis_df = df[["category.main", "amount.chargedAmount.amount"]].copy()

        # 3. Expenses are negative (e.g., -326). We want the absolute value to calculate total spend.
        analysis_df["category"] = analysis_df["category.main"].fillna("Uncategorized")
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


# Dependency Injection provider function
def get_insights_service():
    return InsightsService()
