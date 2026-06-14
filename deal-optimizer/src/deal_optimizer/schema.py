"""Target deal schema (Part 2a of the plan).

This module is the source of truth for the *lean* enriched-deal shape the
optimizer engine consumes. It is intentionally self-contained — the engine does
not import anything from the main `lessley_deals` package.

Two top-level facts describe a deal for the graph:
  * ``deal_type`` — which layer it lives in (Part 1).
  * ``constraints`` — combinability / limits / channels / eligibility.

The engine works on plain dicts (see ``adapter.py``); these Pydantic models are
the contract for validation, the categorization fallback, and tests.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

TriState = Literal["yes", "no", "unknown"]


class DealType(StrEnum):
    """The six graph layers, in fixed global application order."""

    STORE_SALE = "store_sale"
    MEMBER_DISCOUNT = "member_discount"
    COUPON = "coupon"
    GIFTCARD_DISCOUNT = "giftcard_discount"
    PAYMENT_DISCOUNT = "payment_discount"
    CASHBACK = "cashback"


class Combinability(BaseModel):
    stackable_with_store_sale: TriState = "unknown"
    stackable_with_member_discounts: TriState = "unknown"
    stackable_with_coupons: TriState = "unknown"
    stackable_with_payment_discounts: TriState = "unknown"
    stackable_with_giftcards: TriState = "unknown"
    stackable_with_cashback: TriState = "unknown"


class Limits(BaseModel):
    max_uses_per_transaction: int | None = None
    max_uses_per_month: int | None = None
    minimum_purchase: float | None = None  # ₪ threshold the customer must spend


class RedemptionChannels(BaseModel):
    website: TriState = "unknown"
    mobile_app: TriState = "unknown"
    physical_store: TriState = "unknown"


class Eligibility(BaseModel):
    membership_required: TriState = "unknown"
    payment_method_required: str | None = None


class DealConstraints(BaseModel):
    combinability: Combinability
    limits: Limits
    redemption_channels: RedemptionChannels
    eligibility: Eligibility


class DealParseResult(BaseModel):
    """What the LLM constraints parser returns: deal_type + constraints in one call."""

    deal_type: DealType
    constraints: DealConstraints
