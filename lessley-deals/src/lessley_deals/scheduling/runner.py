"""SourceRunner — everything that wraps one execution of one source.

Responsibilities, in order:

1. take the cross-process lease (skip the run if another replica holds it)
2. journal the attempt as RUNNING
3. execute the job under a hard timeout
4. on failure, retry with exponential backoff + jitter, up to ``max_attempts``
5. journal the outcome (SUCCESS / PARTIAL / FAILED / SKIPPED) with counters
6. release the lease — always, including on cancellation

The actual work is injected as a :class:`SourceJob`, so the runner has no idea
what a scraper is and can be unit-tested with a two-line fake.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from lessley_deals.domain.enums import RunStatus
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scheduling.journal import RunJournal, RunRecord
from lessley_deals.scheduling.locks import RunLock
from lessley_deals.scheduling.schedule import ScheduleSpec

logger = logging.getLogger(__name__)


@dataclass
class JobResult:
    """What a source job reports back to the runner."""

    ok: bool
    scraped_records: int = 0
    deals_new: int = 0
    deals_updated: int = 0
    deals_unchanged: int = 0
    deals_expired: int = 0
    deals_reactivated: int = 0
    sent_to_review: int = 0
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SourceJob(Protocol):
    """The unit of work the scheduler executes for a source."""

    async def __call__(self, source_id: str, run_id: str) -> JobResult: ...


class SourceRunner:
    def __init__(
        self,
        job: SourceJob,
        journal: RunJournal,
        lock: RunLock,
        lock_ttl_multiplier: float = 2.0,
        rng: random.Random | None = None,
    ) -> None:
        self._job = job
        self._journal = journal
        self._lock = lock
        self._lock_ttl_multiplier = lock_ttl_multiplier
        self._rng = rng or random.Random()

    async def run(self, spec: ScheduleSpec, trigger: str = "schedule") -> RunRecord:
        """Run one source to completion (including retries) and journal it."""
        run_id = generate_id()
        lock_key = f"scrape:{spec.source_id}"
        # The lease must outlive the whole retry sequence, otherwise another
        # replica could start the same source while we are backing off.
        lock_ttl = self._total_budget_seconds(spec) * self._lock_ttl_multiplier

        token = await asyncio.to_thread(self._lock.acquire, lock_key, lock_ttl)
        if token is None:
            record = RunRecord(
                run_id=run_id,
                source_id=spec.source_id,
                trigger=trigger,
                status=RunStatus.SKIPPED,
                started_at=self._now(),
                finished_at=self._now(),
                error="another worker holds the run lock",
            )
            logger.info("Skipping %s — lock held by another worker", spec.source_id)
            await self._journal_safely(record)
            return record

        try:
            return await self._run_with_retries(spec, trigger, run_id, lock_key, token)
        finally:
            await asyncio.to_thread(self._lock.release, lock_key, token)

    # ------------------------------------------------------------------ #
    # internals                                                          #
    # ------------------------------------------------------------------ #

    async def _run_with_retries(
        self,
        spec: ScheduleSpec,
        trigger: str,
        run_id: str,
        lock_key: str,
        token: str,
    ) -> RunRecord:
        policy = spec.retry
        last_record: RunRecord | None = None

        for attempt in range(1, policy.max_attempts + 1):
            record = RunRecord(
                run_id=run_id,
                source_id=spec.source_id,
                trigger=trigger,
                status=RunStatus.RUNNING,
                started_at=self._now(),
                attempt=attempt,
                max_attempts=policy.max_attempts,
            )
            await self._journal_safely(record)
            logger.info(
                "Running source %s (run=%s attempt=%d/%d)",
                spec.source_id, run_id, attempt, policy.max_attempts,
            )

            try:
                result = await asyncio.wait_for(
                    self._job(spec.source_id, run_id), timeout=spec.timeout_seconds
                )
                self._apply_result(record, result)
                record.status = RunStatus.SUCCESS if result.ok else RunStatus.PARTIAL
                record.error = "; ".join(result.errors) or None
            except TimeoutError:
                record.status = RunStatus.FAILED
                record.error = f"timed out after {spec.timeout_seconds:.0f}s"
                logger.error("Source %s timed out after %.0fs", spec.source_id, spec.timeout_seconds)
            except asyncio.CancelledError:
                # Graceful shutdown — journal it, then let the cancellation
                # propagate so the scheduler can actually stop.
                record.status = RunStatus.FAILED
                record.error = "cancelled (shutdown)"
                record.finished_at = self._now()
                await self._journal_safely(record)
                raise
            except Exception as exc:
                record.status = RunStatus.FAILED
                record.error = f"{type(exc).__name__}: {exc}"
                logger.exception("Source %s failed on attempt %d", spec.source_id, attempt)

            record.finished_at = self._now()
            await self._journal_safely(record)
            last_record = record

            if record.status in (RunStatus.SUCCESS, RunStatus.PARTIAL):
                logger.info(
                    "Source %s finished in %.1fs — new=%d updated=%d unchanged=%d expired=%d",
                    spec.source_id, record.duration_seconds, record.deals_new,
                    record.deals_updated, record.deals_unchanged, record.deals_expired,
                )
                return record

            if attempt < policy.max_attempts:
                delay = policy.delay_for(attempt, self._rng)
                logger.warning(
                    "Source %s failed (%s) — retrying in %.1fs",
                    spec.source_id, record.error, delay,
                )
                # Keep the lease alive while we sleep off the backoff.
                await asyncio.to_thread(
                    self._lock.renew, lock_key, token, delay + spec.timeout_seconds
                )
                await asyncio.sleep(delay)

        assert last_record is not None  # loop runs at least once
        logger.error(
            "Source %s exhausted %d attempts: %s",
            spec.source_id, policy.max_attempts, last_record.error,
        )
        return last_record

    @staticmethod
    def _apply_result(record: RunRecord, result: JobResult) -> None:
        record.scraped_records = result.scraped_records
        record.deals_new = result.deals_new
        record.deals_updated = result.deals_updated
        record.deals_unchanged = result.deals_unchanged
        record.deals_expired = result.deals_expired
        record.deals_reactivated = result.deals_reactivated
        record.sent_to_review = result.sent_to_review
        record.metadata = result.metadata

    @staticmethod
    def _total_budget_seconds(spec: ScheduleSpec) -> float:
        """Worst-case wall clock for a full retry sequence."""
        policy = spec.retry
        backoff = sum(
            min(policy.base_delay_seconds * policy.multiplier**i, policy.max_delay_seconds)
            for i in range(max(0, policy.max_attempts - 1))
        )
        return spec.timeout_seconds * policy.max_attempts + backoff

    async def _journal_safely(self, record: RunRecord) -> None:
        """A broken journal must never take down a working scraper."""
        try:
            await asyncio.to_thread(self._journal.record, record)
        except Exception as exc:
            logger.warning("Failed to journal run %s: %s", record.run_id, exc)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
