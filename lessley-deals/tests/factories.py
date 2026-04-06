from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from lessley_deals.domain.enums import (
    AliasSource,
    MatchDecision,
    ReviewStatus,
)
from lessley_deals.domain.models import (
    CanonicalStore,
    Deal,
    Explanation,
    MatchCandidate,
    MatchVerdict,
    NameForms,
    PriceInfo,
    RawScrapedRecord,
    RawStore,
    ReviewItem,
    StoreAlias,
)
from lessley_deals.persistence.id_gen import generate_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_name_forms(name: str) -> NameForms:
    """Build NameForms with sensible defaults from a plain name string."""
    import re

    normalized = name.strip().lower()
    compact = re.sub(r"[\s\W]", "", normalized)
    final_map = str.maketrans("םןץףך", "מנצפכ")
    compact = compact.translate(final_map)
    tokens = tuple(sorted(set(w for w in normalized.split() if len(w) > 1)))
    return NameForms(normalized=normalized, compact=compact, tokens=tokens)


def make_raw_deal(**overrides: Any) -> RawScrapedRecord:
    defaults: dict[str, Any] = dict(
        id=generate_id(),
        source_id="test_source",
        store_name="Test Store",
        deal_description="Buy 2 get 1 free",
        price_text="\u20aa29.90",
        scraped_at=_now(),
        raw_payload={},
        url=None,
    )
    defaults.update(overrides)
    return RawScrapedRecord(**defaults)


def make_raw_store(**overrides: Any) -> RawStore:
    defaults: dict[str, Any] = dict(
        id=generate_id(),
        source_id="test_source",
        name="Test Store",
        scraped_at=_now(),
        raw_payload={},
        branch=None,
        address=None,
        url=None,
    )
    defaults.update(overrides)
    return RawStore(**defaults)


def make_store(**overrides: Any) -> CanonicalStore:
    name = overrides.pop("name", "Test Store")
    defaults: dict[str, Any] = dict(
        id=generate_id(),
        name=name,
        name_forms=make_name_forms(name),
        created_at=_now(),
        updated_at=_now(),
        metadata={},
    )
    defaults.update(overrides)
    return CanonicalStore(**defaults)


def make_alias(store_id: str, alias: str, **overrides: Any) -> StoreAlias:
    defaults: dict[str, Any] = dict(
        id=generate_id(),
        store_id=store_id,
        alias=alias,
        alias_forms=make_name_forms(alias),
        source=AliasSource.SEED,
        created_at=_now(),
    )
    defaults.update(overrides)
    return StoreAlias(**defaults)


def make_match_verdict(**overrides: Any) -> MatchVerdict:
    defaults: dict[str, Any] = dict(
        record_id="raw_001",
        input_name="test store",
        decision=MatchDecision.NO_MATCH,
        candidates=(),
        explanation=Explanation(
            stages_run=("exact_alias",),
            reason="no candidates above review threshold",
        ),
        best=None,
    )
    defaults.update(overrides)
    return MatchVerdict(**defaults)


def make_review_item(raw_id: str | None = None, **overrides: Any) -> ReviewItem:
    rid = raw_id or generate_id()
    input_name = overrides.pop("input_name", "test store")
    verdict = overrides.pop("verdict", None) or make_match_verdict(record_id=rid)
    defaults: dict[str, Any] = dict(
        id=generate_id(),
        raw_id=rid,
        input_name=input_name,
        input_name_forms=make_name_forms(input_name),
        raw_input_name=None,
        verdict=verdict,
        created_at=_now(),
        status=ReviewStatus.PENDING,
        decision=None,
        reviewed_at=None,
    )
    defaults.update(overrides)
    return ReviewItem(**defaults)


def make_price_info(**overrides: Any) -> PriceInfo:
    defaults: dict[str, Any] = dict(
        expression="\u20aa10.00",
        unit_price=Decimal("10.00"),
        quantity=1,
        total=None,
        currency="ILS",
    )
    defaults.update(overrides)
    return PriceInfo(**defaults)


def make_deal(**overrides: Any) -> Deal:
    defaults: dict[str, Any] = dict(
        id=generate_id(),
        store_id=generate_id(),
        raw_id=generate_id(),
        source_id="test_source",
        description="Buy 2 get 1 free",
        scraped_at=_now(),
        resolved_at=_now(),
        price=None,
        url=None,
    )
    defaults.update(overrides)
    return Deal(**defaults)
