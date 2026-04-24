from __future__ import annotations

import logging
from pathlib import Path

from lessley_deals.enrichment.llm_client import get_store_category
from lessley_deals.persistence.config import PersistenceConfig
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository

logger = logging.getLogger(__name__)


def enrich_stores(
    data_dir: str = "data",
    limit: int = 0,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, int]:
    """Add `metadata.mcc_codes` to each store in stores.json using the LLM classifier.

    Additive and idempotent: stores that already have `mcc_codes` are skipped
    unless `force=True`. All other fields (id, name, name_forms, timestamps,
    existing metadata like image_urls) are preserved.
    """
    config = PersistenceConfig(base_dir=Path(data_dir))
    repo = CanonicalStoreJsonRepository(config.stores_path)
    stores = repo.get_all()

    stats = {"processed": 0, "skipped": 0, "failed": 0, "total": len(stores)}

    for store in stores:
        if limit and stats["processed"] >= limit:
            break

        if not force and "mcc_codes" in store.metadata:
            stats["skipped"] += 1
            logger.debug("Skipping already-enriched store: %s", store.name)
            continue

        try:
            result = get_store_category(store.name)
        except Exception as exc:
            stats["failed"] += 1
            logger.warning("Enrichment failed for %s: %s", store.name, exc)
            continue

        logger.info(
            "Enriched %s -> official=%s mcc=%s conf=%s",
            store.name, result.official_name, result.mcc_codes, result.confidence_level,
        )

        if not dry_run:
            store.metadata["mcc_codes"] = list(result.mcc_codes)
            repo.save(store)

        stats["processed"] += 1

    return stats
