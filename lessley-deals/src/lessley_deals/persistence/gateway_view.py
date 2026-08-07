"""Project the pipeline's collections into the read model the Gateway queries.

The scraper owns ``deals`` / ``stores``; ``Lessley.Gateway.Api`` reads
``deal_list`` / ``store_list`` (see ``DealFinderRepository``). They are not the
same documents, so this is a projection rather than a rename:

* ``scraped_at``/``resolved_at`` are ISO **strings** in ``deals``, and the C#
  driver needs real BSON dates to bind them to ``DateTime``;
* ``metadata.mcc_codes`` are canonical category names today, but older rows may
  still hold the raw 4-digit **numbers**, and the Gateway filters them with
  ``AnyIn(..., List<string>)``, which never matches an int;
* the Gateway's ``StoreDocument`` binds ``[BsonId]`` to an **ObjectId** and
  carries the business key in a separate ``id`` field, while ``stores`` uses
  the business key as ``_id`` directly.

``deals`` is the source of truth (see ``deal-optimizer``'s ``deals_source``),
so every row is published. Unlike ``deals_current`` it has no ``status``, which
means **there is no expiry filter here** — a deal disappears from search only
when it is deleted from ``deals``.

Writes are upserts keyed on ``id`` and stale rows are pruned after, so the view
is rebuilt in place and never observed empty by a live reader.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Iterable

from pymongo import UpdateOne

logger = logging.getLogger(__name__)

# The value each channel maps to when the constraints parser marked it available.
_TRUTHY = ("yes", "true", True, 1)


def _as_datetime(value: Any) -> datetime | None:
    """ISO string (or datetime) -> datetime. The C# driver cannot bind a string."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        logger.debug("Unparseable timestamp %r — leaving it null", value)
        return None


def _redeem_channels(constraints: Any) -> list[str]:
    """``{"website": "yes", "physical_store": "no"}`` -> ``["website"]``."""
    if not isinstance(constraints, dict):
        return []
    channels = constraints.get("redemption_channels") or {}
    if isinstance(channels, list):
        return [str(c) for c in channels]
    if not isinstance(channels, dict):
        return []
    return [name for name, available in channels.items() if available in _TRUTHY]


def deal_list_document(deal: dict[str, Any]) -> dict[str, Any] | None:
    """One ``deals`` row -> one ``deal_list`` document."""
    # Imported rows keep an ObjectId ``_id`` plus the business key in ``id``;
    # rows written by DealMongoRepository put the business key in ``_id``.
    deal_id = deal.get("id") or deal.get("_id")
    store_id = deal.get("store_id")
    if not deal_id or not store_id:
        return None

    return {
        "id": str(deal_id),
        "store_id": store_id,
        "title": deal.get("title") or "",
        "deal_description": deal.get("deal_description"),
        "club_id": deal.get("club_id") or "",
        "scraped_at": _as_datetime(deal.get("scraped_at")),
        "resolved_at": _as_datetime(deal.get("resolved_at")),
        "benefit_url": deal.get("benefit_url"),
        "url": deal.get("url"),
        "redeem_channels": _redeem_channels(deal.get("constraints")),
        "coupon_code": deal.get("coupon_code"),
    }


def store_list_document(store: dict[str, Any]) -> dict[str, Any] | None:
    """One ``stores`` document -> one ``store_list`` document."""
    store_id = store.get("_id") or store.get("id")
    if not store_id:
        return None

    metadata = store.get("metadata") or {}
    return {
        "id": store_id,
        "name": store.get("name") or "",
        "metadata": {
            # Stringified on purpose — the Gateway filters with List<string>.
            "mcc_codes": [str(code) for code in (metadata.get("mcc_codes") or [])],
            "store_url": metadata.get("store_url"),
            "image_urls": list(metadata.get("image_urls") or []),
        },
    }


def _sync_collection(
    db: Any, name: str, documents: Iterable[dict[str, Any] | None]
) -> dict[str, int]:
    """Upsert every document by ``id``, then delete the ones no longer produced."""
    docs = [d for d in documents if d is not None]
    if docs:
        db[name].bulk_write(
            [UpdateOne({"id": d["id"]}, {"$set": d}, upsert=True) for d in docs],
            ordered=False,
        )
    live_ids = [d["id"] for d in docs]
    removed = db[name].delete_many({"id": {"$nin": live_ids}}).deleted_count
    return {"written": len(docs), "removed": removed}


def sync_gateway_view(db: Any) -> dict[str, dict[str, int]]:
    """Rebuild ``deal_list`` and ``store_list`` from the pipeline's collections."""
    deals = _sync_collection(
        db,
        "deal_list",
        (deal_list_document(d) for d in db["deals"].find({})),
    )
    stores = _sync_collection(
        db,
        "store_list",
        (store_list_document(s) for s in db["stores"].find({})),
    )

    logger.info(
        "Gateway view synced — deal_list: %d written / %d removed, "
        "store_list: %d written / %d removed",
        deals["written"], deals["removed"], stores["written"], stores["removed"],
    )
    return {"deal_list": deals, "store_list": stores}
