"""HTTP surface for the stacking engine — a thin FastAPI wrapper over ``optimize()``.

The engine itself stays a pure library; this module only reads deals for the
requested store out of MongoDB, builds a ``UserContext`` from the request, and
returns ``build_export_payload``'s envelope plus a ``deals`` lookup so a client
can render the resulting paths without resolving each ``deal_id`` itself.

Run it with::

    uvicorn deal_optimizer.api:app --host 0.0.0.0 --port 8003
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from pymongo.errors import PyMongoError

from .deals_source import get_database, load_store, load_store_deals, summarize_deals
from .engine import DEFAULT_MAX_DEALS, UserContext, build_export_payload, optimize

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Lessley deal-optimizer",
    description="Layered-DAG deal stacking engine — cheapest legal combination of compatible deals.",
    version="0.1.0",
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
    member_source_ids: list[str] | None = Field(
        None,
        description=(
            "source_ids the user has access to — loyalty programs joined and cards held. "
            "Omit (null) for an unknown user; an empty list means a known user who has "
            "joined nothing, which does prune members-only deals"
        ),
    )
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


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe — also verifies the deals database is reachable."""
    try:
        get_database().client.admin.command("ping")
    except PyMongoError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"MongoDB unreachable: {exc}"
        ) from exc
    return {"status": "ok"}


@app.post("/optimize", response_model=OptimizeResponse)
def optimize_cart(request: OptimizeRequest) -> OptimizeResponse:
    """Rank the cheapest legal deal stacks for a cart at one store."""
    try:
        deals = load_store_deals(request.store_id)
    except PyMongoError as exc:
        logger.exception("Failed to load deals for store %s", request.store_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not read deals: {exc}"
        ) from exc

    # No wallet data in the request means "unknown user", which the engine treats
    # optimistically (no eligibility pruning) — same convention as the CLI, where
    # a UserContext is only built once there's something to put in it.
    #
    # ``member_source_ids`` distinguishes absent from empty on purpose: null is the
    # unknown user, while ``[]`` is a known user who has joined no clubs — and that
    # one *must* build a context, or the caller who tells us the truth about a
    # member-less user gets every members-only deal offered back.
    user_context = None
    if (
        request.member_source_ids is not None
        or request.preferred_store_types
        or request.uses_this_month
    ):
        user_context = UserContext(
            member_source_ids=request.member_source_ids or [],
            preferred_store_types=request.preferred_store_types,
            uses_this_month=request.uses_this_month,
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
        "Optimized store=%s cart=%.2f max_deals=%d — %d deal(s) considered, %d ranked option(s)",
        request.store_id,
        request.cart_total,
        request.max_deals,
        len(deals),
        len(results),
    )

    return OptimizeResponse(
        **payload,
        store=_store_for_display(request.store_id),
        deals=summarize_deals(deals),
        deals_considered=len(deals),
    )
