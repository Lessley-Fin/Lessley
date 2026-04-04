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
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_DEFAULT_GROUPS_PATH = (
    Path(__file__).parent.parent / "config" / "hot_store_groups.json"
)


# ---------------------------------------------------------------------------
# Brand name cleaning
# ---------------------------------------------------------------------------

def clean_brand(raw_brand: str) -> str:
    """Strip HOT-internal noise from a brand name.

    HOT appends numeric suffixes (``_2``, ``_3``, …) to disambiguate
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


def resolve_group_store(
    brand: str,
    title: str,
    groups: dict[str, dict] | None = None,
) -> str:
    """Resolve a HOT group brand name to the specific sub-store name.

    If ``brand`` matches a known group in *groups* (case-insensitive), the
    function strips the configured ``title_prefix`` from *title* (also
    case-insensitive) and returns the remainder as the real store name.

    Returns the original *brand* unchanged when:
    - *brand* is not a known group, or
    - the ``title_prefix`` is not found in *title*, or
    - the resulting store name would be empty.

    Args:
        brand: Cleaned brand name from the HOT API (``item_brand`` field).
        title: Deal title string from the HOT API.
        groups: Override the groups dict (mainly for testing). When ``None``
            the bundled config is loaded via :func:`load_hot_store_groups`.

    Examples::

        resolve_group_store("קבוצת פוקס", "תו קניה FOOT LOCKER")
        # -> "FOOT LOCKER"

        resolve_group_store("AHAVA", "הנחה בAHAVA")  # unknown group
        # -> "AHAVA"
    """
    if groups is None:
        groups = load_hot_store_groups()

    # Case-insensitive group lookup
    brand_lower = brand.strip().lower()
    group_cfg: dict | None = None
    for key, cfg in groups.items():
        if key.strip().lower() == brand_lower:
            group_cfg = cfg
            break

    if group_cfg is None:
        return brand

    prefix: str = group_cfg.get("title_prefix", "").strip()
    if not prefix:
        return brand

    # Strip the prefix (case-insensitive) from the title
    pattern = re.compile(r"^\s*" + re.escape(prefix) + r"\s*", re.IGNORECASE)
    store_name = pattern.sub("", title.strip()).strip()

    if not store_name:
        logger.debug(
            "resolve_group_store: prefix '%s' not found in title '%s'",
            prefix, title,
        )
        return brand

    logger.debug(
        "resolve_group_store: '%s' -> '%s' (from title: '%s')",
        brand, store_name, title,
    )
    return store_name
