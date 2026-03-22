from __future__ import annotations

import logging

from lessley_deals.domain.enums import MatchDecision
from lessley_deals.domain.models import MatchVerdict, NormalizedRecord
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.pipeline import MatchPipeline

logger = logging.getLogger(__name__)


class MatchStage:
    """Stage 3: Match normalized records to canonical stores."""

    def __init__(self, pipeline: MatchPipeline) -> None:
        self._pipeline = pipeline

    def run(
        self,
        records: list[NormalizedRecord],
        index: AliasIndex,
    ) -> list[MatchVerdict]:
        verdicts: list[MatchVerdict] = []
        for record in records:
            try:
                verdict = self._pipeline.match(record, index)
                verdicts.append(verdict)
            except Exception:
                logger.exception("Failed to match record %s", record.raw_id)
        auto = sum(1 for v in verdicts if v.decision == MatchDecision.AUTO_MATCH)
        review = sum(1 for v in verdicts if v.decision == MatchDecision.REVIEW)
        no_match = sum(1 for v in verdicts if v.decision == MatchDecision.NO_MATCH)
        logger.info(
            "Match stage: %d auto, %d review, %d no-match",
            auto, review, no_match,
        )
        return verdicts
