from __future__ import annotations

from lessley_deals.domain.enums import MatchDecision
from lessley_deals.domain.models import (
    Explanation,
    MatchCandidate,
    MatchVerdict,
    NormalizedRecord,
)
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.stages.base import MatchStage
from lessley_deals.matching.stages.compact import CompactForm
from lessley_deals.matching.stages.domain import DomainMatch
from lessley_deals.matching.stages.exact_alias import ExactAlias
from lessley_deals.matching.stages.normalized import NormalizedFuzzy
from lessley_deals.matching.stages.token import TokenOverlap

_TOKEN_ONLY_STAGES = frozenset({"token_overlap"})


def _default_stages() -> list[MatchStage]:
    return [ExactAlias(), CompactForm(), NormalizedFuzzy(), DomainMatch(), TokenOverlap()]


class MatchPipeline:
    def __init__(
        self,
        config: MatchConfig | None = None,
        stages: list[MatchStage] | None = None,
    ) -> None:
        self.config = config or MatchConfig()
        self.stages = stages if stages is not None else _default_stages()

    def match(self, normalized: NormalizedRecord, index: AliasIndex) -> MatchVerdict:
        candidates: list[MatchCandidate] = []
        stages_run: list[str] = []
        stage_matched: str | None = None

        for stage in self.stages:
            stages_run.append(stage.name)
            candidate = stage.evaluate(normalized, index, self.config)
            if candidate is not None:
                candidates.append(candidate)
                # Short-circuit on auto-match (but not for token-only stages)
                if (
                    candidate.confidence >= self.config.auto_match_threshold
                    and candidate.stage not in _TOKEN_ONLY_STAGES
                ):
                    stage_matched = stage.name
                    break

        # Determine best candidate
        best: MatchCandidate | None = None
        if candidates:
            best = max(candidates, key=lambda c: c.confidence)
            if stage_matched is None:
                stage_matched = best.stage

        # Decide
        if best is None:
            decision = MatchDecision.NO_MATCH
            reason = "no candidates above review threshold"
        elif (
            best.confidence >= self.config.auto_match_threshold
            and best.stage not in _TOKEN_ONLY_STAGES
        ):
            decision = MatchDecision.AUTO_MATCH
            reason = (
                f"auto-matched via {best.stage} "
                f"with confidence {best.confidence:.3f}"
            )
        elif best.confidence >= self.config.review_threshold:
            decision = MatchDecision.REVIEW
            reason = (
                f"review needed via {best.stage} "
                f"with confidence {best.confidence:.3f}"
            )
        else:
            decision = MatchDecision.NO_MATCH
            reason = "best confidence below review threshold"

        explanation = Explanation(
            stages_run=tuple(stages_run),
            stage_matched=stage_matched,
            reason=reason,
        )

        return MatchVerdict(
            record_id=normalized.raw_id,
            input_name=normalized.store_name_forms.normalized,
            decision=decision,
            candidates=tuple(candidates),
            explanation=explanation,
            best=best,
        )
