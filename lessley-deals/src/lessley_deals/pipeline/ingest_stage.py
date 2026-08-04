"""Stage 5: hand the matched deals to the versioning layer.

Thin by design — all the decision logic lives in
:mod:`lessley_deals.versioning.ingestion`.  This stage only translates the
pipeline's vocabulary (``ScrapeOutcome``, ``Deal``) into the ingestion's
(per-source batches + which sources were healthy).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Sequence

from lessley_deals.domain.models import Deal
from lessley_deals.pipeline.scrape_stage import ScrapeOutcome
from lessley_deals.versioning.ingestion import IngestionReport, IngestionService

logger = logging.getLogger(__name__)


@dataclass
class IngestSummary:
    """Aggregate of the per-source ingestion reports."""

    reports: list[IngestionReport] = field(default_factory=list)

    @property
    def new(self) -> int:
        return sum(r.new for r in self.reports)

    @property
    def updated(self) -> int:
        return sum(r.updated for r in self.reports)

    @property
    def unchanged(self) -> int:
        return sum(r.unchanged for r in self.reports)

    @property
    def expired(self) -> int:
        return sum(r.expired for r in self.reports)

    @property
    def reactivated(self) -> int:
        return sum(r.reactivated for r in self.reports)

    def summary(self) -> str:
        return (
            f"Ingestion: new={self.new} updated={self.updated} unchanged={self.unchanged} "
            f"expired={self.expired} reactivated={self.reactivated}"
        )


class IngestStage:
    def __init__(self, service: IngestionService) -> None:
        self._service = service

    async def run(
        self,
        deals: Sequence[Deal],
        scrape: ScrapeOutcome,
        run_id: str | None = None,
    ) -> IngestSummary:
        reports = await self._service.ingest_grouped(
            deals,
            run_id=run_id,
            # Only sources that scraped cleanly are allowed to expire anything.
            ok_sources=scrape.ok_sources,
            seen_fingerprints={k: v for k, v in scrape.seen_fingerprints.items()},
            raw_fingerprints=scrape.fingerprint_by_raw_id(),
        )
        summary = IngestSummary(reports=reports)
        logger.info(summary.summary())
        return summary
