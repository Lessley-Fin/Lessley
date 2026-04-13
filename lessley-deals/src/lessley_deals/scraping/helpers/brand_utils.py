"""Shared utilities for brand / store name cleaning across scrapers.

Extracted from legacy ``import_businesses.py`` and ``hot_scraper.py``.
These are *scraper-layer* helpers — they operate on raw strings before
the normalization pipeline touches the data.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_DEFAULT_GROUPS_PATH = (
    Path(__file__).parent.parent / "config" / "hot_store_groups.json"
)


# ---------------------------------------------------------------------------
# Brand name cleaning
# ---------------------------------------------------------------------------

def clean_store_name(name: str) -> str:
    """Remove HOT gift-card noise from a resolved store name.

    Strips the gift-card suffix that HOT appends to group brand names and
    removes any leading ``תו קניה`` prefix that may have survived
    prefix-stripping.  Applied **after** :func:`classify_group_deal` so the
    group config lookup still works on the original brand name.

    The deal title is intentionally left unchanged — these words stay in the
    title / deal description.

    Examples::

        "קבוצת גולף - תווים"  ->  "קבוצת גולף"
        "קבוצת בריל - תווים"  ->  "קבוצת בריל"
        "תווים - פוד אפיל"    ->  "פוד אפיל"
        "sabon"               ->  "sabon"
        "תו קניה sabon"       ->  "sabon"
    """
    name = str(name or "").strip()
    if not name:
        return ""
    # Strip "- תווים" suffix  (e.g. "קבוצת גולף - תווים" → "קבוצת גולף")
    name = re.sub(r"\s*-\s*תווים\s*$", "", name).strip(" -_")
    # Strip "תווים -" prefix  (e.g. "תווים - פוד אפיל" → "פוד אפיל")
    name = re.sub(r"^תווים\s*-\s*", "", name).strip()
    # Strip leading "תו קניה" prefix (safety net — normally already stripped)
    name = re.sub(r"^תו\s*קניה\s*", "", name).strip()
    return name


def clean_brand(raw_brand: str) -> str:
    """Strip HOT-internal noise from a brand name.

    HOT appends numeric suffixes (``_2``, ``_3``, ...) to disambiguate
    duplicate entries internally.  Remove them so downstream matching
    sees a clean name.

    Also collapses whitespace and trims leading/trailing ``-`` or ``_``.

    Examples::

        "ShareSpa - שר ספא הרצליה_2"  ->  "ShareSpa - שר ספא הרצליה"
        "קפה עלית_1"                   ->  "קפה עלית"
    """
    brand = str(raw_brand or "").strip()
    if not brand:
        return ""
    # Legacy: re.sub(r"_[0-9]+$", "", brand) then whitespace normalize
    brand = re.sub(r"_\d+$", "", brand)
    brand = re.sub(r"\s+", " ", brand).strip(" -_")
    return brand


# ---------------------------------------------------------------------------
# Generic brand filtering
# ---------------------------------------------------------------------------

# Patterns that indicate a "club-level" name rather than an actual store.
_HOT_GENERIC_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"מועדון\s*הוט", re.IGNORECASE),
    re.compile(r"הוט\s*מועדון\s*צרכנות", re.IGNORECASE),
    re.compile(r"^\s*hot\s*(club)?\s*$", re.IGNORECASE),
)

_BEHATSDAA_GENERIC_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*בהצדעה\s*$", re.IGNORECASE),
    re.compile(r"^\s*behatsdaa\s*$", re.IGNORECASE),
)


def is_generic_hot_brand(brand: str) -> bool:
    """Return *True* if *brand* is a HOT club-level name, not a real store."""
    if not brand:
        return True
    return any(p.search(brand) for p in _HOT_GENERIC_PATTERNS)


def is_generic_behatsdaa_brand(brand: str) -> bool:
    """Return *True* if *brand* is the Behatsdaa club name itself."""
    if not brand:
        return True
    return any(p.search(brand) for p in _BEHATSDAA_GENERIC_PATTERNS)


# ---------------------------------------------------------------------------
# Website / domain extraction
# ---------------------------------------------------------------------------

def normalize_website(raw_url: str | None) -> str | None:
    """Extract the bare domain from a raw URL string.

    Adds ``https://`` if no scheme, strips ``www.`` prefix, returns just
    the hostname.  Returns ``None`` on empty / unparseable input.

    Examples::

        "www.sharespa.co.il"     ->  "sharespa.co.il"
        "https://shop.co.il/foo" ->  "shop.co.il"
        ""                       ->  None
    """
    url = str(raw_url or "").strip().lower().replace(" ", "")
    if not url:
        return None
    if not re.match(r"^[a-z][a-z0-9+\-.]*://", url):
        url = f"https://{url}"
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    host = parsed.netloc or parsed.path
    host = host.split("@")[-1].split(":")[0].strip(".")
    if host.startswith("www."):
        host = host[4:]
    return host or None


# ---------------------------------------------------------------------------
# Slug generation (for seed / matching)
# ---------------------------------------------------------------------------

def to_slug(value: str) -> str:
    """Generate a URL-friendly slug from a brand name.

    Strips ``_N`` suffixes, lowercases, replaces non-word characters
    with hyphens, and collapses repeated hyphens.
    """
    text = clean_brand(value).lower()
    text = re.sub(r"[^\w\s-]", " ", text, flags=re.UNICODE)
    text = re.sub(r"[_\s]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text


# ---------------------------------------------------------------------------
# Store-group resolution (HOT)
# ---------------------------------------------------------------------------

_groups_cache: dict[str, dict[str, dict]] = {}


def load_hot_store_groups(
    path: Path | None = None,
) -> dict[str, dict]:
    """Load the HOT store-groups config from JSON, cached after first load.

    The config maps a *group brand name* (as returned by ``clean_brand``)
    to a dict with:
    - ``title_prefix`` – the string to strip from the deal title to obtain
      the real sub-store name (e.g. ``"תו קניה"`` → strips leading
      ``"תו קניה "`` from the title).
    - ``stores`` – optional list of known sub-store names (for docs/debug).

    Falls back to an empty dict and logs a warning on any error.
    """
    target = path or _DEFAULT_GROUPS_PATH
    cache_key = str(target)
    if cache_key in _groups_cache:
        return _groups_cache[cache_key]
    try:
        with target.open(encoding="utf-8") as f:
            data = json.load(f)
        # Strip comment keys (keys starting with "_")
        result: dict[str, dict] = {k: v for k, v in data.items() if not k.startswith("_")}
    except FileNotFoundError:
        logger.warning("hot_store_groups config not found at %s", target)
        result = {}
    except Exception:
        logger.exception("Failed to load hot_store_groups from %s", target)
        result = {}
    _groups_cache[cache_key] = result
    return result


def classify_group_deal(
    brand: str,
    title: str,
    groups: dict[str, dict] | None = None,
) -> tuple[str, bool, list[str]]:
    """Classify a HOT group brand deal as store-specific or group-wide.

    When ``brand`` matches a known store-group (case-insensitive), the
    function strips each configured prefix from *title* (trying each in
    order) to derive the candidate sub-store name.  It then checks whether
    that candidate appears in the group's ``stores`` whitelist:

    - **Store-specific deal** — the resolved name matches a known sub-store.
      The real sub-store name is returned and ``is_group_wide`` is ``False``.
    - **Group-wide gift card** — the resolved name does *not* match any
      sub-store (e.g. the gift card covers the whole group).
      The original group brand is returned, ``is_group_wide`` is ``True``,
      and ``group_member_stores`` lists every member store.

    When ``brand`` is *not* a known group the deal is returned unchanged
    as a non-group deal.

    Args:
        brand: Cleaned brand name from the HOT API (``item_brand`` field).
        title: Deal title string from the HOT API.
        groups: Override the groups dict (mainly for testing).  When
            ``None`` the bundled config is loaded via
            :func:`load_hot_store_groups`.

    Returns:
        ``(resolved_store_name, is_group_wide, group_member_stores)``

    Examples::

        classify_group_deal("קבוצת גולף - תווים", "תו קניה sabon")
        # -> ("sabon", False, [])

        classify_group_deal("קבוצת גולף - תווים", "תו קניה קבוצת גולף - תווים")
        # -> ("קבוצת גולף - תווים", True, ["kitan", "sabon", ...])

        classify_group_deal("AHAVA", "הנחה בAHAVA")  # not a group
        # -> ("AHAVA", False, [])
    """
    if groups is None:
        groups = load_hot_store_groups()

    # Case-insensitive group lookup
    brand_lower = brand.strip().lower()
    group_cfg: dict | None = None
    matched_key: str = brand
    for key, cfg in groups.items():
        if key.strip().lower() == brand_lower:
            group_cfg = cfg
            matched_key = key
            break

    if group_cfg is None:
        # Not a group brand — return as-is
        return brand, False, []

    cfg_found: dict[str, Any] = cast("dict[str, Any]", group_cfg)

    # Support both legacy title_prefix (str) and title_prefixes (list[str]).
    raw_prefixes = cfg_found.get("title_prefixes") or cfg_found.get("title_prefix")
    prefixes: list[str]
    if isinstance(raw_prefixes, list):
        prefixes = [str(p).strip() for p in raw_prefixes if p]
    elif raw_prefixes:
        prefixes = [str(raw_prefixes).strip()]
    else:
        prefixes = []

    raw_stores = cfg_found.get("stores")
    member_stores: list[str] = list(raw_stores) if isinstance(raw_stores, list) else []

    if not prefixes:
        # Group with no prefix config — treat as group-wide
        return brand, True, member_stores

    # Try each prefix in order; use the first one that matches the start of the title.
    title_stripped = title.strip()
    candidate: str = ""
    matched_prefix: bool = False

    for prefix in prefixes:
        if not prefix:
            continue
        pattern = re.compile(r"^\s*" + re.escape(prefix) + r"\s*", re.IGNORECASE)
        result, n_subs = pattern.subn("", title_stripped)
        if n_subs > 0:
            candidate = result.strip()
            matched_prefix = True
            logger.debug(
                "classify_group_deal: prefix %r matched title %r -> candidate %r",
                prefix, title, candidate,
            )
            break

    if not matched_prefix:
        # No prefix matched the start of the title — check if any known
        # member store name appears in the title before falling back to group-wide.
        title_lower = title.strip().lower()
        for store in member_stores:
            store_l = store.strip().lower()
            if store_l in title_lower:
                logger.debug(
                    "classify_group_deal: no prefix but title %r contains member store %r",
                    title, store,
                )
                return store, False, []
        logger.debug(
            "classify_group_deal: no prefix matched title %r (tried: %s) — group-wide",
            title, prefixes,
        )
        return matched_key, True, member_stores

    if not candidate:
        # Prefix found but nothing remained after stripping — group-wide
        logger.debug(
            "classify_group_deal: prefix consumed entire title %r — group-wide",
            title,
        )
        return matched_key, True, member_stores

    # Check if the candidate matches a known sub-store (case-insensitive).
    # Also accepts a prefix match for cases where the title has trailing content
    # after the store name (e.g. "תו קניה sabon 200 ₪" → candidate "sabon 200 ₪"
    # should still resolve to canonical "sabon").
    candidate_lower = candidate.lower()
    for store in member_stores:
        store_l = store.strip().lower()
        if candidate_lower == store_l or store_l in candidate_lower:
            logger.debug(
                "classify_group_deal: %r -> store-specific %r (from title: %r)",
                brand, store, title,
            )
            # Return the canonical store name from the whitelist, not the raw
            # candidate, so the case and trailing text are normalised.
            return store, False, []

    # If the remaining text starts with the group name itself, it is still a
    # group-wide gift card (e.g. "תו קניה קבוצת גולף - תווים" → candidate
    # "קבוצת גולף - תווים" starts with "קבוצת גולף").
    group_lower = matched_key.strip().lower()
    if candidate_lower.startswith(group_lower):
        logger.debug(
            "classify_group_deal: %r — candidate %r starts with group name — group-wide",
            brand, candidate,
        )
        return matched_key, True, member_stores

    # Candidate exists but didn't match any known sub-store or group self-reference.
    # If the group has a stores whitelist, treat as group-wide to avoid creating
    # phantom stores (e.g. "DREAM CARD" from "תו קניה DREAM CARD" in Fox group).
    if member_stores:
        logger.debug(
            "classify_group_deal: %r -> unrecognised candidate %r not in stores whitelist — group-wide",
            brand, candidate,
        )
        return matched_key, True, member_stores

    logger.debug(
        "classify_group_deal: %r -> unrecognised sub-store %r (no whitelist) — treating as specific",
        brand, candidate,
    )
    return candidate, False, []


def resolve_group_store(
    brand: str,
    title: str,
    groups: dict[str, dict] | None = None,
) -> str:
    """Resolve a HOT group brand name to the specific sub-store name.

    Thin wrapper around :func:`classify_group_deal` kept for backward
    compatibility.  Prefer :func:`classify_group_deal` in new code when
    you also need to know whether the deal is group-wide.

    Returns the resolved store name.  For group-wide deals (where no
    specific sub-store could be identified) this returns the original
    *brand* unchanged.

    Examples::

        resolve_group_store("קבוצת פוקס - תווים", "תו קניה FOOT LOCKER")
        # -> "FOOT LOCKER"

        resolve_group_store("AHAVA", "הנחה בAHAVA")  # unknown group
        # -> "AHAVA"
    """
    store_name, _is_group_wide, _members = classify_group_deal(brand, title, groups)
    return store_name
