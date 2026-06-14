"""Graph construction (Part 3b / 3c).

Vertices are deal instances (duplicated for repeat-usable deals). Edges encode
which deal may legally be applied after another, given the fixed layer order and
*bidirectional* combinability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Fixed global application order (Part 1).
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
    if val == "yes":
        return True
    if val == "no":
        return False
    return unknown_as_yes


def mutually_compatible(a: DealNode, b: DealNode, unknown_as_yes: bool) -> bool:
    """Both sides must accept the other's category (bidirectional rule)."""
    # Duplicate instances of the same deal are self-stackable by user grant
    # (max_uses_per_transaction >= 2). Combinability with itself is implicit.
    if a.deal_id == b.deal_id:
        return True
    return accepts(a, b.category, unknown_as_yes) and accepts(b, a.category, unknown_as_yes)


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
