from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup, Tag

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig

logger = logging.getLogger(__name__)

_TOPCASH_URL = "https://www.topcash.co.il/all-stores"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
_DETAIL_CONCURRENCY = 5
_DETAIL_DELAY = 0.5


class IsracardTopcashAdapter(BaseSourceAdapter):
    """Scraper for Isracard TOPCASH benefits website."""

    def __init__(self, config: SourceConfig | None = None, fetch_details: bool = True) -> None:
        super().__init__(
            config
            or SourceConfig(
                base_url=_TOPCASH_URL,
                rate_limit_rps=1.0,
                timeout_seconds=30.0,
            )
        )
        self._fetch_details = fetch_details

    @property
    def source_id(self) -> str:
        return "topcash"

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        logger.info("[%s] Starting scrape", self.source_id)

        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": _USER_AGENT},
            ) as client:
                resp = await client.get(self.config.base_url)
                resp.raise_for_status()
                html = resp.text

                soup = BeautifulSoup(html, "html.parser")
                store_containers = soup.find_all("div", class_="store-container")
                logger.info("[%s] Found %d store containers", self.source_id, len(store_containers))

                now = datetime.now(timezone.utc)
                deals: list[RawScrapedRecord] = []

                for store in store_containers:
                    try:
                        record = self._process_store(store, now)
                    except Exception:
                        logger.warning("[%s] Failed to process a store container, skipping", self.source_id, exc_info=True)
                        continue
                    if record is not None:
                        deals.append(record)

                if self._fetch_details:
                    deals = await self._enrich_with_details(client, deals)

        except Exception:
            logger.exception("[%s] Failed to fetch TOPCASH page", self.source_id)
            return [], []

        stores_map: dict[str, RawStore] = {}
        for record in deals:
            sname = record.store_name
            if sname and sname not in stores_map:
                stores_map[sname] = RawStore(
                    id=generate_id(),
                    source_id=self.source_id,
                    name=sname,
                    scraped_at=record.scraped_at,
                    url=record.url,
                    raw_payload={"source_page": _TOPCASH_URL},
                )

        stores = list(stores_map.values())
        logger.info(
            "[%s] Scrape complete – %d stores, %d deals",
            self.source_id,
            len(stores),
            len(deals),
        )
        return stores, deals

    async def _enrich_with_details(
        self, client: httpx.AsyncClient, deals: list[RawScrapedRecord]
    ) -> list[RawScrapedRecord]:
        """Fetch each deal's detail page and enrich raw_payload with description and terms."""
        semaphore = asyncio.Semaphore(_DETAIL_CONCURRENCY)
        logger.info("[%s] Enriching %d deals with detail pages", self.source_id, len(deals))

        async def enrich_one(record: RawScrapedRecord) -> RawScrapedRecord:
            benefit_url = record.raw_payload.get("benefit_url")
            if not benefit_url:
                return record
            async with semaphore:
                try:
                    resp = await client.get(benefit_url)
                    resp.raise_for_status()
                    detail_soup = BeautifulSoup(resp.text, "html.parser")

                    desc_tag = detail_soup.find("p", class_="details")
                    description = desc_tag.get_text(" ").strip() if isinstance(desc_tag, Tag) else None

                    limits_tag = detail_soup.find("div", id="limits")
                    terms = limits_tag.get_text(" ").strip() if isinstance(limits_tag, Tag) else None

                    updated_payload = dict(record.raw_payload)
                    if description:
                        updated_payload["full_description"] = description
                    if terms:
                        updated_payload["terms_and_conditions"] = terms

                    return RawScrapedRecord(
                        id=record.id,
                        source_id=record.source_id,
                        store_name=record.store_name,
                        deal_description=description or record.deal_description,
                        price_text=record.price_text,
                        scraped_at=record.scraped_at,
                        url=record.url,
                        raw_payload=updated_payload,
                    )
                except Exception:
                    logger.warning(
                        "[%s] Failed to fetch detail page %s, skipping",
                        self.source_id, benefit_url, exc_info=True,
                    )
                    await asyncio.sleep(_DETAIL_DELAY)
                    return record
            await asyncio.sleep(_DETAIL_DELAY)

        return list(await asyncio.gather(*[enrich_one(r) for r in deals]))

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds, follow_redirects=True
            ) as client:
                resp = await client.head(self.config.base_url, headers={"User-Agent": _USER_AGENT})
                return resp.status_code < 400
        except httpx.HTTPError:
            logger.debug("[%s] Health check failed", self.source_id, exc_info=True)
            return False

    def _process_store(self, store: BeautifulSoup, now: datetime) -> RawScrapedRecord | None:
        a_tag = store.find('div', class_='storeName').find('a')
        if not a_tag:
            return None

        title = a_tag.text.strip()
        details_url = a_tag.get('href', '')
        if details_url:
            details_url = details_url.strip()
            if details_url.startswith("/"):
                details_url = f"https://www.topcash.co.il{details_url}"

        external_id = None
        store_id = None
        if details_url:
            parts = details_url.rstrip('/').split('/')
            if len(parts) >= 2:
                store_id = parts[-2]
                external_id = parts[-1]

        subtitle_tag = store.find('div', class_='store-block-sub-title')
        reward_text = subtitle_tag.text.strip() if subtitle_tag else ""

        reward_type = "unknown"
        reward_value = None

        if '%' in reward_text:
            reward_type = "percentage_off"
            match = re.search(r'([\d.]+)', reward_text)
            if match:
                reward_value = float(match.group(1)) / 100.0
        elif '₪' in reward_text or "$" in reward_text:
            reward_type = "fixed_discount_amount"
            match = re.search(r'([\d.]+)', reward_text)
            if match:
                reward_value = float(match.group(1))

        img_tag = store.find('img')
        image_url = ""
        if img_tag:
            image_url = img_tag.get('data-src') or img_tag.get('src')
            if image_url and image_url.startswith('/'):
                image_url = f"https://www.topcash.co.il{image_url}"

        buy_btn = store.find('a', class_='isracard-new-button')
        store_url = buy_btn.get('href') if buy_btn else details_url
        if store_url:
            store_url = store_url.strip()
            if store_url.startswith("/"):
                store_url = f"https://www.topcash.co.il{store_url}"

        discount_logic = None
        if reward_type != "unknown":
            discount_logic = {
                "type": "percentage" if reward_type == "percentage_off" else "fixed_discount",
                "condition": {"type": "min_quantity", "value": 1},
                "reward": {
                    "type": reward_type,
                    "value": reward_value,
                },
            }

        # Build raw payload (mimicking the schema produced by legacy scraper and adapted slightly)
        raw_payload = {
            "external_id": external_id,
            "store_id": store_id,
            "club_id": "topcash",
            "title": f"{reward_text} באתר {title}",
            "description": f"{reward_text} באתר {title}. ההטבה מותנית במעבר דרך לינק הקאשבק.",
            "store_url": store_url,
            "benefit_url": details_url,
            "image_url": str(image_url).replace(" ", "%20"),
            "trigger_type": "auto",
            "discount_logic": discount_logic,
            # Every TopCash benefit is cashback paid on purchases made through
            # the TopCash referral link (deal-optimizer's DealType) — never a
            # store sale, coupon, or gift card.
            "deal_type": "cashback",
            "deal_title": f"{reward_text} באתר {title}",
            "full_description": f"{reward_text} באתר {title}. ההטבה מותנית במעבר דרך לינק הקאשבק.",
        }

        return RawScrapedRecord(
            id=generate_id(),
            source_id=self.source_id,
            store_name=title,
            deal_description=raw_payload["description"],
            price_text=reward_text,
            scraped_at=now,
            url=store_url,
            raw_payload=raw_payload,
        )
