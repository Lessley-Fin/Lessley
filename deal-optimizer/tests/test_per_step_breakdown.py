"""per_step's richer breakdown fields (discount_rate, savings,
amount_paid_on_covered, remaining_to_allocate, cumulative_*) — generalizes
across both price-level (chain) and tender steps."""

from __future__ import annotations

import pytest

from deal_optimizer.engine import optimize

from conftest import mk_deal


def test_price_level_step_covers_whole_running_bill():
    # A single 10% coupon on a 100 ILS cart: no ils_covered (price-level deals
    # discount whatever's left, not a specific payment slice), but
    # discount_rate/savings/amount_paid_on_covered still generalize correctly
    # by treating the whole running bill as "covered".
    deal = mk_deal("c", "coupon", reward_type="percentage_off", reward_value=0.10, accepts_all=True)
    res = optimize([deal], cart_total=100, cart_quantity=1)[0]
    step = res["per_step"][0]

    assert step["ils_covered"] is None
    assert step["discount_rate"] == pytest.approx(0.10)
    assert step["savings"] == pytest.approx(10.0)
    assert step["amount_paid_on_covered"] == pytest.approx(90.0)
    assert step["remaining_to_allocate"] is None
    assert step["cumulative_savings"] == pytest.approx(10.0)
    assert step["cumulative_discount_rate"] == pytest.approx(0.10)


def test_cumulative_fields_accumulate_across_chain_then_tender_steps():
    # A 10% coupon (chain) followed by an uncapped 20% giftcard (tender) on a
    # 100 ILS cart: coupon takes it to 90; giftcard then covers that full 90
    # (tender phase starts wherever the chain phase left off) at 20% off.
    coupon = mk_deal("c", "coupon", reward_type="percentage_off", reward_value=0.10, accepts_all=True)
    giftcard = mk_deal("g", "giftcard_discount", reward_type="percentage_off", reward_value=0.20, accepts_all=True)
    res = optimize([coupon, giftcard], cart_total=100, cart_quantity=1)[0]
    coupon_step, giftcard_step = res["per_step"]

    assert coupon_step["ils_covered"] is None
    assert coupon_step["remaining_to_allocate"] is None
    assert coupon_step["cumulative_savings"] == pytest.approx(10.0)
    assert coupon_step["cumulative_discount_rate"] == pytest.approx(0.10)

    assert giftcard_step["ils_covered"] == pytest.approx(90.0)
    assert giftcard_step["discount_rate"] == pytest.approx(0.20)
    assert giftcard_step["savings"] == pytest.approx(18.0)
    assert giftcard_step["amount_paid_on_covered"] == pytest.approx(72.0)
    assert giftcard_step["remaining_to_allocate"] == pytest.approx(0.0)
    assert giftcard_step["cumulative_savings"] == pytest.approx(28.0)
    assert giftcard_step["cumulative_discount_rate"] == pytest.approx(0.28)
