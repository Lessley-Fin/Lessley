from __future__ import annotations

import re

from pymongo.collection import Collection
from pymongo.database import Database

from lessley_deals.domain.models import StoreAlias
from lessley_deals.persistence.serialization import alias_from_dict, to_dict


class AliasMongoRepository:
    def __init__(self, db: Database) -> None:  # type: ignore[type-arg]
        self._col: Collection = db["store_aliases"]  # type: ignore[type-arg]
        # Non-unique index — same alias string can map to multiple stores
        # (matches JSON behaviour; find_by_alias returns the first match)
        self._col.create_index("alias")
        self._col.create_index("store_id")

    def save(self, alias: StoreAlias) -> None:
        doc = to_dict(alias)
        doc["_id"] = doc.pop("id")
        self._col.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)

    def find_by_alias(self, alias: str) -> StoreAlias | None:
        doc = self._col.find_one({"alias": alias})
        if doc is None:
            return None
        doc["id"] = doc.pop("_id")
        return alias_from_dict(doc)

    def get_all(self) -> list[StoreAlias]:
        result = []
        for doc in self._col.find():
            doc["id"] = doc.pop("_id")
            result.append(alias_from_dict(doc))
        return result

    def get_by_store(self, store_id: str) -> list[StoreAlias]:
        result = []
        for doc in self._col.find({"store_id": store_id}):
            doc["id"] = doc.pop("_id")
            result.append(alias_from_dict(doc))
        return result

    def search(self, query: str) -> list[StoreAlias]:
        """Case-insensitive substring search on ``alias`` and ``alias_forms.normalized``.

        Mirrors :meth:`AliasJsonRepository.search` so the review TUI works
        against either backend.
        """
        q = query.strip()
        if not q:
            return []
        pattern = re.escape(q)
        result = []
        for doc in self._col.find({"$or": [
            {"alias": {"$regex": pattern, "$options": "i"}},
            {"alias_forms.normalized": {"$regex": pattern, "$options": "i"}},
        ]}):
            doc["id"] = doc.pop("_id")
            result.append(alias_from_dict(doc))
        return result

    def delete(self, alias_id: str) -> None:
        self._col.delete_one({"_id": alias_id})
