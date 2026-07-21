"""Pathfinding engine (Part 3e/3f/3g).

State-tracking DP over a DAG. The validity of adding a deal depends on every
deal already in the chain, so DP state is ``(current_vertex_id, frozenset(applied))``.

Two phases:

  1. A DAG chain over store_sale/member_discount/coupon — price-level deals.
     Each really does discount whatever's left, regardless of how the bill is
     eventually paid, so chaining them one after another is exact.
  2. An optimal tender allocation over giftcard_discount/payment_discount/
     cashback — payment-instrument deals. Each only discounts the specific
     slice of money routed through that instrument (a gift-card load, a
     card-brand rebate, cashback earned on the card actually used) — you
     can't pay the same ILS through two instruments, so these can't chain the
     same way without double-counting. See ``tender.py`` for the bill-
     splitting solver.

Phase 2 runs once per state reached in phase 1 and IS the final phase — its
result is the final price, there is nothing after it.
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
from .tender import TenderAllocation, TenderUsage, allocate_tender_top_k
from .transform import apply_deal

_CHAIN_CATEGORIES = ("store_sale", "member_discount", "coupon")
_TENDER_CATEGORIES = ("giftcard_discount", "payment_discount", "cashback")


@dataclass
class UserContext:
    member_club_ids: list[str] = field(default_factory=list)
    preferred_store_types: list[str] = field(default_factory=list)  # outlets|online|physical
    uses_this_month: dict[str, int] = field(default_factory=dict)  # {deal_id: uses_in_current_month}


# preferred_store_type value → store_coverage key
_STORE_TYPE_KEYS = {
    "outlets": "is_include_outlets_stores",
    "online": "is_include_online_stores",
    "physical": "is_include_physical_stores",
}

# A store type is "excluded" when the deal says so explicitly — as the yes/no/unknown
# string "no" (optimizer/mock convention) or the boolean False (enriched-deal output).
_EXCLUDED = ("no", False)


def _deal_eligibility(deal: dict[str, Any], ctx: UserContext) -> tuple[bool, str]:
    """Return ``(keep, reason)`` — the single source of truth for the eligibility prune."""
    constraints = deal.get("constraints", {}) or {}
    elig = constraints.get("eligibility", {}) or {}
    limits = constraints.get("limits", {}) or {}
    coverage = constraints.get("store_coverage", {}) or {}

    # Membership required but user is not a member of the deal's club.
    if elig.get("membership_required") == "yes":
        club_id = deal.get("club_id")
        if club_id not in ctx.member_club_ids:
            return False, f"membership_required=yes, club_id={club_id!r} not in user clubs {ctx.member_club_ids}"

    # Store-type preference: reject only if EVERY preferred store type is explicitly
    # excluded by the deal. ("unknown"/absent is treated optimistically — no disqualify.)
    if ctx.preferred_store_types:
        if all(
            coverage.get(_STORE_TYPE_KEYS.get(st, st)) in _EXCLUDED for st in ctx.preferred_store_types
        ):
            return False, f"all preferred store types {ctx.preferred_store_types} are excluded ({coverage})"

    # Monthly usage cap already exhausted.
    cap = limits.get("max_uses_per_month")
    if cap is not None:
        used = ctx.uses_this_month.get(deal["id"], 0)
        if used >= cap:
            return False, f"monthly cap reached: used {used}/{cap}"

    return True, "eligible"


def _wrapper_node(deal: dict[str, Any]) -> DealNode:
    """A DealNode for a tender-phase deal, used only for combinability checks."""
    return DealNode(
        vertex_id=deal["id"],
        deal_id=deal["id"],
        category=deal["deal_type"],
        copy_index=1,
        discount_logic=deal.get("discount_logic", {}) or {},
        constraints=deal.get("constraints", {}) or {},
        raw=deal,
    )


def _synthetic_tender_node(deal: dict[str, Any], usage: TenderUsage) -> DealNode:
    """A DealNode representing exactly this deal's share of the tender
    allocation — ``discount_logic`` is overridden to a flat deduction so
    ``apply_deal`` reproduces the allocator's result during price-trace
    reconstruction; ``ils_covered`` records how much of the bill it paid for;
    ``raw`` keeps the original deal for display/reporting."""
    return DealNode(
        vertex_id=f"{deal['id']}#tender",
        deal_id=deal["id"],
        category=deal["deal_type"],
        copy_index=1,
        discount_logic={
            "condition": {"type": "min_spend", "value": 0},
            "reward": {"type": "fixed_discount_amount", "value": usage.savings},
        },
        constraints=deal.get("constraints", {}) or {},
        raw=deal,
        ils_covered=usage.ils_covered,
    )


def _run_chain_dp(
    vertices: list[DealNode],
    seed: dict[tuple[str, frozenset[str]], tuple[float, tuple | None]],
    by_id: dict[str, DealNode],
    cart_quantity: int,
    unknown_as_yes: bool,
    verbose: bool,
) -> dict[tuple[str, frozenset[str]], tuple[float, tuple | None]]:
    """The state-DP sweep (Part 3e/3f/3g) over the price-level chain vertices."""
    dp = dict(seed)
    for v in vertices:
        new_dp: dict[tuple[str, frozenset[str]], tuple[float, tuple | None]] = {}
        stats = {"already_applied": 0, "edge_blocked": 0, "path_conflict": 0, "condition_failed": 0, "accepted": 0}
        for (cur_id, applied), (price, _prev) in dp.items():
            if v.vertex_id in applied:
                stats["already_applied"] += 1
                continue

            if cur_id != START_ID:
                cur = by_id[cur_id]
                if not directed_edge_allowed(cur, v, unknown_as_yes):
                    stats["edge_blocked"] += 1
                    continue

            if any(not mutually_compatible(by_id[u_id], v, unknown_as_yes) for u_id in applied):
                stats["path_conflict"] += 1
                continue

            p_out = apply_deal(price, cart_quantity, v)
            if p_out is None:
                stats["condition_failed"] += 1
                continue

            stats["accepted"] += 1
            new_state = (v.vertex_id, applied | {v.vertex_id})
            existing = new_dp.get(new_state)
            if existing is None or p_out < existing[0]:
                new_dp[new_state] = (p_out, (cur_id, applied))

        if verbose:
            print(
                f"  {v.vertex_id:<28} states_before={len(dp):<5} accepted={stats['accepted']:<4} "
                f"already_applied={stats['already_applied']:<4} edge_blocked={stats['edge_blocked']:<4} "
                f"path_conflict={stats['path_conflict']:<4} condition_failed={stats['condition_failed']:<4}"
            )

        for k, val in new_dp.items():
            existing = dp.get(k)
            if existing is None or val[0] < existing[0]:
                dp[k] = val

    return dp


def _reconstruct_chain_path(
    chain_state: tuple[str, frozenset[str]],
    dp: dict[tuple[str, frozenset[str]], tuple[float, tuple | None]],
    by_id: dict[str, DealNode],
    init: tuple[str, frozenset[str]],
) -> list[DealNode]:
    """Walk phase-1's predecessor pointers back from ``chain_state`` to ``init``."""
    path: list[DealNode] = []
    cur: tuple | None = chain_state
    while cur is not None and cur != init:
        cur_id, _applied = cur
        if cur_id != START_ID:
            path.append(by_id[cur_id])
        cur = dp[cur][1]
    path.reverse()
    return path


def find_top_paths(
    cart_total: float,
    cart_quantity: int,
    deal_dicts: list[dict[str, Any]],
    user_context: UserContext | None = None,
    unknown_as_yes: bool = True,
    top_n: int = 5,
    verbose: bool = False,
) -> list[list[DealNode]]:
    """Find up to ``top_n`` distinct legal combinations of deals, cheapest
    first (rank 0 is the same winner ``find_best_path`` would return), in two
    phases:

    1. DAG chain over store_sale/member_discount/coupon (price-level deals).
    2. For every state reached in phase 1, solve up to ``top_n`` tender
       allocations (giftcard_discount/payment_discount/cashback) that split
       the remaining bill across payment instruments — see ``tender.py``.
       This is the final phase; its results are the final prices.

    Every (chain state, tender allocation) combination is a candidate; they
    are pooled, deduplicated by their actual set of deals used (many
    candidates collapse to the same real-world outcome), and the cheapest
    ``top_n`` are returned.

    ``verbose=True`` prints the eligibility prune, the phase-1 DP sweep, and
    the tender allocations chosen from every phase-1 state.
    """

    # 1. Normalize shapes, then eligibility prune.
    deal_dicts = normalize_deals(deal_dicts)
    if verbose:
        print(f"\n=== ELIGIBILITY ({len(deal_dicts)} deals, unknown_as_yes={unknown_as_yes}) ===")
    if user_context is not None:
        kept = []
        for d in deal_dicts:
            keep, reason = _deal_eligibility(d, user_context)
            if verbose:
                print(f"  [{'KEEP ' if keep else 'PRUNE'}] {d['id']:<28} {reason}")
            if keep:
                kept.append(d)
        deal_dicts = kept
    elif verbose:
        print("  (no user_context supplied — every deal is eligible)")

    chain_deals = [d for d in deal_dicts if d["deal_type"] in _CHAIN_CATEGORIES]
    tender_deals = [d for d in deal_dicts if d["deal_type"] in _TENDER_CATEGORIES]
    tender_by_deal_id = {d["id"]: d for d in tender_deals}
    tender_nodes_by_id = {d["id"]: _wrapper_node(d) for d in tender_deals}

    # 2. Phase 1 — chain DP over store_sale/member_discount/coupon.
    vertices = build_vertices(chain_deals)
    vertices.sort(key=lambda v: (LAYER_ORDER[v.category], v.deal_id, v.copy_index))
    by_id: dict[str, DealNode] = {v.vertex_id: v for v in vertices}
    by_id.update(tender_nodes_by_id)

    if verbose:
        print(f"\n=== PHASE 1 — PRICE-LEVEL CHAIN ({len(vertices)} vertices: store_sale/member_discount/coupon) ===")

    INIT = (START_ID, frozenset())
    dp = _run_chain_dp(vertices, {INIT: (cart_total, None)}, by_id, cart_quantity, unknown_as_yes, verbose)

    # The same combo of chain deals (`applied`) can be reached via different
    # `cur_id` (last-added vertex) and therefore appear as separate dp keys —
    # collapse to one entry per distinct combo, keeping its cheapest price.
    best_by_applied: dict[frozenset[str], tuple[float, tuple[str, frozenset[str]]]] = {}
    for chain_state, (price_in, _prev) in dp.items():
        _cur_id, applied = chain_state
        existing = best_by_applied.get(applied)
        if existing is None or price_in < existing[0]:
            best_by_applied[applied] = (price_in, chain_state)

    # 3. Phase 2 — up to top_n tender allocations per distinct phase-1 combo. Final phase.
    def _conflicts(id_a: str, id_b: str) -> bool:
        return not mutually_compatible(tender_nodes_by_id[id_a], tender_nodes_by_id[id_b], unknown_as_yes)

    if verbose:
        print(
            f"\n=== PHASE 2 — TENDER ALLOCATION "
            f"({len(tender_deals)} candidate deals: giftcard_discount/payment_discount/cashback) ==="
        )

    candidates: list[tuple[float, tuple[str, frozenset[str]], TenderAllocation]] = []
    for applied, (price_in, chain_state) in best_by_applied.items():
        eligible = [
            d
            for d in tender_deals
            if all(mutually_compatible(by_id[u_id], tender_nodes_by_id[d["id"]], unknown_as_yes) for u_id in applied)
        ]
        allocations = allocate_tender_top_k(price_in, cart_quantity, eligible, _conflicts, k=top_n)
        for allocation in allocations:
            candidates.append((allocation.price_after, chain_state, allocation))

        if verbose:
            print(f"  from chain-state {sorted(applied)}: price {price_in:.2f}, {len(allocations)} tender option(s):")
            for allocation in allocations:
                if allocation.used:
                    detail = ", ".join(
                        f"{u.deal_id}:{u.ils_covered:.2f} ILS (saved {u.savings:.2f})" for u in allocation.used
                    )
                else:
                    detail = "(no tender deal used)"
                print(f"    -> {allocation.price_after:.2f}  [{detail}]")

    # 4. Pool every (chain combo, tender allocation) candidate; dedup by the
    # actual set of deals used (different routes can reach the same outcome).
    def _dedup_key(entry: tuple[float, tuple[str, frozenset[str]], TenderAllocation]) -> tuple:
        price_after, (_cur_id, applied), allocation = entry
        deal_ids = frozenset(applied) | frozenset(u.deal_id for u in allocation.used)
        return (round(price_after, 6), deal_ids)

    deduped: dict[tuple, tuple[float, tuple[str, frozenset[str]], TenderAllocation]] = {}
    for entry in candidates:
        key = _dedup_key(entry)
        if key not in deduped:
            deduped[key] = entry

    ranked = sorted(deduped.values(), key=lambda e: e[0])[:top_n]

    # 5. Reconstruct a full path for each ranked candidate.
    results: list[list[DealNode]] = []
    for _price_after, chain_state, allocation in ranked:
        chain_path = _reconstruct_chain_path(chain_state, dp, by_id, INIT)
        tender_path = [
            _synthetic_tender_node(tender_by_deal_id[u.deal_id], u)
            for u in sorted(allocation.used, key=lambda u: u.savings, reverse=True)
        ]
        results.append(chain_path + tender_path)

    if verbose:
        print(f"\n=== TOP {len(results)} (of {len(deduped)} distinct outcomes explored) ===")
        for i, (path, (price_after, _cs, _alloc)) in enumerate(zip(results, ranked), 1):
            print(f"  #{i}  final price {price_after:.4f}  " + " -> ".join(f"{n.deal_id}({n.category})" for n in path))

    return results


def find_best_path(
    cart_total: float,
    cart_quantity: int,
    deal_dicts: list[dict[str, Any]],
    user_context: UserContext | None = None,
    unknown_as_yes: bool = True,
    verbose: bool = False,
) -> list[DealNode]:
    """The single cheapest combination — a convenience wrapper over ``find_top_paths(top_n=1)``."""
    return find_top_paths(cart_total, cart_quantity, deal_dicts, user_context, unknown_as_yes, top_n=1, verbose=verbose)[0]


def get_optimal_deal_path(
    file_path: str,
    target_store_id: str,
    cart_total: float,
    cart_quantity: int,
    user_context: UserContext | None = None,
    unknown_as_yes: bool = True,
    top_n: int = 5,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """Public entry point. Reads deals from ``file_path``, filters by store, optimizes."""
    with open(file_path, encoding="utf-8") as f:
        all_deals = json.load(f)

    store_deals = [d for d in all_deals if _deal_matches_store(d, target_store_id)]
    if verbose:
        print(f"Store {target_store_id!r}: {len(store_deals)}/{len(all_deals)} deals in file match")
    return optimize(store_deals, cart_total, cart_quantity, user_context, unknown_as_yes, top_n=top_n, verbose=verbose)


def _deal_matches_store(deal: dict[str, Any], target_store_id: str) -> bool:
    if deal.get("store_id") == target_store_id:
        return True
    return target_store_id in (deal.get("group_member_stores", []) or [])


def _build_result(cart_total: float, cart_quantity: int, path: list[DealNode], rank: int) -> dict[str, Any]:
    per_step = []
    price = cart_total
    for node in path:
        price_out = apply_deal(price, cart_quantity, node)
        # path nodes are guaranteed applicable, but guard against None defensively
        price_out = price if price_out is None else price_out
        per_step.append(
            {
                "deal_id": node.deal_id,
                "price_in": price,
                "price_out": price_out,
                "ils_covered": node.ils_covered,
            }
        )
        price = price_out

    return {
        "rank": rank,
        "path": [node.raw for node in path],
        "starting_price": cart_total,
        "final_price": price,
        "total_savings": cart_total - price,
        "per_step": per_step,
    }


def optimize(
    deal_dicts: list[dict[str, Any]],
    cart_total: float,
    cart_quantity: int,
    user_context: UserContext | None = None,
    unknown_as_yes: bool = True,
    top_n: int = 5,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """Optimize an in-memory list of deals; returns up to ``top_n`` ranked
    results (cheapest first — ``results[0]`` is the single best), each shaped
    like ``{"rank", "path", "starting_price", "final_price", "total_savings",
    "per_step"}``.

    Each ``per_step`` entry includes ``ils_covered`` — for tender deals
    (giftcard_discount/payment_discount/cashback) this is how much of the
    bill was routed through that specific instrument; ``None`` for
    price-level deals (store_sale/member_discount/coupon), which discount the
    whole running total rather than a specific slice of it.
    """
    paths = find_top_paths(cart_total, cart_quantity, deal_dicts, user_context, unknown_as_yes, top_n=top_n, verbose=verbose)

    results = [_build_result(cart_total, cart_quantity, path, rank) for rank, path in enumerate(paths, 1)]

    if verbose:
        print(f"\n=== RESULTS ({len(results)} ranked option(s)) ===")
        for r in results:
            print(f"\n  --- #{r['rank']}  final price {r['final_price']:.4f}  (saved {r['total_savings']:.4f}) ---")
            for step in r["per_step"]:
                covered = f"  [covers {step['ils_covered']:.2f} ILS of the bill]" if step["ils_covered"] is not None else ""
                print(f"    {step['deal_id']:<28} {step['price_in']:>10.4f} -> {step['price_out']:<10.4f}{covered}")

    return results
