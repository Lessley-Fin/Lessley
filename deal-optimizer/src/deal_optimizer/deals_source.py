"""Load deal dicts for the engine out of ``lessley-deals``' MongoDB.

Reads ``deals_current`` — the SCD Type 2 *head* collection, one row per deal,
which is what product code is meant to read (filtered on ``status: "active"``).
The older append-only ``deals`` collection is deliberately **not** used: with
``DEALS_VERSIONING`` on (the default) the pipeline stops writing it entirely
unless ``DEALS_WRITE_LEGACY=1``, so reading it would silently return nothing.

Each head carries the full serialized ``Deal`` under ``snapshot`` (with ``id``
set to the stable deal id), which is already the plain-dict shape ``adapter.py``
accepts from a deals JSON file — so unwrapping that field is the whole mapping.

Store matching happens in the query rather than via ``engine._deal_matches_store``
so group-wide deals are caught in all the shapes the pipeline produces:
``store_id``, the resolved ``group_member_store_ids``, and the newer
``group_member_stores`` entries that are ``{name, store_id, confidence}`` dicts
rather than bare strings.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from pymongo import MongoClient
from pymongo.database import Database

DEFAULT_MONGO_URI = "mongodb://guest:guest@localhost:27017/lessley?authSource=admin"
DEFAULT_MONGO_DB = "lessley"

# DealLifecycleStatus.ACTIVE, as lessley-deals writes it (a StrEnum value).
ACTIVE_STATUS = "active"


@lru_cache(maxsize=1)
def get_database() -> Database:  # type: ignore[type-arg]
    """Return the deals database, reusing one pooled client per process."""
    uri = os.environ.get("MONGO_URI", DEFAULT_MONGO_URI)
    db_name = os.environ.get("MONGO_DB", DEFAULT_MONGO_DB)
    client: MongoClient = MongoClient(uri, serverSelectionTimeoutMS=5000)  # type: ignore[type-arg]
    return client[db_name]


def _to_engine_dict(doc: dict[str, Any]) -> dict[str, Any]:
    """Unwrap a ``deals_current`` head into the deal dict the engine reads."""
    deal = dict(doc.get("snapshot") or {})
    # ``snapshot`` already carries the stable ``id``; fall back to the head's
    # own deal_id/deal_key for rows written before that was the case, since the
    # engine keys every path and per_step entry on it.
    if not deal.get("id"):
        deal["id"] = doc.get("deal_id") or doc.get("_id")
    deal.setdefault("store_id", doc.get("store_id"))
    deal.setdefault("source_id", doc.get("source_id"))
    return deal


def load_store_deals(store_id: str, db: Database | None = None) -> list[dict[str, Any]]:  # type: ignore[type-arg]
    """Every active deal redeemable at ``store_id``, including group-wide ones."""
    collection = (db if db is not None else get_database())["deals_current"]
    cursor = collection.find(
        {
            # Leads with status so the (store_id, status) / (status, last_seen_at)
            # indexes on the collection are usable.
            "status": ACTIVE_STATUS,
            "$or": [
                {"store_id": store_id},
                {"snapshot.group_member_store_ids": store_id},
                {"snapshot.group_member_stores": store_id},
                {"snapshot.group_member_stores.store_id": store_id},
            ],
        }
    )
    return [_to_engine_dict(doc) for doc in cursor]


def summarize_deals(deals: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Map deal_id → the display fields a client needs to render a result path.

    ``build_export_payload`` deliberately reduces each path to bare ``deal_id``
    strings and expects the application to resolve them against its own deals
    database. This ships that lookup alongside the payload so a client can
    render titles without a second round-trip per deal in the path.
    """
    return {
        deal["id"]: {
            "deal_id": deal["id"],
            "title": deal.get("title"),
            "description": deal.get("deal_description"),
            "deal_type": deal.get("deal_type"),
            "source_id": deal.get("source_id"),
            "club_id": deal.get("club_id"),
            "url": deal.get("benefit_url") or deal.get("url"),
        }
        for deal in deals
    }
