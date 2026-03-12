from pydantic import BaseModel, Field, validator


class UserRequests(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255, description="User ID")

    @validator("user_id")
    def validate_user_id(cls, v):
        if not v.strip():
            raise ValueError("user_id cannot be empty")
        return v


class InsightsCalcRequests(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255, description="User ID")
    use_mock: bool = Field(True, description="Use mock data")
    time_filter: bool = Field(True, description="Filter by time")
    days: int = Field(60, ge=1, le=365, description="Days to analyze (1-365)")

    @validator("user_id")
    def validate_user_id(cls, v):
        if not v.strip():
            raise ValueError("user_id cannot be empty")
        return v


class GetTransactionsByAccountRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255, description="User ID")
    account_id: str = Field(..., min_length=1, max_length=255, description="Account ID")
    time_filter: bool = Field(True, description="Filter by time")
    days: int = Field(60, ge=1, le=365, description="Days to analyze (1-365)")


class GetTransactionsRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255, description="User ID")
    time_filter: bool = Field(True, description="Filter by time")
    days: int = Field(60, ge=1, le=365, description="Days to analyze (1-365)")
