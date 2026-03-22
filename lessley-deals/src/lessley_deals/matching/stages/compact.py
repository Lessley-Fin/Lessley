from __future__ import annotations

from lessley_deals.domain.models import MatchCandidate, NormalizedRecord
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.similarity import jaro_winkler
from lessley_deals.matching.stages.base import MatchStage


class CompactForm(MatchStage):
    """Stage 2: Compare compact forms using Jaro-Winkler with discount."""

    @property
    def name(self) -> str:
        return "compact_form"

    def evaluate(
        self,
        normalized: NormalizedRecord,
        index: AliasIndex,
        config: MatchConfig,
    ) -> MatchCandidate | None:
        input_compact = normalized.store_name_forms.compact
        best_score = 0.0
        best_alias_text: str | None = None
        best_store_id: str | None = None
        best_store_name: str | None = None

        for alias, store in index.all_entries:
            raw_score = jaro_winkler(input_compact, alias.alias_forms.compact)
            score = raw_score * config.compact_discount
            if score > best_score:
                best_score = score
                best_alias_text = alias.alias
                best_store_id = store.id
                best_store_name = store.name

        if best_store_id is None or best_score < config.review_threshold:
            return None

        return MatchCandidate(
            store_id=best_store_id,
            store_name=best_store_name,  # type: ignore[arg-type]
            confidence=best_score,
            stage=self.name,
            matched_alias=best_alias_text,
        )
