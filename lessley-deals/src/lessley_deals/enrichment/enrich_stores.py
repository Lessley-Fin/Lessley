from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from lessley_deals.enrichment.llm_client import get_store_category
from lessley_deals.enrichment.mcc_catalog import normalize_mcc_codes
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

    Codes are canonical category names (`GROCERIES`, `RESTAURANT`, …), never the
    4-digit numbers — see `mcc_catalog`. Additive and idempotent: stores that
    already carry usable codes are skipped unless `force=True`, and stores whose
    codes are still in the legacy numeric form are converted in place without
    spending an LLM call. All other fields (id, name, name_forms, timestamps,
    existing metadata like image_urls) are preserved.
    """
    config = PersistenceConfig(base_dir=Path(data_dir))
    repo = CanonicalStoreJsonRepository(config.stores_path)
    stores = repo.get_all()

    stats = {"processed": 0, "converted": 0, "skipped": 0, "failed": 0, "total": len(stores)}

    for store in stores:
        if limit and stats["processed"] >= limit:
            break

        existing = store.metadata.get("mcc_codes")
        if existing and not force:
            canonical = normalize_mcc_codes(existing)
            if canonical == list(existing):
                stats["skipped"] += 1
                logger.debug("Skipping already-enriched store: %s", store.name)
                continue
            if canonical:
                # Legacy numeric codes (or off-vocabulary spellings) — resolvable
                # from the saved mapping, so no LLM call needed.
                logger.info("Converting %s mcc_codes %s -> %s", store.name, existing, canonical)
                if not dry_run:
                    store.metadata["mcc_codes"] = canonical
                    store.updated_at = datetime.now(timezone.utc)
                    repo.save(store)
                stats["converted"] += 1
                continue

        store_url: str | None = store.metadata.get("store_url")
        try:
            result = get_store_category(store.name, store_url=store_url)
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
            store.metadata["official_name"] = result.official_name
            store.metadata["mcc_confidence"] = result.confidence_level
            store.updated_at = datetime.now(timezone.utc)
            repo.save(store)

        stats["processed"] += 1

    return stats
