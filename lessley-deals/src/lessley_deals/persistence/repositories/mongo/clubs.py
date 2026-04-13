from __future__ import annotations

from pymongo.collection import Collection
from pymongo.database import Database

from lessley_deals.domain.models import Club
from lessley_deals.persistence.serialization import club_from_dict, to_dict


class ClubMongoRepository:
    def __init__(self, db: Database) -> None:  # type: ignore[type-arg]
        self._col: Collection = db["clubs"]  # type: ignore[type-arg]
        self._col.create_index("source_id", unique=True)

    def save(self, club: Club) -> None:
        doc = to_dict(club)
        doc["_id"] = doc.pop("id")
        self._col.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)

    def get_by_id(self, club_id: str) -> Club | None:
        doc = self._col.find_one({"_id": club_id})
        if doc is None:
            return None
        doc["id"] = doc.pop("_id")
        return club_from_dict(doc)

    def get_by_source(self, source_id: str) -> Club | None:
        doc = self._col.find_one({"source_id": source_id})
        if doc is None:
            return None
        doc["id"] = doc.pop("_id")
        return club_from_dict(doc)

    def get_all(self) -> list[Club]:
        result = []
        for doc in self._col.find():
            doc["id"] = doc.pop("_id")
            result.append(club_from_dict(doc))
        return result
