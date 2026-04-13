from __future__ import annotations

import asyncio
import logging
from typing import Sequence

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.persistence.repositories.raw_deals import RawDealJsonRepository
from lessley_deals.persistence.repositories.raw_stores import RawStoreJsonRepository
from lessley_deals.scraping.orchestrator import ScraperOrchestrator
from lessley_deals.scraping.run import ScrapeRun

logger = logging.getLogger(__name__)


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

    async def run(self, source_ids: Sequence[str] | None = None) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        """Run scraping and persist raw data. Returns (new_stores, new_deals)."""
        if source_ids:
            results = []
            for sid in source_ids:
                result = await self._orchestrator.run_source(sid)
                results.append(result)
        else:
            scrape_run = await self._orchestrator.run_all()
            results = scrape_run.results

        all_stores: list[RawStore] = []
        all_deals: list[RawScrapedRecord] = []

        loop = asyncio.get_event_loop()

        for result in results:
            # Dedup stores by fingerprint
            new_stores = [
                s for s in result.stores
                if not await loop.run_in_executor(None, self._store_repo.exists_by_fingerprint, s.fingerprint)
            ]
            if new_stores:
                await loop.run_in_executor(None, self._store_repo.save_many, new_stores)
                all_stores.extend(new_stores)

            # Dedup deals by fingerprint
            new_deals = [
                d for d in result.deals
                if not await loop.run_in_executor(None, self._deal_repo.exists_by_fingerprint, d.fingerprint)
            ]
            if new_deals:
                await loop.run_in_executor(None, self._deal_repo.save_many, new_deals)
                all_deals.extend(new_deals)

            for err in result.errors:
                logger.error("Scrape error from %s: %s", result.source_id, err)

        logger.info(
            "Scrape stage: %d new stores, %d new deals",
            len(all_stores), len(all_deals),
        )
        return all_stores, all_deals
