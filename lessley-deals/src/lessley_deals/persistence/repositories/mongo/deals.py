from __future__ import annotations

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

    def save(self, deal: Deal) -> None:
        doc = to_dict(deal)
        doc["_id"] = doc.pop("id")
        doc["fingerprint"] = deal.fingerprint
        self._col.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)

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
