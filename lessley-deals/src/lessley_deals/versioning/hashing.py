"""Business identity and content hashing for deals.

Two different hashes are involved, and mixing them up breaks history:

``deal_key`` (*identity*)
    Answers "is this the same offer I saw last week?".  It must stay **stable**
    while the offer's wording, price or terms change — otherwise every edit
    looks like a brand-new deal and the history is worthless.

``content_hash`` (*content*)
    Answers "did anything meaningful change?".  It must change whenever a field
    a user would care about changes, and must **not** change because of
    timestamps, run ids or other pipeline bookkeeping.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

from lessley_deals.domain.models import Deal
from lessley_deals.normalization.hebrew_utils import normalize_hebrew

# Fields whose change constitutes a new *version* of the same deal.
# Deliberately excludes: id, raw_id, scraped_at, resolved_at (pipeline noise).
CONTENT_FIELDS: tuple[str, ...] = (
    "title",
    "deal_description",
    "terms_and_conditions",
    "benefit_url",
    "url",
    "currency",
    "discount_logic",
    "deal_type",
    "constraints",
    "club_id",
    "group_member_store_ids",
)

_WHITESPACE_RE = re.compile(r"\s+")
_TRACKING_PARAMS = ("utm_", "gclid", "fbclid", "mc_cid", "mc_eid", "ref")

# Keys a source might use for "this offer ends on".
_EXPIRY_KEYS: tuple[str, ...] = (
    "valid_until",
    "validUntil",
    "expires_at",
    "expiry_date",
    "expiration_date",
    "end_date",
    "endDate",
    "to_date",
    "date_to",
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_text(value: str | None) -> str:
    """Lowercase, collapse whitespace and Hebrew-normalize so cosmetic edits
    (a double space, a stray niqqud mark) don't look like a real change."""
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", normalize_hebrew(value)).strip().lower()


def _canonical_url(url: str | None) -> str:
    """Strip scheme, ``www.``, tracking params and trailing slashes from a URL.

    Sources rotate tracking parameters on every render; without this, every
    single scrape would look like an update.
    """
    if not url:
        return ""
    parts = urlsplit(url.strip())
    host = (parts.netloc or "").lower().removeprefix("www.")
    path = (parts.path or "").rstrip("/")
    query = "&".join(
        sorted(
            piece
            for piece in (parts.query or "").split("&")
            if piece and not any(piece.lower().startswith(p) for p in _TRACKING_PARAMS)
        )
    )
    return f"{host}{path}" + (f"?{query}" if query else "")


def _canonical_value(value: Any) -> Any:
    """Recursively canonicalize a value so dict ordering never affects the hash."""
    if isinstance(value, dict):
        return {k: _canonical_value(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(v) for v in value]
    if isinstance(value, str):
        return _canonical_text(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return value


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

IdentityExtractor = Callable[[Deal], str | None]
"""Per-source hook returning a stable external identifier for a deal, or None."""


def _default_identity(deal: Deal) -> str | None:
    """Best-effort stable identifier when a source exposes no explicit id.

    Preference order: canonical benefit URL (usually contains the source's own
    id) → canonical page URL → normalized title → description prefix.
    """
    for url in (deal.benefit_url, deal.url):
        canonical = _canonical_url(url)
        if canonical:
            return canonical
    if deal.title:
        return _canonical_text(deal.title)
    if deal.deal_description:
        # Only a prefix: long descriptions get edited constantly, and identity
        # must survive those edits.
        return _canonical_text(deal.deal_description)[:160]
    return None


class DealIdentityResolver:
    """Computes the stable ``deal_key`` that ties all versions of a deal together.

    Register a per-source extractor whenever a source exposes a real primary key
    (e.g. HOT's ``benefitId``) — that is always more stable than a URL or title::

        resolver = DealIdentityResolver({
            "hot": lambda d: str((d.discount_logic or {}).get("benefit_id") or "") or None,
        })
    """

    def __init__(self, overrides: Mapping[str, IdentityExtractor] | None = None) -> None:
        self._overrides: dict[str, IdentityExtractor] = dict(overrides or {})

    def register(self, source_id: str, extractor: IdentityExtractor) -> None:
        self._overrides[source_id] = extractor

    def external_id(self, deal: Deal) -> str | None:
        extractor = self._overrides.get(deal.source_id)
        if extractor is not None:
            try:
                value = extractor(deal)
            except Exception:  # a bad hook must never break ingestion
                value = None
            if value:
                return str(value)
        return _default_identity(deal)

    def deal_key(self, deal: Deal) -> str:
        """Return the stable business key: ``source | store | deal_type | external_id``."""
        external = self.external_id(deal) or ""
        parts = (deal.source_id, deal.store_id, deal.deal_type or "", external)
        return _sha256("|".join(parts))


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------

def deal_snapshot(deal: Deal) -> dict[str, Any]:
    """Serialize a ``Deal`` to the dict stored on versions and heads."""
    from lessley_deals.persistence.serialization import to_dict

    snapshot: dict[str, Any] = to_dict(deal)
    return {k: v for k, v in snapshot.items() if v is not None}


def compute_content_hash(deal: Deal) -> str:
    """Hash the semantic content of a deal (see :data:`CONTENT_FIELDS`)."""
    payload: dict[str, Any] = {}
    for name in CONTENT_FIELDS:
        value = getattr(deal, name, None)
        if name in ("benefit_url", "url"):
            payload[name] = _canonical_url(value)
        elif name == "group_member_store_ids":
            payload[name] = sorted(value or [])
        else:
            payload[name] = _canonical_value(value)
    return _sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str))


def diff_snapshots(old: Mapping[str, Any], new: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the names of the content fields that differ between two snapshots.

    Used purely for observability — "what changed" in change reports and logs.
    """
    changed = [
        name
        for name in CONTENT_FIELDS
        if _canonical_value(old.get(name)) != _canonical_value(new.get(name))
    ]
    return tuple(changed)


# ---------------------------------------------------------------------------
# Source-declared expiry
# ---------------------------------------------------------------------------

def _parse_date(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        # Israeli sources commonly emit dd/mm/yyyy or dd.mm.yyyy.
        for fmt in ("%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def extract_source_expiry(deal: Deal) -> datetime | None:
    """Find the end date the *source itself* declared, if any.

    Looked up in ``discount_logic`` and ``constraints`` under the usual key
    names.  A deal past this date is expired even if the source still lists it.
    """
    for container in (deal.discount_logic, deal.constraints):
        if not isinstance(container, Mapping):
            continue
        for key in _EXPIRY_KEYS:
            if key in container:
                parsed = _parse_date(container[key])
                if parsed is not None:
                    return parsed
        limits = container.get("limits")
        if isinstance(limits, Mapping):
            for key in _EXPIRY_KEYS:
                if key in limits:
                    parsed = _parse_date(limits[key])
                    if parsed is not None:
                        return parsed
    return None
