"""Discount mechanics deduction for Israeli deal sources.

Ported and cleaned from legacy ``hot_extract_format.py :: deduce_discount_mechanics``
and ``mastercard_scraper.py :: parse_discount_logic``.

The functions in this module operate on **raw data** (dicts / text fields
straight from the scraper payload).  They are intentionally *stateless*
and can be called from either the scraper layer (to enrich ``raw_payload``)
or the normalization layer.

The return type is a plain dict so it can be stored inside ``raw_payload``
without any model coupling.
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Compiled regexes — reusable across callers
# ---------------------------------------------------------------------------

# "שווי X ב Y" voucher pattern (Hebrew: "worth X for Y")
_SHOVI_RE = re.compile(r"שווי.*?(\d[,0-9]*).*?ב-?\s*(\d[,0-9]*)")

# Spend & Save: "₪50 הנחה ברכישת ₪250" or similar
_SPEND_SAVE_RE = re.compile(
    r"(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?.*?"
    r"(?:ברכישת|בקניית|מעל|במינימום).*?"
    r"(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?"
)

# Percentage
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)%")

# Max discount cap: "עד ₪200"
_MAX_DISCOUNT_RE = re.compile(r"עד\s*(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?")

# Stackability
_NOT_STACKABLE_RE = re.compile(r"לא כולל כפל|ללא כפל|אין כפל")
_STACKABLE_RE = re.compile(r"כולל כפל")

# Redeem channels
_ONLINE_RE = re.compile(r"באתר|אונליין|באתר הסחר|online")
_APP_RE = re.compile(r"באפליקציית|באפליקציה|אפליקציה")
_PHYSICAL_RE = re.compile(r"בחנויות|בסניפי|קופה|בסניפים|בקופה|איסוף עצמי")

# Coupon code
_COUPON_RE = re.compile(r"קוד קופון[א-ת\s]*:?\s*([a-zA-Z0-9]{4,})")

# ₪ amount in title (for benefit_type 1300)
_TITLE_SHEKEL_RE = re.compile(r"(\d[,0-9]*)\s*₪")


# ---------------------------------------------------------------------------
# HOT-specific discount deduction
# ---------------------------------------------------------------------------

def deduce_hot_discount_mechanics(
    main: dict[str, Any],
    combined_text: str = "",
) -> dict[str, Any]:
    """Deduce discount condition / reward / constraints from a HOT benefit record.

    Implements the 6-level priority cascade from legacy ``hot_extract_format.py``:

    1. benefit_type 1300 + before/after prices  → exact_spend + fixed_total_amount
    2. benefit_type 1300 + title ₪ + percentage  → exact_spend + fixed_total_amount
    3. "שווי X ב Y" pattern                     → exact_spend + fixed_total_amount
    4. Percentage in text                        → percentage_off
    5. Spend & Save                              → min_spend + fixed_discount_amount
    6. Price-based fallback                      → exact_spend / percentage_off / unknown

    Parameters
    ----------
    main:
        The ``data.main`` dict from a HOT detail response, or the benefit
        list record (both share the same field names).
    combined_text:
        Pre-joined text from all relevant fields (title + description +
        free_text + terms + value).  If empty, the function builds it
        from *main*.

    Returns
    -------
    dict with keys ``condition``, ``reward``, ``constraints``.
    """
    title = str(main.get("title", "") or "")
    desc = str(main.get("description", "") or "")
    free_text = str(main.get("free_text", "") or "")
    cashback_desc = str(main.get("cashback_description", "") or "")
    value_field = str(main.get("value", "") or "")
    value_num_field = str(main.get("valueNum", "") or "")

    if not combined_text:
        combined_text = (
            f"{title} {desc} {free_text} {cashback_desc} "
            f"{value_field} {value_num_field}"
        )

    price_before = _to_float(main.get("price_before_discount")) or 0.0
    price_after = _to_float(main.get("price_after_discount")) or 0.0
    benefit_type = str(main.get("benefit_type") or main.get("type") or "")

    # Defaults
    condition: dict[str, Any] = {"type": "min_quantity", "value": 1}
    reward: dict[str, Any] = {"type": "percentage_off", "value": 0.0}
    constraints: dict[str, Any] = {}

    # --- Priority 1: Voucher (1300) with before/after prices ---
    if benefit_type == "1300" and price_before > 0 and price_after > 0:
        condition = {"type": "exact_spend", "value": price_before}
        reward = {"type": "fixed_total_amount", "value": price_after}

    # --- Priority 2: Voucher (1300) with title ₪ + percentage ---
    elif benefit_type == "1300":
        title_amount = _TITLE_SHEKEL_RE.search(title)
        search_fields = f"{value_field} {value_num_field} {combined_text}"
        pct = _PERCENT_RE.search(search_fields)
        if title_amount and pct:
            total_val = int(title_amount.group(1).replace(",", ""))
            discount_pct = float(pct.group(1)) / 100.0
            condition = {"type": "exact_spend", "value": total_val}
            reward = {
                "type": "fixed_total_amount",
                "value": round(total_val * (1 - discount_pct), 2),
            }

    # --- Priority 3: "שווי X ב Y" pattern ---
    elif (match := _SHOVI_RE.search(combined_text)):
        val1 = int(match.group(1).replace(",", ""))
        val2 = int(match.group(2).replace(",", ""))
        condition = {"type": "exact_spend", "value": val1}
        reward = {"type": "fixed_total_amount", "value": val2}

    # --- Priority 4: Percentage ---
    elif "%" in combined_text:
        search_order = f"{value_field} {value_num_field} {title} {combined_text}"
        pct = _PERCENT_RE.search(search_order)
        if pct:
            reward = {"type": "percentage_off", "value": float(pct.group(1)) / 100.0}
        elif price_before > 0:
            reward = {
                "type": "percentage_off",
                "value": round(1 - (price_after / price_before), 2),
            }

    # --- Priority 5: Spend & Save ---
    elif (ss := _SPEND_SAVE_RE.search(combined_text)):
        reward_raw = int(ss.group(1).replace(",", ""))
        condition_raw = int(ss.group(2).replace(",", ""))
        condition = {"type": "min_spend", "value": condition_raw}
        reward = {"type": "fixed_discount_amount", "value": reward_raw}

        max_disc = _MAX_DISCOUNT_RE.search(combined_text)
        if max_disc:
            constraints["max_discount_amount"] = int(
                max_disc.group(1).replace(",", "")
            )

    # --- Priority 6: Price fallback ---
    else:
        if price_before > 0 and price_after > 0:
            condition = {"type": "exact_spend", "value": price_before}
            reward = {"type": "fixed_total_amount", "value": price_after}
        elif price_before > 0 and price_after == 0:
            reward = {"type": "percentage_off", "value": 1.0}

    return {
        "condition": condition,
        "reward": reward,
        "constraints": constraints,
    }


# ---------------------------------------------------------------------------
# Mastercard-specific discount deduction
# ---------------------------------------------------------------------------

def deduce_mastercard_discount(
    clean_text: str,
    title: str,
) -> dict[str, Any] | None:
    """Deduce discount logic from Mastercard DXP block text.

    Returns ``None`` if no recognisable discount pattern is found (caller
    should skip the block).

    Priority:
    1. Spend & Save (₪X הנחה ברכישת ₪Y)
    2. Percentage (X%)
    """
    # Spend & Save
    ss = _SPEND_SAVE_RE.search(clean_text)
    if ss:
        reward_raw = int(ss.group(1).replace(",", ""))
        condition_raw = int(ss.group(2).replace(",", ""))
        result: dict[str, Any] = {
            "type": "spend_and_save",
            "condition": {"type": "min_spend", "value": condition_raw},
            "reward": {"type": "fixed_discount_amount", "value": reward_raw},
            "constraints": {},
            "matched_text": ss.group(0),
        }
        max_disc = _MAX_DISCOUNT_RE.search(clean_text)
        if max_disc:
            result["constraints"]["max_discount_amount"] = int(
                max_disc.group(1).replace(",", "")
            )
        return result

    # Percentage
    pct = _PERCENT_RE.search(title) or _PERCENT_RE.search(clean_text)
    if pct:
        return {
            "type": "percentage",
            "condition": {"type": "min_quantity", "value": 1},
            "reward": {"type": "percentage_off", "value": float(pct.group(1)) / 100.0},
            "constraints": {},
            "percent": int(pct.group(1)),
            "matched_text": pct.group(0),
        }

    return None


# ---------------------------------------------------------------------------
# Shared extraction helpers
# ---------------------------------------------------------------------------

def check_stackable(text: str) -> bool:
    """Determine whether a deal is stackable with other promotions."""
    if _NOT_STACKABLE_RE.search(text):
        return False
    if _STACKABLE_RE.search(text):
        return True
    return False  # default: unknown / assume not stackable


def extract_redeem_channels(text: str) -> list[str]:
    """Identify where the deal can be redeemed."""
    channels: list[str] = []
    if _ONLINE_RE.search(text):
        channels.append("online")
    if _APP_RE.search(text):
        channels.append("mobile_app")
    if _PHYSICAL_RE.search(text):
        channels.append("physical_store")
    return channels


def extract_coupon(text: str) -> str | None:
    """Extract a coupon code if present."""
    m = _COUPON_RE.search(text)
    return m.group(1) if m else None


def classify_hot_benefit_type(record: dict[str, Any]) -> str:
    """Classify a HOT benefit into a semantic type.

    Heuristic based on legacy ``_normalize_benefit_type``:
    - cashback / voucher / coupon / discount_at_billing
    """
    text = " ".join(
        str(v or "")
        for v in (
            record.get("small_text"),
            record.get("value"),
            record.get("title"),
            record.get("description"),
        )
    ).lower()
    if any(tok in text for tok in ("cashback", "money back", "refund")):
        return "cashback"
    if any(tok in text for tok in ("voucher", "gift card", "giftcard")):
        return "voucher"
    if any(tok in text for tok in ("coupon", "promo code", "code")):
        return "coupon"
    return "discount_at_billing"


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except (ValueError, TypeError):
        return None
