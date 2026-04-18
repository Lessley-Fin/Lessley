from pydantic import BaseModel
from typing import Optional


class TransactionSchema(BaseModel):
    """Schema for transaction data"""

    transaction_id: str
    amount: float
    description: str
    category: Optional[str] = None


class CategoryEnrichmentRequestSchema(BaseModel):
    """Schema for category enrichment request"""

    transactions: list[TransactionSchema]
    user_id: Optional[str] = None
