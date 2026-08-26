"""Dataclass <-> dict <-> JSON serialization helpers."""

from __future__ import annotations

import dataclasses
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
from lessley_deals.domain.models import (
    CanonicalStore,
    Club,
    CurrentDeal,
    Deal,
    DealVersion,
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
    "DealLifecycleStatus": DealLifecycleStatus,
    "DealChangeType": DealChangeType,
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
        scraped_at=_parse_datetime(d["scraped_at"]),  # type: ignore[arg-type]
        resolved_at=_parse_datetime(d["resolved_at"]),  # type: ignore[arg-type]
        title=d.get("title"),
        deal_description=d.get("deal_description") or d.get("description"),
        terms_and_conditions=d.get("terms_and_conditions"),
        benefit_url=d.get("benefit_url"),
        currency=d.get("currency"),
        url=d.get("url"),
        discount_logic=d.get("discount_logic"),
        deal_type=d.get("deal_type"),
        constraints=d.get("constraints"),
        club_id=d.get("club_id"),
        group_member_stores=d.get("group_member_stores") or None,
        group_member_store_ids=d.get("group_member_store_ids") or None,
        deal_key=d.get("deal_key"),
        # Rows written before the lifecycle existed carry no ``status``; they
        # are on offer as far as anyone knew, so they read back as ACTIVE.
        status=DealLifecycleStatus(d.get("status") or DealLifecycleStatus.ACTIVE),
        first_seen_at=_parse_datetime(d.get("first_seen_at")),
        last_seen_at=_parse_datetime(d.get("last_seen_at")),
        expires_at=_parse_datetime(d.get("expires_at")),
        expired_at=_parse_datetime(d.get("expired_at")),
    )


def deal_version_from_dict(d: dict[str, Any]) -> DealVersion:
    return DealVersion(
        id=d["id"],
        deal_key=d["deal_key"],
        version=int(d["version"]),
        store_id=d["store_id"],
        source_id=d["source_id"],
        content_hash=d["content_hash"],
        change_type=DealChangeType(d["change_type"]),
        status=DealLifecycleStatus(d["status"]),
        valid_from=_parse_datetime(d["valid_from"]),  # type: ignore[arg-type]
        valid_to=_parse_datetime(d.get("valid_to")),
        is_current=bool(d["is_current"]),
        snapshot=d.get("snapshot", {}),
        run_id=d.get("run_id"),
        changed_fields=tuple(d.get("changed_fields", ())),
        source_expires_at=_parse_datetime(d.get("source_expires_at")),
    )


def current_deal_from_dict(d: dict[str, Any]) -> CurrentDeal:
    return CurrentDeal(
        deal_key=d["deal_key"],
        deal_id=d["deal_id"],
        store_id=d["store_id"],
        source_id=d["source_id"],
        version=int(d["version"]),
        content_hash=d["content_hash"],
        status=DealLifecycleStatus(d["status"]),
        first_seen_at=_parse_datetime(d["first_seen_at"]),  # type: ignore[arg-type]
        last_seen_at=_parse_datetime(d["last_seen_at"]),  # type: ignore[arg-type]
        valid_from=_parse_datetime(d["valid_from"]),  # type: ignore[arg-type]
        valid_to=_parse_datetime(d.get("valid_to")),
        missing_runs=int(d.get("missing_runs", 0)),
        missing_since=_parse_datetime(d.get("missing_since")),
        source_expires_at=_parse_datetime(d.get("source_expires_at")),
        raw_fingerprint=d.get("raw_fingerprint"),
        snapshot=d.get("snapshot", {}),
    )


def club_from_dict(d: dict[str, Any]) -> Club:
    return Club(
        id=d["id"],
        name=d["name"],
        source_id=d["source_id"],
        description=d.get("description"),
        metadata=d.get("metadata", {}),
        stores=d.get("stores", []),
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
        raw_input_name=d.get("raw_input_name"),
        verdict=_parse_match_verdict(d["verdict"]),
        created_at=_parse_datetime(d["created_at"]),  # type: ignore[arg-type]
        status=ReviewStatus(d["status"]),
        decision=_parse_review_decision(d.get("decision")),
        reviewed_at=_parse_datetime(d.get("reviewed_at")),  # type: ignore[arg-type]
    )
