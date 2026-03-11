import pandas as pd


def normalize_amount_spent(row: dict) -> float:
    """Reusable logic to calculate the absolute spent amount with fallbacks."""
    charged = row.get("amount.chargedAmount.amount")
    if pd.notna(charged) and charged != "":
        return abs(float(charged))

    original = row.get("amount.originalAmount.amount")
    if pd.notna(original) and original != "":
        return abs(float(original))

    return 0.0


def normalize_merchant_name(row: dict) -> str:
    """Reusable logic to safely extract and trim the merchant name."""
    name = row.get("merchantName")
    # str.strip() removes leading/trailing whitespaces
    if pd.notna(name) and str(name).strip() != "":
        return str(name).strip()
    return "Unknown Merchant"
