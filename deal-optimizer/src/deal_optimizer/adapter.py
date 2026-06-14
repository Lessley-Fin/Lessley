"""Normalize heterogeneous deal dicts into the engine's input shape.

The engine wants every deal to carry two top-level keys: ``deal_type`` and a
lean ``constraints`` block (see ``schema.py``). Real data arrives in two shapes:

  * **New** — already has top-level ``deal_type`` + lean ``constraints``. Pass through.
  * **Legacy** — the old enrichment, where constraints live under
    ``discount_logic.constraints`` with the old field names (``stackable_with_promotions``,
    ``transaction_limits``, structured ``max_uses_per_period``, string ``minimum_purchase``)
    and no ``deal_type``. We translate field names and infer ``deal_type``.

``normalize_deal`` is idempotent and never mutates its input.
"""

from __future__ import annotations

import re
from typing import Any

from .schema import DealType

# --- legacy combinability field name → new field name -----------------------
_LEGACY_COMBINABILITY = {
    "stackable_with_promotions": "stackable_with_store_sale",
    "stackable_with_coupons": "stackable_with_coupons",
    "stackable_with_member_discounts": "stackable_with_member_discounts",
    "stackable_with_credit_card_promos": "stackable_with_payment_discounts",
}

_NEW_COMBINABILITY_KEYS = (
    "stackable_with_store_sale",
    "stackable_with_member_discounts",
    "stackable_with_coupons",
    "stackable_with_payment_discounts",
    "stackable_with_giftcards",
    "stackable_with_cashback",
)


def _coerce_period_to_month(period: dict[str, Any] | None) -> int | None:
    """Convert legacy ``max_uses_per_period`` to a monthly figure (Part 2c).

    period_days == 30 → as-is; == 7 → *4; == 365 → /12 rounded; else best-effort scale.
    """
    if not period:
        return None
    days = period.get("period_days") or 30
    uses = period.get("max_uses")
    if uses is None:
        return None
    if days == 30:
        return uses
    if days == 7:
        return uses * 4
    if days == 365:
        return max(1, round(uses / 12))
    # general fallback: scale to a 30-day window
    return max(1, round(uses * 30 / days))


def _parse_minimum_purchase(raw: Any) -> float | None:
    """Legacy ``minimum_purchase`` is a free-text string; pull the first number."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    m = re.search(r"\d+(?:[.,]\d+)?", str(raw))
    return float(m.group(0).replace(",", "")) if m else None


def _empty_constraints() -> dict[str, Any]:
    return {
        "combinability": {k: "unknown" for k in _NEW_COMBINABILITY_KEYS},
        "limits": {"max_uses_per_transaction": None, "max_uses_per_month": None, "minimum_purchase": None},
        "redemption_channels": {"website": "unknown", "mobile_app": "unknown", "physical_store": "unknown"},
        "eligibility": {"membership_required": "unknown", "payment_method_required": None},
    }


def _translate_legacy_constraints(legacy: dict[str, Any]) -> dict[str, Any]:
    out = _empty_constraints()

    legacy_comb = legacy.get("combinability", {}) or {}
    for old_key, new_key in _LEGACY_COMBINABILITY.items():
        if old_key in legacy_comb:
            out["combinability"][new_key] = legacy_comb[old_key]

    tx = legacy.get("transaction_limits", {}) or {}
    elig = legacy.get("eligibility", {}) or {}
    out["limits"]["max_uses_per_transaction"] = tx.get("max_uses_per_transaction")
    out["limits"]["max_uses_per_month"] = _coerce_period_to_month(tx.get("max_uses_per_period"))
    out["limits"]["minimum_purchase"] = _parse_minimum_purchase(elig.get("minimum_purchase"))

    ch = legacy.get("redemption_channels", {}) or {}
    for k in ("website", "mobile_app", "physical_store"):
        if k in ch:
            out["redemption_channels"][k] = ch[k]

    out["eligibility"]["membership_required"] = elig.get("membership_required", "unknown")
    out["eligibility"]["payment_method_required"] = elig.get("payment_method_required")
    return out


# --- deterministic deal_type fallback (Part 1 categorization) ----------------
# Keyword hints are checked against title + description + terms_and_conditions.
_GIFTCARD_HINTS = ("תו קניה", "תווי קניה", "גיפט קארד", "gift card", "giftcard", "שובר", "תו דיגיטלי")
_CASHBACK_HINTS = ("קאשבק", "cashback", "cash back", "החזר כספי")
_PAYMENT_HINTS = ("הנחה במעמד החיוב", "במעמד חיוב", "כרטיס אשראי המשויך", "כרטיס האשראי")
_MEMBER_HINTS = ("הנחת מועדון", "הטבת מועדון", "לחברי מועדון", "הטבות מועדון")


def infer_deal_type(deal: dict[str, Any]) -> str:
    """Deterministic structural+keyword fallback when no deal_type is set."""
    text = " ".join(
        str(deal.get(k, "") or "")
        for k in ("title", "deal_description", "description", "terms_and_conditions")
    )
    cond_type = (deal.get("discount_logic", {}) or {}).get("condition", {}).get("type")

    if deal.get("coupon_code"):
        return DealType.COUPON.value
    if any(h in text for h in _CASHBACK_HINTS):
        return DealType.CASHBACK.value
    if any(h in text for h in _GIFTCARD_HINTS) or cond_type in ("exact_spend", "voucher_value"):
        return DealType.GIFTCARD_DISCOUNT.value
    if any(h in text for h in _PAYMENT_HINTS):
        return DealType.PAYMENT_DISCOUNT.value
    if any(h in text for h in _MEMBER_HINTS):
        return DealType.MEMBER_DISCOUNT.value
    if "קופון" in text or "coupon" in text.lower():
        return DealType.COUPON.value
    return DealType.STORE_SALE.value


def _has_new_constraints(constraints: dict[str, Any] | None) -> bool:
    if not constraints:
        return False
    comb = constraints.get("combinability", {}) or {}
    # new shape uses these keys; legacy used stackable_with_promotions
    return any(k in comb for k in ("stackable_with_store_sale", "stackable_with_giftcards"))


def normalize_deal(deal: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``deal`` carrying top-level ``deal_type`` + lean ``constraints``."""
    out = dict(deal)

    top_constraints = out.get("constraints")
    legacy_constraints = (out.get("discount_logic", {}) or {}).get("constraints")

    if _has_new_constraints(top_constraints):
        constraints = top_constraints  # already new shape
    elif legacy_constraints is not None:
        constraints = _translate_legacy_constraints(legacy_constraints)
    elif top_constraints:
        # partial / unknown shape — merge onto the empty template defensively
        merged = _empty_constraints()
        for section, vals in top_constraints.items():
            if section in merged and isinstance(vals, dict):
                merged[section].update(vals)
        constraints = merged
    else:
        constraints = _empty_constraints()

    out["constraints"] = constraints

    if not out.get("deal_type"):
        out["deal_type"] = infer_deal_type(out)

    # drop the legacy nested constraints so the engine never reads stale data
    if isinstance(out.get("discount_logic"), dict) and "constraints" in out["discount_logic"]:
        dl = dict(out["discount_logic"])
        dl.pop("constraints", None)
        out["discount_logic"] = dl

    return out


def normalize_deals(deals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_deal(d) for d in deals]
