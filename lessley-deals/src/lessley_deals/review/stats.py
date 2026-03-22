from __future__ import annotations

import logging

from lessley_deals.domain.enums import ReviewStatus
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.review.queue import QueueStats

logger = logging.getLogger(__name__)


class ReviewStats:
    """Compute statistics over the review queue."""

    def __init__(self, repo: ReviewJsonRepository) -> None:
        self._repo = repo

    def compute(self) -> QueueStats:
        """Return counts by status."""
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

    def approval_rate(self) -> float:
        """Fraction of reviewed items that were approved (APPROVED or CREATED)."""
        all_items = self._repo.get_all()
        reviewed = [
            i for i in all_items
            if i.status not in (ReviewStatus.PENDING, ReviewStatus.SKIPPED)
        ]
        if not reviewed:
            return 0.0
        approved_count = sum(
            1 for i in reviewed
            if i.status in (ReviewStatus.APPROVED, ReviewStatus.CREATED)
        )
        return approved_count / len(reviewed)

    def avg_confidence_at_review(self) -> float:
        """Average best-candidate confidence across all reviewed items."""
        all_items = self._repo.get_all()
        confidences: list[float] = []
        for item in all_items:
            if item.status in (ReviewStatus.PENDING, ReviewStatus.SKIPPED):
                continue
            best = item.verdict.best
            if best is None and item.verdict.candidates:
                best = item.verdict.candidates[0]
            if best is not None:
                confidences.append(best.confidence)
        if not confidences:
            return 0.0
        return sum(confidences) / len(confidences)
