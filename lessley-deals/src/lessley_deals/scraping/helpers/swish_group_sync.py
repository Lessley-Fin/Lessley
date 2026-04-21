"""Sync Swish gift-card catalogue into the store-groups config.

Swish (``נפשונית``) is a multi-brand gift card platform.  Each Swish
benefit is a card redeemable at a curated list of retailers.  The scraper
``test_swish.py`` writes a flat ``swish_database.json`` with one record per
benefit (``benefit_id`` + ``benefit_name`` + ``stores``).

This module turns that flat file into entries in ``hot_store_groups.json``
that the rest of the pipeline already understands as group-wide gift cards
(:func:`classify_group_deal_resolved`).  The conversion does three things:

1. Build one group entry per Swish benefit, keyed ``swish:<benefit_id>``,
   tagged ``managed_by="swish_scraper"``.
2. Resolve each member store name against the canonical stores via the
   matching pipeline (auto-accept ≥ ``DEALS_AUTO_MATCH_THRESHOLD``).
   Resolved entries get ``store_id`` and ``confidence`` filled in.
3. Push every unresolved member to the review queue as a
   ``GROUP_MEMBER_MATCH`` item so a human can either link it to an existing
   store or create a new one.  Approved decisions feed back via the alias
   learner so the next sync resolves them automatically.

Hand-maintained HOT entries in the same config file are preserved verbatim;
only entries with ``managed_by == "swish_scraper"`` are touched.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
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


SWISH_GROUP_PREFIX = "swish:"
SWISH_MANAGED_BY = "swish_scraper"
SWISH_SOURCE_ID = "swish"
SWISH_TITLE_PREFIX = "תו קניה"


@dataclass
class SwishSyncResult:
    """Summary of one sync run, useful for logging / CLI output."""

    benefits_processed: int = 0
    groups_written: int = 0
    groups_removed: int = 0
    members_total: int = 0
    members_resolved: int = 0
    members_to_review: int = 0
    review_items_created: int = 0
    pre_existing_review_skipped: int = 0
    benefit_ids: list[str] = field(default_factory=list)


def _build_name_forms(name: str) -> NameForms:
    """Mirror NormalizationPipeline._build_name_forms for stand-alone use."""
    normalized = collapse_whitespace(normalize_hebrew(name)).lower()
    compact = re.sub(r"[\s\W]+", "", normalized)
    compact = normalize_final_forms(compact)
    tokens = tuple(sorted({w for w in normalized.split() if len(w) > 1}))
    return NameForms(normalized=normalized, compact=compact, tokens=tokens)


def _to_normalized_record(name: str, source_record_id: str) -> NormalizedRecord:
    """Synthesize a NormalizedRecord for a bare store name.

    Avoids running the full normalization pipeline (which expects a
    RawScrapedRecord with deal text, price, etc.) — only the name forms
    matter for matching.
    """
    return NormalizedRecord(
        raw_id=source_record_id,
        source_id=SWISH_SOURCE_ID,
        store_name_forms=_build_name_forms(name),
        deal_description="",
        normalized_at=datetime.now(timezone.utc),
        price=None,
        domain=None,
    )


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write ``payload`` to ``path`` atomically (tempfile + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _load_groups_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}, got {type(data).__name__}")
    return data


def _load_swish_database(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Swish database not found at {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {path}, got {type(data).__name__}")
    return data


def _existing_pending_names(queue: ReviewQueue) -> set[str]:
    """Return exact ``raw_input_name`` of every pending review item.

    Dedup is on the raw name string, not on the raw_id prefix.  This prevents
    the same store name being pushed multiple times when it appears in more than
    one Swish benefit, or when it is already pending from a different source.
    """
    return {item.raw_input_name for item in queue.get_pending() if item.raw_input_name}


def _make_review_verdict(
    group_key: str,
    raw_name: str,
    verdict: MatchVerdict,
) -> MatchVerdict:
    """Re-stamp the verdict's ``record_id`` to the synthetic ``group_key|name``.

    The ReviewItem indexes on ``raw_id``; the verdict's ``record_id`` mirrors
    it for downstream filtering / display.
    """
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
            },
        ),
        best=verdict.best,
    )


def _resolve_member(
    raw_name: str,
    group_key: str,
    pipeline: MatchPipeline,
    index: AliasIndex,
    config: MatchConfig,
) -> tuple[dict[str, Any], MatchVerdict | None]:
    """Match one raw member name → canonical store.

    Returns ``({"name", "store_id", "confidence"}, verdict_or_none)``.
    The verdict is returned only when the member needs review (so the caller
    can build a ReviewItem).  ``None`` means the member was auto-resolved.
    """
    record_id = f"{group_key}::{raw_name}"
    normalized = _to_normalized_record(raw_name, record_id)
    verdict = pipeline.match(normalized, index)

    if verdict.decision == MatchDecision.AUTO_MATCH and verdict.best is not None:
        member: dict[str, Any] = {
            "name": raw_name,
            "store_id": verdict.best.store_id,
            "confidence": round(verdict.best.confidence, 4),
        }
        return member, None

    # REVIEW or NO_MATCH — leave store_id null, return verdict for review
    member = {"name": raw_name, "store_id": None, "confidence": None}
    return member, verdict


def sync_swish_groups(
    swish_db_path: Path,
    alias_index: AliasIndex,
    review_queue: ReviewQueue,
    *,
    groups_config_path: Path | None = None,
    match_config: MatchConfig | None = None,
    pipeline: MatchPipeline | None = None,
) -> SwishSyncResult:
    """Sync the Swish catalogue into the store-groups config.

    Args:
        swish_db_path: Path to ``swish_database.json`` produced by the Swish scraper.
        alias_index: Pre-built :class:`AliasIndex` (canonical stores + aliases).
        review_queue: Queue used for unresolved members.
        groups_config_path: Path to ``hot_store_groups.json``.  Defaults to
            the bundled config alongside :mod:`brand_utils`.
        match_config: Optional :class:`MatchConfig` override (thresholds).
        pipeline: Optional :class:`MatchPipeline` override (mainly for tests).

    Returns:
        A :class:`SwishSyncResult` summarising the run.

    Raises:
        FileNotFoundError: if ``swish_db_path`` does not exist.
        ValueError: if either input file has an unexpected JSON shape.
    """
    config_path = groups_config_path or _DEFAULT_GROUPS_PATH
    cfg = match_config or MatchConfig()
    match_pipeline = pipeline or MatchPipeline(config=cfg)

    swish_records = _load_swish_database(swish_db_path)
    groups = _load_groups_config(config_path)

    result = SwishSyncResult()
    seen_keys: set[str] = set()
    pending_names = _existing_pending_names(review_queue)
    now = datetime.now(timezone.utc)

    for record in swish_records:
        benefit_id = str(record.get("benefit_id") or "").strip()
        if not benefit_id:
            logger.debug("Skipping Swish record without benefit_id: %r", record)
            continue
        result.benefits_processed += 1
        result.benefit_ids.append(benefit_id)

        group_key = f"{SWISH_GROUP_PREFIX}{benefit_id}"
        seen_keys.add(group_key)

        raw_member_names: list[str] = [
            str(s).strip() for s in (record.get("stores") or []) if str(s).strip()
        ]
        # de-duplicate while preserving order
        raw_member_names = list(dict.fromkeys(raw_member_names))

        members: list[dict[str, Any]] = []
        for raw_name in raw_member_names:
            member, verdict = _resolve_member(
                raw_name, group_key, match_pipeline, alias_index, cfg,
            )
            members.append(member)
            result.members_total += 1
            if member["store_id"]:
                result.members_resolved += 1
                continue
            result.members_to_review += 1
            if verdict is None:
                continue
            review_record_id = f"{group_key}::{raw_name}"
            if raw_name in pending_names:
                result.pre_existing_review_skipped += 1
                continue
            review_item = ReviewItem(
                id=generate_id(),
                raw_id=review_record_id,
                input_name=raw_name,
                input_name_forms=_build_name_forms(raw_name),
                raw_input_name=raw_name,
                verdict=_make_review_verdict(group_key, raw_name, verdict),
                created_at=now,
            )
            review_queue.add(review_item)
            pending_names.add(raw_name)
            result.review_items_created += 1

        groups[group_key] = {
            "managed_by": SWISH_MANAGED_BY,
            "source_id": SWISH_SOURCE_ID,
            "benefit_id": benefit_id,
            "display_name": str(record.get("benefit_name") or "").strip() or None,
            "title_prefix": SWISH_TITLE_PREFIX,
            "last_scraped": now.isoformat(),
            "stores": members,
        }
        result.groups_written += 1

    # Full-refresh policy: drop Swish-managed entries that are no longer in
    # the live database (the benefit was removed from the Swish catalogue).
    stale_keys = [
        key for key, cfg_entry in groups.items()
        if isinstance(cfg_entry, dict)
        and cfg_entry.get("managed_by") == SWISH_MANAGED_BY
        and key not in seen_keys
    ]
    for key in stale_keys:
        groups.pop(key, None)
        result.groups_removed += 1

    _atomic_write_json(config_path, groups)
    logger.info(
        "Swish sync complete: %d benefits, %d members (%d resolved, %d to review), "
        "%d new review items, %d stale groups removed",
        result.benefits_processed,
        result.members_total,
        result.members_resolved,
        result.members_to_review,
        result.review_items_created,
        result.groups_removed,
    )
    return result
