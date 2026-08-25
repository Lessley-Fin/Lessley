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

    email: str
    recommendations: list[ClubRecommendationSchema]


class MissedShopPurchaseSchema(BaseModel):
    """One purchase a shop's deal could have applied to."""

    transaction_id: str = Field(..., description="Unique transaction identifier")
    merchant_name: str = Field(..., description="The merchant name exactly as the bank reported it")
    amount: float = Field(..., description="What the purchase cost")
    date: str | None = Field(default=None, description="When the purchase happened")
    account_id: str | None = Field(
        default=None,
        description=(
            "The account the purchase was charged to. Only the id travels — the client already "
            "holds the accounts themselves from /open-finance/accounts and reads the product and "
            "provider off its own copy, so this DTO never restates them."
        ),
    )
    covered_by_club_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Clubs whose own benefit card paid for this purchase, so the saving was already "
            "taken. Empty means the purchase genuinely missed out. Non-empty means the "
            "opposite of a missed saving and must never be worded as one — see BENEFIT_CARDS."
        ),
    )


class MissedShopSchema(BaseModel):
    """
    One shop that runs a deal, with the purchases it could have covered.

    `match_band` is what the wording has to follow. EXACT and STRONG mean this is the shop the
    user bought from — "you missed a coupon here". SIMILAR means the names only share a word
    naming a line of business ('קפה'), so it is a shop *like* theirs and must be worded that
    way. Anything weaker is not returned.

    `missed_*` and `committed_*` split `covered_*`, and the split is the second thing to read.
    A committed purchase was charged to a club's own benefit card and already took the discount
    at the till, so it is a saving *made*, not missed. A shop with `missed_transaction_count`
    of zero has nothing left to suggest and belongs wherever the client says "you already saved
    here" — never in a list headed "you missed out".
    """

    store_id: str = Field(..., description="The store ID")
    store_name: str = Field(..., description="The store name")
    match_band: str = Field(..., description="EXACT | STRONG | SIMILAR — how sure the name match is")
    is_same_store: bool = Field(..., description="True when this is the shop the user actually used")
    deal_count: int = Field(..., description="How many deals this shop is running")
    deal_titles: list[str] = Field(default_factory=list, description="A few of the deals on offer")
    club_ids: list[str] = Field(default_factory=list, description="Clubs through which the deals apply")
    also_known_as: list[str] = Field(
        default_factory=list, description="Other names this shop is filed under in the catalogue"
    )
    covered_transaction_count: int = Field(..., description="How many purchases this shop could have covered")
    covered_amount: float = Field(..., description="Total spend across those purchases")
    missed_transaction_count: int = Field(
        default=0, description="Of those, how many actually missed out — the number to lead with"
    )
    missed_amount: float = Field(default=0.0, description="Total spend across the missed purchases")
    committed_transaction_count: int = Field(
        default=0, description="Of those, how many already earned a club's benefit at the till"
    )
    committed_amount: float = Field(default=0.0, description="Total spend across the committed purchases")
    committed_club_ids: list[str] = Field(
        default_factory=list, description="The clubs that already paid off at this shop"
    )
    purchases: list[MissedShopPurchaseSchema] = Field(
        default_factory=list, description="The purchases themselves"
    )
