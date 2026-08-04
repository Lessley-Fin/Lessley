"""The scraper worker process.

    python -m lessley_deals.scheduling.service       # or: deals serve

Long-running container that owns the whole loop: schedule → scrape → normalize →
match → version → persist, for every registered source, concurrently and
independently.  Stateless apart from the database, so it scales horizontally —
the Mongo lease lock keeps replicas from scraping the same source twice.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Sequence

from lessley_deals.pipeline.factory import PipelineBundle, PipelineConfig, build_pipeline
from lessley_deals.scheduling.config import load_schedules
from lessley_deals.scheduling.journal import (
    JsonRunJournal,
    MongoRunJournal,
    NullRunJournal,
    RunJournal,
)
from lessley_deals.scheduling.locks import MongoLeaseLock, NullRunLock, RunLock
from lessley_deals.scheduling.runner import JobResult, SourceRunner
from lessley_deals.scheduling.schedule import ScheduleSpec
from lessley_deals.scheduling.scheduler import SchedulerService

logger = logging.getLogger(__name__)


class PipelineSourceJob:
    """Adapts the pipeline to the :class:`SourceJob` protocol.

    One instance serves every source; the pipeline itself is stateless per run,
    and per-source isolation comes from calling it with a single source id.
    """

    def __init__(self, bundle: PipelineBundle) -> None:
        self._bundle = bundle

    async def __call__(self, source_id: str, run_id: str) -> JobResult:
        report = await self._bundle.pipeline.run([source_id], run_id=run_id)
        failed = source_id in report.failed_sources
        return JobResult(
            ok=not failed,
            scraped_records=report.scraped_records,
            deals_new=report.deals_new,
            deals_updated=report.deals_updated,
            deals_unchanged=report.deals_unchanged,
            deals_expired=report.deals_expired,
            deals_reactivated=report.deals_reactivated,
            sent_to_review=report.sent_to_review,
            errors=[f"{source_id} scrape failed"] if failed else [],
            metadata={
                "auto_matched": report.auto_matched,
                "no_match": report.no_match,
                "duration_seconds": round(report.duration_seconds, 2),
            },
        )


def setup_logging() -> None:
    """JSON-ish single-line logs — Loki-friendly, same shape as the other services."""
    level = os.environ.get("DEALS_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    # These are chatty at DEBUG and tell us nothing we want.
    for noisy in ("httpx", "httpcore", "urllib3", "selenium", "pymongo"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def build_journal(bundle: PipelineBundle) -> RunJournal:
    if os.environ.get("DEALS_RUN_JOURNAL", "on").lower() in ("off", "0", "false"):
        return NullRunJournal()
    if bundle.database is not None:
        retention = int(os.environ.get("DEALS_RUN_RETENTION_DAYS", "90"))
        return MongoRunJournal(bundle.database, retention_days=retention)
    data_dir = os.environ.get("DEALS_DATA_DIR", "data")
    from pathlib import Path

    return JsonRunJournal(Path(data_dir) / "scrape_runs.json")


def build_lock(bundle: PipelineBundle) -> RunLock:
    """Mongo lease lock when a database is configured, otherwise a no-op."""
    if bundle.database is not None:
        return MongoLeaseLock(bundle.database)
    logger.warning("No database configured — running without a cross-process run lock")
    return NullRunLock()


def build_scheduler(bundle: PipelineBundle, specs: Sequence[ScheduleSpec]) -> SchedulerService:
    runner = SourceRunner(
        job=PipelineSourceJob(bundle),
        journal=build_journal(bundle),
        lock=build_lock(bundle),
    )
    return SchedulerService(
        specs=specs,
        runner=runner,
        max_concurrency=int(os.environ.get("DEALS_MAX_CONCURRENCY", "3")),
        shutdown_grace_seconds=float(os.environ.get("DEALS_SHUTDOWN_GRACE", "30")),
    )


async def run_service() -> int:
    setup_logging()
    bundle = build_pipeline(PipelineConfig())
    specs = load_schedules(bundle.source_ids)

    if not any(spec.enabled for spec in specs):
        logger.error("No enabled sources — check data/seed/schedules.json / DEALS_SCHEDULE_* vars")
        return 1

    scheduler = build_scheduler(bundle, specs)

    # SIGTERM is what Docker/Kubernetes send on stop; SIGINT is Ctrl-C.
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, scheduler.request_shutdown)
        except NotImplementedError:  # Windows
            signal.signal(sig, lambda *_: scheduler.request_shutdown())

    logger.info("Scraper worker up (pid=%s)", os.getpid())
    await scheduler.start()
    logger.info("Scraper worker exited cleanly")
    return 0


def main() -> None:
    try:
        raise SystemExit(asyncio.run(run_service()))
    except KeyboardInterrupt:
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
