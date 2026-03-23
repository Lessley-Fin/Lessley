"""Shared utilities for brand / store name cleaning across scrapers.

Extracted from legacy ``import_businesses.py`` and ``hot_scraper.py``.
These are *scraper-layer* helpers — they operate on raw strings before
the normalization pipeline touches the data.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse


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
