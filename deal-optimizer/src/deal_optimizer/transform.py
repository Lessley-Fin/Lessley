"""Vertex math — the price transform applied at each deal (Part 3d).

Both plan bug fixes (Part 3a) are baked in here:
  * BUG 1 — percentage values are stored as ratios already (0.13 == 13%), so we
    multiply by ``rval`` directly, NOT ``rval / 100``.
  * BUG 2 — min_quantity uses strict ``<`` (quantity 1 qualifies for min_quantity 1).
"""

from __future__ import annotations

from .graph import DealNode

_VOUCHER_CONDS = ("exact_spend", "voucher_value")


def apply_deal(price_in: float, quantity: int, deal: DealNode) -> float | None:
    """Return ``price_out``, or ``None`` if this deal cannot be applied to ``price_in``."""
    dl = deal.discount_logic
    cond = dl.get("condition", {}) or {}
    rew = dl.get("reward", {}) or {}
    cond_type = cond.get("type")
    cval = cond.get("value", 0) or 0
    rval = rew.get("value", 0) or 0

    # Validate condition against the *incoming* price.
    if cond_type == "min_spend" and price_in < cval:
        return None
    if cond_type == "min_quantity" and quantity < cval:  # BUG 2 fix: strict <
        return None
    if cond_type in _VOUCHER_CONDS and price_in < cval:
        return None

    # Compute savings.
    rt = rew.get("type")
    if rt == "fixed_discount_amount":
        savings = rval
    elif rt == "fixed_total_amount":
        savings = (cval - rval) if cond_type in _VOUCHER_CONDS else 0
    elif rt == "percentage_off":
        tiers = rew.get("tiers")
        if tiers:
            # A tiered loadable card: the rate steps down as the load grows, so
            # savings accrue rung by rung against the cumulative thresholds
            # (25% on the first 600, then 15% up to 1500). Walking the ladder
            # bounds savings on its own — a bill past the top rung simply stops
            # accruing — which is why an uncapped flat rate overstated it.
            savings = sum(
                max(0.0, min(price_in, t["to_amount"]) - t["from_amount"]) * t["percentage_off"]
                for t in tiers
            )
        else:
            base = cval if cond_type in _VOUCHER_CONDS else price_in
            savings = base * rval  # BUG 1 fix: rval is already a ratio
    else:
        savings = 0

    # Optional savings ceiling, e.g. a gift card loadable up to 1000 ILS at 30%
    # off is expressed as {"type": "percentage_off", "value": 0.30,
    # "max_discount_amount": 300} — equivalent to capping the base at 1000
    # ILS, but works uniformly across every reward type.
    max_discount = rew.get("max_discount_amount")
    if max_discount is not None:
        savings = min(savings, max_discount)

    savings = min(savings, price_in)  # never refund more than the running price
    return max(0.0, price_in - savings)
