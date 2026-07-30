from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from lessley_deals.domain.enums import MatchDecision, RecordFate, ReviewStatus
from lessley_deals.domain.models import (
    Deal,
    MatchVerdict,
    NormalizedRecord,
    PipelineRecord,
    ReviewItem,
)
from lessley_deals.domain.protocols import (
    CanonicalStoreRepository,
    DealRepository,
    ReviewRepository,
)
from lessley_deals.enrichment.enrich_store_urls import clean_store_url
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.review.actions import build_name_forms

logger = logging.getLogger(__name__)

_BATCH_SIZE = 50


class PersistStage:
    """Stage 4: Route matched records to deals or review queue.

    Works with any storage backend (JSON files or database) as long as the
    repositories satisfy the protocol interfaces defined in domain.protocols.
    Records are processed in batches so the event loop is not starved when
    dealing with large result sets.
    """

    def __init__(
        self,
        deal_repo: DealRepository,
        review_repo: ReviewRepository,
        store_repo: CanonicalStoreRepository,
        review_no_match: bool = False,
        club_repo: Any = None,
    ) -> None:
        self._deal_repo = deal_repo
        self._review_repo = review_repo
        self._store_repo = store_repo
        self._review_no_match = review_no_match
        self._club_repo = club_repo
        # Build source_id → club_id map once at init (small dataset)
        self._club_map: dict[str, str] = {}
        if club_repo is not None:
            self._club_map = {c.source_id: c.id for c in club_repo.get_all()}

    def _update_club_stores(self, club_id: str | None, store_id: str) -> None:
        if not club_id or self._club_repo is None:
            return
        club = self._club_repo.get_by_id(club_id)
        if club and store_id not in club.stores:
            club.stores.append(store_id)
            self._club_repo.save(club)

    async def run(
        self,
        pipeline_records: list[PipelineRecord],
        normalized_map: dict[str, NormalizedRecord],
        verdict_map: dict[str, MatchVerdict],
        constraints_map: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        constraints_map = constraints_map or {}

        # ------------------------------------------------------------------ #
        # Classify every record by verdict so we can batch-persist per type. #
        # ------------------------------------------------------------------ #
        auto_match_batch: list[tuple[PipelineRecord, Deal]] = []
        review_batch: list[tuple[PipelineRecord, ReviewItem]] = []

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
                full_desc = raw_payload.get("full_description")
                deal = Deal(
                    id=generate_id(),
                    store_id=verdict.best.store_id,
                    raw_id=raw_id,
                    source_id=prec.raw.source_id,
                    scraped_at=prec.raw.scraped_at,
                    resolved_at=now,
                    title=raw_payload.get("deal_title"),
                    deal_description=full_desc,
                    terms_and_conditions=raw_payload.get("terms_and_conditions", full_desc),
                    benefit_url=raw_payload.get("benefit_url") or prec.raw.url,
                    currency=normalized.price.currency if normalized.price else "ILS",
                    url=prec.raw.url,
                    discount_logic=raw_payload.get("discount_logic"),
                    deal_type=raw_payload.get("deal_type"),
                    constraints=constraints_map.get(raw_id) or raw_payload.get("constraints"),
                    club_id=self._club_map.get(prec.raw.source_id),
                    group_member_stores=raw_payload.get("group_member_stores") or None,
                    group_member_store_ids=raw_payload.get("group_member_store_ids") or None,
                )
                auto_match_batch.append((prec, deal))

            elif verdict.decision == MatchDecision.REVIEW or self._review_no_match:
                review_item = ReviewItem(
                    id=generate_id(),
                    raw_id=raw_id,
                    input_name=verdict.input_name,
                    input_name_forms=build_name_forms(verdict.input_name),
                    raw_input_name=prec.raw.store_name,
                    verdict=verdict,
                    created_at=now,
                    status=ReviewStatus.PENDING,
                )
                review_batch.append((prec, review_item))

            else:
                prec.fate = RecordFate.NO_MATCH

        # ------------------------------------------------------------------ #
        # Persist auto-matched deals in batches.                             #
        # image_url propagation and fingerprint dedup happen per record.     #
        # ------------------------------------------------------------------ #
        for i in range(0, len(auto_match_batch), _BATCH_SIZE):
            chunk = auto_match_batch[i : i + _BATCH_SIZE]
            for prec, deal in chunk:
                raw_payload = prec.raw.raw_payload
                image_url = raw_payload.get("image_url")
                store_url_candidate = clean_store_url(deal.url)

                if image_url or store_url_candidate:
                    store = self._store_repo.get_by_id(deal.store_id)
                    if store:
                        changed = False
                        if image_url:
                            image_urls = store.metadata.setdefault("image_urls", [])
                            if image_url not in image_urls:
                                image_urls.append(image_url)
                                changed = True
                        if store_url_candidate and not store.metadata.get("store_url"):
                            store.metadata["store_url"] = store_url_candidate
                            changed = True
                        if changed:
                            self._store_repo.save(store)

                self._deal_repo.save(deal)
                self._update_club_stores(deal.club_id, deal.store_id)
                prec.fate = RecordFate.AUTO_MATCHED
            await asyncio.sleep(0)  # yield control between batches

        # ------------------------------------------------------------------ #
        # Persist review items in batches.                                   #
        # ------------------------------------------------------------------ #
        for i in range(0, len(review_batch), _BATCH_SIZE):
            chunk = review_batch[i : i + _BATCH_SIZE]
            for prec, review_item in chunk:
                self._review_repo.save(review_item)
                prec.fate = RecordFate.SENT_TO_REVIEW
            await asyncio.sleep(0)

        auto = sum(1 for r in pipeline_records if r.fate == RecordFate.AUTO_MATCHED)
        review = sum(1 for r in pipeline_records if r.fate == RecordFate.SENT_TO_REVIEW)
        logger.info("Persist stage: %d deals created, %d sent to review", auto, review)
