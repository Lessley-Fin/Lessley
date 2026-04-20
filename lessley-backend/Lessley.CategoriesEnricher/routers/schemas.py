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
    mcc_codes: list[int]
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


class ClubScoreSchema(BaseModel):
    """Schema for club recommendation score"""

    club_id: str
    club_name: str
    hit_count: int
    total_stores: int


class RecommendationByCategoryRequestSchema(BaseModel):
    """Schema for recommendation by category request"""

    user_id: str


class RecommendationByCategoryResponseSchema(BaseModel):
    """Schema for recommendation by category response"""

    user_id: str
    club_scores: list[ClubScoreSchema]
    recommended_club: Optional[ClubScoreSchema] = None
