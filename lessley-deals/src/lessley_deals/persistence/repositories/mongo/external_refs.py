from __future__ import annotations

from pymongo.collection import Collection
from pymongo.database import Database

from lessley_deals.domain.models import ExternalReference
from lessley_deals.persistence.serialization import external_ref_from_dict, to_dict


class ExternalRefMongoRepository:
    def __init__(self, db: Database) -> None:  # type: ignore[type-arg]
        self._col: Collection = db["external_refs"]  # type: ignore[type-arg]
        self._col.create_index("store_id")
        self._col.create_index("system")

    def save(self, ref: ExternalReference) -> None:
        doc = to_dict(ref)
        doc["_id"] = doc.pop("id")
        self._col.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)

    def get_by_store(self, store_id: str) -> list[ExternalReference]:
        result = []
        for doc in self._col.find({"store_id": store_id}):
            doc["id"] = doc.pop("_id")
            result.append(external_ref_from_dict(doc))
        return result

    def get_by_system(self, system: str) -> list[ExternalReference]:
        result = []
        for doc in self._col.find({"system": system}):
            doc["id"] = doc.pop("_id")
            result.append(external_ref_from_dict(doc))
        return result

    def delete(self, ref_id: str) -> None:
        self._col.delete_one({"_id": ref_id})
