from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Sequence

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.persistence.repositories.raw_deals import RawDealJsonRepository
from lessley_deals.persistence.repositories.raw_stores import RawStoreJsonRepository
from lessley_deals.scraping.orchestrator import ScraperOrchestrator
from lessley_deals.scraping.run import SourceRunResult

logger = logging.getLogger(__name__)


@dataclass
class ScrapeOutcome:
    """Everything downstream stages need to know about a scrape.

    ``new_deals`` only contains records the fingerprint dedup let through — that
    is what the expensive normalize/match/enrich path should process.  The
    versioning layer, however, needs to know about *every* record that was
    scraped, including the byte-identical ones that were filtered out: a deal
    absent from this set is a deal the source stopped offering, and that is what
    drives expiry.  ``seen_fingerprints`` carries exactly that.
    """

    new_stores: list[RawStore] = field(default_factory=list)
    new_deals: list[RawScrapedRecord] = field(default_factory=list)
    seen_fingerprints: dict[str, set[str]] = field(default_factory=dict)
    scraped_counts: dict[str, int] = field(default_factory=dict)
    ok_sources: set[str] = field(default_factory=set)
    failed_sources: dict[str, list[str]] = field(default_factory=dict)

    @property
    def total_scraped(self) -> int:
        return sum(self.scraped_counts.values())

    def fingerprint_by_raw_id(self) -> dict[str, str]:
        """``raw_id -> fingerprint`` for the records that made it through."""
        return {record.id: record.fingerprint for record in self.new_deals}


class ScrapeStage:
    """Stage 1: Run scrapers and persist raw data."""

    def __init__(
        self,
        orchestrator: ScraperOrchestrator,
        raw_deal_repo: RawDealJsonRepository,
        raw_store_repo: RawStoreJsonRepository,
    ) -> None:
        self._orchestrator = orchestrator
        self._deal_repo = raw_deal_repo
        self._store_repo = raw_store_repo

    async def run(
        self, source_ids: Sequence[str] | None = None
    ) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        """Run scraping and persist raw data. Returns (new_stores, new_deals)."""
        outcome = await self.run_detailed(source_ids)
        return outcome.new_stores, outcome.new_deals

    async def run_detailed(self, source_ids: Sequence[str] | None = None) -> ScrapeOutcome:
        """Same as :meth:`run` but returns the full :class:`ScrapeOutcome`."""
        if source_ids:
            results: list[SourceRunResult] = []
            for sid in source_ids:
                results.append(await self._orchestrator.run_source(sid))
        else:
            scrape_run = await self._orchestrator.run_all()
            results = scrape_run.results

        outcome = ScrapeOutcome()
        loop = asyncio.get_event_loop()

        for result in results:
            outcome.scraped_counts[result.source_id] = len(result.deals)
            if result.ok:
                outcome.ok_sources.add(result.source_id)
            else:
                outcome.failed_sources[result.source_id] = list(result.errors)

            # Every scraped record counts as "seen", even the ones dedup drops.
            outcome.seen_fingerprints.setdefault(result.source_id, set()).update(
                d.fingerprint for d in result.deals
            )

            # Dedup stores by fingerprint
            new_stores = [
                s for s in result.stores
                if not await loop.run_in_executor(None, self._store_repo.exists_by_fingerprint, s.fingerprint)
            ]
            if new_stores:
                await loop.run_in_executor(None, self._store_repo.save_many, new_stores)
                outcome.new_stores.extend(new_stores)

            # Dedup deals by fingerprint
            new_deals = [
                d for d in result.deals
                if not await loop.run_in_executor(None, self._deal_repo.exists_by_fingerprint, d.fingerprint)
            ]
            if new_deals:
                await loop.run_in_executor(None, self._deal_repo.save_many, new_deals)
                outcome.new_deals.extend(new_deals)

            for err in result.errors:
                logger.error("Scrape error from %s: %s", result.source_id, err)

        logger.info(
            "Scrape stage: %d scraped, %d new stores, %d new deals, %d failed source(s)",
            outcome.total_scraped, len(outcome.new_stores), len(outcome.new_deals),
            len(outcome.failed_sources),
        )
        return outcome
