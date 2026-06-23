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


class StoreCategoryRequestSchema(BaseModel):
    """Schema for store category classification request"""

    store_name: str


class StoreCategoryResponseSchema(BaseModel):
    """Schema for store category classification response"""

    official_name: str
    mcc_codes: list[str]
    confidence_level: str


class DealCategoryRequestSchema(BaseModel):
    """Schema for deal category classification request"""

    deal_name: str
    deal_description: Optional[str] = None


class DealCategoryResponseSchema(BaseModel):
    """Schema for deal category classification response"""

    deal_name: str
    category: str
    subcategory: str
    relevance_score: float
    confidence_level: str


class ClassifyDealRequestSchema(BaseModel):
    deal_id: str


class ClassifyDealResponseSchema(BaseModel):
    deal_id: str
    deal_title: str
    store_id: str
    store_name: str
    store_official_name: str
    mcc_codes: list[str]
    confidence_level: str
    reasoning: str


class StoreClassificationResult(BaseModel):
    store_id: str
    store_name: str
    store_official_name: str
    mcc_codes: list[str]
    confidence_level: str
    status: str
    error: Optional[str] = None


class ClassifyAllStoresRequestSchema(BaseModel):
    page: int = 1
    page_size: int = 20


class ClassifyAllStoresResponseSchema(BaseModel):
    total_stores: int
    page: int
    page_size: int
    classified: int
    skipped: int
    failed: int
    results: list[StoreClassificationResult]
