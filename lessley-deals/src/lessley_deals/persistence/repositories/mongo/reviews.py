from __future__ import annotations

from pymongo.collection import Collection
from pymongo.database import Database

from lessley_deals.domain.models import ReviewItem
from lessley_deals.persistence.serialization import review_item_from_dict, to_dict


class ReviewMongoRepository:
    def __init__(self, db: Database) -> None:  # type: ignore[type-arg]
        self._col: Collection = db["store_match_review"]  # type: ignore[type-arg]
        self._col.create_index("status")

    def save(self, item: ReviewItem) -> None:
        doc = to_dict(item)
        doc["_id"] = doc.pop("id")
        self._col.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)

    def get_by_id(self, item_id: str) -> ReviewItem | None:
        doc = self._col.find_one({"_id": item_id})
        if doc is None:
            return None
        doc["id"] = doc.pop("_id")
        return review_item_from_dict(doc)

    def get_pending(self) -> list[ReviewItem]:
        result = []
        for doc in self._col.find({"status": "pending"}):
            doc["id"] = doc.pop("_id")
            result.append(review_item_from_dict(doc))
        return result

    def get_all(self) -> list[ReviewItem]:
        result = []
        for doc in self._col.find():
            doc["id"] = doc.pop("_id")
            result.append(review_item_from_dict(doc))
        return result

    def update(self, item: ReviewItem) -> None:
        # Partial update — only touch decision-related fields so concurrent
        # reviews of different items never clobber each other.
        update_fields = {
            "status": item.status.value if hasattr(item.status, "value") else item.status,
            "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
            "decision": to_dict(item.decision) if item.decision else None,
        }
        self._col.update_one({"_id": item.id}, {"$set": update_fields})
