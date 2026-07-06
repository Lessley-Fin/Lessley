"""Adapter: legacy enriched JSON → lean target schema, + deal_type inference."""

from __future__ import annotations

import pytest

from deal_optimizer.adapter import infer_deal_type, normalize_deal
from deal_optimizer.engine import optimize

# A trimmed copy of the real legacy lee_cooper_deal.json shape.
LEGACY_LEE_COOPER = {
    "id": "019dc1b5b48a_0c5ee03c07a2aab6",
    "store_id": "019d209b8101_f9b9017f2ef608d3",
    "title": "תו קניה Lee Cooper",
    "deal_description": "תו קניה Lee Cooper",
    "terms_and_conditions": "תו דיגיטלי בהנחה של 13% ... כולל כפל מבצעים והנחות. ניתן לממש עד 2 שוברים בעסקה.",
    "discount_logic": {
        "condition": {"type": "min_quantity", "value": 1},
        "reward": {"type": "percentage_off", "value": 0.13},
        "constraints": {
            "eligibility": {
                "membership_required": "unknown",
                "payment_method_required": "כרטיס אשראי המשויך למועדון הוט",
                "minimum_purchase": None,
            },
            "redemption_channels": {"website": "no", "physical_store": "yes", "mobile_app": "unknown"},
            "combinability": {
                "stackable_with_promotions": "yes",
                "stackable_with_coupons": "yes",
                "stackable_with_member_discounts": "unknown",
                "stackable_with_credit_card_promos": "unknown",
            },
            "transaction_limits": {"max_uses_per_transaction": 2, "max_uses_per_period": None},
        },
    },
    "coupon_code": None,
    "club_id": "club_hot",
}


def test_legacy_normalizes_to_new_shape():
    norm = normalize_deal(LEGACY_LEE_COOPER)
    # deal_type inferred from "תו קניה" hint
    assert norm["deal_type"] == "giftcard_discount"
    comb = norm["constraints"]["combinability"]
    assert comb["stackable_with_store_sale"] == "yes"  # was stackable_with_promotions
    assert comb["stackable_with_coupons"] == "yes"
    assert comb["stackable_with_payment_discounts"] == "unknown"  # was credit_card_promos
    # giftcard/cashback absent in legacy → unknown
    assert comb["stackable_with_giftcards"] == "unknown"
    # transaction limit moved up
    assert norm["constraints"]["limits"]["max_uses_per_transaction"] == 2
    # legacy nested constraints dropped
    assert "constraints" not in norm["discount_logic"]


def test_period_coercion_to_month():
    weekly = {"id": "w", "deal_type": "coupon",
              "discount_logic": {"constraints": {"transaction_limits":
              {"max_uses_per_transaction": None, "max_uses_per_period": {"period_days": 7, "max_uses": 2}}}}}
    norm = normalize_deal(weekly)
    assert norm["constraints"]["limits"]["max_uses_per_month"] == 8  # 2 * 4


def test_legacy_deal_runs_through_engine():
    # giftcard_discount goes through the tender allocator, not the price-level
    # chain. It's an uncapped rate (no max_discount_amount), so a second unit
    # (max_uses_per_transaction=2) has nothing left to cover once the first
    # unit already discounts the whole bill — no compounding to 0.87^2.
    res = optimize([LEGACY_LEE_COOPER], cart_total=500, cart_quantity=1)[0]
    assert res["final_price"] == pytest.approx(435.0)


def test_infer_deal_type_coupon_code():
    d = {"id": "c", "coupon_code": "SAVE10", "discount_logic": {}}
    assert infer_deal_type(d) == "coupon"


def test_infer_deal_type_exact_spend_is_giftcard():
    d = {"id": "g", "discount_logic": {"condition": {"type": "exact_spend", "value": 50}}}
    assert infer_deal_type(d) == "giftcard_discount"
