from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig

logger = logging.getLogger(__name__)

BENEFIT_TYPES = ("100", "300", "700", "800", "1100", "1200", "1300")

_BASE_URL = "https://www.hot.co.il"
_API_URL = "https://api.hot.co.il/api/website/2.0/getAllBenefits/"
_DETAILS_URL = "https://api.hot.co.il/api/website/2.0/getDetailedBenefitByIdForWeb/"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_PAGE_SIZE = 50


class HotAdapter(BaseSourceAdapter):
    """Scraper for the Hot Mobile benefits API.

    Fetches benefits (deals/promotions) from Hot Mobile's public API,
    iterating over all supported benefit types and pages.  Produces
    raw, un-normalised :class:`RawStore` and :class:`RawScrapedRecord`
    instances.
    """

    def __init__(self, config: SourceConfig | None = None) -> None:
        super().__init__(
            config
            or SourceConfig(
                base_url=_BASE_URL,
                rate_limit_rps=0.7,
                timeout_seconds=30.0,
            ),
        )
        self._api_url = _API_URL
        self._details_url = _DETAILS_URL
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # BaseSourceAdapter interface
    # ------------------------------------------------------------------

    @property
    def source_id(self) -> str:
        return "hot"

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        """Run the full scrape: session init, fetch, transform, return."""
        logger.info("[%s] Starting scrape", self.source_id)
        try:
            await self._initialize_session()
            benefits = await self._fetch_all_benefits()
            logger.info(
                "[%s] Fetched %d total benefit records", self.source_id, len(benefits)
            )

            now = datetime.now(timezone.utc)
            seen_brands: dict[str, RawStore] = {}
            stores: list[RawStore] = []
            deals: list[RawScrapedRecord] = []

            for record in benefits:
                # --- stores (one per unique brand) ---
                store = self._to_raw_store(record, now)
                if store is not None and store.name not in seen_brands:
                    seen_brands[store.name] = store
                    stores.append(store)

                # --- deals ---
                deals.append(self._to_raw_deal(record, now))

            logger.info(
                "[%s] Scrape complete - %d stores, %d deals",
                self.source_id,
                len(stores),
                len(deals),
            )
            return stores, deals
        finally:
            await self._close()

    async def health_check(self) -> bool:
        """Verify connectivity to the Hot Mobile website."""
        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds, follow_redirects=True
            ) as client:
                resp = await client.head(self.config.base_url)
                return resp.status_code < 400  # noqa: PLR2004
        except httpx.HTTPError:
            logger.debug("[%s] Health check failed", self.source_id, exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def _initialize_session(self) -> None:
        """Create the HTTP client and perform the XSRF cookie handshake."""
        self._client = httpx.AsyncClient(
            http2=True,
            timeout=self.config.timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": _USER_AGENT,
                "Origin": self.config.base_url,
                "Referer": self.config.base_url + "/",
            },
        )

        # Fetch the homepage to pick up session cookies.
        logger.debug("[%s] GET %s (cookie handshake)", self.source_id, self.config.base_url)
        await self._client.get(self.config.base_url)

        # Extract the XSRF-TOKEN value from the cookie jar.
        xsrf_token = self._extract_xsrf_token()
        self._client.headers["x-xsrf-token"] = xsrf_token
        logger.debug("[%s] XSRF token set (%s...)", self.source_id, xsrf_token[:8] if len(xsrf_token) > 8 else xsrf_token)

    def _extract_xsrf_token(self) -> str:
        """Pull the XSRF-TOKEN value from the client's cookie jar.

        Tries the cookie name directly first, then iterates the jar.
        Falls back to ``"1"`` if no cookie is found (legacy behaviour).
        """
        if self._client is None:
            return "1"

        # Direct lookup by name.
        jar = self._client.cookies
        token = jar.get("XSRF-TOKEN")
        if token:
            return token

        # Iterate over the jar (some servers set the cookie on a
        # different domain/path, so direct lookup may miss it).
        for cookie in jar.jar:
            if cookie.name == "XSRF-TOKEN":
                return cookie.value

        logger.warning(
            "[%s] XSRF-TOKEN cookie not found - using fallback value",
            self.source_id,
        )
        return "1"

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    async def _fetch_benefits_page(
        self, page: int, benefit_type: str = ""
    ) -> list[dict[str, Any]]:
        """Fetch a single page of benefits from the API.

        Returns the list of records, or an empty list on error / end of
        data.
        """
        if self._client is None:
            return []

        form_data: dict[str, Any] = {
            "radius": "0",
            "page": str(page),
            "platform": "web",
            "size": str(_PAGE_SIZE),
        }

        params: dict[str, str] = {}
        if benefit_type:
            params["benefitType"] = benefit_type

        try:
            resp = await self._client.post(
                self._api_url, data=form_data, params=params
            )
            resp.raise_for_status()
            body = resp.json()
            records: list[dict[str, Any]] = (
                body.get("data", {}).get("records") or []
            )
            return records
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "[%s] HTTP %d fetching page %d (type=%s)",
                self.source_id,
                exc.response.status_code,
                page,
                benefit_type,
            )
            return []
        except Exception:
            logger.exception(
                "[%s] Unexpected error fetching page %d (type=%s)",
                self.source_id,
                page,
                benefit_type,
            )
            return []

    async def _fetch_all_benefits(self) -> list[dict[str, Any]]:
        """Paginate through every benefit type and collect all records.

        De-duplicates by record ``id`` across types and pages.
        """
        seen_ids: set[str] = set()
        all_records: list[dict[str, Any]] = []

        for btype in BENEFIT_TYPES:
            page = 1
            logger.debug(
                "[%s] Fetching benefit type %s", self.source_id, btype
            )
            while True:
                records = await self._fetch_benefits_page(page, benefit_type=btype)
                if not records:
                    break

                for rec in records:
                    rid = str(rec.get("id", ""))
                    if rid and rid not in seen_ids:
                        seen_ids.add(rid)
                        all_records.append(rec)

                page += 1
                await asyncio.sleep(self.config.rate_limit_rps)

        return all_records

    async def _fetch_benefit_details(
        self, benefit_id: str, is_commerce: str = "false"
    ) -> dict[str, Any] | None:
        """Fetch detailed info for a single benefit.

        Uses the multipart/form-data trick required by the API (files
        dict with ``(None, value)`` tuples).
        """
        if self._client is None:
            return None

        payload = {
            "benefitId": benefit_id,
            "isCommerce": is_commerce,
        }
        files = {k: (None, v) for k, v in payload.items()}

        try:
            resp = await self._client.post(
                self._details_url,
                files=files,
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.debug(
                "[%s] Failed to fetch details for benefit %s",
                self.source_id,
                benefit_id,
                exc_info=True,
            )
            return None

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _to_raw_store(
        self, record: dict[str, Any], now: datetime
    ) -> RawStore | None:
        """Create a :class:`RawStore` from a benefit record.

        Returns ``None`` if the record has no ``item_brand``.
        """
        brand = record.get("item_brand")
        if not brand:
            return None

        return RawStore(
            id=generate_id(),
            source_id=self.source_id,
            name=brand,
            scraped_at=now,
            raw_payload=record,
            url=record.get("supplierWebsite"),
        )

    def _to_raw_deal(
        self, record: dict[str, Any], now: datetime
    ) -> RawScrapedRecord:
        """Map a benefit record to a :class:`RawScrapedRecord`."""
        store_name = record.get("item_brand") or record.get("title", "")
        title = record.get("title", "")
        description = record.get("description", "")
        deal_description = f"{title} - {description}" if description else title
        price_text = record.get("value") or record.get("small_text") or ""

        record_id = record.get("id")
        url = f"https://www.hot.co.il/benefit/{record_id}" if record_id else None

        return RawScrapedRecord(
            id=generate_id(),
            source_id=self.source_id,
            store_name=str(store_name),
            deal_description=str(deal_description),
            price_text=str(price_text),
            scraped_at=now,
            raw_payload=record,
            url=url,
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def _close(self) -> None:
        """Close the underlying HTTP client if open."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
