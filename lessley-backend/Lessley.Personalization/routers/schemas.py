from pydantic import BaseModel, Field
from config.constants import LIMITS  # still used by InsightsCalcRequests / GetTransactionsRequest


# Identity is NEVER a request field. The edge authenticates every caller and injects the
# verified email as X-Auth-Email; routes read it via dependencies.auth.authenticated_email.
# Accepting an `email` parameter here would let any caller read any user's data.

# Neither is `use_mock`. The services still accept it so tests can inject a fixed transaction
# set, but it is not a request field: bound from the query string it let any caller swap their
# own transactions for the contents of a file on disk — a 500 today, and a cross-user data leak
# the moment such a file ships.


class InsightsCalcRequests(BaseModel):
    time_filter: bool = Field(True, description="Filter by time")
    days: int = Field(LIMITS.DAYS, ge=1, le=365, description="Days to analyze (1-365)")


class GetTransactionsByAccountRequest(BaseModel):
    account_id: str = Field(..., min_length=1, max_length=255, description="Account ID")
    time_filter: bool = Field(True, description="Filter by time")
    days: int = Field(LIMITS.DAYS, ge=1, le=365, description="Days to analyze (1-365)")


class GetTransactionsRequest(BaseModel):
    time_filter: bool = Field(True, description="Filter by time")
    days: int = Field(LIMITS.DAYS, ge=1, le=365, description="Days to analyze (1-365)")
