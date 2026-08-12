from __future__ import annotations

import logging
from typing import Any, Callable, Sequence

from lessley_deals.domain.models import NormalizedRecord, PipelineRecord
from lessley_deals.domain.protocols import AliasRepository, CanonicalStoreRepository
from lessley_deals.matching.index import AliasIndex
from lessley_deals.pipeline.constraints_stage import ConstraintsStage
from lessley_deals.pipeline.context import PipelineContext
from lessley_deals.pipeline.ingest_stage import IngestStage, IngestSummary
from lessley_deals.pipeline.match_stage import MatchStage
from lessley_deals.pipeline.normalize_stage import NormalizeStage
from lessley_deals.pipeline.persist_stage import PersistStage
from lessley_deals.pipeline.report import PipelineReport
from lessley_deals.pipeline.scrape_stage import ScrapeStage

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Top-level entry point: scrape -> normalize -> match -> persist -> ingest."""

    def __init__(
        self,
        scrape_stage: ScrapeStage,
        normalize_stage: NormalizeStage,
        match_stage: MatchStage,
        persist_stage: PersistStage,
        store_repo: CanonicalStoreRepository,
        alias_repo: AliasRepository,
        constraints_stage: ConstraintsStage | None = None,
        ingest_stage: IngestStage | None = None,
    ) -> None:
        self._scrape = scrape_stage
        self._normalize = normalize_stage
        self._match = match_stage
        self._persist = persist_stage
        self._store_repo = store_repo
        self._alias_repo = alias_repo
        self._constraints = constraints_stage
        self._ingest = ingest_stage

    async def run(
        self,
        source_ids: Sequence[str] | None = None,
        run_id: str | None = None,
    ) -> PipelineReport:
        ctx = PipelineContext()

        # Stage 1: Scrape
        logger.info("Starting scrape stage...")
        scrape = await self._scrape.run_detailed(source_ids)
        deals = scrape.new_deals

        # Add raw deals to context
        pipeline_records: list[PipelineRecord] = []
        for deal in deals:
            prec = ctx.add_raw(deal)
            pipeline_records.append(prec)

        if not deals:
            # Still ingest: a run that scraped known-unchanged records must
            # refresh last_seen_at, and a source that dropped a deal must be
            # able to expire it even when nothing new came in.
            if self._ingest is not None:
                empty_run = await self._ingest.run([], scrape, run_id=run_id)
                ctx.finish()
                return PipelineReport.from_context(ctx, scrape=scrape, ingest=empty_run)
            logger.info("No new deals scraped, pipeline complete.")
            ctx.finish()
            return PipelineReport.from_context(ctx, scrape=scrape)

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

        # Stage 3b: Constraints (optional) — parse each deal's terms into a
        # structured constraints block, for every source uniformly.
        constraints_map: dict[str, dict[str, Any]] = {}
        if self._constraints is not None:
            logger.info("Starting constraints stage...")
            constraints_map = await self._constraints.run(deals)

        # Stage 4: Persist
        logger.info("Starting persist stage...")
        built_deals = await self._persist.run(
            pipeline_records, normalized_map, verdict_map, constraints_map
        )

        # Stage 5: Version & ingest (optional)
        summary: IngestSummary | None = None
        if self._ingest is not None:
            logger.info("Starting ingestion stage...")
            summary = await self._ingest.run(built_deals, scrape, run_id=run_id)

        # No publish stage: the Gateway and Personalization read `deals`/`stores`/`clubs`
        # directly now, so what this run just persisted is already what they serve.

        ctx.finish()
        report = PipelineReport.from_context(ctx, scrape=scrape, ingest=summary)
        logger.info(report.summary())
        return report
