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
    relevant_category: list[MccCountSchema]


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
