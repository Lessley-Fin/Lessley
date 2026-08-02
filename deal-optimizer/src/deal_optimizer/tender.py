"""Optimal payment-instrument ("tender") allocation.

Store-sale/member/coupon deals are pure price reductions — chaining them
sequentially against a shrinking running total is correct, because they all
discount the SAME final bill regardless of how it's eventually paid.

Gift-card loads, card-brand payment discounts, and cashback are different:
each only discounts (or rebates) the specific slice of money actually routed
through that instrument — cashback is earned on whatever was charged to the
card that earns it, same as a payment_discount. You cannot pay the same 400
ILS with two different cards, so chaining these the same way as price-
reduction deals double-counts (e.g. a capped 30%-off card would still
"discount" money that a different card already covered). This module treats
them instead as splitting one bill across instruments:

  * "voucher" deals (fixed face value, e.g. buy a 200 ILS gift card for 160)
    are all-or-nothing lumps.
  * "rate" deals (X% off, optionally capped via ``max_discount_amount``) are
    continuous — any amount can be routed through them, up to their cap.

Given a fixed set of voucher units to redeem, the optimal split of the
remaining bill across the rate deals is the classic fractional-knapsack
greedy: fill the highest-rate option first (up to its cap), then the next,
and so on — optimal because each rate option's marginal saving per ILS is
constant up to its cap, then zero. We brute-force every combination of
voucher units and rate-deal subsets (bounded, always small in practice —
a handful of deals per store) and greedily fill the rest for each, so the
result is the true global optimum, not a single-instrument approximation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations, product
from typing import Any, Callable

_VOUCHER_CONDS = ("exact_spend", "voucher_value")


@dataclass(frozen=True)
class _Voucher:
    deal_id: str
    size: float  # face value covered per unit
    savings: float  # savings per unit
    max_units: int  # how many times it can be redeemed in this transaction


@dataclass(frozen=True)
class _RateOption:
    deal_id: str
    rate: float  # savings per ILS routed through it
    cap_ils: float | None  # max ILS it can cover (None = uncapped)


@dataclass
class TenderUsage:
    deal_id: str
    ils_covered: float
    savings: float


@dataclass
class TenderAllocation:
    price_after: float
    total_savings: float
    used: list[TenderUsage] = field(default_factory=list)


def _condition_met(deal: dict[str, Any], price: float, quantity: int) -> bool:
    """Same condition semantics as ``transform.apply_deal``, checked against the
    price entering the tender phase (vouchers are re-checked per-unit below)."""
    cond = (deal.get("discount_logic", {}) or {}).get("condition", {}) or {}
    cond_type = cond.get("type")
    cval = cond.get("value", 0) or 0
    if cond_type == "min_spend" and price < cval:
        return False
    if cond_type == "min_quantity" and quantity < cval:
        return False
    if cond_type in _VOUCHER_CONDS and price < cval:
        return False
    return True


def _classify(deal: dict[str, Any]) -> _Voucher | _RateOption | None:
    dl = deal.get("discount_logic", {}) or {}
    cond = dl.get("condition", {}) or {}
    rew = dl.get("reward", {}) or {}
    cond_type = cond.get("type")
    cval = cond.get("value", 0) or 0
    rval = rew.get("value", 0) or 0
    rt = rew.get("type")

    limits = (deal.get("constraints", {}) or {}).get("limits", {}) or {}
    # A null max_uses_per_transaction means the source text never stated a
    # per-transaction cap (the LLM enrichment prompt is instructed to emit
    # null rather than guess) — it is NOT a claim of "exactly one". Fall back
    # to max_uses_per_month as an upper bound instead: a single transaction
    # can't span two calendar months, so a deal usable up to N times/month
    # can't be used more than N times in one transaction either. Only default
    # to 1 when neither limit is stated at all.
    max_units = limits.get("max_uses_per_transaction")
    if max_units is None:
        max_units = limits.get("max_uses_per_month")
    if max_units is None:
        max_units = 1

    if rt == "fixed_total_amount" and cond_type in _VOUCHER_CONDS:
        return _Voucher(deal["id"], size=cval, savings=cval - rval, max_units=max_units)
    if rt == "percentage_off":
        cap_savings = rew.get("max_discount_amount")
        # A capped rate deal usable N times (max_uses_per_transaction) covers N times
        # the per-unit cap — e.g. two "up to 200 ILS at 13%" vouchers cover 400 ILS
        # combined. An uncapped rate deal stays uncapped regardless of N: one unit
        # already covers the entire remaining bill, so extra units add nothing —
        # unlike the old sequential-chain model, redundant uses can't compound.
        cap_ils = (cap_savings / rval * max_units) if (cap_savings is not None and rval > 0) else None
        return _RateOption(deal["id"], rate=rval, cap_ils=cap_ils)
    return None  # unsupported reward shape for the tender layer — excluded, not crashed on


def _greedy_fill(remaining: float, rate_options: list[_RateOption]) -> tuple[float, list[TenderUsage]]:
    """Fractional-knapsack fill: highest rate first, each up to its own cap."""
    used: list[TenderUsage] = []
    total_savings = 0.0
    for opt in sorted(rate_options, key=lambda o: o.rate, reverse=True):
        if remaining <= 0:
            break
        amount = remaining if opt.cap_ils is None else min(remaining, opt.cap_ils)
        if amount <= 0:
            continue
        savings = amount * opt.rate
        used.append(TenderUsage(opt.deal_id, ils_covered=amount, savings=savings))
        total_savings += savings
        remaining -= amount
    return total_savings, used


def _enumerate_allocations(
    price: float,
    quantity: int,
    deals: list[dict[str, Any]],
    conflicts: Callable[[str, str], bool],
) -> list[TenderAllocation]:
    """Every distinct feasible way to split ``price`` across ``deals``, ranked
    best-savings-first (always includes the "use nothing" option).

    ``conflicts(id_a, id_b)`` must return True when the two deals cannot be
    combined (e.g. explicit ``stackable_with_giftcards: "no"``). Feasible
    subsets respecting ``conflicts`` are brute-forced alongside voucher unit
    counts — tractable because a store's deal count is always small. Many
    subsets collapse to the same actual outcome (an "eligible but never
    filled" rate option doesn't change what was used), so results are
    deduplicated by the actual (deal_id, ils_covered) combination reached.
    """
    candidates = [d for d in deals if _condition_met(d, price, quantity)]
    vouchers: list[_Voucher] = []
    rate_options: list[_RateOption] = []
    for d in candidates:
        c = _classify(d)
        if isinstance(c, _Voucher):
            vouchers.append(c)
        elif isinstance(c, _RateOption):
            rate_options.append(c)

    seen: dict[tuple, TenderAllocation] = {}

    # Every subset of rate options (small N in practice) — needed because two
    # rate deals might conflict with each other even though each is fine alone.
    for r in range(len(rate_options) + 1):
        for rate_subset in combinations(rate_options, r):
            if _has_conflict([o.deal_id for o in rate_subset], conflicts):
                continue
            # Every feasible unit-count combination of vouchers compatible with this subset.
            usable_vouchers = [
                v for v in vouchers if not any(conflicts(v.deal_id, o.deal_id) for o in rate_subset)
            ]
            for counts in _voucher_unit_counts(usable_vouchers):
                chosen_vouchers = [(v, n) for v, n in zip(usable_vouchers, counts) if n > 0]
                if _has_conflict([v.deal_id for v, _ in chosen_vouchers], conflicts):
                    continue
                total_voucher_size = sum(v.size * n for v, n in chosen_vouchers)
                if total_voucher_size > price:
                    continue  # can't redeem more voucher face value than the bill itself
                voucher_savings = sum(v.savings * n for v, n in chosen_vouchers)
                remaining = price - total_voucher_size
                continuous_savings, continuous_used = _greedy_fill(remaining, list(rate_subset))

                used = [TenderUsage(v.deal_id, ils_covered=v.size * n, savings=v.savings * n) for v, n in chosen_vouchers]
                used.extend(continuous_used)
                total_savings = voucher_savings + continuous_savings

                key = tuple(sorted((u.deal_id, round(u.ils_covered, 6)) for u in used))
                if key not in seen or total_savings > seen[key].total_savings:
                    seen[key] = TenderAllocation(price_after=price - total_savings, total_savings=total_savings, used=used)

    return sorted(seen.values(), key=lambda a: a.total_savings, reverse=True)


def allocate_tender(
    price: float,
    quantity: int,
    deals: list[dict[str, Any]],
    conflicts: Callable[[str, str], bool],
) -> TenderAllocation:
    """The single savings-maximizing way to split ``price`` across ``deals``."""
    return _enumerate_allocations(price, quantity, deals, conflicts)[0]


def allocate_tender_top_k(
    price: float,
    quantity: int,
    deals: list[dict[str, Any]],
    conflicts: Callable[[str, str], bool],
    k: int = 5,
) -> list[TenderAllocation]:
    """Up to ``k`` distinct ways to split ``price`` across ``deals``, ranked
    best-savings-first — for presenting ranked alternatives, not just the winner."""
    return _enumerate_allocations(price, quantity, deals, conflicts)[:k]


def _has_conflict(ids: list[str], conflicts: Callable[[str, str], bool]) -> bool:
    return any(conflicts(a, b) for i, a in enumerate(ids) for b in ids[i + 1 :])


def _voucher_unit_counts(vouchers: list[_Voucher]):
    ranges = [range(v.max_units + 1) for v in vouchers]
    if not ranges:
        yield ()
        return
    yield from product(*ranges)
