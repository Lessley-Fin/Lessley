"""HTTP surface for the stacking engine — a thin FastAPI wrapper over ``optimize()``.

The engine itself stays a pure library; this module only reads deals for the
requested store out of MongoDB, builds a ``UserContext`` from the request, and
returns ``build_export_payload``'s envelope plus a ``deals`` lookup so a client
can render the resulting paths without resolving each ``deal_id`` itself.

Exposed at the edge (Caddy) on ``/api/v1/optimizer/*``, never through the Gateway.
Caddy strips ``/api/v1`` and this app carries the ``/optimizer`` prefix itself —
the same split Personalization uses, so one edge rule covers both services.

Run it with::

    uvicorn deal_optimizer.api:app --host 0.0.0.0 --port 5003
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from pymongo.errors import PyMongoError

from .auth import authenticated_email
from .deals_source import get_database, load_store, load_store_deals, summarize_deals
from .edge_auth import EdgeAuthMiddleware, dev_bypass_active
from .engine import DEFAULT_MAX_DEALS, UserContext, build_export_payload, optimize
from .user_source import member_source_ids_for

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Lessley deal-optimizer",
    description="Layered-DAG deal stacking engine — cheapest legal combination of compatible deals.",
    version="0.1.0",
)

# Every route lives under /optimizer so the edge can strip a single /api/v1 prefix.
router = APIRouter(prefix="/optimizer")

app.add_middleware(EdgeAuthMiddleware)  # Enforce edge-only access

if dev_bypass_active():
    logger.warning(
        "EDGE VERIFICATION BYPASSED — X-Edge-Key is not required and identity falls back to "
        "decoding the access_token cookie directly. Development only; never enable "
        "Edge_AllowUnverified outside local debugging."
    )


class OptimizeRequest(BaseModel):
    store_id: str = Field(..., min_length=1, description="Canonical store the cart is being priced for")
    cart_total: float = Field(..., gt=0, description="Total cart value in ILS")
    cart_quantity: int = Field(1, ge=1, description="Number of items in the cart")
    top_n: int = Field(5, ge=1, le=20, description="How many ranked options to return")
    max_deals: int = Field(
        DEFAULT_MAX_DEALS,
        ge=1,
        le=10,
        description="Longest combination to search for — the most deals one ranked option may stack",
    )
    strict: bool = Field(False, description="Treat combinability 'unknown' as 'no' instead of 'yes'")
    # No member_source_ids here on purpose. Which loyalty programs the caller belongs to is
    # resolved from the verified X-Auth-Email against the users collection (see
    # user_source.py) — a client that could name its own memberships could hand itself every
    # members-only deal in the database. A body that still sends the field is ignored.
    preferred_store_types: list[str] = Field(default_factory=list)
    uses_this_month: dict[str, int] = Field(
        default_factory=dict, description="deal_id → times already used this month, for monthly-cap pruning"
    )


class OptimizeResponse(BaseModel):
    generated_at: str
    store_id: str
    cart_total: float
    cart_quantity: int
    wallet_id: str | None = None
    store: dict[str, Any] | None = None
    results: list[dict[str, Any]]
    deals: dict[str, dict[str, Any]]
    deals_considered: int


def _store_for_display(store_id: str) -> dict[str, Any] | None:
    """The store's name and imagery, or None if it can't be read.

    Purely decorative, so a failure here must not cost the caller its prices —
    the stack is already computed by the time this runs.
    """
    try:
        return load_store(store_id)
    except PyMongoError:
        logger.warning("Could not read store %s for display", store_id, exc_info=True)
        return None


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe — also verifies the deals database is reachable."""
    try:
        get_database().client.admin.command("ping")
    except PyMongoError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"MongoDB unreachable: {exc}"
        ) from exc
    return {"status": "ok"}


@router.post("/optimize", response_model=OptimizeResponse)
def optimize_cart(request: OptimizeRequest, email: str = Depends(authenticated_email)) -> OptimizeResponse:
    """Rank the cheapest legal deal stacks for a cart at one store.

    ``email`` is the identity Caddy verified against the Gateway, and it is what decides
    eligibility: the caller's saved clubs become the ``source_id``s the engine prunes on.
    """
    try:
        deals = load_store_deals(request.store_id)
    except PyMongoError as exc:
        logger.exception("Failed to load deals for store %s", request.store_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not read deals: {exc}"
        ) from exc

    # Eligibility comes from who the caller is, never from what they sent. Caddy has
    # already authenticated them against the Gateway, so this is a lookup, not a claim.
    try:
        member_source_ids = member_source_ids_for(email)
    except PyMongoError as exc:
        logger.exception("Failed to resolve clubs for the caller")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not read user clubs: {exc}"
        ) from exc

    if member_source_ids is None:
        # Authenticated by the edge, but no such user in our database. Answering with
        # prices computed as an unknown user would quietly offer members-only deals.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # A context is always built, even for a user who has joined nothing: an empty list is
    # a *known* user with no memberships, and pruning members-only deals is the whole point.
    # (`None` — the unknown user the engine treats optimistically — is what the CLI passes;
    # an authenticated request is never that.)
    user_context = UserContext(
        member_source_ids=member_source_ids,
        preferred_store_types=request.preferred_store_types,
        uses_this_month=request.uses_this_month,
        # Only offer deals from programs this caller has actually joined. Their clubs are
        # verified here, so a deal from a club they are not in is never usable — and the
        # deal's own membership_required flag is too often unset to rely on.
        require_source_membership=True,
    )

    ranked = optimize(
        deals,
        request.cart_total,
        request.cart_quantity,
        user_context,
        unknown_as_yes=not request.strict,
        top_n=request.top_n,
        max_deals=request.max_deals,
    )

    # The DP always includes the trivial START → END path — "apply nothing, pay
    # full price". It's a legitimate path for the engine but not an *option* to
    # offer, so it's dropped here: an empty ``results`` is how this endpoint says
    # "nothing stacks on this cart". It always sorts last (zero savings), so the
    # remaining ranks stay contiguous.
    results = [r for r in ranked if r["path"]]

    payload = build_export_payload(
        results,
        store_id=request.store_id,
        cart_total=request.cart_total,
        cart_quantity=request.cart_quantity,
    )

    logger.info(
        "Optimized store=%s cart=%.2f max_deals=%d for %s — %d deal(s) considered, %d ranked option(s)",
        request.store_id,
        request.cart_total,
        request.max_deals,
        email,
        len(deals),
        len(results),
    )

    return OptimizeResponse(
        **payload,
        store=_store_for_display(request.store_id),
        deals=summarize_deals(deals),
        deals_considered=len(deals),
    )


app.include_router(router)
