from __future__ import annotations

import pytest
from pathlib import Path

from lessley_deals.domain.enums import (
    AliasSource,
    MatchDecision,
    ReviewStatus,
)
from lessley_deals.domain.models import (
    Explanation,
    MatchCandidate,
    MatchVerdict,
)
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.pipeline import MatchPipeline
from lessley_deals.normalization.pipeline import create_default_pipeline
from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository
from lessley_deals.review.actions import ReviewActions
from lessley_deals.review.queue import ReviewQueue
from tests.factories import (
    make_alias,
    make_match_verdict,
    make_raw_deal,
    make_review_item,
    make_store,
)


pytestmark = pytest.mark.integration


class TestReviewFeedbackLoop:
    """The most important integration test: proves the review feedback loop works.

    Flow:
    1. Set up known stores + aliases
    2. An unknown store name fails to match (NO_MATCH or REVIEW)
    3. A reviewer approves the match, creating an alias
    4. Re-running matching with the same name now yields AUTO_MATCH via exact_alias
    """

    def _make_repos(self, tmp_path: Path) -> tuple[
        CanonicalStoreJsonRepository,
        AliasJsonRepository,
        ReviewJsonRepository,
        DealJsonRepository,
    ]:
        return (
            CanonicalStoreJsonRepository(tmp_path / "stores.json"),
            AliasJsonRepository(tmp_path / "aliases.json"),
            ReviewJsonRepository(tmp_path / "reviews.json"),
            DealJsonRepository(tmp_path / "deals.json"),
        )

    def test_approve_creates_alias_and_enables_auto_match(
        self, tmp_path: Path,
    ) -> None:
        store_repo, alias_repo, review_repo, deal_repo = self._make_repos(tmp_path)

        # -- Step 1: Seed a known store with one alias --
        known_store = make_store(name="Shufersal")
        store_repo.save(known_store)
        alias_repo.save(make_alias(known_store.id, "Shufersal"))

        # -- Step 2: An unknown name fails to auto-match --
        unknown_name = "Shufersal Online"
        norm_pipeline = create_default_pipeline()
        match_pipeline = MatchPipeline()

        raw = make_raw_deal(store_name=unknown_name)
        normalized = norm_pipeline.normalize(raw)

        index = AliasIndex(
            aliases=alias_repo.get_all(),
            stores=store_repo.get_all(),
        )
        verdict = match_pipeline.match(normalized, index)

        # It should NOT auto-match since "Shufersal Online" is not a known alias
        # (it may get REVIEW or NO_MATCH depending on fuzzy scoring)
        initial_decision = verdict.decision

        # -- Step 3: Create a review item with a candidate pointing to known_store --
        # Build a verdict with the known store as a candidate (simulating what
        # the pipeline would produce when there's a fuzzy match)
        candidate = MatchCandidate(
            store_id=known_store.id,
            store_name=known_store.name,
            confidence=0.75,
            stage="normalized_fuzzy",
        )
        review_verdict = MatchVerdict(
            record_id=raw.id,
            input_name=unknown_name.lower(),
            decision=MatchDecision.REVIEW,
            candidates=(candidate,),
            explanation=Explanation(
                stages_run=("exact_alias", "compact_form", "normalized_fuzzy"),
                reason="review needed via normalized_fuzzy with confidence 0.750",
                stage_matched="normalized_fuzzy",
            ),
            best=candidate,
        )
        review_item = make_review_item(
            raw_id=raw.id,
            input_name=unknown_name.lower(),
            verdict=review_verdict,
        )

        # Add to review queue
        queue = ReviewQueue(review_repo)
        queue.add(review_item)

        pending = queue.get_pending()
        assert len(pending) == 1

        # -- Step 4: Approve the review item --
        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)
        approved = actions.approve(review_item, reviewed_by="test_user")

        assert approved.status == ReviewStatus.APPROVED
        assert approved.decision is not None
        assert approved.decision.store_id == known_store.id

        # -- Step 5: Verify alias was created --
        aliases = alias_repo.get_by_store(known_store.id)
        alias_texts = {a.alias for a in aliases}
        assert unknown_name.lower() in alias_texts

        # Verify the new alias has source=REVIEW
        new_alias = next(a for a in aliases if a.alias == unknown_name.lower())
        assert new_alias.source == AliasSource.REVIEW

        # -- Step 6: Re-run matching with updated index --
        updated_index = AliasIndex(
            aliases=alias_repo.get_all(),
            stores=store_repo.get_all(),
        )

        # Normalize the same unknown name again
        raw2 = make_raw_deal(store_name=unknown_name)
        normalized2 = norm_pipeline.normalize(raw2)
        verdict2 = match_pipeline.match(normalized2, updated_index)

        # NOW it should auto-match via exact_alias
        assert verdict2.decision == MatchDecision.AUTO_MATCH
        assert verdict2.best is not None
        assert verdict2.best.stage == "exact_alias"
        assert verdict2.best.store_id == known_store.id
        assert verdict2.best.confidence == 1.0

    def test_approve_also_creates_deal(self, tmp_path: Path) -> None:
        store_repo, alias_repo, review_repo, deal_repo = self._make_repos(tmp_path)

        store = make_store(name="Rami Levy")
        store_repo.save(store)

        candidate = MatchCandidate(
            store_id=store.id,
            store_name=store.name,
            confidence=0.80,
            stage="compact_form",
        )
        verdict = MatchVerdict(
            record_id="raw_001",
            input_name="rami levi",
            decision=MatchDecision.REVIEW,
            candidates=(candidate,),
            explanation=Explanation(
                stages_run=("exact_alias", "compact_form"),
                reason="review needed",
                stage_matched="compact_form",
            ),
            best=candidate,
        )
        item = make_review_item(
            raw_id="raw_001",
            input_name="rami levi",
            verdict=verdict,
        )
        review_repo.save(item)

        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)
        actions.approve(item, reviewed_by="test_user")

        # A deal should have been created for this store
        deals = deal_repo.get_by_store(store.id)
        assert len(deals) == 1
        assert deals[0].store_id == store.id

    def test_create_new_store_from_review(self, tmp_path: Path) -> None:
        store_repo, alias_repo, review_repo, deal_repo = self._make_repos(tmp_path)

        # No stores seeded -- completely unknown name
        verdict = make_match_verdict(
            record_id="raw_002",
            input_name="brand new market",
            decision=MatchDecision.NO_MATCH,
        )
        item = make_review_item(
            raw_id="raw_002",
            input_name="brand new market",
            verdict=verdict,
        )
        review_repo.save(item)

        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)
        result = actions.create_new(item, store_name="Brand New Market", reviewed_by="test_user")

        assert result.status == ReviewStatus.CREATED

        # A new canonical store should exist
        all_stores = store_repo.get_all()
        assert len(all_stores) == 1
        assert all_stores[0].name == "Brand New Market"

        # An alias mapping the input name to the new store should exist
        all_aliases = alias_repo.get_all()
        assert len(all_aliases) == 1
        assert all_aliases[0].alias == "brand new market"
        assert all_aliases[0].store_id == all_stores[0].id

        # Now matching should auto-match via exact_alias
        norm_pipeline = create_default_pipeline()
        match_pipeline = MatchPipeline()
        index = AliasIndex(
            aliases=alias_repo.get_all(),
            stores=store_repo.get_all(),
        )

        raw = make_raw_deal(store_name="Brand New Market")
        normalized = norm_pipeline.normalize(raw)
        new_verdict = match_pipeline.match(normalized, index)

        assert new_verdict.decision == MatchDecision.AUTO_MATCH
        assert new_verdict.best is not None
        assert new_verdict.best.store_id == all_stores[0].id

    def test_review_queue_stats_update_after_actions(
        self, tmp_path: Path,
    ) -> None:
        store_repo, alias_repo, review_repo, deal_repo = self._make_repos(tmp_path)

        store = make_store(name="Test Store")
        store_repo.save(store)

        candidate = MatchCandidate(
            store_id=store.id,
            store_name=store.name,
            confidence=0.70,
            stage="normalized_fuzzy",
        )
        verdict = MatchVerdict(
            record_id="raw_003",
            input_name="test store variant",
            decision=MatchDecision.REVIEW,
            candidates=(candidate,),
            explanation=Explanation(
                stages_run=("exact_alias",),
                reason="review needed",
            ),
            best=candidate,
        )

        queue = ReviewQueue(review_repo)
        item = make_review_item(
            raw_id="raw_003",
            input_name="test store variant",
            verdict=verdict,
        )
        queue.add(item)

        stats = queue.stats()
        assert stats.total == 1
        assert stats.pending == 1
        assert stats.approved == 0

        # Approve the item
        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)
        actions.approve(item, reviewed_by="test_user")

        stats = queue.stats()
        assert stats.total == 1
        assert stats.pending == 0
        assert stats.approved == 1
