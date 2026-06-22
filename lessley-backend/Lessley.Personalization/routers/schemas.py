from pydantic import BaseModel, Field, validator
from config.constants import LIMITS  # still used by InsightsCalcRequests / GetTransactionsRequest


# Email is the system-wide primary identifier (the same value Open Finance uses and the
# Gateway addresses users by). It is accepted on every request as `email`.
class UserRequests(BaseModel):
    email: str = Field(..., min_length=1, max_length=255, description="User email")

    @validator("email")
    def validate_email(cls, v):
        if not v.strip():
            raise ValueError("email cannot be empty")
        return v


class InsightsCalcRequests(BaseModel):
    email: str = Field(..., min_length=1, max_length=255, description="User email")
    use_mock: bool = Field(False, description="Use mock data")
    time_filter: bool = Field(True, description="Filter by time")
    days: int = Field(LIMITS.DAYS, ge=1, le=365, description="Days to analyze (1-365)")

    @validator("email")
    def validate_email(cls, v):
        if not v.strip():
            raise ValueError("email cannot be empty")
        return v


class ClubCalcRequests(BaseModel):
    club_id: str = Field(..., min_length=1, max_length=255, description="Club ID")

    @validator("club_id")
    def validate_club_id(cls, v):
        if not v.strip():
            raise ValueError("club_id cannot be empty")
        return v


class GetTransactionsByAccountRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255, description="User email")
    account_id: str = Field(..., min_length=1, max_length=255, description="Account ID")
    time_filter: bool = Field(True, description="Filter by time")
    days: int = Field(LIMITS.DAYS, ge=1, le=365, description="Days to analyze (1-365)")


class GetTransactionsRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255, description="User email")
    time_filter: bool = Field(True, description="Filter by time")
    days: int = Field(LIMITS.DAYS, ge=1, le=365, description="Days to analyze (1-365)")


class RecommendationByCategoryRequestSchema(BaseModel):
    """Matching-clubs request — uses pre-computed tags from UserRepository."""

    email: str = Field(..., min_length=1, max_length=255, description="User email")

    @validator("email")
    def validate_email(cls, v):
        if not v.strip():
            raise ValueError("email cannot be empty")
        return v


class BroadcastDealRequest(BaseModel):
    """
    Request to broadcast a deal. The deal's category is resolved from its store, so only the
    deal_id and message are required.
    """

    deal_id: str = Field(..., min_length=1, max_length=255, description="Deal ID")
    message: str = Field(..., min_length=1, max_length=1000, description="Notification message")
