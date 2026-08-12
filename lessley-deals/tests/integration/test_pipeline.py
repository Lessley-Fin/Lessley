from __future__ import annotations

import pytest
from pathlib import Path

from lessley_deals.domain.enums import MatchDecision
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.pipeline import MatchPipeline
from lessley_deals.normalization.pipeline import create_default_pipeline
from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository
from tests.factories import make_alias, make_raw_deal, make_store


pytestmark = pytest.mark.integration


class TestEndToEndPipeline:
    """End-to-end test: normalization -> matching on real JSON-backed repos."""

    def _seed_data(self, tmp_path: Path) -> tuple[
        CanonicalStoreJsonRepository,
        AliasJsonRepository,
    ]:
        """Seed canonical stores and aliases into tmp_path repos."""
        store_repo = CanonicalStoreJsonRepository(tmp_path / "stores.json")
        alias_repo = AliasJsonRepository(tmp_path / "aliases.json")

        # Create two known stores
        shufersal = make_store(name="Shufersal")
        rami = make_store(name="Rami Levy")
        store_repo.save(shufersal)
        store_repo.save(rami)

        # Seed aliases that map to these stores
        alias_repo.save(make_alias(shufersal.id, "Shufersal"))
        alias_repo.save(make_alias(shufersal.id, "Shufersal Deal"))
        alias_repo.save(make_alias(rami.id, "Rami Levy"))

        return store_repo, alias_repo

    def _build_index(
        self,
        store_repo: CanonicalStoreJsonRepository,
        alias_repo: AliasJsonRepository,
    ) -> AliasIndex:
        return AliasIndex(
            aliases=alias_repo.get_all(),
            stores=store_repo.get_all(),
        )

    def test_known_store_gets_auto_match(self, tmp_path: Path) -> None:
        store_repo, alias_repo = self._seed_data(tmp_path)
        index = self._build_index(store_repo, alias_repo)

        norm_pipeline = create_default_pipeline()
        match_pipeline = MatchPipeline()

        # Raw deal with a known store name
        raw = make_raw_deal(store_name="Shufersal")
        normalized = norm_pipeline.normalize(raw)
        verdict = match_pipeline.match(normalized, index)

        assert verdict.decision == MatchDecision.AUTO_MATCH
        assert verdict.best is not None
        assert verdict.best.confidence == 1.0
        assert verdict.best.stage == "exact_alias"

    def test_known_store_variant_gets_auto_match(self, tmp_path: Path) -> None:
        store_repo, alias_repo = self._seed_data(tmp_path)
        index = self._build_index(store_repo, alias_repo)

        norm_pipeline = create_default_pipeline()
        match_pipeline = MatchPipeline()

        # "Shufersal Deal" is a known alias
        raw = make_raw_deal(store_name="Shufersal Deal")
        normalized = norm_pipeline.normalize(raw)
        verdict = match_pipeline.match(normalized, index)

        assert verdict.decision == MatchDecision.AUTO_MATCH
        assert verdict.best is not None

    def test_unknown_store_gets_no_match_or_review(self, tmp_path: Path) -> None:
        store_repo, alias_repo = self._seed_data(tmp_path)
        index = self._build_index(store_repo, alias_repo)

        norm_pipeline = create_default_pipeline()
        match_pipeline = MatchPipeline()

        # Completely unknown store name
        raw = make_raw_deal(store_name="XYZ Groceries International")
        normalized = norm_pipeline.normalize(raw)
        verdict = match_pipeline.match(normalized, index)

        # Should not auto-match -- either REVIEW or NO_MATCH
        assert verdict.decision in (MatchDecision.REVIEW, MatchDecision.NO_MATCH)

    def test_multiple_deals_mixed_results(self, tmp_path: Path) -> None:
        store_repo, alias_repo = self._seed_data(tmp_path)
        index = self._build_index(store_repo, alias_repo)

        norm_pipeline = create_default_pipeline()
        match_pipeline = MatchPipeline()

        raw_known = make_raw_deal(store_name="Rami Levy")
        raw_unknown = make_raw_deal(store_name="Unknown Market ABC")

        norm_known = norm_pipeline.normalize(raw_known)
        norm_unknown = norm_pipeline.normalize(raw_unknown)

        verdict_known = match_pipeline.match(norm_known, index)
        verdict_unknown = match_pipeline.match(norm_unknown, index)

        assert verdict_known.decision == MatchDecision.AUTO_MATCH
        assert verdict_unknown.decision in (
            MatchDecision.REVIEW,
            MatchDecision.NO_MATCH,
        )

    def test_normalization_produces_consistent_forms(self, tmp_path: Path) -> None:
        """Verify that the normalization pipeline produces stable name forms."""
        norm_pipeline = create_default_pipeline()

        raw1 = make_raw_deal(store_name="  Shufersal  Deal  ")
        raw2 = make_raw_deal(store_name="Shufersal Deal")

        norm1 = norm_pipeline.normalize(raw1)
        norm2 = norm_pipeline.normalize(raw2)

        # After normalization, whitespace differences should be collapsed
        assert norm1.store_name_forms.compact == norm2.store_name_forms.compact
        assert norm1.store_name_forms.normalized == norm2.store_name_forms.normalized
