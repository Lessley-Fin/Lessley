"""Tender allocation: splitting one bill across multiple payment instruments.

Mirrors the real Lee Cooper scenario that motivated this module: Hever (30%
off, loadable up to 1000 ILS) and Behatsdaa (30% off, up to 500 ILS) are
prepaid cards; Mastercard (20% off) is a card-brand rebate. You can't pay the
same ILS through two of them, but you CAN split a large bill across several —
covering the highest-rate options first, up to their own ceiling.
"""

from __future__ import annotations

import pytest

from deal_optimizer.engine import optimize
from deal_optimizer.tender import allocate_tender

from conftest import mk_deal


def _hever():
    return mk_deal("hever", "giftcard_discount", reward_type="percentage_off",
                    reward_value=0.30, max_discount_amount=300, cond_type="min_spend",
                    cond_value=0, accepts_all=True)


def _behatsdaa():
    return mk_deal("behatsdaa", "giftcard_discount", reward_type="percentage_off",
                    reward_value=0.30, max_discount_amount=150, cond_type="min_spend",
                    cond_value=0, accepts_all=True)


def _mastercard():
    return mk_deal("mastercard", "payment_discount", reward_type="percentage_off",
                    reward_value=0.20, cond_type="min_spend", cond_value=0, accepts_all=True)


# --- unit tests on the allocator directly -------------------------------------

def test_small_cart_uses_only_the_best_rate_no_reason_to_split():
    # 500 ILS: Hever alone (30%, cap covers up to 1000) absorbs it all —
    # no benefit to routing any of it through the lower-rate Mastercard (20%).
    allocation = allocate_tender(500, 1, [_hever(), _mastercard()], conflicts=lambda a, b: False)
    assert [u.deal_id for u in allocation.used] == ["hever"]
    assert allocation.total_savings == pytest.approx(150.0)
    assert allocation.price_after == pytest.approx(350.0)


def test_large_cart_splits_across_all_three_by_rate_then_cap():
    # 2000 ILS: Hever covers the first 1000 (30%, its ceiling), Behatsdaa the
    # next 500 (30%, its ceiling), Mastercard the remaining 500 (20%).
    allocation = allocate_tender(2000, 1, [_hever(), _behatsdaa(), _mastercard()], conflicts=lambda a, b: False)
    by_id = {u.deal_id: u for u in allocation.used}
    assert by_id["hever"].ils_covered == pytest.approx(1000.0)
    assert by_id["hever"].savings == pytest.approx(300.0)
    assert by_id["behatsdaa"].ils_covered == pytest.approx(500.0)
    assert by_id["behatsdaa"].savings == pytest.approx(150.0)
    assert by_id["mastercard"].ils_covered == pytest.approx(500.0)
    assert by_id["mastercard"].savings == pytest.approx(100.0)
    assert allocation.total_savings == pytest.approx(550.0)
    assert allocation.price_after == pytest.approx(1450.0)


def test_conflicting_pair_never_combined():
    # If Hever and Mastercard are declared mutually exclusive, the allocator
    # must pick whichever single one saves more instead of "using" both.
    conflicts = lambda a, b: {a, b} == {"hever", "mastercard"}
    allocation = allocate_tender(500, 1, [_hever(), _mastercard()], conflicts=conflicts)
    assert [u.deal_id for u in allocation.used] == ["hever"]


def test_voucher_plus_rate_options_combine():
    # Pais: 200 ILS voucher for 150 (effective rate 25% — better than
    # Mastercard's 20%, worse than Hever/Behatsdaa's 30%) — should slot in
    # between them once their caps are exhausted.
    pais = mk_deal("pais", "giftcard_discount", reward_type="fixed_total_amount",
                    reward_value=150, cond_type="exact_spend", cond_value=200, accepts_all=True)
    allocation = allocate_tender(2000, 1, [_hever(), _behatsdaa(), _mastercard(), pais],
                                 conflicts=lambda a, b: False)
    by_id = {u.deal_id: u for u in allocation.used}
    assert by_id["hever"].ils_covered == pytest.approx(1000.0)
    assert by_id["behatsdaa"].ils_covered == pytest.approx(500.0)
    assert by_id["pais"].ils_covered == pytest.approx(200.0)
    assert by_id["pais"].savings == pytest.approx(50.0)
    assert by_id["mastercard"].ils_covered == pytest.approx(300.0)
    assert by_id["mastercard"].savings == pytest.approx(60.0)
    assert allocation.total_savings == pytest.approx(300.0 + 150.0 + 50.0 + 60.0)


# --- end to end through optimize(), matching the user's own example ----------

def test_end_to_end_500_ils_cart_uses_only_hever():
    res = optimize([_hever(), _behatsdaa(), _mastercard()], cart_total=500, cart_quantity=1)[0]
    assert [d["id"] for d in res["path"]] == ["hever"]
    assert res["final_price"] == pytest.approx(350.0)


def test_end_to_end_2000_ils_cart_splits_hever_behatsdaa_mastercard():
    res = optimize([_hever(), _behatsdaa(), _mastercard()], cart_total=2000, cart_quantity=1)[0]
    assert {d["id"] for d in res["path"]} == {"hever", "behatsdaa", "mastercard"}
    assert res["final_price"] == pytest.approx(1450.0)
    assert res["total_savings"] == pytest.approx(550.0)


def test_top_n_ranks_alternative_tender_combinations():
    # 2000 ILS: best is Hever+Behatsdaa+Mastercard (1450). Weaker alternatives
    # (fewer instruments, or a lower-rate substitute) should rank below it.
    results = optimize([_hever(), _behatsdaa(), _mastercard()], cart_total=2000, cart_quantity=1, top_n=5)
    assert len(results) >= 2
    assert results[0]["final_price"] == pytest.approx(1450.0)
    prices = [r["final_price"] for r in results]
    assert prices == sorted(prices)
    assert [r["rank"] for r in results] == list(range(1, len(results) + 1))
