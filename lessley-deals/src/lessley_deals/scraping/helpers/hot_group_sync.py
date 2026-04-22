"""Sync HOT store-group member names against the canonical store database.

Reads manually maintained HOT gift-card group entries from
``hot_store_groups.json``, resolves each plain-string member name via the
matching pipeline, writes ``store_id`` back for auto-matched members, and
pushes unresolved members to the review queue.

Only entries WITHOUT ``managed_by: "swish_scraper"`` are processed.
Swish-managed entries are left untouched (owned by ``sync-swish-groups``).
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lessley_deals.domain.enums import MatchDecision
from lessley_deals.domain.models import (
    Explanation,
    MatchVerdict,
    NameForms,
    NormalizedRecord,
    ReviewItem,
)
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.pipeline import MatchPipeline
from lessley_deals.normalization.hebrew_utils import normalize_final_forms, normalize_hebrew
from lessley_deals.normalization.text import collapse_whitespace
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.review.queue import ReviewQueue
from lessley_deals.scraping.helpers.brand_utils import _DEFAULT_GROUPS_PATH

logger = logging.getLogger(__name__)

HOT_SOURCE_ID = "hot_groups"
SWISH_MANAGED_BY = "swish_scraper"


@dataclass
class HotGroupSyncSummary:
    groups_processed: int = 0
    members_resolved: int = 0
    members_pending: int = 0
    review_items_created: int = 0
    pre_existing_review_skipped: int = 0


def _build_name_forms(name: str) -> NameForms:
    normalized = collapse_whitespace(normalize_hebrew(name)).lower()
    compact = re.sub(r"[\s\W]+", "", normalized)
    compact = normalize_final_forms(compact)
    tokens = tuple(sorted({w for w in normalized.split() if len(w) > 1}))
    return NameForms(normalized=normalized, compact=compact, tokens=tokens)


def _to_normalized_record(name: str, group_key: str) -> NormalizedRecord:
    return NormalizedRecord(
        raw_id=f"{group_key}::{name}",
        source_id=HOT_SOURCE_ID,
        store_name_forms=_build_name_forms(name),
        deal_description="",
        normalized_at=datetime.now(timezone.utc),
        price=None,
        domain=None,
    )


def _make_review_verdict(
    group_key: str,
    raw_name: str,
    verdict: MatchVerdict,
) -> MatchVerdict:
    return MatchVerdict(
        record_id=f"{group_key}::{raw_name}",
        input_name=verdict.input_name,
        decision=verdict.decision,
        candidates=verdict.candidates,
        explanation=Explanation(
            stages_run=verdict.explanation.stages_run,
            reason=f"group-member resolution: {verdict.explanation.reason}",
            stage_matched=verdict.explanation.stage_matched,
            details={
                **verdict.explanation.details,
                "group_key": group_key,
                "kind": "group_member_match",
                "source": "hot_groups",
            },
        ),
        best=verdict.best,
    )


def _resolve_member(
    raw_name: str,
    group_key: str,
    pipeline: MatchPipeline,
    index: AliasIndex,
) -> tuple[dict[str, Any], MatchVerdict | None]:
    normalized = _to_normalized_record(raw_name, group_key)
    verdict = pipeline.match(normalized, index)

    if verdict.decision == MatchDecision.AUTO_MATCH and verdict.best is not None:
        return {
            "name": raw_name,
            "store_id": verdict.best.store_id,
            "confidence": round(verdict.best.confidence, 4),
        }, None

    return {"name": raw_name, "store_id": None, "confidence": None}, verdict


def _existing_pending_names(queue: ReviewQueue) -> set[str]:
    return {item.raw_input_name for item in queue.get_pending() if item.raw_input_name}


def _resolve_member_list(
    members: list[str | dict],
    group_key: str,
    pending_names: set[str],
    pipeline: MatchPipeline,
    index: AliasIndex,
    review_queue: ReviewQueue,
    summary: HotGroupSyncSummary,
    now: datetime,
) -> list[dict[str, Any]]:
    """Resolve a list of member entries (strings or dicts) for one group."""
    result: list[dict[str, Any]] = []
    for entry in members:
        if isinstance(entry, str):
            raw_name = entry.strip()
        elif isinstance(entry, dict):
            if entry.get("store_id"):
                result.append(entry)
                continue
            raw_name = str(entry.get("name") or "").strip()
        else:
            continue
        if not raw_name:
            continue

        member, verdict = _resolve_member(raw_name, group_key, pipeline, index)
        result.append(member)

        if member["store_id"]:
            summary.members_resolved += 1
            continue

        summary.members_pending += 1
        if raw_name in pending_names:
            summary.pre_existing_review_skipped += 1
            continue
        if verdict is None:
            continue

        review_item = ReviewItem(
            id=generate_id(),
            raw_id=f"{group_key}::{raw_name}",
            input_name=raw_name,
            input_name_forms=_build_name_forms(raw_name),
            raw_input_name=raw_name,
            verdict=_make_review_verdict(group_key, raw_name, verdict),
            created_at=now,
        )
        review_queue.add(review_item)
        pending_names.add(raw_name)
        summary.review_items_created += 1

    return result


def sync_hot_groups(
    alias_index: AliasIndex,
    review_queue: ReviewQueue,
    *,
    groups_config_path: Path | None = None,
    match_config: MatchConfig | None = None,
    pipeline: MatchPipeline | None = None,
) -> HotGroupSyncSummary:
    raise NotImplementedError("implemented in Task 3")
