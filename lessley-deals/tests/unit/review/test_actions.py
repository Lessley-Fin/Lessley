from __future__ import annotations

from pathlib import Path

import pytest

from lessley_deals.domain.enums import (
    AliasSource,
    MatchDecision,
    ReviewAction,
    ReviewStatus,
)
from lessley_deals.domain.models import (
    Explanation,
    MatchCandidate,
    MatchVerdict,
    NameForms,
)
from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository
from lessley_deals.review.actions import ReviewActions, build_name_forms
from tests.factories import make_review_item, make_store


def _make_repos(tmp_path: Path) -> tuple[
    ReviewJsonRepository,
    CanonicalStoreJsonRepository,
    AliasJsonRepository,
    DealJsonRepository,
]:
    return (
        ReviewJsonRepository(tmp_path / "reviews.json"),
        CanonicalStoreJsonRepository(tmp_path / "stores.json"),
        AliasJsonRepository(tmp_path / "aliases.json"),
        DealJsonRepository(tmp_path / "deals.json"),
    )


class TestBuildNameForms:
    def test_produces_valid_name_forms(self) -> None:
        nf = build_name_forms("Test Store")
        assert isinstance(nf, NameForms)
        assert nf.normalized == "test store"
        assert nf.compact == "teststore"
        assert isinstance(nf.tokens, tuple)
        assert "test" in nf.tokens
        assert "store" in nf.tokens

    def test_hebrew_name(self) -> None:
        nf = build_name_forms("\u05e9\u05d5\u05e4\u05e8\u05e1\u05dc")  # שופרסל
        assert isinstance(nf, NameForms)
        assert nf.compact != ""
        assert nf.normalized != ""

    def test_strips_whitespace(self) -> None:
        nf = build_name_forms("  Spaced   Out  ")
        assert nf.normalized == "spaced out"
        assert nf.compact == "spacedout"


class TestApprove:
    def test_approve_creates_alias_and_deal(self, tmp_path: Path) -> None:
        review_repo, store_repo, alias_repo, deal_repo = _make_repos(tmp_path)
        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)

        # Set up a store and a review item with a matching candidate
        store = make_store(name="Rami Levy")
        store_repo.save(store)

        best = MatchCandidate(
            store_id=store.id,
            store_name="Rami Levy",
            confidence=0.85,
            stage="exact_alias",
        )
        verdict = MatchVerdict(
            record_id="raw_001",
            input_name="rami levy",
            decision=MatchDecision.REVIEW,
            candidates=(best,),
            explanation=Explanation(
                stages_run=("exact_alias",),
                reason="review needed",
            ),
            best=best,
        )
        item = make_review_item(raw_id="raw_001", verdict=verdict)
        review_repo.save(item)

        # Act
        result = actions.approve(item, reviewed_by="tester")

        # Assert
        assert result.status == ReviewStatus.APPROVED
        assert result.decision is not None
        assert result.decision.action == ReviewAction.APPROVE
        assert result.decision.store_id == store.id

        aliases = alias_repo.get_all()
        assert len(aliases) == 1
        assert aliases[0].store_id == store.id

        deals = deal_repo.get_all()
        assert len(deals) == 1
        assert deals[0].store_id == store.id

    def test_approve_without_candidates_raises(self, tmp_path: Path) -> None:
        review_repo, store_repo, alias_repo, deal_repo = _make_repos(tmp_path)
        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)

        item = make_review_item()
        review_repo.save(item)

        with pytest.raises(ValueError, match="no candidates"):
            actions.approve(item, reviewed_by="tester")

    def test_approve_prefers_raw_input_name_for_alias(self, tmp_path: Path) -> None:
        review_repo, store_repo, alias_repo, deal_repo = _make_repos(tmp_path)
        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)

        store = make_store(name='מרפאת שיניים ד"ר עלימי')
        store_repo.save(store)

        best = MatchCandidate(
            store_id=store.id,
            store_name=store.name,
            confidence=0.85,
            stage="exact_alias",
        )
        verdict = MatchVerdict(
            record_id="raw_001",
            input_name="מרפאת שיניים",
            decision=MatchDecision.REVIEW,
            candidates=(best,),
            explanation=Explanation(
                stages_run=("exact_alias",),
                reason="review needed",
            ),
            best=best,
        )
        item = make_review_item(
            raw_id="raw_001",
            input_name="מרפאת שיניים",
            raw_input_name='מרפאת שיניים ד"ר עלימי',
            verdict=verdict,
        )
        review_repo.save(item)

        actions.approve(item, reviewed_by="tester")

        aliases = alias_repo.get_all()
        assert len(aliases) == 1
        assert aliases[0].alias == 'מרפאת שיניים ד"ר עלימי'


class TestCreateNew:
    def test_create_new_creates_store_alias_and_deal(self, tmp_path: Path) -> None:
        review_repo, store_repo, alias_repo, deal_repo = _make_repos(tmp_path)
        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)

        item = make_review_item(raw_id="raw_002")
        review_repo.save(item)

        result = actions.create_new(item, store_name="Brand New Store", reviewed_by="tester")

        assert result.status == ReviewStatus.CREATED
        assert result.decision is not None
        assert result.decision.action == ReviewAction.CREATE_NEW
        assert result.decision.new_store_name == "Brand New Store"

        stores = store_repo.get_all()
        assert len(stores) == 1
        assert stores[0].name == "Brand New Store"

        aliases = alias_repo.get_all()
        assert len(aliases) == 1
        assert aliases[0].store_id == stores[0].id

        deals = deal_repo.get_all()
        assert len(deals) == 1
        assert deals[0].store_id == stores[0].id

    def test_create_new_prefers_raw_input_name_for_alias(self, tmp_path: Path) -> None:
        review_repo, store_repo, alias_repo, deal_repo = _make_repos(tmp_path)
        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)

        item = make_review_item(
            raw_id="raw_002",
            input_name="מרפאת שיניים",
            raw_input_name='מרפאת שיניים ד"ר עלימי',
        )
        review_repo.save(item)

        actions.create_new(item, store_name='מרפאת שיניים ד"ר עלימי', reviewed_by="tester")

        aliases = alias_repo.get_all()
        assert len(aliases) == 1
        assert aliases[0].alias == 'מרפאת שיניים ד"ר עלימי'


class TestDiscard:
    def test_discard_only_changes_status(self, tmp_path: Path) -> None:
        review_repo, store_repo, alias_repo, deal_repo = _make_repos(tmp_path)
        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)

        item = make_review_item(raw_id="raw_003")
        review_repo.save(item)

        result = actions.discard(item, reviewed_by="tester", note="not relevant")

        assert result.status == ReviewStatus.DISCARDED
        assert result.decision is not None
        assert result.decision.action == ReviewAction.DISCARD
        assert result.decision.note == "not relevant"

        # No stores, aliases, or deals should be created
        assert store_repo.get_all() == []
        assert alias_repo.get_all() == []
        assert deal_repo.get_all() == []


class TestSetStoreMcc:
    def test_writes_canonical_names(self, tmp_path: Path) -> None:
        review_repo, store_repo, alias_repo, deal_repo = _make_repos(tmp_path)
        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)
        store = make_store(name="Shufersal")
        store_repo.save(store)

        updated = actions.set_store_mcc(store.id, ["groceries", 5812])

        assert updated.metadata["mcc_codes"] == ["GROCERIES", "RESTAURANT"]
        assert updated.metadata["mcc_confidence"] == "HIGH"
        assert updated.metadata["mcc_source"] == "review:cli_user"

    def test_persists_through_the_repository(self, tmp_path: Path) -> None:
        review_repo, store_repo, alias_repo, deal_repo = _make_repos(tmp_path)
        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)
        store = make_store(name="Shufersal")
        store_repo.save(store)

        actions.set_store_mcc(store.id, ["GROCERIES"])

        reloaded = store_repo.get_by_id(store.id)
        assert reloaded is not None
        assert reloaded.metadata["mcc_codes"] == ["GROCERIES"]

    def test_keeps_other_metadata(self, tmp_path: Path) -> None:
        review_repo, store_repo, alias_repo, deal_repo = _make_repos(tmp_path)
        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)
        store = make_store(
            name="Shufersal",
            metadata={"store_url": "https://shufersal.co.il", "image_urls": ["a.png"]},
        )
        store_repo.save(store)

        updated = actions.set_store_mcc(store.id, ["GROCERIES"])

        assert updated.metadata["store_url"] == "https://shufersal.co.il"
        assert updated.metadata["image_urls"] == ["a.png"]

    def test_bumps_updated_at(self, tmp_path: Path) -> None:
        review_repo, store_repo, alias_repo, deal_repo = _make_repos(tmp_path)
        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)
        store = make_store(name="Shufersal")
        store_repo.save(store)
        before = store.updated_at

        updated = actions.set_store_mcc(store.id, ["GROCERIES"])

        assert updated.updated_at >= before

    def test_rejects_unknown_store(self, tmp_path: Path) -> None:
        review_repo, store_repo, alias_repo, deal_repo = _make_repos(tmp_path)
        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)

        with pytest.raises(ValueError, match="Unknown store"):
            actions.set_store_mcc("nope", ["GROCERIES"])

    def test_rejects_input_with_no_resolvable_category(self, tmp_path: Path) -> None:
        review_repo, store_repo, alias_repo, deal_repo = _make_repos(tmp_path)
        actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)
        store = make_store(name="Shufersal")
        store_repo.save(store)

        with pytest.raises(ValueError, match="No canonical MCC category"):
            actions.set_store_mcc(store.id, ["banana"])

        reloaded = store_repo.get_by_id(store.id)
        assert reloaded is not None
        assert "mcc_codes" not in reloaded.metadata
