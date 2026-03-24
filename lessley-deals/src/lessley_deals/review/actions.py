from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from lessley_deals.domain.enums import AliasSource, ReviewAction, ReviewStatus
from lessley_deals.domain.models import (
    CanonicalStore,
    Deal,
    NameForms,
    ReviewDecision,
    ReviewItem,
    StoreAlias,
)
from lessley_deals.normalization.hebrew_utils import normalize_hebrew
from lessley_deals.normalization.text import collapse_whitespace
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository

logger = logging.getLogger(__name__)


def build_name_forms(name: str) -> NameForms:
    """Build normalized name forms from a raw store name."""
    normalized = collapse_whitespace(normalize_hebrew(name)).lower()
    compact = re.sub(r"[\s\W]", "", normalized)
    # Normalize final forms in compact representation
    final_map = str.maketrans("םןץףך", "מנצפכ")
    compact = compact.translate(final_map)
    tokens = tuple(sorted(set(w for w in normalized.split() if len(w) > 1)))
    return NameForms(normalized=normalized, compact=compact, tokens=tokens)


class ReviewActions:
    def __init__(
        self,
        review_repo: ReviewJsonRepository,
        store_repo: CanonicalStoreJsonRepository,
        alias_repo: AliasJsonRepository,
        deal_repo: DealJsonRepository,
    ) -> None:
        self._review_repo = review_repo
        self._store_repo = store_repo
        self._alias_repo = alias_repo
        self._deal_repo = deal_repo

    def approve(
        self,
        item: ReviewItem,
        reviewed_by: str,
        note: str | None = None,
    ) -> ReviewItem:
        """Approve: link the input name to the best candidate store."""
        now = datetime.now(timezone.utc)
        best = item.verdict.best
        if best is None and item.verdict.candidates:
            best = item.verdict.candidates[0]

        if best is None:
            raise ValueError(
                f"Cannot approve item {item.id}: no candidates available"
            )

        store_id = best.store_id
        logger.info(
            "Approving item %s -> store %s (%s)",
            item.id, store_id, best.store_name,
        )

        # Record the decision
        item.status = ReviewStatus.APPROVED
        item.reviewed_at = now
        item.decision = ReviewDecision(
            action=ReviewAction.APPROVE,
            reviewed_by=reviewed_by,
            store_id=store_id,
            note=note,
        )

        # Create alias for the input name -> matched store
        alias = StoreAlias(
            id=generate_id(),
            store_id=store_id,
            alias=item.input_name,
            alias_forms=build_name_forms(item.input_name),
            source=AliasSource.REVIEW,
            created_at=now,
        )
        self._alias_repo.save(alias)

        # Create deal linked to the matched store
        deal = Deal(
            id=generate_id(),
            store_id=store_id,
            raw_id=item.raw_id,
            source_id=item.verdict.record_id,
            description=item.verdict.input_name,
            scraped_at=item.created_at,
            resolved_at=now,
        )
        self._deal_repo.save(deal)

        self._review_repo.update(item)
        return item

    def approve_existing(
        self,
        item: ReviewItem,
        store_id: str,
        store_name: str,
        reviewed_by: str,
        note: str | None = None,
    ) -> ReviewItem:
        """Approve: link the input name to a manually selected existing store."""
        now = datetime.now(timezone.utc)
        logger.info(
            "Linking item %s -> existing store %s (%s)",
            item.id, store_id, store_name,
        )

        item.status = ReviewStatus.APPROVED
        item.reviewed_at = now
        item.decision = ReviewDecision(
            action=ReviewAction.APPROVE,
            reviewed_by=reviewed_by,
            store_id=store_id,
            note=note,
        )

        alias = StoreAlias(
            id=generate_id(),
            store_id=store_id,
            alias=item.input_name,
            alias_forms=build_name_forms(item.input_name),
            source=AliasSource.REVIEW,
            created_at=now,
        )
        self._alias_repo.save(alias)

        deal = Deal(
            id=generate_id(),
            store_id=store_id,
            raw_id=item.raw_id,
            source_id=item.verdict.record_id,
            description=item.verdict.input_name,
            scraped_at=item.created_at,
            resolved_at=now,
        )
        self._deal_repo.save(deal)

        self._review_repo.update(item)
        return item

    def create_new(
        self,
        item: ReviewItem,
        store_name: str,
        reviewed_by: str,
        note: str | None = None,
    ) -> ReviewItem:
        """Create a new canonical store for an unmatched name."""
        now = datetime.now(timezone.utc)
        logger.info(
            "Creating new store '%s' for item %s", store_name, item.id,
        )

        # Create the new canonical store
        store = CanonicalStore(
            id=generate_id(),
            name=store_name,
            name_forms=build_name_forms(store_name),
            created_at=now,
            updated_at=now,
        )
        self._store_repo.save(store)

        # Create alias for the input name -> new store
        alias = StoreAlias(
            id=generate_id(),
            store_id=store.id,
            alias=item.input_name,
            alias_forms=build_name_forms(item.input_name),
            source=AliasSource.REVIEW,
            created_at=now,
        )
        self._alias_repo.save(alias)

        # Create deal linked to the new store
        deal = Deal(
            id=generate_id(),
            store_id=store.id,
            raw_id=item.raw_id,
            source_id=item.verdict.record_id,
            description=item.verdict.input_name,
            scraped_at=item.created_at,
            resolved_at=now,
        )
        self._deal_repo.save(deal)

        # Record the decision
        item.status = ReviewStatus.CREATED
        item.reviewed_at = now
        item.decision = ReviewDecision(
            action=ReviewAction.CREATE_NEW,
            reviewed_by=reviewed_by,
            store_id=store.id,
            new_store_name=store_name,
            note=note,
        )

        self._review_repo.update(item)
        return item

    def discard(
        self,
        item: ReviewItem,
        reviewed_by: str,
        note: str | None = None,
    ) -> ReviewItem:
        """Discard: mark item as not worth resolving."""
        now = datetime.now(timezone.utc)
        logger.info("Discarding item %s", item.id)

        item.status = ReviewStatus.DISCARDED
        item.reviewed_at = now
        item.decision = ReviewDecision(
            action=ReviewAction.DISCARD,
            reviewed_by=reviewed_by,
            note=note,
        )

        self._review_repo.update(item)
        return item

    def skip(self, item: ReviewItem) -> ReviewItem:
        """Skip: defer review for later."""
        now = datetime.now(timezone.utc)
        logger.info("Skipping item %s", item.id)

        item.status = ReviewStatus.SKIPPED
        item.reviewed_at = now

        self._review_repo.update(item)
        return item
