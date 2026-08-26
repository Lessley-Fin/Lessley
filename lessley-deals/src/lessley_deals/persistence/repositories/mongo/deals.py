from __future__ import annotations

from typing import Any, Sequence

from pymongo import UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database

from lessley_deals.domain.models import Deal
from lessley_deals.persistence.serialization import deal_from_dict, to_dict


class DealMongoRepository:
    def __init__(self, db: Database) -> None:  # type: ignore[type-arg]
        self._col: Collection = db["deals"]  # type: ignore[type-arg]
        # No ``fingerprint`` index. It used to be unique, which this collection
        # cannot satisfy: rows imported from data/deals.json carry no such field
        # at all, and store+source+description+currency genuinely repeats across
        # distinct deals (404 groups today, the largest 10 rows deep). Nothing
        # queries the field either — the pipeline dedups against the *raw* repo
        # in ScrapeStage — so a plain index would only cost write throughput.
        self._col.create_index("store_id")
        # Every consumer query filters expired rows out, and the projector
        # sweeps by key — both would otherwise scan the whole collection.
        self._col.create_index("status")
        self._col.create_index("deal_key")

    def save(self, deal: Deal) -> None:
        self._col.update_one({"_id": deal.id}, {"$set": self._to_doc(deal)}, upsert=True)

    def bulk_upsert(self, deals: Sequence[Deal]) -> int:
        """Upsert deals by ``id`` in one round-trip. Returns the number written.

        This is how the versioning layer keeps ``deals`` current: a deal's id is
        stable across all its versions, so re-projecting it overwrites the row
        rather than growing a second copy of the same offer.
        """
        if not deals:
            return 0
        operations = [
            UpdateOne({"_id": deal.id}, {"$set": self._to_doc(deal)}, upsert=True)
            for deal in deals
        ]
        result = self._col.bulk_write(operations, ordered=False)
        return result.upserted_count + result.modified_count

    def delete_by_ids(self, deal_ids: Sequence[str]) -> int:
        if not deal_ids:
            return 0
        return self._col.delete_many({"_id": {"$in": list(deal_ids)}}).deleted_count

    def get_ids_by_source(self, source_id: str) -> set[str]:
        """Business keys of every row this source owns, expired ones included."""
        return {
            str(doc.get("id") or doc["_id"])
            for doc in self._col.find({"source_id": source_id}, {"_id": 1, "id": 1})
        }

    @staticmethod
    def _to_doc(deal: Deal) -> dict[str, Any]:
        doc = to_dict(deal)
        doc["_id"] = doc.pop("id")
        doc["fingerprint"] = deal.fingerprint
        return doc

    def exists_by_fingerprint(self, fingerprint: str) -> bool:
        return self._col.count_documents({"fingerprint": fingerprint}, limit=1) > 0

    def get_by_store(self, store_id: str) -> list[Deal]:
        result = []
        for doc in self._col.find({"store_id": store_id}):
            doc["id"] = doc.pop("_id")
            doc.pop("fingerprint", None)
            result.append(deal_from_dict(doc))
        return result

    def get_all(self) -> list[Deal]:
        result = []
        for doc in self._col.find():
            doc["id"] = doc.pop("_id")
            doc.pop("fingerprint", None)
            result.append(deal_from_dict(doc))
        return result
