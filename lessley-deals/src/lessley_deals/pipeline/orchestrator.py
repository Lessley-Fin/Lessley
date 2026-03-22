from __future__ import annotations

import logging
from typing import Sequence

from lessley_deals.domain.models import NormalizedRecord, PipelineRecord
from lessley_deals.matching.index import AliasIndex
from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository
from lessley_deals.pipeline.context import PipelineContext
from lessley_deals.pipeline.match_stage import MatchStage
from lessley_deals.pipeline.normalize_stage import NormalizeStage
from lessley_deals.pipeline.persist_stage import PersistStage
from lessley_deals.pipeline.report import PipelineReport
from lessley_deals.pipeline.scrape_stage import ScrapeStage

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Top-level entry point: scrape -> normalize -> match -> persist."""

    def __init__(
        self,
        scrape_stage: ScrapeStage,
        normalize_stage: NormalizeStage,
        match_stage: MatchStage,
        persist_stage: PersistStage,
        store_repo: CanonicalStoreJsonRepository,
        alias_repo: AliasJsonRepository,
    ) -> None:
        self._scrape = scrape_stage
        self._normalize = normalize_stage
        self._match = match_stage
        self._persist = persist_stage
        self._store_repo = store_repo
        self._alias_repo = alias_repo

    async def run(self, source_ids: Sequence[str] | None = None) -> PipelineReport:
        ctx = PipelineContext()

        # Stage 1: Scrape
        logger.info("Starting scrape stage...")
        _stores, deals = await self._scrape.run(source_ids)

        # Add raw deals to context
        pipeline_records: list[PipelineRecord] = []
        for deal in deals:
            prec = ctx.add_raw(deal)
            pipeline_records.append(prec)

        if not deals:
            logger.info("No new deals scraped, pipeline complete.")
            ctx.finish()
            return PipelineReport.from_context(ctx)

        # Stage 2: Normalize
        logger.info("Starting normalize stage...")
        normalized = self._normalize.run(deals)
        normalized_map: dict[str, NormalizedRecord] = {n.raw_id: n for n in normalized}

        # Stage 3: Match
        logger.info("Starting match stage...")
        stores = self._store_repo.get_all()
        aliases = self._alias_repo.get_all()
        index = AliasIndex(aliases=aliases, stores=stores)
        verdicts = self._match.run(normalized, index)
        verdict_map = {v.record_id: v for v in verdicts}

        # Stage 4: Persist
        logger.info("Starting persist stage...")
        self._persist.run(pipeline_records, normalized_map, verdict_map)

        ctx.finish()
        report = PipelineReport.from_context(ctx)
        logger.info(report.summary())
        return report
