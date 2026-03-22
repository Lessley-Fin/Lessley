from __future__ import annotations

from pathlib import Path

from lessley_deals.domain.enums import ReviewStatus
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.review.queue import ReviewQueue, QueueStats
from tests.factories import make_review_item


class TestQueueStats:
    def test_counts_are_correct(self, tmp_path: Path) -> None:
        repo = ReviewJsonRepository(tmp_path / "reviews.json")
        queue = ReviewQueue(repo)

        # Add items with different statuses
        pending1 = make_review_item()
        pending2 = make_review_item()
        approved = make_review_item()
        approved.status = ReviewStatus.APPROVED
        discarded = make_review_item()
        discarded.status = ReviewStatus.DISCARDED

        for item in [pending1, pending2, approved, discarded]:
            queue.add(item)

        stats = queue.stats()
        assert stats.total == 4
        assert stats.pending == 2
        assert stats.approved == 1
        assert stats.discarded == 1
        assert stats.created == 0
        assert stats.skipped == 0

    def test_empty_queue_stats(self, tmp_path: Path) -> None:
        repo = ReviewJsonRepository(tmp_path / "reviews.json")
        queue = ReviewQueue(repo)

        stats = queue.stats()
        assert stats.total == 0
        assert stats.pending == 0


class TestGetPending:
    def test_returns_only_pending(self, tmp_path: Path) -> None:
        repo = ReviewJsonRepository(tmp_path / "reviews.json")
        queue = ReviewQueue(repo)

        pending = make_review_item()
        approved = make_review_item()
        approved.status = ReviewStatus.APPROVED

        queue.add(pending)
        queue.add(approved)

        result = queue.get_pending()
        assert len(result) == 1
        assert result[0].id == pending.id

    def test_empty_queue_returns_empty(self, tmp_path: Path) -> None:
        repo = ReviewJsonRepository(tmp_path / "reviews.json")
        queue = ReviewQueue(repo)

        result = queue.get_pending()
        assert result == []
