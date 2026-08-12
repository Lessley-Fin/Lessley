"""HOT Mobile benefits scraper adapter.

Fetches deals from the HOT loyalty club public API.  Supports:

- Paginated benefit list (``getAllBenefits``)
- Per-benefit detail fetch (``getDetailedBenefitByIdForWeb``)
- 7 benefit types: 100, 300, 700, 800, 1100, 1200, 1300
- XSRF cookie handshake
- Brand name cleaning (``_N`` suffix stripping)
- Discount mechanics deduction (6-level priority cascade)

The adapter produces thin ``RawStore`` / ``RawScrapedRecord`` instances.
Heavy normalisation happens downstream in the normalization pipeline.

Legacy lineage
--------------
- ``lessley-backend/Scraper/hot/hot_scraper.py`` — session, pagination, detail fetch
- ``lessley-backend/Scraper/hot/hot_extract_format.py`` — discount mechanics
- ``lessley-backend/Scraper/hot/export.py`` — benefit-type filtering, chunked detail fetch
- ``lessley-backend/Scraper/import_businesses.py`` — brand cleaning, generic filtering
"""

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
from lessley_deals.scraping.helpers.brand_utils import (
    clean_brand,
    clean_store_name,
    classify_group_deal_resolved,
    is_generic_hot_brand,
    load_hot_store_groups,
    normalize_website,
    resolve_group_store,
)
from lessley_deals.scraping.helpers.discount_parser import (
    classify_hot_benefit_type,
    deduce_hot_discount_mechanics,
)
from lessley_deals.scraping.helpers.html_utils import clean_html

logger = logging.getLogger(__name__)

BENEFIT_TYPES = ("100", "300", "700", "800", "1100", "1200", "1300")

# deal-optimizer's DealType per HOT benefitType code (confirmed against live
# data: 100 dominates the catalogue, 1300/800/700 are the next largest, 300/
# 1100/1200 are rare and deliberately left unmapped — deal-optimizer's own
# infer_deal_type() text-based fallback handles those when deal_type is None.
_BENEFIT_TYPE_DEAL_TYPE: dict[str, str] = {
    "100": "payment_discount",
    "700": "coupon",
    "800": "coupon",
    "1300": "giftcard_discount",
}

_BASE_URL = "https://www.hot.co.il"
_API_URL = "https://api.hot.co.il/api/website/2.0/getAllBenefits/"
_DETAILS_URL = "https://api.hot.co.il/api/website/2.0/getDetailedBenefitByIdForWeb/"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_PAGE_SIZE = 30


class HotAdapter(BaseSourceAdapter):
    """Scraper for the Hot Mobile benefits API.

    Fetches benefits (deals/promotions) from Hot Mobile's public API,
    iterating over all supported benefit types and pages.  Optionally
    enriches each benefit with detail-level data (terms, locations,
    discount mechanics).

    Produces raw, un-normalised :class:`RawStore` and
    :class:`RawScrapedRecord` instances.
    """

    def __init__(
        self,
        config: SourceConfig | None = None,
        benefit_types: tuple[str, ...] | None = None,
        *,
        fetch_details: bool = False,
        details_delay_seconds: float = 2.0,
        request_delay_seconds: float = 1.5,
    ) -> None:
        super().__init__(
            config
            or SourceConfig(
                base_url=_BASE_URL,
                rate_limit_rps=0.7,
                timeout_seconds=30.0,
            ),
        )
        self._benefit_types: tuple[str, ...] = benefit_types if benefit_types else BENEFIT_TYPES
        self._fetch_details = fetch_details
        self._details_delay = details_delay_seconds
        self._request_delay = request_delay_seconds
        self._api_url = _API_URL
        self._details_url = _DETAILS_URL
        self._client: httpx.AsyncClient | None = None
        self._store_groups = load_hot_store_groups()

    # ------------------------------------------------------------------
    # BaseSourceAdapter interface
    # ------------------------------------------------------------------

    @property
    def source_id(self) -> str:
        return "hot"

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        """Run the full scrape: session init, fetch, transform, return."""
        logger.info("[%s] Starting scrape (types=%s, details=%s)",
                    self.source_id, self._benefit_types, self._fetch_details)
        try:
            await self._initialize_session()
            benefits = await self._fetch_all_benefits()
            logger.info(
                "[%s] Fetched %d total benefit records", self.source_id, len(benefits)
            )

            # Optionally enrich with detail data
            if self._fetch_details:
                benefits = await self._enrich_with_details(benefits)

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
        logger.debug(
            "[%s] XSRF token set (%s...)",
            self.source_id,
            xsrf_token[:8] if len(xsrf_token) > 8 else xsrf_token,
        )

    def _extract_xsrf_token(self) -> str:
        """Pull the XSRF-TOKEN value from the client's cookie jar.

        Tries the cookie name directly first, then iterates the jar.
        Falls back to ``"1"`` if no cookie is found (legacy behaviour —
        the API commonly accepts it).
        """
        if self._client is None:
            return "1"

        jar = self._client.cookies
        token = jar.get("XSRF-TOKEN")
        if token:
            return token

        # Iterate the jar (some servers set the cookie on a different
        # domain/path, so direct lookup may miss it).
        for cookie in jar.jar:
            if cookie.name.upper() in {"XSRF-TOKEN", "CSRF-TOKEN"}:
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
    ) -> tuple[list[dict[str, Any]], int]:
        """Fetch a single page of benefits from the API.

        Returns ``(records, total_count)`` where ``total_count`` is the
        server-reported total for this benefit type (0 if not available).
        Returns an empty list on error / end of data.
        """
        if self._client is None:
            return [], 0

        form_data: dict[str, Any] = {
            "radius": "0",
            "page": str(page),
            "platform": "web",
            "size": str(_PAGE_SIZE),
        }

        # benefitType must be in the POST body, not the URL query string.
        # The API ignores query params on POST requests.
        if benefit_type:
            form_data["benefitType"] = benefit_type

        try:
            resp = await self._client.post(
                self._api_url, data=form_data
            )
            resp.raise_for_status()
            body = resp.json()
            data_block = body.get("data", {}) or {}
            records: list[dict[str, Any]] = data_block.get("records") or []
            total: int = int(data_block.get("total") or data_block.get("count") or 0)
            return records, total
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "[%s] HTTP %d fetching page %d (type=%s)",
                self.source_id,
                exc.response.status_code,
                page,
                benefit_type,
            )
            return [], 0
        except Exception:
            logger.exception(
                "[%s] Unexpected error fetching page %d (type=%s)",
                self.source_id,
                page,
                benefit_type,
            )
            return [], 0

    async def _fetch_all_for_type(
        self,
        btype: str,
        seen_ids: set[str],
        semaphore: asyncio.Semaphore,
    ) -> list[dict[str, Any]]:
        """Paginate all pages for a single benefit type.

        Uses ``semaphore`` to bound concurrent requests across types.
        Stops as soon as a page returns fewer records than ``_PAGE_SIZE``
        (early-termination — avoids an extra empty-page round-trip).
        """
        collected: list[dict[str, Any]] = []
        page = 1

        while True:
            async with semaphore:
                records, total = await self._fetch_benefits_page(page, benefit_type=btype)

            if not records:
                break

            new_count = 0
            for rec in records:
                rid = str(rec.get("id", ""))
                if rid and rid not in seen_ids:
                    seen_ids.add(rid)
                    collected.append(rec)
                    new_count += 1

            logger.info(
                "[%s] type=%-4s  page=%d  got=%d  new=%d  total_so_far=%d%s",
                self.source_id,
                btype,
                page,
                len(records),
                new_count,
                len(collected),
                f"  (server total: {total})" if total else "",
            )

            # Early stop: if the page wasn't full, there are no more pages.
            if len(records) < _PAGE_SIZE:
                break

            page += 1
            await asyncio.sleep(self._request_delay)

        return collected

    async def _fetch_all_benefits(self) -> list[dict[str, Any]]:
        """Fetch all benefit types concurrently and collect all records.

        De-duplicates by record ``id`` across types and pages.
        Types are fetched in parallel, bounded by a semaphore so we never
        fire more than ``_MAX_CONCURRENT_TYPES`` simultaneous requests.
        """
        _MAX_CONCURRENT = 3
        seen_ids: set[str] = set()
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

        logger.info(
            "[%s] Fetching %d benefit type(s) with up to %d concurrent requests: %s",
            self.source_id,
            len(self._benefit_types),
            _MAX_CONCURRENT,
            ", ".join(self._benefit_types),
        )

        tasks = [
            self._fetch_all_for_type(btype, seen_ids, semaphore)
            for btype in self._benefit_types
        ]
        results = await asyncio.gather(*tasks)

        all_records: list[dict[str, Any]] = [rec for chunk in results for rec in chunk]
        return all_records

    async def _fetch_benefit_details(
        self, benefit_id: str, is_commerce: str = "false"
    ) -> dict[str, Any] | None:
        """Fetch detailed info for a single benefit.

        Uses the multipart/form-data trick required by the API (files
        dict with ``(None, value)`` tuples).  Retries up to 3 times on
        429 Too Many Requests with exponential backoff.
        """
        if self._client is None:
            return None

        payload = {
            "benefitId": benefit_id,
            "isCommerce": is_commerce,
        }
        files = {k: (None, v) for k, v in payload.items()}

        _MAX_RETRIES = 3
        backoff = self._details_delay * 2

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = await self._client.post(
                    self._details_url,
                    files=files,
                    headers={"Accept": "application/json"},
                )
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", backoff))
                    logger.warning(
                        "[%s] 429 for benefit %s — waiting %.1fs (attempt %d/%d)",
                        self.source_id, benefit_id, retry_after, attempt, _MAX_RETRIES,
                    )
                    await asyncio.sleep(retry_after)
                    backoff *= 2
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError:
                logger.debug(
                    "[%s] HTTP error fetching details for benefit %s",
                    self.source_id, benefit_id, exc_info=True,
                )
                return None
            except Exception:
                logger.debug(
                    "[%s] Failed to fetch details for benefit %s",
                    self.source_id, benefit_id, exc_info=True,
                )
                return None

        logger.warning(
            "[%s] Giving up on benefit %s after %d retries (429)",
            self.source_id, benefit_id, _MAX_RETRIES,
        )
        return None

    # ------------------------------------------------------------------
    # Detail enrichment
    # ------------------------------------------------------------------

    def _merge_detail(self, record: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
        """Merge a detail API response into a benefit record."""
        merged = dict(record)
        merged["_detail"] = detail

        data = detail.get("data", {})
        main = data.get("main", {}) if isinstance(data, dict) else {}
        info = data.get("information", []) if isinstance(data, dict) else []
        main_info = main.get("information", []) if isinstance(main, dict) else []
        all_info = (info if isinstance(info, list) else []) + (
            main_info if isinstance(main_info, list) else []
        )

        terms_html = ""
        details_html = ""
        for section in all_info:
            if not isinstance(section, dict):
                continue
            section_title = section.get("title", "")
            content = section.get("content", "")
            if "תנאי" in section_title or "מימוש" in section_title:
                terms_html += content + " \n"
            elif "פרטי" in section_title:
                details_html += content + " \n"

        terms_text = clean_html(terms_html)
        details_text = clean_html(details_html)
        combined_text = f"{details_text} {terms_text}"

        merged["_terms_text"] = terms_text
        merged["_details_text"] = details_text
        merged["_dynamic_link"] = main.get("dynamicLink")
        merged["discount_logic"] = deduce_hot_discount_mechanics(main, combined_text)
        merged["image_url"] = f"https://cdn.hot.co.il{main.get('imagePath', '')}" if main.get('imagePath') else ""
        merged["_locations"] = self._extract_locations(data.get("supplierLocations", {}))
        merged["_benefit_type_classified"] = classify_hot_benefit_type(main if main else record)
        return merged

    async def _enrich_one(
        self,
        record: dict[str, Any],
        index: int,
        total: int,
        semaphore: asyncio.Semaphore,
    ) -> dict[str, Any]:
        """Fetch and merge detail for a single benefit record."""
        benefit_id = str(record.get("id") or "")
        if not benefit_id:
            return record

        async with semaphore:
            detail = await self._fetch_benefit_details(benefit_id)
            await asyncio.sleep(self._details_delay)

        if detail is None:
            return record

        logger.info(
            "[%s] Detail %d/%d id=%s OK", self.source_id, index, total, benefit_id
        )
        return self._merge_detail(record, detail)

    async def _enrich_with_details(
        self, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Fetch detail endpoint for each benefit and merge into the record.

        Enriches each record with:
        - ``_detail``: full detail response
        - ``_terms_text``: cleaned terms & conditions
        - ``_details_text``: cleaned offer details
        - ``discount_logic``: condition / reward
        - ``_locations``: branch addresses

        Details are fetched concurrently (up to 5 at a time).
        """
        _MAX_CONCURRENT = 5
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
        total = len(records)
        logger.info(
            "[%s] Enriching %d records with detail data (concurrency=%d)",
            self.source_id, total, _MAX_CONCURRENT,
        )

        tasks = [
            self._enrich_one(rec, i, total, semaphore)
            for i, rec in enumerate(records, 1)
        ]
        return list(await asyncio.gather(*tasks))

    @staticmethod
    def _extract_locations(
        supplier_locations: Any,
    ) -> list[dict[str, str]]:
        """Extract branch addresses from the detail ``supplierLocations`` field.

        The field can be either a ``dict[city, list[loc]]`` or a flat ``list[loc]``.
        """
        branches: list[dict[str, str]] = []
        if isinstance(supplier_locations, dict):
            for _city, locations in supplier_locations.items():
                if not isinstance(locations, list):
                    continue
                for loc in locations:
                    if isinstance(loc, dict) and loc.get("fullAddress"):
                        branches.append({
                            "address": loc["fullAddress"],
                            "city": loc.get("cityName", ""),
                            "lat": str(loc.get("lat", "")),
                            "lng": str(loc.get("lon", loc.get("lng", ""))),
                        })
        elif isinstance(supplier_locations, list):
            for loc in supplier_locations:
                if isinstance(loc, dict) and loc.get("fullAddress"):
                    branches.append({
                        "address": loc["fullAddress"],
                        "city": loc.get("cityName", ""),
                    })
        return branches

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_brand(brand: str) -> str:
        """Remove HOT-internal noise from a brand name.

        Delegates to shared :func:`clean_brand` from ``brand_utils``.
        """
        return clean_brand(brand)

    def _to_raw_store(
        self, record: dict[str, Any], now: datetime
    ) -> RawStore | None:
        """Create a :class:`RawStore` from a benefit record.

        Returns ``None`` if the record has no ``item_brand`` or if the
        brand is a generic HOT club name.

        When the brand belongs to a known store-group (e.g. "קבוצת פוקס"),
        the real sub-store name is resolved from the deal title and used
        instead of the group name.  When the deal is group-wide (no specific
        sub-store in the title), the group itself is kept as the store so that
        it gets its own :class:`CanonicalStore`.
        """
        brand = record.get("item_brand")
        if not brand:
            return None

        cleaned = self._clean_brand(brand)
        if is_generic_hot_brand(cleaned):
            return None

        title = record.get("title", "")
        store_name, _is_group_wide, _members = classify_group_deal_resolved(
            cleaned, title, self._store_groups
        )
        store_name = clean_store_name(store_name)

        return RawStore(
            id=generate_id(),
            source_id=self.source_id,
            name=store_name,
            scraped_at=now,
            raw_payload=record,
            url=record.get("supplierWebsite"),
        )

    def _to_raw_deal(
        self, record: dict[str, Any], now: datetime
    ) -> RawScrapedRecord:
        """Map a benefit record to a :class:`RawScrapedRecord`.

        When the brand belongs to a known store-group, the real sub-store
        name is resolved from the deal title.  When the deal is a group-wide
        gift card (no specific sub-store in the title), the group brand is
        kept as the store name and ``group_member_stores`` is added to
        ``raw_payload`` so that query-time fan-out can surface the deal for
        any member store.
        """
        raw_brand = record.get("item_brand") or record.get("title", "")
        title = record.get("title", "")
        group_member_stores: list[str] = []
        if raw_brand:
            logger.info("the title is [%s] and the raw brand is [%s]",
                    title, raw_brand)
            cleaned_brand = self._clean_brand(raw_brand)
            # נופשונית deals are Swish gift cards — each one references a specific
            # Swish benefit via a swish.co.il/product-XXXXX URL embedded in the
            # payload.  Substitute the brand with swish:{id} so the group classifier
            # can look up the correct member stores from hot_store_groups.json.
            # The original store name is preserved after classification.
            lookup_brand = cleaned_brand
            if cleaned_brand == "נופשונית":
                swish_ids = re.findall(r"product-(\d+)", str(record))
                for sid in swish_ids:
                    swish_key = f"swish:{sid}"
                    if swish_key in self._store_groups:
                        lookup_brand = swish_key
                        break
            store_name, is_group_wide, resolved_members = classify_group_deal_resolved(
                lookup_brand, title, self._store_groups
            )
            group_member_stores = [
                m["store_id"] if m.get("store_id") else m["name"]
                for m in resolved_members
            ]
            if lookup_brand != cleaned_brand:
                store_name = cleaned_brand
            store_name = clean_store_name(store_name)
            logger.info("the group brand is [%s] and is_group_wide is [%s]",
                    store_name, is_group_wide)
        else:
            store_name = ""
            is_group_wide = False
        description = record.get("description", "")
        deal_description = f"{title} - {description}" if description else title
        price_text = record.get("value") or record.get("small_text") or ""

        supplier_website = record.get("supplierWebsite") or ""
        if supplier_website and not supplier_website.startswith("http"):
            supplier_website = f"https://{supplier_website}"
        benefit_id = record.get("id")
        url = supplier_website or (
            f"{self.config.base_url}/benefit/{benefit_id}" if benefit_id else None
        )

        payload = dict(record)

        if is_group_wide and group_member_stores:
            payload["group_member_stores"] = group_member_stores

        payload["deal_title"] = title
        payload["full_description"] = deal_description
        payload["benefit_url"] = record.get("_dynamic_link") or record.get("dynamicLink")
        benefit_type = str(record.get("benefit_type") or record.get("type") or "")
        payload["deal_type"] = _BENEFIT_TYPE_DEAL_TYPE.get(benefit_type)

        # Extract T&C from the record's own information array if detail hasn't
        # already been merged (which sets _terms_text via _merge_detail).
        if "_terms_text" not in record:
            terms_html = ""
            for section in record.get("information", []):
                if not isinstance(section, dict):
                    continue
                section_title = section.get("title", "")
                if "תנאי" in section_title or "מימוש" in section_title:
                    terms_html += section.get("content", "") + " \n"
            payload["terms_and_conditions"] = clean_html(terms_html) if terms_html else None
        else:
            payload["terms_and_conditions"] = record["_terms_text"] or None

        return RawScrapedRecord(
            id=generate_id(),
            source_id=self.source_id,
            store_name=str(store_name),
            deal_description=str(deal_description),
            price_text=str(price_text),
            scraped_at=now,
            raw_payload=payload,
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
