"""Load deal dicts for the engine out of ``lessley-deals``' MongoDB.

Reads ``deals`` — the collection ``lessley-deals``' own Mongo repository writes,
in the same flat shape as its ``data/deals.json``. That file is the reference
format: one document per deal, with ``discount_logic`` and ``constraints``
embedded, which is already the plain-dict shape ``adapter.py`` accepts — so
there is no unwrapping to do. ``stores`` is its counterpart for store display
fields.

``Lessley.Gateway.Api`` and ``Lessley.Personalization`` read these same two
collections, so all three consumers now share one shape. There is no longer a
``deal_list``/``store_list`` projection in between — the C# and Python DTOs bind
the pipeline's documents directly.

The names stay overridable via ``DEALS_COLLECTION`` / ``STORES_COLLECTION``
rather than hardcoded, for pointing a debugging session at a copy. Note that
``deals`` is only as fresh as the last pipeline run that used Mongo storage
(``DEALS_STORAGE=mongo``): a database whose scrapes ran against the default JSON
storage will have a stale ``deals`` — and a stale copy predating
``discount_logic.reward.tiers`` makes a tiered loadable card look like an
uncapped flat rate, quoting 25% of a 10,000 ILS cart instead of stopping at the
card's 1,500 ILS ceiling. The failure is silent, since a stale-but-populated
collection returns plausible deals rather than erroring.

``deals_current``/``deal_versions`` are still written by the pipeline's
versioning layer, but they are history rather than the read path: they carry a
``snapshot`` sub-document instead of the flat deal, and only cover the sources
of whichever run last populated them. Reading them is what previously hid every
HOT deal from the optimizer.

Two consequences of ``deals`` being the source of truth, both deliberate:

* there is no ``status`` field to filter on, so an expired deal keeps being
  returned until it is deleted — the collection has no lifecycle of its own;
* the business key is ``_id`` on rows the pipeline writes, but imported rows
  keep an ObjectId ``_id`` plus a real ``id``, so it is read off whichever is
  present (see ``_to_engine_dict``).

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

# Defaults are the long-standing names, so an environment that was already
# working keeps working. Set these to "deal_list"/"store_list" where the Gateway
# projection is the fresher copy — see the module docstring for the trade-off.
DEALS_COLLECTION = os.environ.get("DEALS_COLLECTION", "deals")
STORES_COLLECTION = os.environ.get("STORES_COLLECTION", "stores")

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
    collection = (db if db is not None else get_database())[DEALS_COLLECTION]
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


def load_store(store_id: str, db: Database | None = None) -> dict[str, Any] | None:  # type: ignore[type-arg]
    """Display fields for the store a cart is being priced at.

    Deals carry no imagery of their own — the pipeline attaches every image it
    scrapes alongside a deal to that deal's store, so this is where a client
    gets a picture to show next to a result.
    """
    collection = (db if db is not None else get_database())[STORES_COLLECTION]
    # The business key is ``_id`` on pipeline-written rows and ``id`` on imported
    # ones, the same split ``_to_engine_dict`` handles for deals.
    doc = collection.find_one({"$or": [{"_id": store_id}, {"id": store_id}]})
    if not doc:
        return None

    metadata = doc.get("metadata") or {}
    return {
        "store_id": store_id,
        "name": doc.get("name"),
        "store_url": metadata.get("store_url"),
        "image_urls": list(metadata.get("image_urls") or []),
        "mcc_codes": list(metadata.get("mcc_codes") or []),
    }


def _summarize_deal(deal: dict[str, Any]) -> dict[str, Any]:
    """One deal reduced to what a client renders — identity, link and terms.

    The terms fields are read out of the nested ``constraints``/``discount_logic``
    sub-documents rather than shipped whole: a client showing "why this deal
    applies and under what conditions" needs the handful of caps below, not the
    engine's full rule input.
    """
    constraints = deal.get("constraints") or {}
    limits = constraints.get("limits") or {}
    eligibility = constraints.get("eligibility") or {}
    reward = (deal.get("discount_logic") or {}).get("reward") or {}

    return {
        "deal_id": deal["id"],
        "title": deal.get("title"),
        "description": deal.get("deal_description"),
        "deal_type": deal.get("deal_type"),
        "source_id": deal.get("source_id"),
        "club_id": deal.get("club_id"),
        # Where the deal is claimed; ``url`` is the merchant's own site.
        "url": deal.get("benefit_url") or deal.get("url"),
        "store_url": deal.get("url"),
        "terms_and_conditions": deal.get("terms_and_conditions"),
        "minimum_purchase": limits.get("minimum_purchase"),
        "max_uses_per_transaction": limits.get("max_uses_per_transaction"),
        "max_uses_per_month": limits.get("max_uses_per_month"),
        "max_discount_amount": reward.get("max_discount_amount"),
        # True / "yes" / None — the same tri-state ``deal_eligibility`` reads.
        "membership_required": eligibility.get("membership_required"),
    }


def summarize_deals(deals: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Map deal_id → the display fields a client needs to render a result path.

    ``build_export_payload`` deliberately reduces each path to bare ``deal_id``
    strings and expects the application to resolve them against its own deals
    database. This ships that lookup alongside the payload so a client can
    render titles, links and benefit terms without a second round-trip per deal.
    """
    return {deal["id"]: _summarize_deal(deal) for deal in deals}
