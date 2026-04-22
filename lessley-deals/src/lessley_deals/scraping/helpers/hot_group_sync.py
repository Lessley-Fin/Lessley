"""Sync HOT store-group member names against the canonical store database.

Reads manually maintained HOT gift-card group entries from
``hot_store_groups.json``, resolves each plain-string member name via the
matching pipeline, writes ``store_id`` back for auto-matched members, and
pushes unresolved members to the review queue.

Only entries WITHOUT ``managed_by: "swish_scraper"`` are processed.
Swish-managed entries are left untouched (owned by ``sync-swish-groups``).
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
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
        normalized_at=datetime.now(UTC),
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
    members: list[str | dict[str, Any]],
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


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def _load_groups_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}, got {type(data).__name__}")
    return data


def sync_hot_groups(
    alias_index: AliasIndex,
    review_queue: ReviewQueue,
    *,
    groups_config_path: Path | None = None,
    match_config: MatchConfig | None = None,
    pipeline: MatchPipeline | None = None,
) -> HotGroupSyncSummary:
    """Resolve HOT store-group members against the canonical store database.

    Skips Swish-managed entries (``managed_by: "swish_scraper"``).
    Upgrades plain-string member names to ``{name, store_id, confidence}`` dicts.
    Pushes unresolved names to ``review_queue``.
    Writes the updated config back atomically.
    """
    config_path = groups_config_path or _DEFAULT_GROUPS_PATH
    cfg = match_config or MatchConfig()
    match_pipeline = pipeline or MatchPipeline(config=cfg)

    groups = _load_groups_config(config_path)
    summary = HotGroupSyncSummary()
    pending_names = _existing_pending_names(review_queue)
    now = datetime.now(UTC)

    for group_key, group_entry in groups.items():
        if group_key.startswith("_"):
            continue
        if not isinstance(group_entry, dict):
            continue
        if group_entry.get("managed_by") == SWISH_MANAGED_BY:
            continue

        summary.groups_processed += 1

        group_entry["stores"] = _resolve_member_list(
            members=group_entry.get("stores", []),
            group_key=group_key,
            pending_names=pending_names,
            pipeline=match_pipeline,
            index=alias_index,
            review_queue=review_queue,
            summary=summary,
            now=now,
        )

        sub_groups = group_entry.get("sub_groups", {})
        if isinstance(sub_groups, dict):
            for sub_key, sub_members in sub_groups.items():
                if isinstance(sub_members, list):
                    sub_groups[sub_key] = _resolve_member_list(
                        members=sub_members,
                        group_key=f"{group_key}/{sub_key}",
                        pending_names=pending_names,
                        pipeline=match_pipeline,
                        index=alias_index,
                        review_queue=review_queue,
                        summary=summary,
                        now=now,
                    )

    _atomic_write_json(config_path, groups)
    logger.info(
        "HOT groups sync: %d groups, %d resolved, %d pending, %d review items created",
        summary.groups_processed,
        summary.members_resolved,
        summary.members_pending,
        summary.review_items_created,
    )
    return summary
