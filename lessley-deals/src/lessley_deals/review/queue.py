from __future__ import annotations

import logging
from dataclasses import dataclass

from lessley_deals.domain.enums import ReviewStatus
from lessley_deals.domain.models import ReviewItem
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository

logger = logging.getLogger(__name__)


@dataclass
class QueueFilter:
    status: ReviewStatus | None = None
    source_id: str | None = None


@dataclass
class QueueStats:
    total: int
    pending: int
    approved: int
    created: int
    discarded: int
    skipped: int


class ReviewQueue:
    def __init__(self, repo: ReviewJsonRepository) -> None:
        self._repo = repo

    def add(self, item: ReviewItem) -> None:
        logger.info("Adding review item %s for '%s'", item.id, item.input_name)
        self._repo.save(item)

    def get_pending(self, filter: QueueFilter | None = None) -> list[ReviewItem]:
        items = self._repo.get_pending()
        if filter is not None:
            if filter.status is not None:
                # If caller explicitly requests a non-pending status, fetch all
                # and filter; otherwise the repo already gave us pending items.
                if filter.status != ReviewStatus.PENDING:
                    items = [
                        i for i in self._repo.get_all()
                        if i.status == filter.status
                    ]
            if filter.source_id is not None:
                items = [
                    i for i in items
                    if i.verdict.record_id.startswith(filter.source_id)
                       or getattr(i, "source_id", None) == filter.source_id
                ]
        logger.debug("Returning %d pending items", len(items))
        return items

    def stats(self) -> QueueStats:
        all_items = self._repo.get_all()
        counts: dict[ReviewStatus, int] = {s: 0 for s in ReviewStatus}
        for item in all_items:
            counts[item.status] += 1
        return QueueStats(
            total=len(all_items),
            pending=counts[ReviewStatus.PENDING],
            approved=counts[ReviewStatus.APPROVED],
            created=counts[ReviewStatus.CREATED],
            discarded=counts[ReviewStatus.DISCARDED],
            skipped=counts[ReviewStatus.SKIPPED],
        )
