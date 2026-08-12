from __future__ import annotations

from datetime import datetime, timezone

from lessley_deals.domain.models import NormalizedRecord
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.stages.exact_alias import ExactAlias
from tests.factories import make_alias, make_name_forms, make_store


def _make_normalized(name: str) -> NormalizedRecord:
    forms = make_name_forms(name)
    return NormalizedRecord(
        raw_id="raw_001",
        source_id="test_source",
        store_name_forms=forms,
        deal_description="test deal",
        normalized_at=datetime.now(timezone.utc),
    )


class TestExactAlias:
    def test_exact_match_returns_candidate(self) -> None:
        """Input whose compact form matches an alias exactly returns confidence 1.0."""
        store = make_store(name="Rami Levy")
        alias = make_alias(store.id, "Rami Levy")
        index = AliasIndex(aliases=[alias], stores=[store])
        config = MatchConfig()
        stage = ExactAlias()

        normalized = _make_normalized("Rami Levy")
        candidate = stage.evaluate(normalized, index, config)

        assert candidate is not None
        assert candidate.confidence == 1.0
        assert candidate.store_id == store.id
        assert candidate.stage == "exact_alias"

    def test_no_match_returns_none(self) -> None:
        """Input that doesn't match any alias returns None."""
        store = make_store(name="Rami Levy")
        alias = make_alias(store.id, "Rami Levy")
        index = AliasIndex(aliases=[alias], stores=[store])
        config = MatchConfig()
        stage = ExactAlias()

        normalized = _make_normalized("Completely Different Store")
        candidate = stage.evaluate(normalized, index, config)

        assert candidate is None

    def test_empty_index_returns_none(self) -> None:
        """Empty index always returns None."""
        index = AliasIndex(aliases=[], stores=[])
        config = MatchConfig()
        stage = ExactAlias()

        normalized = _make_normalized("Any Store")
        candidate = stage.evaluate(normalized, index, config)

        assert candidate is None
