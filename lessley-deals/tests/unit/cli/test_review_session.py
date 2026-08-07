from __future__ import annotations

import builtins
import sys
import types

sys.modules.setdefault(
    "bidi.algorithm",
    types.SimpleNamespace(get_display=lambda text: text),
)

from lessley_deals.cli.review_session import parse_mcc_selection, run_review_session
from lessley_deals.domain.enums import MatchDecision
from lessley_deals.domain.models import Explanation, MatchCandidate
from lessley_deals.enrichment.mcc_catalog import MCC_CATEGORIES
from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.repositories.raw_deals import RawDealJsonRepository
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository
from tests.factories import (
    make_match_verdict,
    make_raw_deal,
    make_review_item,
    make_store,
)


class TestReviewSessionCreateNew:
    def test_create_new_defaults_to_raw_input_name(self, tmp_path, monkeypatch) -> None:
        review_repo = ReviewJsonRepository(tmp_path / "reviews.json")
        store_repo = CanonicalStoreJsonRepository(tmp_path / "stores.json")
        alias_repo = AliasJsonRepository(tmp_path / "aliases.json")
        deal_repo = DealJsonRepository(tmp_path / "deals.json")

        verdict = make_match_verdict(
            record_id="raw_001",
            input_name="חנ",
            decision=MatchDecision.NO_MATCH,
            explanation=Explanation(
                stages_run=("exact_alias",),
                reason="no match",
            ),
        )
        item = make_review_item(
            raw_id="raw_001",
            input_name="חנ",
            raw_input_name="חן",
            verdict=verdict,
        )
        review_repo.save(item)

        # "c" -> create, "" -> keep default name, "" -> skip the MCC prompt
        answers = iter(["c", "", ""])
        monkeypatch.setattr(builtins, "input", lambda _="": next(answers))

        run_review_session(
            review_repo=review_repo,
            store_repo=store_repo,
            alias_repo=alias_repo,
            deal_repo=deal_repo,
        )

        stores = store_repo.get_all()
        assert len(stores) == 1
        assert stores[0].name == "חן"

    def test_create_new_uses_raw_deal_name_for_existing_review_items(
        self, tmp_path, monkeypatch,
    ) -> None:
        review_repo = ReviewJsonRepository(tmp_path / "reviews.json")
        store_repo = CanonicalStoreJsonRepository(tmp_path / "stores.json")
        alias_repo = AliasJsonRepository(tmp_path / "aliases.json")
        deal_repo = DealJsonRepository(tmp_path / "deals.json")
        raw_deal_repo = RawDealJsonRepository(tmp_path / "raw_deals.json")

        raw_deal_repo.save(make_raw_deal(id="raw_001", store_name="חן"))

        verdict = make_match_verdict(
            record_id="raw_001",
            input_name="חנ",
            decision=MatchDecision.NO_MATCH,
            explanation=Explanation(
                stages_run=("exact_alias",),
                reason="no match",
            ),
        )
        item = make_review_item(
            raw_id="raw_001",
            input_name="חנ",
            raw_input_name=None,
            verdict=verdict,
        )
        review_repo.save(item)

        # "c" -> create, "" -> keep default name, "" -> skip the MCC prompt
        answers = iter(["c", "", ""])
        monkeypatch.setattr(builtins, "input", lambda _="": next(answers))

        run_review_session(
            review_repo=review_repo,
            store_repo=store_repo,
            alias_repo=alias_repo,
            deal_repo=deal_repo,
            raw_deal_repo=raw_deal_repo,
        )

        stores = store_repo.get_all()
        assert len(stores) == 1
        assert stores[0].name == "חן"


class TestParseMccSelection:
    def test_accepts_catalog_numbers(self) -> None:
        categories, unknown = parse_mcc_selection("22, 39")
        assert categories == [MCC_CATEGORIES[21], MCC_CATEGORIES[38]]
        assert unknown == []

    def test_accepts_names_and_four_digit_codes(self) -> None:
        categories, unknown = parse_mcc_selection("groceries, 5812")
        assert categories == ["GROCERIES", "RESTAURANT"]
        assert unknown == []

    def test_reports_unknown_tokens(self) -> None:
        categories, unknown = parse_mcc_selection("GROCERIES, banana, 999")
        assert categories == ["GROCERIES"]
        assert unknown == ["banana", "999"]

    def test_drops_duplicates_and_blanks(self) -> None:
        categories, unknown = parse_mcc_selection("GROCERIES, , 5411")
        assert categories == ["GROCERIES"]
        assert unknown == []


class TestReviewSessionSetMcc:
    def _repos(self, tmp_path):
        return (
            ReviewJsonRepository(tmp_path / "reviews.json"),
            CanonicalStoreJsonRepository(tmp_path / "stores.json"),
            AliasJsonRepository(tmp_path / "aliases.json"),
            DealJsonRepository(tmp_path / "deals.json"),
        )

    def test_m_tags_the_best_candidate_store(self, tmp_path, monkeypatch) -> None:
        review_repo, store_repo, alias_repo, deal_repo = self._repos(tmp_path)

        store = make_store(name="שופרסל")
        store_repo.save(store)
        candidate = MatchCandidate(
            store_id=store.id, store_name=store.name, confidence=0.7, stage="normalized",
        )
        verdict = make_match_verdict(
            record_id="raw_001",
            input_name="shufersal deal",
            decision=MatchDecision.REVIEW,
            candidates=(candidate,),
            best=candidate,
        )
        review_repo.save(make_review_item(raw_id="raw_001", verdict=verdict))

        # "m" -> set MCC, pick two by name, then "s" to defer the item itself
        answers = iter(["m", "GROCERIES, 5812", "s"])
        monkeypatch.setattr(builtins, "input", lambda _="": next(answers))

        run_review_session(
            review_repo=review_repo,
            store_repo=store_repo,
            alias_repo=alias_repo,
            deal_repo=deal_repo,
        )

        saved = store_repo.get_by_id(store.id)
        assert saved is not None
        assert saved.metadata["mcc_codes"] == ["GROCERIES", "RESTAURANT"]
        assert saved.metadata["mcc_source"] == "review:cli_user"

    def test_m_leaves_codes_untouched_when_cancelled(self, tmp_path, monkeypatch) -> None:
        review_repo, store_repo, alias_repo, deal_repo = self._repos(tmp_path)

        store = make_store(name="שופרסל", metadata={"mcc_codes": ["GROCERIES"]})
        store_repo.save(store)
        candidate = MatchCandidate(
            store_id=store.id, store_name=store.name, confidence=0.7, stage="normalized",
        )
        verdict = make_match_verdict(
            record_id="raw_001", decision=MatchDecision.REVIEW,
            candidates=(candidate,), best=candidate,
        )
        review_repo.save(make_review_item(raw_id="raw_001", verdict=verdict))

        answers = iter(["m", "", "s"])
        monkeypatch.setattr(builtins, "input", lambda _="": next(answers))

        run_review_session(
            review_repo=review_repo,
            store_repo=store_repo,
            alias_repo=alias_repo,
            deal_repo=deal_repo,
        )

        saved = store_repo.get_by_id(store.id)
        assert saved is not None
        assert saved.metadata["mcc_codes"] == ["GROCERIES"]
        assert "mcc_source" not in saved.metadata

    def test_create_new_prompts_for_mcc(self, tmp_path, monkeypatch) -> None:
        review_repo, store_repo, alias_repo, deal_repo = self._repos(tmp_path)

        verdict = make_match_verdict(record_id="raw_001", input_name="חן")
        review_repo.save(
            make_review_item(raw_id="raw_001", input_name="חן", verdict=verdict)
        )

        answers = iter(["c", "", "GROCERIES"])
        monkeypatch.setattr(builtins, "input", lambda _="": next(answers))

        run_review_session(
            review_repo=review_repo,
            store_repo=store_repo,
            alias_repo=alias_repo,
            deal_repo=deal_repo,
        )

        stores = store_repo.get_all()
        assert len(stores) == 1
        assert stores[0].metadata["mcc_codes"] == ["GROCERIES"]

    def test_no_mcc_on_create_skips_the_prompt(self, tmp_path, monkeypatch) -> None:
        review_repo, store_repo, alias_repo, deal_repo = self._repos(tmp_path)

        verdict = make_match_verdict(record_id="raw_001", input_name="חן")
        review_repo.save(
            make_review_item(raw_id="raw_001", input_name="חן", verdict=verdict)
        )

        # Only two answers: a third input() call would raise StopIteration.
        answers = iter(["c", ""])
        monkeypatch.setattr(builtins, "input", lambda _="": next(answers))

        run_review_session(
            review_repo=review_repo,
            store_repo=store_repo,
            alias_repo=alias_repo,
            deal_repo=deal_repo,
            mcc_on_create=False,
        )

        stores = store_repo.get_all()
        assert len(stores) == 1
        assert "mcc_codes" not in stores[0].metadata
