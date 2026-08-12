from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.base import BaseSourceAdapter
from lessley_deals.scraping.run import ScrapeRun, SourceRunResult

logger = logging.getLogger(__name__)


class ScraperOrchestrator:
    """Runs multiple :class:`BaseSourceAdapter` instances concurrently."""

    def __init__(self, adapters: list[BaseSourceAdapter] | None = None) -> None:
        self._adapters: dict[str, BaseSourceAdapter] = {}
        if adapters:
            self._adapters = {a.source_id: a for a in adapters}

    @classmethod
    def from_registry(cls, registry: object) -> ScraperOrchestrator:
        """Build from a SourceRegistry."""
        from lessley_deals.scraping.registry import SourceRegistry
        assert isinstance(registry, SourceRegistry)
        adapters = [registry.get(sid) for sid in registry.list_all()]
        return cls(adapters)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_all(self) -> ScrapeRun:
        """Execute every registered adapter concurrently and return a :class:`ScrapeRun`."""
        started_at = datetime.now(timezone.utc)
        logger.info("Starting scrape run across %d source(s)", len(self._adapters))

        tasks = [self.run_source(sid) for sid in self._adapters]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        finished_at = datetime.now(timezone.utc)
        run = ScrapeRun(
            run_id=generate_id(),
            started_at=started_at,
            finished_at=finished_at,
            results=list(results),
        )
        logger.info(
            "Scrape run %s finished – %d stores, %d deals, %d errors",
            run.run_id,
            run.total_stores,
            run.total_deals,
            run.total_errors,
        )
        return run

    async def run_source(self, source_id: str) -> SourceRunResult:
        """Run a single source adapter by its *source_id*."""
        adapter = self._adapters.get(source_id)
        if adapter is None:
            return SourceRunResult(
                source_id=source_id,
                stores=[],
                deals=[],
                errors=[f"Unknown source_id: {source_id}"],
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
            )

        started_at = datetime.now(timezone.utc)
        try:
            logger.info("Scraping source %s …", source_id)
            stores, deals = await adapter.scrape()
            finished_at = datetime.now(timezone.utc)
            logger.info(
                "Source %s done – %d stores, %d deals",
                source_id,
                len(stores),
                len(deals),
            )
            return SourceRunResult(
                source_id=source_id,
                stores=stores,
                deals=deals,
                errors=[],
                started_at=started_at,
                finished_at=finished_at,
            )
        except Exception as exc:
            finished_at = datetime.now(timezone.utc)
            logger.exception("Source %s failed: %s", source_id, exc)
            return SourceRunResult(
                source_id=source_id,
                stores=[],
                deals=[],
                errors=[str(exc)],
                started_at=started_at,
                finished_at=finished_at,
            )
