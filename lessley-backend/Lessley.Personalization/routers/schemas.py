from pydantic import BaseModel, Field, validator
from config.constants import LIMITS  # still used by InsightsCalcRequests / GetTransactionsRequest


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
    """Matching-clubs request — uses pre-computed tags from UserRepository."""

    user_id: str = Field(..., min_length=1, max_length=255, description="User ID")

    @validator("user_id")
    def validate_user_id(cls, v):
        if not v.strip():
            raise ValueError("user_id cannot be empty")
        return v


class DealRequest(BaseModel):
    """Deal recommendation request — uses pre-computed tags from UserRepository."""

    club_id: str = Field(..., min_length=1, max_length=255, description="Club ID")
    deal_id: str = Field(..., min_length=1, max_length=255, description="Deal ID")
    store_id: str = Field(..., min_length=1, max_length=255, description="Store ID")
    user_id: str = Field(..., min_length=1, max_length=255, description="User ID")


class BroadcastDealRequest(BaseModel):
    """Request to broadcast a deal notification to all users in a category tag group."""

    deal_category: str = Field(..., min_length=1, max_length=255, description="Category tag (e.g. ELECTRONICS)")
    deal_id: str = Field(..., min_length=1, max_length=255, description="Deal ID")
    message: str = Field(..., min_length=1, max_length=1000, description="Notification message")
