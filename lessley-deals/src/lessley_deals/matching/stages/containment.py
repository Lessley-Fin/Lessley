from __future__ import annotations

from lessley_deals.domain.models import MatchCandidate, NormalizedRecord
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.stages.base import MatchStage


class ContainmentMatch(MatchStage):
    """Stage 4: Canonical-tokens-in-input containment check.

    Fires when every token of a canonical alias is present in the input tokens
    and the canonical alias is not so short that it would produce false
    positives.  Produces a high-confidence score that scales with the ratio
    ``canonical_token_count / input_token_count``, so a canonical alias that
    covers a large fraction of the input scores higher than one that covers
    only a small fraction.

    Example: input "רמי לוי שיווק השקמה" (4 tokens) vs canonical alias
    "רמי לוי" (2 tokens) → containment=1.0, ratio=0.5,
    score = 0.88 + 0.12×0.5 = 0.94 → AUTO_MATCH.

    Guards against false positives:
    - Canonical must have ≥ 2 tokens (single-word aliases are too ambiguous).
    - Input must have ≥ 2 tokens.
    - ``canonical_token_count / input_token_count`` must meet
      ``config.containment_min_token_ratio`` (default 0.35), preventing a
      2-token canonical from matching a 10-token input spuriously.
    """

    @property
    def name(self) -> str:
        return "containment_match"

    def evaluate(
        self,
        normalized: NormalizedRecord,
        index: AliasIndex,
        config: MatchConfig,
    ) -> MatchCandidate | None:
        input_tokens = set(normalized.store_name_forms.tokens)
        input_token_count = len(input_tokens)

        if input_token_count < 2:
            return None

        best_score = 0.0
        best_alias_text: str | None = None
        best_store_id: str | None = None
        best_store_name: str | None = None

        for alias, store in index.all_entries:
            canonical_tokens = set(alias.alias_forms.tokens)
            canonical_token_count = len(canonical_tokens)

            if canonical_token_count < 2:
                continue

            if not canonical_tokens.issubset(input_tokens):
                continue

            ratio = canonical_token_count / input_token_count
            if ratio < config.containment_min_token_ratio:
                continue

            score = config.containment_base_score + (
                1.0 - config.containment_base_score
            ) * ratio

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
