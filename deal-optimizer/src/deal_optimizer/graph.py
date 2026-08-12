"""Graph construction (Part 3b / 3c).

Vertices are deal instances (duplicated for repeat-usable deals). Edges encode
which deal may legally be applied after another, given the fixed layer order and
*bidirectional* combinability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Fixed global application order (Part 1).
#
# Only store_sale/member_discount/coupon actually chain through this graph
# (engine.py's phase 1) — giftcard_discount/payment_discount/cashback are all
# "tender" deals (they discount whichever slice of the bill was paid through
# that specific instrument, not the bill as a whole) and are instead solved as
# a bill-splitting allocation in tender.py. Their entries below only matter
# for ACCEPTS_KEY (combinability lookups) and are otherwise unused numbers.
LAYER_ORDER = {
    "store_sale": 0,
    "member_discount": 1,
    "coupon": 2,
    "giftcard_discount": 3,
    "payment_discount": 4,
    "cashback": 5,
}

# Combinability key governing whether a deal ACCEPTS a partner of the given deal_type.
ACCEPTS_KEY = {
    "store_sale": "stackable_with_store_sale",
    "member_discount": "stackable_with_member_discounts",
    "coupon": "stackable_with_coupons",
    "giftcard_discount": "stackable_with_giftcards",
    "payment_discount": "stackable_with_payment_discounts",
    "cashback": "stackable_with_cashback",
}

START_ID = "__start__"
END_ID = "__end__"


@dataclass(frozen=True)
class DealNode:
    vertex_id: str  # e.g. "019dc1b5...#1" — copy number for duplicates
    deal_id: str  # the underlying deal's canonical id
    category: str  # the deal_type value
    copy_index: int  # 1..N for duplicates; 1 for single-use deals
    discount_logic: dict[str, Any]
    constraints: dict[str, Any]  # the full lean DealConstraints dict
    raw: dict[str, Any]  # the original deal dict (for output)
    ils_covered: float | None = None  # tender deals only: how much of the bill this deal paid for
    # Tiered tender deals only: the per-rung split of ``ils_covered``, as plain
    # dicts (tier_index/rate/ils_covered/savings). None for flat deals.
    tender_segments: list[dict[str, Any]] | None = None


def build_vertices(deals: list[dict[str, Any]]) -> list[DealNode]:
    """Expand deals into vertices, honoring ``max_uses_per_transaction`` duplicates."""
    vertices: list[DealNode] = []
    for d in deals:
        limits = (d.get("constraints", {}) or {}).get("limits", {}) or {}
        max_per_tx = limits.get("max_uses_per_transaction") or 1
        if max_per_tx < 1:
            max_per_tx = 1
        deal_id = d["id"]
        for i in range(1, max_per_tx + 1):
            vertices.append(
                DealNode(
                    vertex_id=f"{deal_id}#{i}",
                    deal_id=deal_id,
                    category=d["deal_type"],
                    copy_index=i,
                    discount_logic=d.get("discount_logic", {}) or {},
                    constraints=d.get("constraints", {}) or {},
                    raw=d,
                )
            )
    return vertices


def accepts(deal: DealNode, other_type: str, unknown_as_yes: bool) -> bool:
    """True if ``deal`` allows being stacked with a deal of ``other_type``."""
    key = ACCEPTS_KEY[other_type]
    val = (deal.constraints.get("combinability", {}) or {}).get(key, "unknown")
    # Enriched deals carry booleans (True/False); the mock/legacy string
    # convention uses "yes"/"no". Honor both; anything else falls back.
    if val is True or val == "yes":
        return True
    if val is False or val == "no":
        return False
    return unknown_as_yes


def exclusive_group(deal: DealNode) -> str | None:
    """The mutual-exclusion key two deals must not share, if any.

    Some sources emit several deals describing the *same* physical instrument —
    a PaisPlus cash card publishes one deal per membership tier (regular / vip),
    but a cardholder has exactly one tier. They aren't alternatives the graph can
    stack; they're alternatives it must choose between. Combinability can't say
    this: it is keyed on ``deal_type``, and both sides are ``giftcard_discount``.
    """
    group = deal.discount_logic.get("exclusive_group")
    return group if isinstance(group, str) and group else None


def mutually_compatible(a: DealNode, b: DealNode, unknown_as_yes: bool) -> bool:
    """Both sides must accept the other's category (bidirectional rule)."""
    # Duplicate instances of the same deal are self-stackable by user grant
    # (max_uses_per_transaction >= 2). Combinability with itself is implicit.
    if a.deal_id == b.deal_id:
        return True
    group = exclusive_group(a)
    if group is not None and group == exclusive_group(b):
        return False
    return accepts(a, b.category, unknown_as_yes) and accepts(b, a.category, unknown_as_yes)


def refusal_reasons(a: DealNode, b: DealNode, unknown_as_yes: bool) -> list[str]:
    """Human-readable reasons ``a`` and ``b`` are NOT mutually compatible (empty if they are)."""
    if a.deal_id == b.deal_id:
        return []
    group = exclusive_group(a)
    if group is not None and group == exclusive_group(b):
        return [f"{a.deal_id} and {b.deal_id} are mutually exclusive (exclusive_group={group!r})"]
    reasons = []
    if not accepts(a, b.category, unknown_as_yes):
        val = (a.constraints.get("combinability", {}) or {}).get(ACCEPTS_KEY[b.category], "unknown")
        reasons.append(f"{a.deal_id} refuses {b.category} ({ACCEPTS_KEY[b.category]}={val!r})")
    if not accepts(b, a.category, unknown_as_yes):
        val = (b.constraints.get("combinability", {}) or {}).get(ACCEPTS_KEY[a.category], "unknown")
        reasons.append(f"{b.deal_id} refuses {a.category} ({ACCEPTS_KEY[a.category]}={val!r})")
    return reasons


def directed_edge_allowed(src: DealNode, dst: DealNode, unknown_as_yes: bool) -> bool:
    """Raw graph construction rule (the chain-validity check in engine is binding)."""
    if src.vertex_id == dst.vertex_id:
        return False

    # Duplicate vertices of the same deal chain strictly in copy-index order.
    if src.deal_id == dst.deal_id:
        return dst.copy_index == src.copy_index + 1

    # Layer order: never go to an earlier layer.
    if LAYER_ORDER[dst.category] < LAYER_ORDER[src.category]:
        return False

    # Same-layer pair oriented deterministically by deal_id to keep the graph acyclic.
    if LAYER_ORDER[src.category] == LAYER_ORDER[dst.category]:
        if src.deal_id >= dst.deal_id:
            return False

    return mutually_compatible(src, dst, unknown_as_yes)
