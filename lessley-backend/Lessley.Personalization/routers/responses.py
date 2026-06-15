from pydantic import BaseModel, Field
from typing import Generic, TypeVar
from datetime import datetime

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Consistent response format for all endpoints"""

    status: str  # "success" or "error"
    count: int | None = None
    data: T | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BasicResponse(BaseModel, Generic[T]):
    """Basic response format for endpoints that don't return data"""

    status: str  # "success" or "error"
    data: T | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MccCountSchema(BaseModel):
    mcc: int
    store_count: int


class ClubMccDistributionResponseSchema(BaseModel):
    club_id: str
    club_name: str
    categories: list[MccCountSchema]


class ClubRecommendationSchema(BaseModel):
    """Schema for a single club recommendation based on spending analysis."""

    club_id: str
    club_name: str
    hit_count: int
    total_stores: int
    fit_score: float = Field(..., ge=0, le=1, description="The ratio of matching stores to total stores in the club.")
    is_recommended: bool = Field(
        ..., description="Whether the club is recommended based on the fit score and threshold."
    )
    is_member: bool = Field(
        False, description="Whether the user is already a member of this club."
    )


class ClubRecommendationResponseSchema(BaseModel):
    """Schema for the club recommendation by spending analysis response."""

    user_id: str
    recommendations: list[ClubRecommendationSchema]


class DealRecommendationResponseSchema(BaseModel):
    """Schema for a single deal recommendation response."""

    deal_id: str
    user_id: str
    store_id: str
    club_id: str
    is_recommended: bool
    fit_score: float
    matching_mcc_codes: list[int]


class MissedStoreSchema(BaseModel):
    """Schema for a store with alternative discount."""

    store_id: str = Field(..., description="The store ID")
    store_name: str = Field(..., description="The store name")


class MissedStoreDiscountSchema(BaseModel):
    """Schema for alternative stores with active discounts for a given club."""

    club_id: str = Field(..., description="The club ID offering the discount")
    missed_store: list[MissedStoreSchema] = Field(..., description="List of stores with active discounts in this club")
    store_count: int = Field(..., description="Total count of stores with discounts in this club")


class TransactionInsightSchema(BaseModel):
    """Schema for a single transaction's missed savings insight."""

    transaction_id: str = Field(..., description="Unique transaction identifier")
    had_discount: bool = Field(..., description="Whether the transaction's store had an active deal")
    store_name: str = Field(..., description="The name of the store where the transaction occurred")
    mcc_code: int = Field(..., description="The MCC code of the store where the transaction occurred")
    mcc_description: str = Field(..., description="The description of the MCC code")
    amount: float = Field(..., description="The amount of the transaction")
    missed_store_discont: list[MissedStoreDiscountSchema] = Field(
        default_factory=list,
        description="List of alternative stores grouped by club where better deals were available",
    )
