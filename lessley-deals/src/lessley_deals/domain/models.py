from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from lessley_deals.domain.enums import (
    AliasSource,
    DealChangeType,
    DealLifecycleStatus,
    MatchDecision,
    RecordFate,
    ReviewAction,
    ReviewStatus,
)


# ---------------------------------------------------------------------------
# Value objects (frozen)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NameForms:
    normalized: str
    compact: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class PriceInfo:
    expression: str
    unit_price: Decimal | None = None
    quantity: int = 1
    total: Decimal | None = None
    currency: str = "ILS"


# ---------------------------------------------------------------------------
# Raw data (frozen – verbatim from scrapers)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RawScrapedRecord:
    id: str
    source_id: str
    store_name: str
    deal_description: str
    price_text: str
    scraped_at: datetime
    raw_payload: dict[str, Any] = field(default_factory=dict)
    url: str | None = None

    @property
    def fingerprint(self) -> str:
        data = f"{self.source_id}|{self.deal_description}|{self.price_text}"
        return hashlib.sha256(data.encode()).hexdigest()


@dataclass(frozen=True)
class RawStore:
    id: str
    source_id: str
    name: str
    scraped_at: datetime
    raw_payload: dict[str, Any] = field(default_factory=dict)
    branch: str | None = None
    address: str | None = None
    url: str | None = None

    @property
    def fingerprint(self) -> str:
        data = f"{self.source_id}|{self.name}|{self.branch or ''}"
        return hashlib.sha256(data.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Normalized data (frozen – output of normalization pipeline)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NormalizedRecord:
    raw_id: str
    source_id: str
    store_name_forms: NameForms
    deal_description: str
    normalized_at: datetime
    price: PriceInfo | None = None
    domain: str | None = None


# ---------------------------------------------------------------------------
# Matching (frozen – output of matching pipeline)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MatchCandidate:
    store_id: str
    store_name: str
    confidence: float
    stage: str
    matched_alias: str | None = None


@dataclass(frozen=True)
class Explanation:
    stages_run: tuple[str, ...]
    reason: str
    stage_matched: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MatchVerdict:
    record_id: str
    input_name: str
    decision: MatchDecision
    candidates: tuple[MatchCandidate, ...]
    explanation: Explanation
    best: MatchCandidate | None = None


# ---------------------------------------------------------------------------
# Canonical entities (mutable – source of truth)
# ---------------------------------------------------------------------------

@dataclass
class CanonicalStore:
    id: str
    name: str
    name_forms: NameForms
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StoreAlias:
    id: str
    store_id: str
    alias: str
    alias_forms: NameForms
    source: AliasSource
    created_at: datetime


@dataclass
class Deal:
    id: str
    store_id: str
    raw_id: str
    source_id: str
    scraped_at: datetime
    resolved_at: datetime
    title: str | None = None
    deal_description: str | None = None
    terms_and_conditions: str | None = None
    benefit_url: str | None = None
    currency: str | None = None
    url: str | None = None
    discount_logic: dict[str, Any] | None = None
    # Which of deal-optimizer's DealType layers this deal belongs to (e.g.
    # "giftcard_discount"). Optional at scrape time — deal-optimizer's own
    # adapter.py infers it from text/discount_logic when left unset.
    deal_type: str | None = None
    # Structured deal terms parsed from ``terms_and_conditions`` (combinability,
    # limits, redemption_channels, eligibility). Populated by the constraints
    # enrichment step; see enrichment/constaints_parser.py for the schema.
    constraints: dict[str, Any] | None = None
    club_id: str | None = None
    # Either a list[str] (legacy: member store names) or list[dict] of
    # {"name", "store_id", "confidence"} (resolved members from group sync).
    group_member_stores: list[Any] | None = None
    # Resolved canonical store IDs for group-wide deals.  Populated by the
    # group-sync flow; query-time fan-out matches against these for accuracy.
    group_member_store_ids: list[str] | None = None

    # --- Lifecycle ---------------------------------------------------------
    # Owned by the versioning layer, not by the scrape: ``DealProjector`` stamps
    # these onto every row from the head table on each run (see
    # versioning/projection.py).  They are what makes ``deals`` a *current* read
    # model instead of an append-only log — consumers filter on ``status``.
    deal_key: str | None = None
    """Stable business key shared by every version of this offer."""

    status: DealLifecycleStatus = DealLifecycleStatus.ACTIVE
    """ACTIVE while the source still offers it, EXPIRED once it stops."""

    first_seen_at: datetime | None = None

    last_seen_at: datetime | None = None
    """Last run that still saw this offer — how stale the row is, in one field."""

    expires_at: datetime | None = None
    """End date the source declared for itself, when it publishes one."""

    expired_at: datetime | None = None
    """When *we* concluded it was gone.  None while ACTIVE."""

    @property
    def fingerprint(self) -> str:
        data = f"{self.store_id}|{self.source_id}|{self.deal_description or ''}|{self.currency or ''}"
        return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class Club:
    id: str
    name: str
    source_id: str
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    stores: list[str] = field(default_factory=list)


@dataclass
class ExternalReference:
    id: str
    store_id: str
    system: str
    external_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Deal history (SCD Type 2)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DealVersion:
    """One immutable row in the Slowly-Changing-Dimension (Type 2) history.

    Every time a deal is first seen, changes, expires or comes back, a new
    ``DealVersion`` is appended.  Rows are never updated in place except for
    *closing* them (``valid_to`` / ``is_current`` / ``status``), which is what
    makes the "what did this deal look like on date X" query possible.
    """

    id: str
    deal_key: str          # stable business key — same across all versions
    version: int           # 1-based, monotonic per deal_key
    store_id: str
    source_id: str
    content_hash: str      # hash of the semantic fields only (see versioning.hashing)
    change_type: DealChangeType
    status: DealLifecycleStatus
    valid_from: datetime
    valid_to: datetime | None      # None => still the current version
    is_current: bool
    snapshot: dict[str, Any]       # full serialized Deal as observed at valid_from
    run_id: str | None = None      # scrape run that produced this version
    changed_fields: tuple[str, ...] = ()
    source_expires_at: datetime | None = None  # end date declared by the source itself


@dataclass
class CurrentDeal:
    """Head record — exactly one per ``deal_key``, always the latest state.

    This is the collection product code should read (filtered on
    ``status == ACTIVE``).  ``DealVersion`` is the audit trail behind it.
    """

    deal_key: str
    deal_id: str           # stable Deal.id — assigned on version 1, never changes
    store_id: str
    source_id: str
    version: int
    content_hash: str
    status: DealLifecycleStatus
    first_seen_at: datetime
    last_seen_at: datetime
    valid_from: datetime
    valid_to: datetime | None = None
    # Anti-flapping bookkeeping: a deal missing from one run is not expired
    # immediately (a source may paginate badly or rate-limit us).
    missing_runs: int = 0
    missing_since: datetime | None = None
    source_expires_at: datetime | None = None
    raw_fingerprint: str | None = None  # last raw record fingerprint that produced it
    snapshot: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Review (mutable)
# ---------------------------------------------------------------------------

@dataclass
class ReviewDecision:
    action: ReviewAction
    reviewed_by: str
    store_id: str | None = None
    new_store_name: str | None = None
    note: str | None = None


@dataclass
class ReviewItem:
    id: str
    raw_id: str
    input_name: str
    input_name_forms: NameForms
    verdict: MatchVerdict
    created_at: datetime
    raw_input_name: str | None = None
    status: ReviewStatus = ReviewStatus.PENDING
    decision: ReviewDecision | None = None
    reviewed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Pipeline context (mutable – tracks each record through the pipeline)
# ---------------------------------------------------------------------------

@dataclass
class PipelineRecord:
    raw: RawScrapedRecord
    normalized: NormalizedRecord | None = None
    verdict: MatchVerdict | None = None
    fate: RecordFate | None = None
    error: str | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)
