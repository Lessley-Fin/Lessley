"""Canonical MCC category vocabulary.

Stores carry ``metadata.mcc_codes`` as *category names* (``GROCERIES``,
``RESTAURANT``, …), not the 4-digit ISO 18245 numbers.  The 46 names below are
the closed set — anything outside it is not a valid value for a store.

``mcc_categories.json`` next to this module is the numeric-MCC → category
mapping (5952 codes) kept so older records that stored raw 4-digit codes can be
read back as categories.  It is generated from ``main/resources/mccs.json``;
regenerate it there if the mapping ever changes.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

_CATEGORY_MAP_PATH = Path(__file__).with_name("mcc_categories.json")

#: The closed set of category names a store may be tagged with, in the order
#: the LLM prompt lists them.
MCC_CATEGORIES: tuple[str, ...] = (
    "ALCOHOL_&_TOBACCO",
    "BARS",
    "BEAUTY",
    "BOOKS_&_GAMES",
    "BUSINESS_EXPENSES",
    "CAPITAL_MARKET",
    "CAR_&_FUEL",
    "CHARITY",
    "CLOTHES_&_ACCESSORIES",
    "COFFEE_&_SNACKS",
    "COMMUNICATIONS",
    "CULTURE_&_EVENTS",
    "EDUCATION",
    "ELECTRONICS",
    "FEES",
    "FINANCE_OTHER",
    "FLIGHTS",
    "FOOD_&_DRINKS_OTHER",
    "FURNITURE_&_INTERIOR",
    "GARDEN",
    "GIFTS",
    "GROCERIES",
    "HEALTHCARE",
    "HEALTH_&_BEAUTY_OTHER",
    "HOBBIES",
    "HOBBY_&_SPORTS_EQUIPMENT",
    "HOME",
    "HOME_IMPROVEMENTS_OTHER",
    "HOUSEHOLD_&_SERVICES_-_OTHER",
    "INSURANCE_&_FEES",
    "KIDS",
    "LEISURE_OTHER",
    "LOANS",
    "OTHER",
    "PETS",
    "PHARMACY",
    "PUBLIC_TRANSPORT",
    "RENOVATION_&_REPAIRS",
    "RESTAURANT",
    "SAVINGS",
    "SERVICES",
    "SHOPPING_OTHER",
    "SPORTS_&_FITNESS",
    "TRANSPORT_OTHER",
    "UTILITIES",
    "VACATION",
)

CATEGORY_SET: frozenset[str] = frozenset(MCC_CATEGORIES)

#: Category used when nothing better can be determined.
FALLBACK_CATEGORY = "OTHER"

#: At most this many categories per store — the prompt asks for a ranked 1-3.
MAX_CODES_PER_STORE = 3


#: Off-vocabulary spellings the LLM classifier is known to emit, mapped to the
#: canonical name they unambiguously mean.  Keys are compared after
#: :func:`_squash`, so case, spacing and punctuation variants are already
#: covered — only genuine misspellings belong here.
#:
#: ``RESTUARANT`` is a recurring output of the store classifier.  Because
#: :func:`coerce_category` resolves by exact squashed match it was dropped as
#: unresolvable, and stores the model had confidently identified as restaurants
#: fell through to :data:`FALLBACK_CATEGORY` instead.  Deterministic decoding
#: (``temperature=0``, fixed seed) means re-running reproduces the typo exactly,
#: so it has to be absorbed here rather than retried.
SPELLING_ALIASES: dict[str, str] = {
    "RESTUARANT": "RESTAURANT",
}


def _squash(text: str) -> str:
    """Strip everything but letters, digits and ``&`` so spelling variants match."""
    return "".join(ch for ch in text.upper() if ch.isalnum() or ch == "&")


_BY_SQUASHED: dict[str, str] = {_squash(name): name for name in MCC_CATEGORIES}

for _alias, _canonical in SPELLING_ALIASES.items():
    if _canonical not in CATEGORY_SET:
        raise ValueError(f"SPELLING_ALIASES maps {_alias!r} to unknown category {_canonical!r}")
    # setdefault, never assignment: an alias must not be able to shadow a real
    # category name if one is ever added that squashes to the same string.
    _BY_SQUASHED.setdefault(_squash(_alias), _canonical)


@cache
def category_by_numeric_code() -> dict[str, str]:
    """4-digit MCC (zero-padded string) → canonical category name."""
    with _CATEGORY_MAP_PATH.open(encoding="utf-8") as fh:
        raw: dict[str, str] = json.load(fh)
    return {code: category for code, category in raw.items() if category in CATEGORY_SET}


def category_for_numeric_code(code: int | str) -> str | None:
    """Resolve a numeric MCC to its category, or None if it is unknown."""
    text = str(code).strip()
    if not text.isdigit():
        return None
    return category_by_numeric_code().get(text.zfill(4))


def coerce_category(value: Any) -> str | None:
    """Best-effort read of one stored/LLM-supplied value as a category name.

    Accepts a canonical name in any case, a name written with spaces or hyphens
    instead of underscores, a known misspelling from :data:`SPELLING_ALIASES`,
    or a numeric MCC (int or string).  Returns None when the value cannot be
    resolved.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return category_for_numeric_code(value)

    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return category_for_numeric_code(text)

    return _BY_SQUASHED.get(_squash(text))


def normalize_mcc_codes(
    values: Any,
    *,
    max_codes: int = MAX_CODES_PER_STORE,
    fallback: str | None = None,
) -> list[str]:
    """Normalize a store's ``mcc_codes`` into ranked canonical category names.

    Order is preserved (the list is ranked most-specific first), duplicates and
    unresolvable entries are dropped, and the result is truncated to
    ``max_codes``.  Pass ``fallback=FALLBACK_CATEGORY`` to guarantee a non-empty
    result.
    """
    if values is None:
        items: list[Any] = []
    elif isinstance(values, (str, int)):
        items = [values]
    else:
        items = list(values)

    result: list[str] = []
    for item in items:
        category = coerce_category(item)
        if category is not None and category not in result:
            result.append(category)
        if len(result) >= max_codes:
            break

    if not result and fallback is not None:
        return [fallback]
    return result


def unresolvable_codes(values: Any) -> list[Any]:
    """The entries of ``values`` that :func:`coerce_category` cannot resolve."""
    if values is None:
        return []
    items = [values] if isinstance(values, (str, int)) else list(values)
    return [item for item in items if coerce_category(item) is None]
