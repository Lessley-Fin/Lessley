"""Tiered loadable cards (``reward.tiers``) and their mutual exclusion.

The motivating source is PaisPlus's cash cards, whose real ladders are:

    networks/regular      25% on 0-600,  15% on 600-1500   -> max 285 saved
    networks/vip          25% on 0-1200, 15% on 1200-1800  -> max 390 saved
    food-chains/regular   7.5% on 0-400, 5% on 400-2200    -> max 120 saved

Before ladders existed these were emitted as an uncapped flat 25%, so a
10,000 ILS cart claimed 2,500 ILS of savings from a card that tops out at
1,500 ILS of load.
"""

from __future__ import annotations

import pytest

from deal_optimizer.adapter import normalize_deal
from deal_optimizer.engine import optimize
from deal_optimizer.graph import DealNode, mutually_compatible, refusal_reasons
from deal_optimizer.tender import allocate_tender
from deal_optimizer.transform import apply_deal

from conftest import mk_deal

NETWORKS_REGULAR = [
    {"from_amount": 0, "to_amount": 600, "percentage_off": 0.25},
    {"from_amount": 600, "to_amount": 1500, "percentage_off": 0.15},
]
NETWORKS_VIP = [
    {"from_amount": 0, "to_amount": 1200, "percentage_off": 0.25},
    {"from_amount": 1200, "to_amount": 1800, "percentage_off": 0.15},
]


def _card(deal_id="pais", tiers=None, **kw):
    tiers = NETWORKS_REGULAR if tiers is None else tiers
    kw.setdefault("reward_value", tiers[0]["percentage_off"])
    kw.setdefault("accepts_all", True)
    return mk_deal(deal_id, "giftcard_discount", tiers=tiers, **kw)


def _no_conflicts(a, b):
    return False


# ── the reported bug ───────────────────────────────────────────────────────


def test_huge_cart_is_bounded_by_the_top_of_the_ladder():
    # The whole point: 10,000 ILS must not yield 25% of 10,000.
    allocation = allocate_tender(10_000, 1, [_card()], _no_conflicts)

    assert allocation.total_savings == pytest.approx(285.0)
    (usage,) = allocation.used
    assert usage.ils_covered == pytest.approx(1500.0)


def test_both_rungs_are_reported_separately():
    allocation = allocate_tender(10_000, 1, [_card()], _no_conflicts)
    (usage,) = allocation.used

    assert [(s.tier_index, s.rate, s.ils_covered, s.savings) for s in usage.segments] == [
        (0, 0.25, pytest.approx(600.0), pytest.approx(150.0)),
        (1, 0.15, pytest.approx(900.0), pytest.approx(135.0)),
    ]
    assert sum(s.ils_covered for s in usage.segments) == pytest.approx(usage.ils_covered)
    assert sum(s.savings for s in usage.segments) == pytest.approx(usage.savings)


@pytest.mark.parametrize(
    "cart,expected_savings,expected_covered,expected_rungs",
    [
        (400, 100.0, 400, 1),  # inside rung 1
        (600, 150.0, 600, 1),  # exactly the rung-1 boundary
        (700, 165.0, 700, 2),  # 600 @ 25% + 100 @ 15%
        (1500, 285.0, 1500, 2),  # exactly the ceiling
        (10_000, 285.0, 1500, 2),  # past the ceiling
    ],
)
def test_ladder_across_the_boundaries(cart, expected_savings, expected_covered, expected_rungs):
    allocation = allocate_tender(cart, 1, [_card()], _no_conflicts)
    (usage,) = allocation.used

    assert allocation.total_savings == pytest.approx(expected_savings)
    assert usage.ils_covered == pytest.approx(expected_covered)
    assert len(usage.segments) == expected_rungs


# ── the interleaving case that a naive per-option greedy gets wrong ────────


def test_a_better_flat_deal_outranks_a_ladders_lower_rung():
    # Card A: 30% on the first 500, then only 10% on the next 500.
    # Card B: flat 20%, uncapped.
    # Optimal on 1500 is A's top rung (500 @ 30% = 150) + B on the rest
    # (1000 @ 20% = 200) = 350. Sorting whole cards by headline rate would
    # drain A's 10% rung first and return 300.
    ladder = _card(
        "A",
        tiers=[
            {"from_amount": 0, "to_amount": 500, "percentage_off": 0.30},
            {"from_amount": 500, "to_amount": 1000, "percentage_off": 0.10},
        ],
    )
    flat = mk_deal("B", "giftcard_discount", reward_value=0.20, accepts_all=True)

    allocation = allocate_tender(1500, 1, [ladder, flat], _no_conflicts)
    by_id = {u.deal_id: u for u in allocation.used}

    assert allocation.total_savings == pytest.approx(350.0)
    assert by_id["A"].ils_covered == pytest.approx(500.0)
    assert by_id["B"].ils_covered == pytest.approx(1000.0)
    # A's second rung was correctly left unused.
    assert [s.tier_index for s in by_id["A"].segments] == [0]


def test_a_ladders_lower_rung_is_still_used_when_it_beats_the_alternative():
    ladder = _card(
        "A",
        tiers=[
            {"from_amount": 0, "to_amount": 500, "percentage_off": 0.30},
            {"from_amount": 500, "to_amount": 1000, "percentage_off": 0.10},
        ],
    )
    flat = mk_deal("B", "giftcard_discount", reward_value=0.05, accepts_all=True)

    allocation = allocate_tender(1500, 1, [ladder, flat], _no_conflicts)
    by_id = {u.deal_id: u for u in allocation.used}

    # 500 @ 30% + 500 @ 10% + 500 @ 5% = 150 + 50 + 25
    assert allocation.total_savings == pytest.approx(225.0)
    assert [s.tier_index for s in by_id["A"].segments] == [0, 1]


# ── flat deals must be untouched ───────────────────────────────────────────


def test_flat_capped_deal_behaves_exactly_as_before_and_reports_no_segments():
    flat = mk_deal(
        "flat", "giftcard_discount", reward_value=0.30, max_discount_amount=300, accepts_all=True
    )
    allocation = allocate_tender(2000, 1, [flat], _no_conflicts)
    (usage,) = allocation.used

    assert usage.ils_covered == pytest.approx(1000.0)  # 300 / 0.30
    assert usage.savings == pytest.approx(300.0)
    assert usage.segments == []


def test_max_uses_per_transaction_multiplies_every_rung():
    card = _card(max_uses_per_transaction=2)
    allocation = allocate_tender(10_000, 1, [card], _no_conflicts)
    (usage,) = allocation.used

    assert usage.ils_covered == pytest.approx(3000.0)  # 2 x 1500
    assert usage.savings == pytest.approx(570.0)  # 2 x 285


# ── malformed ladders degrade, never raise ────────────────────────────────


@pytest.mark.parametrize(
    "tiers",
    [
        [],
        "not-a-list",
        [{"from_amount": 0, "to_amount": None, "percentage_off": 0.25}],
        [{"from_amount": 0, "percentage_off": 0.25}],
        [{"from_amount": 600, "to_amount": 600, "percentage_off": 0.25}],  # zero width
        ["not-a-dict"],
    ],
)
def test_malformed_ladder_falls_back_to_the_flat_cap(tiers):
    deal = mk_deal(
        "broken",
        "giftcard_discount",
        reward_value=0.25,
        max_discount_amount=285,
        accepts_all=True,
    )
    deal["discount_logic"]["reward"]["tiers"] = tiers

    allocation = allocate_tender(10_000, 1, [deal], _no_conflicts)
    (usage,) = allocation.used

    # Flat path: capped at 285 saved, i.e. 285 / 0.25 = 1140 ILS covered.
    assert usage.savings == pytest.approx(285.0)
    assert usage.ils_covered == pytest.approx(1140.0)
    assert usage.segments == []


# ── apply_deal (the chain path) ────────────────────────────────────────────


@pytest.mark.parametrize(
    "price,expected_savings",
    [
        (400, 100.0),
        (600, 150.0),
        (1000, 210.0),  # 600 @ 25% + 400 @ 15% — a flat 25% would say 250
        (1500, 285.0),
        (10_000, 285.0),
    ],
)
def test_apply_deal_walks_the_ladder(price, expected_savings):
    deal = _card()
    node = DealNode(
        vertex_id="v",
        deal_id="pais",
        category="giftcard_discount",
        copy_index=1,
        discount_logic=deal["discount_logic"],
        constraints=deal["constraints"],
        raw=deal,
    )
    assert apply_deal(price, 1, node) == pytest.approx(price - expected_savings)


# ── mutual exclusion between membership tiers ─────────────────────────────


def _node(deal):
    return DealNode(
        vertex_id=deal["id"],
        deal_id=deal["id"],
        category=deal["deal_type"],
        copy_index=1,
        discount_logic=deal["discount_logic"],
        constraints=deal["constraints"],
        raw=deal,
    )


def test_deals_sharing_an_exclusive_group_cannot_be_combined():
    a = _node(_card("regular", exclusive_group="paisplus_networks:chit-5001"))
    b = _node(_card("vip", tiers=NETWORKS_VIP, exclusive_group="paisplus_networks:chit-5001"))

    assert not mutually_compatible(a, b, unknown_as_yes=True)
    assert "mutually exclusive" in refusal_reasons(a, b, unknown_as_yes=True)[0]


def test_different_or_absent_exclusive_groups_are_unaffected():
    a = _node(_card("a", exclusive_group="paisplus_networks:chit-5001"))
    b = _node(_card("b", exclusive_group="paisplus_food_chains:chit-1020"))
    plain_x = _node(_card("x"))
    plain_y = _node(_card("y"))

    assert mutually_compatible(a, b, unknown_as_yes=True)
    assert mutually_compatible(plain_x, plain_y, unknown_as_yes=True)


def test_only_one_membership_tier_is_allocated_to_a_cart():
    regular = _card("regular", exclusive_group="g")
    vip = _card("vip", tiers=NETWORKS_VIP, exclusive_group="g")

    def conflicts(id_a, id_b):
        return not mutually_compatible(
            {"regular": _node(regular), "vip": _node(vip)}[id_a],
            {"regular": _node(regular), "vip": _node(vip)}[id_b],
            unknown_as_yes=True,
        )

    allocation = allocate_tender(10_000, 1, [regular, vip], conflicts)

    assert [u.deal_id for u in allocation.used] == ["vip"]
    assert allocation.total_savings == pytest.approx(390.0)
    # Not 285 + 390 — the two tiers are the same physical card.
    assert allocation.total_savings < 675.0


# ── end to end through optimize() ─────────────────────────────────────────


def test_optimize_reports_the_split_in_per_step():
    regular = _card("regular", exclusive_group="g", store_id="s1")
    vip = _card("vip", tiers=NETWORKS_VIP, exclusive_group="g", store_id="s1")

    best = optimize([regular, vip], cart_total=10_000, cart_quantity=1, top_n=1)[0]

    assert best["total_savings"] == pytest.approx(390.0)
    (step,) = best["per_step"]
    assert step["deal_id"] == "vip"
    assert step["ils_covered"] == pytest.approx(1800.0)
    assert step["segments"] == [
        {"tier_index": 0, "rate": 0.25, "ils_covered": 1200.0, "savings": 300.0},
        {"tier_index": 1, "rate": 0.15, "ils_covered": 600.0, "savings": 90.0},
    ]


def test_flat_deals_report_segments_as_none():
    flat = mk_deal("flat", "coupon", reward_value=0.10, accepts_all=True)
    best = optimize([flat], cart_total=100, cart_quantity=1, top_n=1)[0]

    (step,) = best["per_step"]
    assert step["segments"] is None


def test_normalize_deal_preserves_tiers_and_exclusive_group():
    # normalize_deal strips discount_logic["constraints"]; it must not take
    # the new keys with it.
    deal = _card(exclusive_group="g")
    deal["discount_logic"]["constraints"] = {"legacy": True}

    out = normalize_deal(deal)

    assert "constraints" not in out["discount_logic"]
    assert out["discount_logic"]["reward"]["tiers"] == NETWORKS_REGULAR
    assert out["discount_logic"]["exclusive_group"] == "g"
