from __future__ import annotations

import builtins
import sys
import types

sys.modules.setdefault(
    "bidi.algorithm",
    types.SimpleNamespace(get_display=lambda text: text),
)

from lessley_deals.cli.review_session import run_review_session
from lessley_deals.domain.enums import MatchDecision
from lessley_deals.domain.models import Explanation
from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.repositories.raw_deals import RawDealJsonRepository
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository
from tests.factories import make_match_verdict, make_raw_deal, make_review_item


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

        answers = iter(["c", ""])
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

        answers = iter(["c", ""])
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
