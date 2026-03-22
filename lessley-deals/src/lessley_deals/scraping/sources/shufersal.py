from __future__ import annotations

import logging

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig

logger = logging.getLogger(__name__)


class ShufersalAdapter(BaseSourceAdapter):
    """Scraper for the Shufersal promotions website (HTML).

    This adapter is expected to:
    1. Fetch the promotions listing pages using :class:`HttpClient`.
    2. Parse HTML with *selectolax* to extract store and deal data.
    3. Handle pagination across multiple listing pages.

    Currently returns empty results as a scaffold.
    """

    def __init__(self, config: SourceConfig | None = None) -> None:
        super().__init__(
            config
            or SourceConfig(
                base_url="https://www.shufersal.co.il",
                rate_limit_rps=1.0,
                timeout_seconds=30.0,
            )
        )

    @property
    def source_id(self) -> str:
        return "shufersal"

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        """Scrape Shufersal promotions.

        Returns empty lists until real parsing logic is implemented.
        """
        logger.info("[%s] Starting scrape (stub implementation)", self.source_id)

        # TODO: Instantiate HttpClient with self.config
        # TODO: Fetch the promotions landing page
        # TODO: Parse store list from HTML using selectolax
        # TODO: For each store, fetch deal pages and parse deal cards
        # TODO: Build RawStore and RawScrapedRecord instances via generate_id()
        # TODO: Handle pagination using PageNumber or OffsetLimit strategy

        stores: list[RawStore] = []
        deals: list[RawScrapedRecord] = []

        logger.info(
            "[%s] Scrape complete (stub) – %d stores, %d deals",
            self.source_id,
            len(stores),
            len(deals),
        )
        return stores, deals

    async def health_check(self) -> bool:
        """Check that the Shufersal website is reachable."""
        # TODO: Perform a lightweight HEAD request to self.config.base_url
        logger.debug("[%s] Health check (stub – always True)", self.source_id)
        return True
