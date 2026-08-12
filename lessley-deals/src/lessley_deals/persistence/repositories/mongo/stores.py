from __future__ import annotations

from pymongo.collection import Collection
from pymongo.database import Database

from lessley_deals.domain.models import CanonicalStore
from lessley_deals.persistence.serialization import canonical_store_from_dict, to_dict


class CanonicalStoreMongoRepository:
    def __init__(self, db: Database) -> None:  # type: ignore[type-arg]
        self._col: Collection = db["stores"]  # type: ignore[type-arg]
        self._col.create_index("name_forms.normalized")

    def save(self, store: CanonicalStore) -> None:
        doc = to_dict(store)
        doc["_id"] = doc.pop("id")
        self._col.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)

    def get_by_id(self, store_id: str) -> CanonicalStore | None:
        doc = self._col.find_one({"_id": store_id})
        if doc is None:
            return None
        doc["id"] = doc.pop("_id")
        return canonical_store_from_dict(doc)

    def get_all(self) -> list[CanonicalStore]:
        result = []
        for doc in self._col.find():
            doc["id"] = doc.pop("_id")
            result.append(canonical_store_from_dict(doc))
        return result

    def search(self, query: str) -> list[CanonicalStore]:
        q = query.lower()
        result = []
        for doc in self._col.find({"$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"name_forms.normalized": {"$regex": q, "$options": "i"}},
        ]}):
            doc["id"] = doc.pop("_id")
            result.append(canonical_store_from_dict(doc))
        return result
