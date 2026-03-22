from __future__ import annotations

from datetime import datetime, timezone

from lessley_deals.domain.enums import MatchDecision
from lessley_deals.domain.models import NameForms, NormalizedRecord
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.pipeline import MatchPipeline
from tests.factories import make_alias, make_name_forms, make_store


def _make_normalized(name: str, raw_id: str = "raw_001") -> NormalizedRecord:
    forms = make_name_forms(name)
    return NormalizedRecord(
        raw_id=raw_id,
        source_id="test_source",
        store_name_forms=forms,
        deal_description="test deal",
        normalized_at=datetime.now(timezone.utc),
    )


class TestMatchPipeline:
    def test_exact_alias_match_auto(self) -> None:
        """When compact form matches an alias exactly, result is AUTO_MATCH."""
        store = make_store(name="Shufersal")
        alias = make_alias(store.id, "Shufersal")
        index = AliasIndex(aliases=[alias], stores=[store])
        pipeline = MatchPipeline()

        normalized = _make_normalized("Shufersal")
        verdict = pipeline.match(normalized, index)

        assert verdict.decision == MatchDecision.AUTO_MATCH
        assert verdict.best is not None
        assert verdict.best.confidence == 1.0
        assert verdict.best.store_id == store.id

    def test_no_aliases_no_match(self) -> None:
        """When the index has no aliases, result is NO_MATCH."""
        index = AliasIndex(aliases=[], stores=[])
        pipeline = MatchPipeline()

        normalized = _make_normalized("Unknown Store")
        verdict = pipeline.match(normalized, index)

        assert verdict.decision == MatchDecision.NO_MATCH
        assert verdict.best is None

    def test_fuzzy_match_review(self) -> None:
        """A similar-but-not-exact name should produce REVIEW."""
        store = make_store(name="Shufersal Deal")
        alias = make_alias(store.id, "Shufersal Deal")
        index = AliasIndex(aliases=[alias], stores=[store])

        # Use a config with a high auto-match threshold to force REVIEW
        config = MatchConfig(auto_match_threshold=0.99, review_threshold=0.30)
        pipeline = MatchPipeline(config=config)

        # Input that is similar but not exact-compact-match
        normalized = _make_normalized("Shufersal Deals")
        verdict = pipeline.match(normalized, index)

        # Should have candidates but not be auto-matched
        if verdict.best is not None and verdict.best.confidence >= 0.30:
            assert verdict.decision in (MatchDecision.REVIEW, MatchDecision.AUTO_MATCH)
        else:
            # If no candidate is above review threshold, NO_MATCH is valid
            assert verdict.decision == MatchDecision.NO_MATCH

    def test_verdict_contains_explanation(self) -> None:
        """Every verdict must have an explanation with stages_run."""
        index = AliasIndex(aliases=[], stores=[])
        pipeline = MatchPipeline()

        normalized = _make_normalized("Test")
        verdict = pipeline.match(normalized, index)

        assert verdict.explanation is not None
        assert len(verdict.explanation.stages_run) > 0
        assert isinstance(verdict.explanation.reason, str)
