from __future__ import annotations

from lessley_deals.domain.models import MatchCandidate, NormalizedRecord
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.similarity import jaro_winkler, token_jaccard
from lessley_deals.matching.stages.base import MatchStage


class NormalizedFuzzy(MatchStage):
    """Stage 3: Weighted combination of Jaro-Winkler on normalized + token Jaccard."""

    @property
    def name(self) -> str:
        return "normalized_fuzzy"

    def evaluate(
        self,
        normalized: NormalizedRecord,
        index: AliasIndex,
        config: MatchConfig,
    ) -> MatchCandidate | None:
        input_norm = normalized.store_name_forms.normalized
        input_tokens = normalized.store_name_forms.tokens

        best_score = 0.0
        best_alias_text: str | None = None
        best_store_id: str | None = None
        best_store_name: str | None = None

        for alias, store in index.all_entries:
            jw = jaro_winkler(input_norm, alias.alias_forms.normalized)
            tj = token_jaccard(input_tokens, alias.alias_forms.tokens)
            score = config.normalized_jw_weight * jw + config.normalized_token_weight * tj
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
