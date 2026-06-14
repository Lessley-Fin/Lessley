"""Part 5 verification scenarios from the plan."""

from __future__ import annotations

import pytest

from deal_optimizer.engine import find_best_path, optimize
from deal_optimizer.graph import DealNode, build_vertices, directed_edge_allowed

from conftest import mk_deal


def _ids(path: list[DealNode]) -> list[str]:
    return [n.deal_id for n in path]


# 1. Bug fixes -----------------------------------------------------------------

def test_percentage_is_ratio_not_divided_again():
    # Lee Cooper: 13% off, min_quantity 1, cart 500 qty 1 → savings 65, final 435.
    deal = mk_deal("lc", "giftcard_discount", reward_type="percentage_off",
                   reward_value=0.13, cond_type="min_quantity", cond_value=1, accepts_all=True)
    res = optimize([deal], cart_total=500, cart_quantity=1)
    assert res["total_savings"] == pytest.approx(65.0)
    assert res["final_price"] == pytest.approx(435.0)


def test_min_quantity_off_by_one_qty1_qualifies():
    deal = mk_deal("lc", "giftcard_discount", reward_type="percentage_off",
                   reward_value=0.13, cond_type="min_quantity", cond_value=1, accepts_all=True)
    # quantity 1 must qualify for min_quantity 1 (was rejected by <=).
    path = find_best_path(500, 1, [deal])
    assert _ids(path) == ["lc"]


# 2. Single-deal sanity --------------------------------------------------------

def test_single_deal_matches_legacy_result():
    # Plan's worked example: final price 472.5 on a 500 cart → a 5.5% store sale.
    rami = mk_deal("rami", "store_sale", reward_type="percentage_off",
                   reward_value=0.055, cond_type="min_spend", cond_value=0, accepts_all=True)
    res = optimize([rami], cart_total=500, cart_quantity=1)
    assert res["final_price"] == pytest.approx(472.5)


# 3. Stack scenario ------------------------------------------------------------

def test_two_coupons_stack():
    a = mk_deal("A", "coupon", reward_type="percentage_off", reward_value=0.10,
                combinability={"stackable_with_coupons": "yes"})
    b = mk_deal("B", "coupon", reward_type="percentage_off", reward_value=0.05,
                combinability={"stackable_with_coupons": "yes"})
    res = optimize([a, b], cart_total=1000, cart_quantity=1)
    assert res["final_price"] == pytest.approx(855.0)
    assert sorted(_ids(find_best_path(1000, 1, [a, b]))) == ["A", "B"]


# 4. Conflicting deals (one-sided refusal blocks the edge) ---------------------

def test_one_sided_refusal_blocks_edge():
    x = mk_deal("X", "coupon", reward_type="percentage_off", reward_value=0.10,
                combinability={"stackable_with_payment_discounts": "yes"})
    y = mk_deal("Y", "payment_discount", reward_type="percentage_off", reward_value=0.20,
                combinability={"stackable_with_coupons": "no"})
    # strict so 'unknown' fields don't accidentally permit stacking
    path = find_best_path(1000, 1, [x, y], unknown_as_yes=False)
    # Y refuses coupons → cannot stack → pick the single best (Y at 20%).
    assert _ids(path) == ["Y"]


# 5. Layer-order enforcement ---------------------------------------------------

def test_layer_order_direction():
    p = mk_deal("P", "store_sale", accepts_all=True)
    c = mk_deal("C", "cashback", accepts_all=True)
    verts = {v.deal_id: v for v in build_vertices([p, c])}
    assert directed_edge_allowed(verts["P"], verts["C"], unknown_as_yes=True) is True
    assert directed_edge_allowed(verts["C"], verts["P"], unknown_as_yes=True) is False


# 6. Path-wide chain validity (3-deal stack, mid-chain refusal) ----------------

def test_path_wide_chain_validity():
    a = mk_deal("A", "coupon", reward_type="percentage_off", reward_value=0.10, accepts_all=True)
    b = mk_deal("B", "giftcard_discount", reward_type="percentage_off", reward_value=0.10, accepts_all=True)
    # C accepts everything EXCEPT coupons.
    c = mk_deal("C", "payment_discount", reward_type="percentage_off", reward_value=0.10,
                accepts_all=True, combinability={"stackable_with_coupons": "no"})
    path = find_best_path(1000, 1, [a, b, c], unknown_as_yes=True)
    ids = set(_ids(path))
    # The full A,B,C stack is illegal (C refuses A). A and C must never coexist.
    assert not ({"A", "C"} <= ids)
    # whichever valid pair is cheaper — both yield same % here, so length 2.
    assert len(path) == 2


# 7. Duplicate vertices for repeat-use ----------------------------------------

def test_duplicate_vertices_apply_twice():
    deal = mk_deal("tx", "giftcard_discount", reward_type="percentage_off",
                   reward_value=0.10, accepts_all=True, max_uses_per_transaction=2)
    verts = build_vertices([deal])
    assert [v.vertex_id for v in verts] == ["tx#1", "tx#2"]
    # 100 → 90 → 81 when applied twice.
    res = optimize([deal], cart_total=100, cart_quantity=1)
    assert res["final_price"] == pytest.approx(81.0)
    assert len(res["per_step"]) == 2


def test_duplicate_vertices_edge_only_in_order():
    deal = mk_deal("tx", "giftcard_discount", reward_value=0.10, accepts_all=True,
                   max_uses_per_transaction=2)
    verts = {v.vertex_id: v for v in build_vertices([deal])}
    assert directed_edge_allowed(verts["tx#1"], verts["tx#2"], True) is True
    assert directed_edge_allowed(verts["tx#2"], verts["tx#1"], True) is False


# 9. End-to-end ----------------------------------------------------------------

def test_end_to_end_lee_cooper():
    lc = mk_deal("lc", "giftcard_discount", reward_type="percentage_off",
                 reward_value=0.13, cond_type="min_quantity", cond_value=1, accepts_all=True)
    res = optimize([lc], cart_total=500, cart_quantity=1)
    assert res["final_price"] == pytest.approx(435.0)
