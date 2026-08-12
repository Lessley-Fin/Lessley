from __future__ import annotations

from lessley_deals.domain.models import MatchCandidate, NormalizedRecord
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.stages.base import MatchStage


class ExactAlias(MatchStage):
    """Stage 1: O(1) dict lookup on compact form."""

    @property
    def name(self) -> str:
        return "exact_alias"

    def evaluate(
        self,
        normalized: NormalizedRecord,
        index: AliasIndex,
        config: MatchConfig,
    ) -> MatchCandidate | None:
        compact = normalized.store_name_forms.compact
        result = index.exact_lookup(compact)
        if result is None:
            return None

        store_id, alias_text = result
        store = index.get_store(store_id)
        store_name = store.name if store else alias_text

        return MatchCandidate(
            store_id=store_id,
            store_name=store_name,
            confidence=1.0,
            stage=self.name,
            matched_alias=alias_text,
        )
