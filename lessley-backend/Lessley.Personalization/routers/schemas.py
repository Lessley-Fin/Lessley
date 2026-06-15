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
    use_mock: bool = Field(False, description="Use mock data")
    time_filter: bool = Field(True, description="Filter by time")
    days: int = Field(LIMITS.DAYS, ge=1, le=365, description="Days to analyze (1-365)")

    @validator("user_id")
    def validate_user_id(cls, v):
        if not v.strip():
            raise ValueError("user_id cannot be empty")
        return v


class ClubCalcRequests(BaseModel):
    club_id: str = Field(..., min_length=1, max_length=255, description="Club ID")

    @validator("club_id")
    def validate_club_id(cls, v):
        if not v.strip():
            raise ValueError("club_id cannot be empty")
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


class RecommendationByCategoryRequestSchema(BaseModel):
    """Schema for recommendation by category request"""

    user_id: str = Field(..., min_length=1, max_length=255, description="User ID")
    use_mock: bool = Field(False, description="Use mock data")
    time_filter: bool = Field(True, description="Filter by time")
    days: int = Field(LIMITS.DAYS, ge=1, le=365, description="Days to analyze (1-365)")
    threshold: float = Field(LIMITS.HIT_THRESHOLD, ge=0, le=1, description="Threshold for club recommendation")
    user_club_ids: str | None = Field(
        None,
        description="Comma-separated club IDs the user is already a member of",
    )

    @validator("user_id")
    def validate_user_id(cls, v):
        if not v.strip():
            raise ValueError("user_id cannot be empty")
        return v


class DealRequest(BaseModel):
    """Schema for recommendation by category request"""

    club_id: str = Field(..., min_length=1, max_length=255, description="Club ID")
    deal_id: str = Field(..., min_length=1, max_length=255, description="Deal ID")
    store_id: str = Field(..., min_length=1, max_length=255, description="Store ID")
    user_id: str = Field(..., min_length=1, max_length=255, description="User ID")
    use_mock: bool = Field(False, description="Use mock data")
    time_filter: bool = Field(True, description="Filter by time")
    days: int = Field(LIMITS.DAYS, ge=1, le=365, description="Days to analyze (1-365)")
    threshold: float = Field(LIMITS.HIT_THRESHOLD, ge=0, le=1, description="Threshold for club recommendation")
