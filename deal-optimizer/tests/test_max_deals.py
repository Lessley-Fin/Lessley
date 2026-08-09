"""The ``max_deals`` cap — how long a combination the engine may return.

Seven stacked coupons is a better number and a worse suggestion: the cap keeps
results to something a person will actually execute at a checkout. It applies
across both phases together (chain + tender), and it bounds the search rather
than filtering its output, so what comes back is the best combination that
*fits* the cap, not a truncated version of a bigger one.
"""

from __future__ import annotations

import pytest

from deal_optimizer.engine import find_best_path, optimize

from conftest import mk_deal


def _coupons(n: int) -> list[dict]:
    """``n`` freely stackable coupons, each 10% off."""
    return [
        mk_deal(f"C{i}", "coupon", reward_type="percentage_off", reward_value=0.10, accepts_all=True)
        for i in range(n)
    ]


def _cards(n: int) -> list[dict]:
    """``n`` freely stackable payment cards, each 20% off up to 100 ILS of bill."""
    return [
        mk_deal(
            f"P{i}",
            "payment_discount",
            reward_type="percentage_off",
            reward_value=0.20,
            max_discount_amount=20.0,  # 20% of 100 ILS → each card covers 100 ILS
            accepts_all=True,
        )
        for i in range(n)
    ]


# 1. The chain phase ----------------------------------------------------------

@pytest.mark.parametrize("cap", [1, 2, 3, 4, 5])
def test_chain_is_capped(cap: int):
    path = find_best_path(1000, 1, _coupons(6), max_deals=cap)
    assert len(path) == cap  # every extra coupon still helps, so it spends the whole budget


def test_uncapped_stacks_everything():
    assert len(find_best_path(1000, 1, _coupons(6), max_deals=None)) == 6


def test_capped_result_is_the_best_of_its_length():
    # 10% + 25% + 5%: with room for two, the engine must pick the best two
    # (25% and 10% → 675), not simply stop after the first two it reaches.
    deals = [
        mk_deal("small", "coupon", reward_type="percentage_off", reward_value=0.05, accepts_all=True),
        mk_deal("big", "coupon", reward_type="percentage_off", reward_value=0.25, accepts_all=True),
        mk_deal("mid", "coupon", reward_type="percentage_off", reward_value=0.10, accepts_all=True),
    ]
    res = optimize(deals, cart_total=1000, cart_quantity=1, max_deals=2)[0]
    assert sorted(d["id"] for d in res["path"]) == ["big", "mid"]
    assert res["final_price"] == pytest.approx(675.0)


# 2. The tender phase ---------------------------------------------------------

def test_tender_allocation_is_capped():
    # Five cards could each cover 100 ILS of a 1000 ILS bill; a cap of 2 lets
    # only two of them be part of the split.
    res = optimize(_cards(5), cart_total=1000, cart_quantity=1, max_deals=2)[0]
    assert len(res["path"]) == 2
    assert res["total_savings"] == pytest.approx(40.0)  # 2 x 100 ILS at 20%


def test_repeat_units_of_one_voucher_count_once():
    # A gift card redeemable three times is one deal to hold, not three, so a
    # cap of 1 must still allow all three units.
    voucher = mk_deal(
        "gc",
        "giftcard_discount",
        reward_type="fixed_total_amount",
        reward_value=80,  # pay 80 for 100 of face value
        cond_type="voucher_value",
        cond_value=100,
        max_uses_per_transaction=3,
        accepts_all=True,
    )
    res = optimize([voucher], cart_total=1000, cart_quantity=1, max_deals=1)[0]
    assert len(res["path"]) == 1
    assert res["total_savings"] == pytest.approx(60.0)  # 3 units x 20 saved


# 3. The budget is shared across both phases ----------------------------------

def test_budget_is_shared_between_chain_and_tender():
    deals = _coupons(3) + _cards(3)
    path = find_best_path(1000, 1, deals, max_deals=3)
    assert len(path) == 3

    # And spending it all on the chain leaves nothing for tender: with a cap of
    # 2 the engine picks whichever pair saves most, but never three deals.
    assert len(find_best_path(1000, 1, deals, max_deals=2)) == 2


def test_cap_of_one_allows_a_single_deal():
    path = find_best_path(1000, 1, _coupons(2) + _cards(2), max_deals=1)
    assert len(path) == 1


def test_ranked_options_all_respect_the_cap():
    results = optimize(_coupons(3) + _cards(3), cart_total=1000, cart_quantity=1, top_n=10, max_deals=2)
    assert results  # something was found
    assert all(len(r["path"]) <= 2 for r in results)
