from __future__ import annotations

import logging

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig

logger = logging.getLogger(__name__)


class RamiLevyAdapter(BaseSourceAdapter):
    """Scraper for the Rami Levy JSON API.

    This adapter is expected to:
    1. Authenticate (if needed) using an :class:`AuthStrategy`.
    2. Fetch paginated JSON endpoints via :class:`HttpClient`.
    3. Deserialise store and deal data from the JSON responses.

    Currently returns empty results as a scaffold.
    """

    def __init__(self, config: SourceConfig | None = None) -> None:
        super().__init__(
            config
            or SourceConfig(
                base_url="https://www.rami-levy.co.il",
                rate_limit_rps=2.0,
                timeout_seconds=30.0,
            )
        )

    @property
    def source_id(self) -> str:
        return "rami_levy"

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        """Scrape Rami Levy promotions via their JSON API.

        Returns empty lists until real parsing logic is implemented.
        """
        logger.info("[%s] Starting scrape (stub implementation)", self.source_id)

        # TODO: Instantiate HttpClient with self.config
        # TODO: Apply auth strategy (e.g. ApiKeyAuth or NoAuth)
        # TODO: Fetch /api/stores endpoint, paginate with OffsetLimit
        # TODO: Fetch /api/promotions endpoint for each store
        # TODO: Deserialise JSON into RawStore and RawScrapedRecord via generate_id()
        # TODO: Handle rate-limiting and retries via HttpClient

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
        """Check that the Rami Levy API is reachable."""
        # TODO: Perform a lightweight GET to an API health/version endpoint
        logger.debug("[%s] Health check (stub – always True)", self.source_id)
        return True
