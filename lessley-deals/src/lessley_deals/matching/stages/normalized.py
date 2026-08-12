from __future__ import annotations

from lessley_deals.domain.models import MatchCandidate, NormalizedRecord
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.similarity import jaro_winkler, token_containment, token_jaccard
from lessley_deals.matching.stages.base import MatchStage


class NormalizedFuzzy(MatchStage):
    """Stage 5: Weighted blend of Jaro-Winkler, token Jaccard, and token containment.

    Score = jw_weight × JW(norm, norm)
          + token_weight × Jaccard(tokens, tokens)
          + containment_weight × containment(tokens, tokens)

    The containment term uses intersection / min(|A|, |B|) so that extra tokens
    in a longer input string do not dilute the score the way Jaccard alone would.
    This makes the stage a useful fallback for cases where ContainmentMatch's
    strict token-subset test fails (e.g. minor spelling differences in tokens).
    """

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
            tc = token_containment(input_tokens, alias.alias_forms.tokens)
            score = (
                config.normalized_jw_weight * jw
                + config.normalized_token_weight * tj
                + config.normalized_containment_weight * tc
            )
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
