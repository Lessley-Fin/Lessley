from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from lessley_deals.domain.enums import (
    AliasSource,
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
    description: str
    scraped_at: datetime
    resolved_at: datetime
    currency: str | None = None
    url: str | None = None
    discount_logic: dict[str, Any] | None = None
    stackable: bool | None = None
    redeem_channels: list[str] = field(default_factory=list)
    coupon_code: str | None = None
    club_id: str | None = None
    group_member_stores: list[str] | None = None

    @property
    def fingerprint(self) -> str:
        data = f"{self.store_id}|{self.source_id}|{self.description}|{self.currency or ''}"
        return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class Club:
    id: str
    name: str
    source_id: str
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExternalReference:
    id: str
    store_id: str
    system: str
    external_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


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
