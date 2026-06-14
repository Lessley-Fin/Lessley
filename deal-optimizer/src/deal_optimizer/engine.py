"""Pathfinding engine (Part 3e/3f/3g).

State-tracking DP over a DAG. The validity of adding a deal depends on every
deal already in the chain, so DP state is ``(current_vertex_id, frozenset(applied))``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .adapter import normalize_deals
from .graph import (
    LAYER_ORDER,
    START_ID,
    DealNode,
    build_vertices,
    directed_edge_allowed,
    mutually_compatible,
)
from .transform import apply_deal


@dataclass
class UserContext:
    member_club_ids: list[str] = field(default_factory=list)
    preferred_channels: list[str] = field(default_factory=list)  # website|mobile_app|physical_store
    uses_this_month: dict[str, int] = field(default_factory=dict)  # {deal_id: uses_in_current_month}


def _deal_is_eligible(deal: dict[str, Any], ctx: UserContext) -> bool:
    constraints = deal.get("constraints", {}) or {}
    elig = constraints.get("eligibility", {}) or {}
    limits = constraints.get("limits", {}) or {}
    channels = constraints.get("redemption_channels", {}) or {}

    # Membership required but user is not a member of the deal's club.
    if elig.get("membership_required") == "yes":
        if deal.get("club_id") not in ctx.member_club_ids:
            return False

    # Channel preference: reject only if EVERY preferred channel is explicitly "no".
    # ("unknown" is treated optimistically — does not disqualify.)
    if ctx.preferred_channels:
        if all(channels.get(ch) == "no" for ch in ctx.preferred_channels):
            return False

    # Monthly usage cap already exhausted.
    cap = limits.get("max_uses_per_month")
    if cap is not None and ctx.uses_this_month.get(deal["id"], 0) >= cap:
        return False

    return True


def find_best_path(
    cart_total: float,
    cart_quantity: int,
    deal_dicts: list[dict[str, Any]],
    user_context: UserContext | None = None,
    unknown_as_yes: bool = True,
) -> list[DealNode]:
    """Find the START → ... → END path yielding the lowest final price."""

    # 1. Normalize shapes, then eligibility prune.
    deal_dicts = normalize_deals(deal_dicts)
    if user_context is not None:
        deal_dicts = [d for d in deal_dicts if _deal_is_eligible(d, user_context)]

    # 2. Expand into vertices (duplicates honored), topological order.
    vertices = build_vertices(deal_dicts)
    vertices.sort(key=lambda v: (LAYER_ORDER[v.category], v.deal_id, v.copy_index))
    by_id = {v.vertex_id: v for v in vertices}

    # 3. State-DP. Keys: (current_vertex_id, frozenset(applied)).
    #    Value: (best_price, predecessor_state_or_None).
    INIT = (START_ID, frozenset())
    dp: dict[tuple[str, frozenset[str]], tuple[float, tuple | None]] = {INIT: (cart_total, None)}

    for v in vertices:
        new_dp: dict[tuple[str, frozenset[str]], tuple[float, tuple | None]] = {}
        for (cur_id, applied), (price, _prev) in dp.items():
            # 4. Try extending this state with v.
            if v.vertex_id in applied:
                continue

            # Edge from cur_id → v must exist (START → anything is always allowed).
            if cur_id != START_ID:
                cur = by_id[cur_id]
                if not directed_edge_allowed(cur, v, unknown_as_yes):
                    continue

            # Path-wide validity: v must be mutually compatible with EVERY prior deal.
            if any(not mutually_compatible(by_id[u_id], v, unknown_as_yes) for u_id in applied):
                continue

            # Apply v's transform; condition may reject (e.g. min_spend not met).
            p_out = apply_deal(price, cart_quantity, v)
            if p_out is None:
                continue

            new_state = (v.vertex_id, applied | {v.vertex_id})
            existing = new_dp.get(new_state)
            if existing is None or p_out < existing[0]:
                new_dp[new_state] = (p_out, (cur_id, applied))

        # Merge new states (their applied sets are distinct from prior ones).
        for k, val in new_dp.items():
            existing = dp.get(k)
            if existing is None or val[0] < existing[0]:
                dp[k] = val

    # 5. Best terminal — END absorbs every state, so pick the global min price.
    best_state, (_best_price, _) = min(dp.items(), key=lambda kv: kv[1][0])

    # 6. Reconstruct path.
    path: list[DealNode] = []
    cur: tuple | None = best_state
    while cur is not None and cur != INIT:
        cur_id, _applied = cur
        if cur_id != START_ID:
            path.append(by_id[cur_id])
        cur = dp[cur][1]
    path.reverse()
    return path


def get_optimal_deal_path(
    file_path: str,
    target_store_id: str,
    cart_total: float,
    cart_quantity: int,
    user_context: UserContext | None = None,
    unknown_as_yes: bool = True,
) -> dict[str, Any]:
    """Public entry point. Reads deals from ``file_path``, filters by store, optimizes."""
    with open(file_path, encoding="utf-8") as f:
        all_deals = json.load(f)

    store_deals = [d for d in all_deals if _deal_matches_store(d, target_store_id)]
    return optimize(store_deals, cart_total, cart_quantity, user_context, unknown_as_yes)


def _deal_matches_store(deal: dict[str, Any], target_store_id: str) -> bool:
    if deal.get("store_id") == target_store_id:
        return True
    return target_store_id in (deal.get("group_member_stores", []) or [])


def optimize(
    deal_dicts: list[dict[str, Any]],
    cart_total: float,
    cart_quantity: int,
    user_context: UserContext | None = None,
    unknown_as_yes: bool = True,
) -> dict[str, Any]:
    """Optimize an in-memory list of deals; returns the structured result dict."""
    path = find_best_path(cart_total, cart_quantity, deal_dicts, user_context, unknown_as_yes)

    per_step = []
    price = cart_total
    for node in path:
        price_out = apply_deal(price, cart_quantity, node)
        # path nodes are guaranteed applicable, but guard against None defensively
        price_out = price if price_out is None else price_out
        per_step.append({"deal_id": node.deal_id, "price_in": price, "price_out": price_out})
        price = price_out

    return {
        "path": [node.raw for node in path],
        "starting_price": cart_total,
        "final_price": price,
        "total_savings": cart_total - price,
        "per_step": per_step,
    }
