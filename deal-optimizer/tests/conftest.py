"""Shared test helpers for building deal dicts in the lean target schema."""

from __future__ import annotations

from typing import Any

_ALL_COMB_KEYS = (
    "stackable_with_store_sale",
    "stackable_with_member_discounts",
    "stackable_with_coupons",
    "stackable_with_payment_discounts",
    "stackable_with_giftcards",
    "stackable_with_cashback",
)


def mk_deal(
    deal_id: str,
    deal_type: str,
    *,
    reward_type: str = "percentage_off",
    reward_value: float = 0.0,
    max_discount_amount: float | None = None,
    cond_type: str = "min_spend",
    cond_value: float = 0,
    accepts_all: bool = False,
    combinability: dict[str, str] | None = None,
    max_uses_per_transaction: int | None = None,
    max_uses_per_month: int | None = None,
    minimum_purchase: float | None = None,
    membership_required: str = "unknown",
    payment_method_required: str | None = None,
    source_id: str | None = None,
    store_coverage: dict[str, str] | None = None,
    store_id: str = "store_default",
    title: str = "",
) -> dict[str, Any]:
    comb = {k: ("yes" if accepts_all else "unknown") for k in _ALL_COMB_KEYS}
    if combinability:
        comb.update(combinability)

    reward: dict[str, Any] = {"type": reward_type, "value": reward_value}
    if max_discount_amount is not None:
        reward["max_discount_amount"] = max_discount_amount

    coverage = {
        "is_include_outlets_stores": "unknown",
        "is_include_online_stores": "unknown",
        "is_include_physical_stores": "unknown",
    }
    if store_coverage:
        coverage.update(store_coverage)

    return {
        "id": deal_id,
        "store_id": store_id,
        "title": title or deal_id,
        "deal_type": deal_type,
        "discount_logic": {
            "condition": {"type": cond_type, "value": cond_value},
            "reward": reward,
        },
        "constraints": {
            "combinability": comb,
            "limits": {
                "max_uses_per_transaction": max_uses_per_transaction,
                "max_uses_per_month": max_uses_per_month,
                "minimum_purchase": minimum_purchase,
            },
            "store_coverage": coverage,
            "eligibility": {
                "membership_required": membership_required,
                "payment_method_required": payment_method_required,
            },
        },
        "source_id": source_id,
    }
