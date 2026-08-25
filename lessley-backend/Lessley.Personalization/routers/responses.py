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


class SavingsPurchaseSchema(BaseModel):
    """One purchase, as it appears under a merchant."""

    transaction_id: str = Field(..., description="Unique transaction identifier")
    amount: float = Field(..., description="What the purchase was worth")
    date: str | None = Field(default=None, description="When the purchase happened")
    account_id: str | None = Field(default=None, description="The account it was charged to")


class SavingsShopSchema(BaseModel):
    """A deal-running shop behind one merchant — what the user could have claimed, and where."""

    store_id: str = Field(..., description="The store ID")
    store_name: str = Field(..., description="The store name")
    match_band: str = Field(..., description="EXACT | STRONG | SIMILAR — how sure this shop match is")
    is_same_store: bool = Field(..., description="True when this is the shop the user actually used")
    deal_count: int = Field(..., description="How many deals this shop is running")
    deal_titles: list[str] = Field(default_factory=list, description="A few of the deals on offer")
    club_ids: list[str] = Field(default_factory=list, description="Clubs through which the deals apply")
    also_known_as: list[str] = Field(default_factory=list, description="Other names it is filed under")


class SavingsMerchantSchema(BaseModel):
    """
    One place the user shopped, with everything the screen shows about it.

    The merchant is the unit because it is what the user recognises — a name off their own
    statement — where a shop is a row in our catalogue. Grouping, de-duplication and every
    total below are done here so that no client has to redo them and reach a different answer.
    """

    merchant_name: str = Field(..., description="The merchant, exactly as the bank reported it")
    band: str = Field(..., description="The band these purchases were counted under")
    purchase_count: int = Field(..., description="How many purchases, each counted once")
    amount: float = Field(..., description="What those purchases were worth in total")
    deal_count: int = Field(..., description="Deals live across every shop matched here")
    account_ids: list[str] = Field(default_factory=list, description="Accounts these were charged to")
    club_ids: list[str] = Field(default_factory=list, description="Clubs the deals apply through")
    shops: list[SavingsShopSchema] = Field(default_factory=list, description="The shops that matched")
    purchases: list[SavingsPurchaseSchema] = Field(default_factory=list, description="The purchases themselves")


class SavingsBandSchema(BaseModel):
    """
    One band's worth of merchants, with its own subtotal.

    Every purchase is counted under exactly one band — its strongest match — so the three
    subtotals add up to `MissedSavingsSchema.total_amount` exactly. They used to overlap, and
    a user adding the tabs up got a bigger number than the headline with nothing to explain it.
    """

    band: str = Field(..., description="EXACT | STRONG | SIMILAR")
    total_amount: float = Field(..., description="What this band's purchases were worth")
    purchase_count: int = Field(..., description="How many purchases fell in this band")
    merchants: list[SavingsMerchantSchema] = Field(default_factory=list)


class MissedSavingsSchema(BaseModel):
    """Purchases that matched a deal the user could have used, and did not."""

    total_amount: float = Field(..., description="Sum of the bands below, each purchase once")
    purchase_count: int = Field(..., description="How many purchases missed out, each counted once")
    bands: list[SavingsBandSchema] = Field(default_factory=list)


class AppliedSavingsSchema(BaseModel):
    """
    Purchases a club's own benefit card paid for, so the discount came off at the till.

    Every such purchase is here, whether or not our catalogue happens to know the shop — the
    card is the evidence, not the match. `club_ids` on these merchants is empty by design: the
    feed says no money left the account, which does not name the club behind the card.
    """

    total_amount: float = Field(..., description="What those purchases were worth")
    purchase_count: int = Field(..., description="How many, each counted once")
    merchants: list[SavingsMerchantSchema] = Field(default_factory=list)


class SavingsAnswerSchema(BaseModel):
    """
    The whole savings picture for a period: what was missed, and what was already taken.

    One payload rather than two endpoints, because the two are cut from the same matching pass
    and must never disagree about which side a purchase fell on.
    """

    missed: MissedSavingsSchema
    applied: AppliedSavingsSchema
