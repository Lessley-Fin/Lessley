from __future__ import annotations

import logging
from datetime import datetime, timezone

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig
from lessley_deals.scraping.engine.llm_scraper import LlmScrapeEngine

logger = logging.getLogger(__name__)


class LlmScraperAdapter(BaseSourceAdapter):
    """Generic AI scraper: render a configured URL and LLM-extract its deals."""

    def __init__(
        self,
        config: SourceConfig,
        *,
        site_id: str,
        url: str,
        instructions: str,
        max_len: int = 6000,
        engine: LlmScrapeEngine | None = None,
    ) -> None:
        super().__init__(config)
        self._site_id = site_id
        self._url = url
        self._instructions = instructions
        self._engine = engine or LlmScrapeEngine(
            timeout_seconds=config.timeout_seconds, max_len=max_len
        )

    @property
    def source_id(self) -> str:
        return self._site_id

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        try:
            extracted = await self._engine.run(self._url, self._instructions)
        except Exception:
            logger.exception("LLM scrape failed for %s (%s)", self._site_id, self._url)
            return [], []

        now = datetime.now(timezone.utc)
        seen_stores: set[str] = set()
        stores: list[RawStore] = []
        deals: list[RawScrapedRecord] = []

        for item in extracted:
            name = item.store_name.strip()
            if not name:
                continue
            if name not in seen_stores:
                seen_stores.add(name)
                stores.append(
                    RawStore(
                        id=generate_id(),
                        source_id=self._site_id,
                        name=name,
                        scraped_at=now,
                        url=item.url,
                        raw_payload={"source": "llm_scraper", "url": self._url},
                    )
                )
            deals.append(
                RawScrapedRecord(
                    id=generate_id(),
                    source_id=self._site_id,
                    store_name=name,
                    deal_description=item.deal_description.strip(),
                    price_text=item.price_text.strip(),
                    scraped_at=now,
                    url=item.url,
                    raw_payload=item.model_dump(),
                )
            )

        logger.info(
            "LLM adapter %s emitted %d stores, %d deals",
            self._site_id,
            len(stores),
            len(deals),
        )
        return stores, deals
