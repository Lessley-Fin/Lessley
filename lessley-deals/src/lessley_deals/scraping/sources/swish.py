"""Swish (נפשונית) source adapter.

The actual browser-driven scrape lives in ``test_swish.py`` at the repo
root (Playwright + stealth, not async-friendly).  Run it separately to
refresh ``swish_database.json``, then the pipeline picks the data up
through this adapter.

Adapter responsibilities:
1. Load ``swish_database.json`` (the scraper output).
2. Optionally trigger :func:`sync_swish_groups` to refresh the
   ``hot_store_groups.json`` entries with resolved store IDs and push
   unresolved members to the review queue.  Sync requires an
   :class:`AliasIndex` + :class:`ReviewQueue` — those aren't available
   inside the adapter, so the CLI is responsible for calling sync
   *before* the scrape stage runs.
3. Emit one :class:`RawStore` per unique member business name across all
   benefits.  No deals are emitted — Swish is an enrichment source.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig
from lessley_deals.scraping.helpers.swish_group_sync import SWISH_SOURCE_ID

logger = logging.getLogger(__name__)


def _resolve_database_path(custom: Path | None = None) -> Path:
    """Locate ``swish_database.json``.

    Priority: explicit arg → repo root (where ``test_swish.py`` writes it).
    """
    if custom is not None:
        return custom
    # repo root is two levels above scraping/sources/
    return Path(__file__).resolve().parents[4] / "swish_database.json"


class SwishAdapter(BaseSourceAdapter):
    """Swish gift-card adapter — pulls from a pre-scraped JSON file."""

    def __init__(
        self,
        config: SourceConfig,
        database_path: Path | None = None,
    ) -> None:
        super().__init__(config)
        self._database_path = _resolve_database_path(database_path)

    @property
    def source_id(self) -> str:
        return SWISH_SOURCE_ID

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        """Read swish_database.json and emit one RawStore per unique member business.

        No RawScrapedRecord is emitted — Swish is an enrichment source, not a
        deal source. The emitted RawStore objects enter the normal pipeline
        (normalize → match → persist) to populate the canonical store catalog
        and feed the review queue for unresolved names.
        """
        if not self._database_path.exists():
            logger.warning(
                "Swish database not found at %s — skipping", self._database_path
            )
            return [], []

        with self._database_path.open(encoding="utf-8") as f:
            records = json.load(f)
        if not isinstance(records, list):
            logger.error(
                "Swish database has unexpected shape: %s", type(records).__name__
            )
            return [], []

        now = datetime.now(timezone.utc)
        seen_names: set[str] = set()
        stores: list[RawStore] = []

        for record in records:
            benefit_id = str(record.get("benefit_id") or "").strip()
            for raw_name in record.get("stores", []):
                name = str(raw_name).strip()
                if not name or name in seen_names:
                    continue
                seen_names.add(name)
                stores.append(
                    RawStore(
                        id=generate_id(),
                        source_id=self.source_id,
                        name=name,
                        scraped_at=now,
                        raw_payload={"benefit_id": benefit_id, "source": "swish"},
                    )
                )

        logger.info("Swish adapter emitted %d stores (0 deals)", len(stores))
        return stores, []
