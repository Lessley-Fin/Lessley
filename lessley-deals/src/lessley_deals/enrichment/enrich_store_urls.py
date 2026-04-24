from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse

from lessley_deals.persistence.config import PersistenceConfig
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository

logger = logging.getLogger(__name__)

_BLOCK_HOSTS: tuple[str, ...] = (
    "hot.co.il",
    "mastercard.com",
    "mastercard.co.il",
    "topcash.co.il",
    "behatsdaa.co.il",
    "tinyurl.com",
)


def clean_store_url(url: str | None) -> str | None:
    """Return scheme://netloc for a merchant URL, or None for blocklisted / invalid URLs."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    host = (parsed.hostname or "").lower()
    for blocked in _BLOCK_HOSTS:
        if host == blocked or host.endswith("." + blocked):
            return None
    return f"{parsed.scheme}://{parsed.netloc}"


def enrich_store_urls(
    data_dir: str = "data",
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, int]:
    """Populate `metadata.store_url` on each store using the first usable deal URL.

    The field is always written (explicit null when no usable URL exists) so
    consumers get a stable key. Stores that already have a non-null
    `store_url` are skipped unless `force=True`; stores with an existing null
    are re-checked in case new deals were added since the last run.
    """
    config = PersistenceConfig(base_dir=Path(data_dir))
    store_repo = CanonicalStoreJsonRepository(config.stores_path)
    deal_repo = DealJsonRepository(config.deals_path)

    stores = store_repo.get_all()
    deals = deal_repo.get_all()

    first_url: dict[str, str] = {}
    for deal in deals:
        if deal.store_id in first_url:
            continue
        cleaned = clean_store_url(deal.url)
        if cleaned:
            first_url[deal.store_id] = cleaned

    stats = {"set": 0, "nulled": 0, "skipped": 0, "total": len(stores)}

    for store in stores:
        has_key = "store_url" in store.metadata
        current = store.metadata.get("store_url")

        if not force and has_key and current is not None:
            stats["skipped"] += 1
            continue

        target = first_url.get(store.id)

        if not force and has_key and current == target:
            stats["skipped"] += 1
            continue

        store.metadata["store_url"] = target
        if target is not None:
            stats["set"] += 1
            logger.info("Set store_url for %s -> %s", store.name, target)
        else:
            stats["nulled"] += 1

        if not dry_run:
            store_repo.save(store)

    return stats
