from __future__ import annotations

from typing import Sequence

from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from lessley_deals.domain.models import RawStore
from lessley_deals.persistence.serialization import raw_store_from_dict, to_dict


class RawStoreMongoRepository:
    def __init__(self, db: Database) -> None:  # type: ignore[type-arg]
        self._col: Collection = db["raw_source_stores"]  # type: ignore[type-arg]
        self._col.create_index("fingerprint", unique=True)
        self._col.create_index("source_id")

    def _to_doc(self, store: RawStore) -> dict:  # type: ignore[type-arg]
        doc = to_dict(store)
        doc["_id"] = doc.pop("id")
        doc["fingerprint"] = store.fingerprint
        return doc

    def save(self, store: RawStore) -> None:
        doc = self._to_doc(store)
        try:
            self._col.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
        except DuplicateKeyError:
            # Same fingerprint already stored under a different _id — skip
            pass

    def save_many(self, stores: Sequence[RawStore]) -> None:
        for store in stores:
            self.save(store)

    def exists_by_fingerprint(self, fingerprint: str) -> bool:
        return self._col.count_documents({"fingerprint": fingerprint}, limit=1) > 0

    def get_all(self) -> list[RawStore]:
        result = []
        for doc in self._col.find():
            doc["id"] = doc.pop("_id")
            doc.pop("fingerprint", None)
            result.append(raw_store_from_dict(doc))
        return result

    def get_by_source(self, source_id: str) -> list[RawStore]:
        result = []
        for doc in self._col.find({"source_id": source_id}):
            doc["id"] = doc.pop("_id")
            doc.pop("fingerprint", None)
            result.append(raw_store_from_dict(doc))
        return result
