from pydantic import BaseModel, Field, validator
from config.constants import LIMITS


class UserRequests(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255, description="User ID")

    @validator("user_id")
    def validate_user_id(cls, v):
        if not v.strip():
            raise ValueError("user_id cannot be empty")
        return v


class InsightsCalcRequests(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255, description="User ID")
    club_id: str = Field(..., min_length=1, max_length=255, description="Club ID")
    use_mock: bool = Field(False, description="Use mock data")
    time_filter: bool = Field(True, description="Filter by time")
    days: int = Field(LIMITS.DAYS, ge=1, le=365, description="Days to analyze (1-365)")

    @validator("user_id")
    def validate_user_id(cls, v):
        if not v.strip():
            raise ValueError("user_id cannot be empty")
        return v


class GetTransactionsByAccountRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255, description="User ID")
    account_id: str = Field(..., min_length=1, max_length=255, description="Account ID")
    time_filter: bool = Field(True, description="Filter by time")
    days: int = Field(LIMITS.DAYS, ge=1, le=365, description="Days to analyze (1-365)")


class GetTransactionsRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255, description="User ID")
    time_filter: bool = Field(True, description="Filter by time")
    days: int = Field(LIMITS.DAYS, ge=1, le=365, description="Days to analyze (1-365)")


class ClubScoreSchema(BaseModel):
    """Schema for club recommendation score"""

    club_id: str
    club_name: str
    hit_count: int
    total_stores: int


class MccCountSchema(BaseModel):
    mcc: int
    store_count: int


class ClubMccDistributionResponseSchema(BaseModel):
    club_id: str
    club_name: str
    relevant_category: list[MccCountSchema]


class RecommendationByCategoryRequestSchema(BaseModel):
    """Schema for recommendation by category request"""

    user_id: str = Field(..., min_length=1, max_length=255, description="User ID")

    @validator("user_id")
    def validate_user_id(cls, v):
        if not v.strip():
            raise ValueError("user_id cannot be empty")
        return v


class RecommendationByCategoryResponseSchema(BaseModel):
    """Schema for recommendation by category response"""

    user_id: str
    club_scores: list[ClubScoreSchema]
    recommended_club: ClubScoreSchema | None = None


class ClubRecommendationSchema(BaseModel):
    """Schema for a single club recommendation based on spending analysis."""

    club_id: str
    club_name: str
    hit_count: int
    total_stores: int
    fit_score: float = Field(..., ge=0, le=1, description="The ratio of matching stores to total stores in the club.")


class ClubRecommendationResponseSchema(BaseModel):
    """Schema for the club recommendation by spending analysis response."""

    user_id: str
    recommendations: list[ClubRecommendationSchema]
