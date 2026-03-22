from __future__ import annotations

from pathlib import Path

from lessley_deals.domain.models import ReviewItem
from lessley_deals.persistence.json_store import JsonStore
from lessley_deals.persistence.serialization import review_item_from_dict, to_dict


class ReviewJsonRepository:
    def __init__(self, path: Path) -> None:
        self._store = JsonStore(path)

    def save(self, item: ReviewItem) -> None:
        self._store.append(to_dict(item))

    def get_by_id(self, item_id: str) -> ReviewItem | None:
        for d in self._store.read():
            if d["id"] == item_id:
                return review_item_from_dict(d)
        return None

    def get_pending(self) -> list[ReviewItem]:
        return [
            review_item_from_dict(d)
            for d in self._store.read()
            if d["status"] == "pending"
        ]

    def get_all(self) -> list[ReviewItem]:
        return [review_item_from_dict(d) for d in self._store.read()]

    def update(self, item: ReviewItem) -> None:
        self._store.update_by_id(item.id, to_dict(item))
