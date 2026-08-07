"""Load deal dicts for the engine out of ``lessley-deals``' MongoDB.

Reads ``deals`` — the collection holding every deal the pipeline has resolved,
in the same flat shape as ``lessley-deals``' ``data/deals.json``. That file is
the reference format: one document per deal, with ``discount_logic`` and
``constraints`` embedded, which is already the plain-dict shape ``adapter.py``
accepts — so there is no unwrapping to do.

``deals_current``/``deal_versions`` are still written by the pipeline's
versioning layer, but they are history rather than the read path: they carry a
``snapshot`` sub-document instead of the flat deal, and only cover the sources
of whichever run last populated them. Reading them is what previously hid every
HOT deal from the optimizer.

Two consequences of ``deals`` being the source of truth, both deliberate:

* there is no ``status`` field to filter on, so an expired deal keeps being
  returned until it is deleted — the collection has no lifecycle of its own;
* the business key lives in ``id``, not ``_id`` (``_id`` is an ObjectId on
  imported rows), so it has to be read off the field rather than the key.

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

# Set by the repository layer, never part of the deal itself.
_INTERNAL_FIELDS = ("_id", "fingerprint")


@lru_cache(maxsize=1)
def get_database() -> Database:  # type: ignore[type-arg]
    """Return the deals database, reusing one pooled client per process."""
    uri = os.environ.get("MONGO_URI", DEFAULT_MONGO_URI)
    db_name = os.environ.get("MONGO_DB", DEFAULT_MONGO_DB)
    client: MongoClient = MongoClient(uri, serverSelectionTimeoutMS=5000)  # type: ignore[type-arg]
    return client[db_name]


def _to_engine_dict(doc: dict[str, Any]) -> dict[str, Any]:
    """Strip the storage-level fields off a ``deals`` row."""
    deal = {k: v for k, v in doc.items() if k not in _INTERNAL_FIELDS}
    # Rows written by DealMongoRepository put the business key in ``_id`` and
    # carry no ``id``; imported rows keep an ObjectId ``_id`` plus a real
    # ``id``. The engine keys every path and per_step entry on it, so it must
    # resolve to the business key either way.
    if not deal.get("id"):
        deal["id"] = str(doc.get("_id"))
    return deal


def load_store_deals(store_id: str, db: Database | None = None) -> list[dict[str, Any]]:  # type: ignore[type-arg]
    """Every deal redeemable at ``store_id``, including group-wide ones."""
    collection = (db if db is not None else get_database())["deals"]
    cursor = collection.find(
        {
            "$or": [
                # Indexed; the group fields are not, but they only ever match a
                # handful of rows and the collection is small enough to scan.
                {"store_id": store_id},
                {"group_member_store_ids": store_id},
                {"group_member_stores": store_id},
                {"group_member_stores.store_id": store_id},
            ]
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
