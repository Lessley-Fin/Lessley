from __future__ import annotations

from lessley_deals.domain.enums import MatchDecision, RecordFate
from lessley_deals.domain.models import Explanation, MatchVerdict, PipelineRecord
from lessley_deals.pipeline.persist_stage import PersistStage
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository
from tests.factories import make_raw_deal


class TestPersistStageReviewItems:
    def test_review_item_keeps_raw_input_name(self, tmp_path) -> None:
        raw = make_raw_deal(id="raw_001", store_name="חן")
        pipeline_record = PipelineRecord(raw=raw)
        verdict = MatchVerdict(
            record_id=raw.id,
            input_name="חנ",
            decision=MatchDecision.REVIEW,
            candidates=(),
            explanation=Explanation(
                stages_run=("exact_alias",),
                reason="review needed",
            ),
            best=None,
        )

        review_repo = ReviewJsonRepository(tmp_path / "reviews.json")
        deal_repo = DealJsonRepository(tmp_path / "deals.json")
        store_repo = CanonicalStoreJsonRepository(tmp_path / "stores.json")
        stage = PersistStage(
            deal_repo=deal_repo,
            review_repo=review_repo,
            store_repo=store_repo,
        )

        stage.run(
            pipeline_records=[pipeline_record],
            normalized_map={raw.id: object()},  # type: ignore[dict-item]
            verdict_map={raw.id: verdict},
        )

        saved = review_repo.get_pending()

        assert pipeline_record.fate == RecordFate.SENT_TO_REVIEW
        assert len(saved) == 1
        assert saved[0].input_name == "חנ"
        assert saved[0].raw_input_name == "חן"
