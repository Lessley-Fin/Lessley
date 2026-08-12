from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from lessley_deals.domain.models import RawScrapedRecord
from lessley_deals.domain.protocols import RawDealRepository
from lessley_deals.enrichment.constaints_parser import parse_deal_constraints
from lessley_deals.pipeline.constraints_stage import ConstraintsParser, ConstraintsStage

logger = logging.getLogger(__name__)

# One LLM call per deal at ~1.5s effective (concurrency 16) means a full
# backfill runs for hours. Persist every chunk so an interrupted run keeps
# everything it already paid for, and a re-run resumes where it stopped.
DEFAULT_CHUNK_SIZE = 200


def _has_terms(record: RawScrapedRecord) -> bool:
    terms = record.raw_payload.get("terms_and_conditions")
    return isinstance(terms, str) and bool(terms.strip())


def select_pending(
    records: Sequence[RawScrapedRecord],
    *,
    source: str = "",
    force: bool = False,
    limit: int = 0,
) -> list[RawScrapedRecord]:
    """Pick the raw records a backfill should spend LLM calls on.

    Skips records from other sources, records with no terms text to parse, and
    — unless *force* — records that already carry constraints. That last skip
    is what makes a re-run resume instead of paying for the same deals twice.
    """
    pending = [
        record
        for record in records
        if (not source or record.source_id == source)
        and _has_terms(record)
        and (force or not record.raw_payload.get("constraints"))
    ]
    return pending[:limit] if limit else pending


def _with_constraints(record: RawScrapedRecord, constraints: dict[str, object]) -> RawScrapedRecord:
    """Return a copy carrying *constraints* — raw records are frozen, never mutated."""
    return replace(record, raw_payload={**record.raw_payload, "constraints": constraints})


async def enrich_raw_constraints(
    raw_repo: RawDealRepository,
    *,
    source: str = "",
    limit: int = 0,
    force: bool = False,
    concurrency: int = 16,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    dry_run: bool = False,
    parser: ConstraintsParser = parse_deal_constraints,
    on_chunk: Callable[[dict[str, int]], None] | None = None,
) -> dict[str, int]:
    """Parse `terms_and_conditions` into `constraints` on already-scraped raw deals.

    Backfills deals that were scraped before the constraints stage existed (or
    while it was disabled) without re-scraping anything. The parsed block is
    written onto the raw record's ``raw_payload["constraints"]``, which is
    exactly where :class:`~lessley_deals.pipeline.persist_stage.PersistStage`
    reads it from — so a following ``deals process`` carries the constraints
    onto the built deals with no further LLM calls.

    Additive and idempotent: only ``raw_payload["constraints"]`` is written, and
    already-enriched records are skipped unless *force*. Work is persisted every
    *chunk_size* records, so an interrupted run loses at most one chunk and a
    re-run picks up from there.

    Args:
        raw_repo:    Raw deal repository (JSON or Mongo).
        source:      Only enrich this ``source_id`` (``""`` = every source).
        limit:       Enrich at most N records (0 = no cap).
        force:       Re-parse records that already have constraints.
        concurrency: Concurrent LLM calls.
        chunk_size:  Distinct terms texts parsed between checkpoint writes.
        dry_run:     Call the LLM but never write back.
        parser:      Constraints parser; injectable for tests.
        on_chunk:    Called with the running counters after each chunk.

    Returns:
        Counters: ``total``, ``pending``, ``processed``, ``skipped``, ``failed``
        and ``llm_calls`` (distinct texts actually sent to the model).
    """
    records = raw_repo.get_all()
    pending = select_pending(records, source=source, force=force, limit=limit)

    stats = {
        "total": len(records),
        "pending": len(pending),
        "processed": 0,
        "skipped": len(records) - len(pending),
        "failed": 0,
        "llm_calls": 0,
    }
    if not pending:
        logger.info("Nothing to enrich: %d raw deals, 0 pending", stats["total"])
        return stats

    # Group the whole backlog by the exact (source, terms) the parser sees, then
    # chunk the GROUPS rather than the records. ConstraintsStage dedups within a
    # call, but chunking records would split a 6k-deal boilerplate group across
    # chunks and pay for it once per chunk. Grouping first makes every distinct
    # text cost exactly one call across the entire run.
    groups: dict[tuple[str, str], list[RawScrapedRecord]] = {}
    for record in pending:
        key = (record.source_id, record.raw_payload["terms_and_conditions"])
        groups.setdefault(key, []).append(record)
    group_items = list(groups.values())
    stats["llm_calls"] = len(group_items)

    logger.info(
        "Enriching %d/%d raw deals via %d distinct terms text(s) — %.1fx fewer calls "
        "(source=%s, concurrency=%d, chunk=%d)%s",
        stats["pending"],
        stats["total"],
        len(group_items),
        stats["pending"] / len(group_items),
        source or "all",
        concurrency,
        chunk_size,
        " [dry-run]" if dry_run else "",
    )

    # A pool sized to the requested concurrency: the interpreter's default
    # executor is sized off the CPU count and would throttle the stage's
    # semaphore down to ~14 threads on a 10-core machine regardless.
    executor = ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="constraints")
    stage = ConstraintsStage(parser, max_concurrency=concurrency, executor=executor)

    try:
        for start in range(0, len(group_items), chunk_size):
            chunk_groups = group_items[start : start + chunk_size]
            # One representative per group is parsed; its answer covers the rest.
            constraints_map = await stage.run([members[0] for members in chunk_groups])

            enriched: list[RawScrapedRecord] = []
            chunk_records = 0
            for members in chunk_groups:
                chunk_records += len(members)
                constraints = constraints_map.get(members[0].id)
                if constraints is None:
                    continue
                enriched.extend(_with_constraints(record, constraints) for record in members)
            stats["failed"] += chunk_records - len(enriched)

            if enriched and not dry_run:
                written = raw_repo.update_many(enriched)
                if written != len(enriched):
                    # An id that is no longer on file: the raw store was rewritten
                    # under us. Count it as failed rather than silently claiming it.
                    logger.warning(
                        "Checkpoint wrote %d/%d records — %d raw ids vanished",
                        written,
                        len(enriched),
                        len(enriched) - written,
                    )
                    stats["failed"] += len(enriched) - written
                stats["processed"] += written
            else:
                stats["processed"] += len(enriched)

            logger.info(
                "Checkpoint: %d/%d enriched (%d failed)",
                stats["processed"],
                stats["pending"],
                stats["failed"],
            )
            if on_chunk is not None:
                on_chunk(dict(stats))
    finally:
        executor.shutdown(wait=False)

    return stats
