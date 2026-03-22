from __future__ import annotations

from lessley_deals.domain.models import MatchCandidate, NormalizedRecord
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.stages.base import MatchStage


class DomainMatch(MatchStage):
    """Stage 4: Match by domain with fixed confidence (never auto-matches)."""

    @property
    def name(self) -> str:
        return "domain"

    def evaluate(
        self,
        normalized: NormalizedRecord,
        index: AliasIndex,
        config: MatchConfig,
    ) -> MatchCandidate | None:
        if not normalized.domain:
            return None

        store_id = index.domain_to_store.get(normalized.domain)
        if store_id is None:
            return None

        store = index.get_store(store_id)
        if store is None:
            return None

        return MatchCandidate(
            store_id=store_id,
            store_name=store.name,
            confidence=config.domain_fixed_confidence,
            stage=self.name,
        )
