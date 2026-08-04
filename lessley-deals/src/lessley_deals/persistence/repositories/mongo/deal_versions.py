"""MongoDB implementations of the deal history repositories.

Collections
-----------
``deal_versions``
    Append-only SCD Type 2 rows.  A partial unique index guarantees that at most
    one row per ``deal_key`` is ever marked ``is_current``.

``deals_current``
    Head table, one document per ``deal_key`` (used as ``_id``).  This is what
    product code should read — filter on ``status: "active"``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

from pymongo import ASCENDING, DESCENDING, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database

from lessley_deals.domain.enums import DealLifecycleStatus
from lessley_deals.domain.models import CurrentDeal, DealVersion
from lessley_deals.persistence.serialization import (
    current_deal_from_dict,
    deal_version_from_dict,
    to_dict,
)


class DealVersionMongoRepository:
    def __init__(self, db: Database) -> None:  # type: ignore[type-arg]
        self._col: Collection = db["deal_versions"]  # type: ignore[type-arg]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        # One immutable row per (deal_key, version) — makes replays idempotent.
        self._col.create_index([("deal_key", ASCENDING), ("version", ASCENDING)], unique=True)
        # At most one *current* row per deal_key — the SCD2 invariant, enforced
        # by the database rather than by hope.
        self._col.create_index(
            [("deal_key", ASCENDING), ("is_current", ASCENDING)],
            unique=True,
            partialFilterExpression={"is_current": True},
            name="uniq_current_version",
        )
        # "What changed for this source on that day" / audit queries.
        self._col.create_index([("source_id", ASCENDING), ("valid_from", DESCENDING)])
        self._col.create_index([("store_id", ASCENDING), ("status", ASCENDING)])
        self._col.create_index("run_id")

    def append_many(self, versions: Sequence[DealVersion]) -> None:
        if not versions:
            return
        operations = []
        for version in versions:
            doc: dict[str, Any] = to_dict(version)
            doc["_id"] = doc.pop("id")
            operations.append(
                UpdateOne(
                    {"deal_key": version.deal_key, "version": version.version},
                    {"$set": doc},
                    upsert=True,
                )
            )
        self._col.bulk_write(operations, ordered=False)

    def close_current(self, closures: Sequence[tuple[str, datetime]]) -> None:
        if not closures:
            return
        operations = [
            UpdateOne(
                {"deal_key": deal_key, "is_current": True},
                # `status` is left as-is on purpose — see the protocol docstring.
                {"$set": {"is_current": False, "valid_to": valid_to.isoformat()}},
            )
            for deal_key, valid_to in closures
        ]
        self._col.bulk_write(operations, ordered=False)

    def get_current(self, deal_key: str) -> DealVersion | None:
        doc = self._col.find_one({"deal_key": deal_key, "is_current": True})
        return self._to_model(doc) if doc else None

    def get_history(self, deal_key: str) -> list[DealVersion]:
        cursor = self._col.find({"deal_key": deal_key}).sort("version", ASCENDING)
        return [self._to_model(doc) for doc in cursor]

    def next_version(self, deal_key: str) -> int:
        doc = self._col.find_one({"deal_key": deal_key}, sort=[("version", DESCENDING)])
        return int(doc["version"]) + 1 if doc else 1

    def as_of(self, deal_key: str, moment: datetime) -> DealVersion | None:
        """Return the version that was in effect at ``moment`` — the point of SCD2."""
        stamp = moment.isoformat()
        doc = self._col.find_one(
            {
                "deal_key": deal_key,
                "valid_from": {"$lte": stamp},
                "$or": [{"valid_to": None}, {"valid_to": {"$gt": stamp}}],
            }
        )
        return self._to_model(doc) if doc else None

    @staticmethod
    def _to_model(doc: dict[str, Any]) -> DealVersion:
        doc = dict(doc)
        doc["id"] = doc.pop("_id")
        return deal_version_from_dict(doc)


class CurrentDealMongoRepository:
    def __init__(self, db: Database) -> None:  # type: ignore[type-arg]
        self._col: Collection = db["deals_current"]  # type: ignore[type-arg]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._col.create_index([("source_id", ASCENDING), ("status", ASCENDING)])
        self._col.create_index([("store_id", ASCENDING), ("status", ASCENDING)])
        self._col.create_index([("status", ASCENDING), ("last_seen_at", DESCENDING)])
        self._col.create_index("deal_id")
        self._col.create_index("content_hash")

    def bulk_upsert(self, heads: Sequence[CurrentDeal]) -> None:
        if not heads:
            return
        operations = []
        for head in heads:
            doc: dict[str, Any] = to_dict(head)
            doc["_id"] = head.deal_key
            operations.append(UpdateOne({"_id": head.deal_key}, {"$set": doc}, upsert=True))
        self._col.bulk_write(operations, ordered=False)

    def get(self, deal_key: str) -> CurrentDeal | None:
        doc = self._col.find_one({"_id": deal_key})
        return current_deal_from_dict(doc) if doc else None

    def get_by_source(self, source_id: str) -> list[CurrentDeal]:
        return [current_deal_from_dict(d) for d in self._col.find({"source_id": source_id})]

    def get_active(self, store_id: str | None = None) -> list[CurrentDeal]:
        query: dict[str, Any] = {"status": str(DealLifecycleStatus.ACTIVE)}
        if store_id is not None:
            query["store_id"] = store_id
        return [current_deal_from_dict(d) for d in self._col.find(query)]

    def count_active(self, source_id: str) -> int:
        return self._col.count_documents(
            {"source_id": source_id, "status": str(DealLifecycleStatus.ACTIVE)}
        )
