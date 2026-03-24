from __future__ import annotations

import logging
from datetime import datetime, timezone

from lessley_deals.domain.enums import MatchDecision, RecordFate, ReviewStatus
from lessley_deals.domain.models import (
    Deal,
    MatchVerdict,
    NormalizedRecord,
    PipelineRecord,
    ReviewItem,
)
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.review.actions import build_name_forms

logger = logging.getLogger(__name__)


class PersistStage:
    """Stage 4: Route matched records to deals or review queue."""

    def __init__(
        self,
        deal_repo: DealJsonRepository,
        review_repo: ReviewJsonRepository,
        review_no_match: bool = False,
    ) -> None:
        self._deal_repo = deal_repo
        self._review_repo = review_repo
        self._review_no_match = review_no_match

    def run(
        self,
        pipeline_records: list[PipelineRecord],
        normalized_map: dict[str, NormalizedRecord],
        verdict_map: dict[str, MatchVerdict],
    ) -> None:
        now = datetime.now(timezone.utc)

        for prec in pipeline_records:
            raw_id = prec.raw.id
            verdict = verdict_map.get(raw_id)
            normalized = normalized_map.get(raw_id)

            if verdict is None or normalized is None:
                prec.fate = RecordFate.ERROR
                prec.error = "Missing verdict or normalized record"
                continue

            prec.verdict = verdict
            prec.normalized = normalized

            if verdict.decision == MatchDecision.AUTO_MATCH and verdict.best:
                raw_payload = prec.raw.raw_payload
                deal = Deal(
                    id=generate_id(),
                    store_id=verdict.best.store_id,
                    raw_id=raw_id,
                    source_id=prec.raw.source_id,
                    description=normalized.deal_description,
                    scraped_at=prec.raw.scraped_at,
                    resolved_at=now,
                    currency=normalized.price.currency if normalized.price else "ILS",
                    url=prec.raw.url,
                    image_url=raw_payload.get("image_url"),
                    discount_logic=raw_payload.get("discount_logic"),
                    stackable=raw_payload.get("stackable"),
                    redeem_channels=raw_payload.get("redeem_channels", []),
                    coupon_code=raw_payload.get("coupon_code"),
                )
                if not self._deal_repo.exists_by_fingerprint(deal.fingerprint):
                    self._deal_repo.save(deal)
                    prec.fate = RecordFate.AUTO_MATCHED
                else:
                    prec.fate = RecordFate.DUPLICATE

            elif verdict.decision == MatchDecision.REVIEW:
                review_item = ReviewItem(
                    id=generate_id(),
                    raw_id=raw_id,
                    input_name=verdict.input_name,
                    input_name_forms=build_name_forms(verdict.input_name),
                    verdict=verdict,
                    created_at=now,
                    status=ReviewStatus.PENDING,
                )
                self._review_repo.save(review_item)
                prec.fate = RecordFate.SENT_TO_REVIEW

            elif self._review_no_match:
                review_item = ReviewItem(
                    id=generate_id(),
                    raw_id=raw_id,
                    input_name=verdict.input_name,
                    input_name_forms=build_name_forms(verdict.input_name),
                    verdict=verdict,
                    created_at=now,
                    status=ReviewStatus.PENDING,
                )
                self._review_repo.save(review_item)
                prec.fate = RecordFate.SENT_TO_REVIEW

            else:
                prec.fate = RecordFate.NO_MATCH

        auto = sum(1 for r in pipeline_records if r.fate == RecordFate.AUTO_MATCHED)
        review = sum(1 for r in pipeline_records if r.fate == RecordFate.SENT_TO_REVIEW)
        logger.info("Persist stage: %d deals created, %d sent to review", auto, review)
