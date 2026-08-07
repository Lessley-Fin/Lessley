"""Project the pipeline's collections into the read model the services query.

The scraper owns ``deals`` / ``stores`` / ``clubs``; ``Lessley.Gateway.Api``
reads ``deal_list`` / ``store_list`` (see ``DealFinderRepository``) and
``Lessley.Personalization`` reads those plus ``club_list`` (see its
``models/db/entities.py``). They are not the same documents, so this is a
projection rather than a rename:

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

**Every field a consumer declares required has to be emitted here.** Beanie
validates each document as it loads and one bad row aborts the whole read, so
an omission is not a partial degradation — it takes the consumer down. That is
exactly how Personalization ended up in a crash loop: ``store_list`` carried
only ``id``/``name``/``metadata`` while its ``Store`` model also requires
``name_forms``, ``created_at`` and ``updated_at``. It only appeared healthy
beforehand because the collection was empty and the load found nothing to
validate. When changing a model on either side, change the projection with it.
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


def deal_list_document(
    deal: dict[str, Any], club_by_source: dict[str, str] | None = None
) -> dict[str, Any] | None:
    """One ``deals`` row -> one ``deal_list`` document.

    ``club_by_source`` maps ``source_id`` -> ``club_id`` and is how the club is
    recovered: every row in ``deals`` carries ``club_id = None``, because the
    deals were persisted before ``data/clubs.json`` existed and ``PersistStage``
    built its map from an empty club list (see ``persistence/seeding.py``).
    Falling back to the stored value keeps this correct once that is fixed
    upstream, and the source join fills the gap until then.
    """
    # Imported rows keep an ObjectId ``_id`` plus the business key in ``id``;
    # rows written by DealMongoRepository put the business key in ``_id``.
    deal_id = deal.get("id") or deal.get("_id")
    store_id = deal.get("store_id")
    if not deal_id or not store_id:
        return None

    source_id = deal.get("source_id") or ""
    club_id = deal.get("club_id") or (club_by_source or {}).get(source_id) or ""

    return {
        "id": str(deal_id),
        "store_id": store_id,
        # Required by Personalization's ``Deal``; absent here it rejects the row.
        "raw_id": deal.get("raw_id") or "",
        "source_id": source_id,
        "title": deal.get("title") or "",
        "deal_description": deal.get("deal_description"),
        "club_id": club_id,
        "scraped_at": _as_datetime(deal.get("scraped_at")),
        "resolved_at": _as_datetime(deal.get("resolved_at")),
        "benefit_url": deal.get("benefit_url"),
        "url": deal.get("url"),
        "redeem_channels": _redeem_channels(deal.get("constraints")),
        "coupon_code": deal.get("coupon_code"),
    }


def club_list_document(club: dict[str, Any]) -> dict[str, Any] | None:
    """One ``clubs`` document -> one ``club_list`` document.

    ``clubs`` keys on the business id, while Personalization's ``Club`` binds
    ``_id`` to an ObjectId and reads the business key from ``id`` — the same
    split ``store_list`` has.
    """
    club_id = club.get("_id") or club.get("id")
    if not club_id:
        return None

    return {
        "id": str(club_id),
        "name": club.get("name") or "",
        "source_id": club.get("source_id") or "",
        "description": club.get("description"),
        "metadata": club.get("metadata") or {},
        "stores": list(club.get("stores") or []),
    }


def store_list_document(store: dict[str, Any]) -> dict[str, Any] | None:
    """One ``stores`` document -> one ``store_list`` document.

    Returns None — dropping the store from search — when it has no usable
    timestamps, because Personalization's ``Store`` requires both and Beanie
    fails the *entire* load on one invalid row. Losing a single store from the
    index beats taking recommendations down for all of them, and the skip is
    logged rather than silent.
    """
    store_id = store.get("_id") or store.get("id")
    if not store_id:
        return None

    # Each falls back to the other so a row carrying only one still publishes.
    created_at = _as_datetime(store.get("created_at")) or _as_datetime(store.get("updated_at"))
    updated_at = _as_datetime(store.get("updated_at")) or created_at
    if created_at is None or updated_at is None:
        logger.warning(
            "Store %s has no parseable created_at/updated_at — omitting it from store_list",
            store_id,
        )
        return None

    name_forms = store.get("name_forms") or {}
    metadata = store.get("metadata") or {}
    return {
        "id": store_id,
        "name": store.get("name") or "",
        # Required by Personalization's ``Store``, which needs all three keys.
        "name_forms": {
            "normalized": name_forms.get("normalized") or "",
            "compact": name_forms.get("compact") or "",
            "tokens": list(name_forms.get("tokens") or []),
        },
        "created_at": created_at,
        "updated_at": updated_at,
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
    """Rebuild ``deal_list``, ``store_list`` and ``club_list`` from the pipeline's
    collections."""
    club_docs = [c for c in db["clubs"].find({})]
    # Built before the deals pass so every deal_list row can carry a real club.
    club_by_source = {
        c["source_id"]: str(c.get("_id") or c.get("id"))
        for c in club_docs
        if c.get("source_id")
    }

    clubs = _sync_collection(
        db,
        "club_list",
        (club_list_document(c) for c in club_docs),
    )
    deals = _sync_collection(
        db,
        "deal_list",
        (deal_list_document(d, club_by_source) for d in db["deals"].find({})),
    )
    stores = _sync_collection(
        db,
        "store_list",
        (store_list_document(s) for s in db["stores"].find({})),
    )

    logger.info(
        "Gateway view synced — deal_list: %d written / %d removed, "
        "store_list: %d written / %d removed, club_list: %d written / %d removed",
        deals["written"], deals["removed"], stores["written"], stores["removed"],
        clubs["written"], clubs["removed"],
    )
    return {"deal_list": deals, "store_list": stores, "club_list": clubs}
