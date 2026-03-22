from __future__ import annotations

import logging

from lessley_deals.domain.models import NormalizedRecord, RawScrapedRecord
from lessley_deals.normalization.pipeline import NormalizationPipeline

logger = logging.getLogger(__name__)


class NormalizeStage:
    """Stage 2: Normalize raw deals into structured records."""

    def __init__(self, pipeline: NormalizationPipeline) -> None:
        self._pipeline = pipeline

    def run(self, deals: list[RawScrapedRecord]) -> list[NormalizedRecord]:
        results: list[NormalizedRecord] = []
        for deal in deals:
            try:
                normalized = self._pipeline.normalize(deal)
                results.append(normalized)
            except Exception:
                logger.exception("Failed to normalize record %s", deal.id)
        logger.info("Normalize stage: %d/%d succeeded", len(results), len(deals))
        return results
