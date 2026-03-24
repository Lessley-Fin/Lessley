"""Dataclass <-> dict <-> JSON serialization helpers."""

from __future__ import annotations

import dataclasses
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
from lessley_deals.domain.models import (
    CanonicalStore,
    Deal,
    Explanation,
    ExternalReference,
    MatchCandidate,
    MatchVerdict,
    NameForms,
    PriceInfo,
    RawScrapedRecord,
    RawStore,
    ReviewDecision,
    ReviewItem,
    StoreAlias,
)

_ENUM_MAP = {
    "MatchDecision": MatchDecision,
    "ReviewStatus": ReviewStatus,
    "ReviewAction": ReviewAction,
    "AliasSource": AliasSource,
    "RecordFate": RecordFate,
}


def to_dict(obj: Any) -> dict[str, Any] | Any:
    """Convert a dataclass (possibly nested) to a plain dict."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        result: dict[str, Any] = {}
        for f in dataclasses.fields(obj):
            value = getattr(obj, f.name)
            result[f.name] = _serialize_value(value)
        return result
    return obj


def _serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, tuple):
        return [_serialize_value(v) for v in value]
    if isinstance(value, list):
        return [_serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return to_dict(value)
    return value


def _parse_datetime(s: str | None) -> datetime | None:
    if s is None:
        return None
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_name_forms(d: dict[str, Any]) -> NameForms:
    return NameForms(
        normalized=d["normalized"],
        compact=d["compact"],
        tokens=tuple(d["tokens"]),
    )


def _parse_price_info(d: dict[str, Any] | None) -> PriceInfo | None:
    if d is None:
        return None
    return PriceInfo(
        expression=d["expression"],
        unit_price=Decimal(d["unit_price"]) if d.get("unit_price") is not None else None,
        quantity=d.get("quantity", 1),
        total=Decimal(d["total"]) if d.get("total") is not None else None,
        currency=d.get("currency", "ILS"),
    )


def _parse_match_candidate(d: dict[str, Any]) -> MatchCandidate:
    return MatchCandidate(
        store_id=d["store_id"],
        store_name=d["store_name"],
        confidence=d["confidence"],
        stage=d["stage"],
        matched_alias=d.get("matched_alias"),
    )


def _parse_explanation(d: dict[str, Any]) -> Explanation:
    return Explanation(
        stages_run=tuple(d["stages_run"]),
        reason=d["reason"],
        stage_matched=d.get("stage_matched"),
        details=d.get("details", {}),
    )


def _parse_match_verdict(d: dict[str, Any]) -> MatchVerdict:
    candidates = tuple(_parse_match_candidate(c) for c in d.get("candidates", []))
    best_data = d.get("best")
    return MatchVerdict(
        record_id=d["record_id"],
        input_name=d["input_name"],
        decision=MatchDecision(d["decision"]),
        candidates=candidates,
        explanation=_parse_explanation(d["explanation"]),
        best=_parse_match_candidate(best_data) if best_data else None,
    )


def _parse_review_decision(d: dict[str, Any] | None) -> ReviewDecision | None:
    if d is None:
        return None
    return ReviewDecision(
        action=ReviewAction(d["action"]),
        reviewed_by=d["reviewed_by"],
        store_id=d.get("store_id"),
        new_store_name=d.get("new_store_name"),
        note=d.get("note"),
    )


# ---------------------------------------------------------------------------
# Public from_dict functions
# ---------------------------------------------------------------------------

def raw_deal_from_dict(d: dict[str, Any]) -> RawScrapedRecord:
    return RawScrapedRecord(
        id=d["id"],
        source_id=d["source_id"],
        store_name=d["store_name"],
        deal_description=d["deal_description"],
        price_text=d["price_text"],
        scraped_at=_parse_datetime(d["scraped_at"]),  # type: ignore[arg-type]
        raw_payload=d.get("raw_payload", {}),
        url=d.get("url"),
    )


def raw_store_from_dict(d: dict[str, Any]) -> RawStore:
    return RawStore(
        id=d["id"],
        source_id=d["source_id"],
        name=d["name"],
        scraped_at=_parse_datetime(d["scraped_at"]),  # type: ignore[arg-type]
        raw_payload=d.get("raw_payload", {}),
        branch=d.get("branch"),
        address=d.get("address"),
        url=d.get("url"),
    )


def canonical_store_from_dict(d: dict[str, Any]) -> CanonicalStore:
    return CanonicalStore(
        id=d["id"],
        name=d["name"],
        name_forms=_parse_name_forms(d["name_forms"]),
        created_at=_parse_datetime(d["created_at"]),  # type: ignore[arg-type]
        updated_at=_parse_datetime(d["updated_at"]),  # type: ignore[arg-type]
        metadata=d.get("metadata", {}),
    )


def alias_from_dict(d: dict[str, Any]) -> StoreAlias:
    return StoreAlias(
        id=d["id"],
        store_id=d["store_id"],
        alias=d["alias"],
        alias_forms=_parse_name_forms(d["alias_forms"]),
        source=AliasSource(d["source"]),
        created_at=_parse_datetime(d["created_at"]),  # type: ignore[arg-type]
    )


def deal_from_dict(d: dict[str, Any]) -> Deal:
    return Deal(
        id=d["id"],
        store_id=d["store_id"],
        raw_id=d["raw_id"],
        source_id=d["source_id"],
        description=d["description"],
        scraped_at=_parse_datetime(d["scraped_at"]),  # type: ignore[arg-type]
        resolved_at=_parse_datetime(d["resolved_at"]),  # type: ignore[arg-type]
        currency=d.get("currency"),
        url=d.get("url"),
        image_url=d.get("image_url"),
        discount_logic=d.get("discount_logic"),
        stackable=d.get("stackable"),
        redeem_channels=d.get("redeem_channels", []),
        coupon_code=d.get("coupon_code"),
    )


def external_ref_from_dict(d: dict[str, Any]) -> ExternalReference:
    return ExternalReference(
        id=d["id"],
        store_id=d["store_id"],
        system=d["system"],
        external_id=d["external_id"],
        metadata=d.get("metadata", {}),
    )


def review_item_from_dict(d: dict[str, Any]) -> ReviewItem:
    return ReviewItem(
        id=d["id"],
        raw_id=d["raw_id"],
        input_name=d["input_name"],
        input_name_forms=_parse_name_forms(d["input_name_forms"]),
        verdict=_parse_match_verdict(d["verdict"]),
        created_at=_parse_datetime(d["created_at"]),  # type: ignore[arg-type]
        status=ReviewStatus(d["status"]),
        decision=_parse_review_decision(d.get("decision")),
        reviewed_at=_parse_datetime(d.get("reviewed_at")),  # type: ignore[arg-type]
    )
