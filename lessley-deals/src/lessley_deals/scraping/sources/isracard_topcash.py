from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig
from lessley_deals.scraping.helpers.discount_parser import (
    check_stackable,
    extract_coupon,
    extract_redeem_channels,
)

logger = logging.getLogger(__name__)

_TOPCASH_URL = "https://www.topcash.co.il/all-stores"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

class IsracardTopcashAdapter(BaseSourceAdapter):
    """Scraper for Isracard TOPCASH benefits website."""

    def __init__(self, config: SourceConfig | None = None) -> None:
        super().__init__(
            config
            or SourceConfig(
                base_url=_TOPCASH_URL,
                rate_limit_rps=1.0,
                timeout_seconds=30.0,
            )
        )

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
        except Exception:
            logger.exception("[%s] Failed to fetch TOPCASH page", self.source_id)
            return [], []

        soup = BeautifulSoup(html, "html.parser")
        store_containers = soup.find_all("div", class_="store-container")

        logger.info("[%s] Found %d store containers", self.source_id, len(store_containers))

        now = datetime.now(timezone.utc)
        stores_map: dict[str, RawStore] = {}
        deals: list[RawScrapedRecord] = []

        for store in store_containers:
            try:
                record = self._process_store(store, now)
            except Exception:
                logger.warning("[%s] Failed to process a store container, skipping", self.source_id, exc_info=True)
                continue

            if record is None:
                continue

            deals.append(record)

            # Deduplicate stores by name.
            sname = record.store_name
            if sname and sname not in stores_map:
                stores_map[sname] = RawStore(
                    id=generate_id(),
                    source_id=self.source_id,
                    name=sname,
                    scraped_at=now,
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
                "constraints": {}
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
            "is_stackable": True,
            "redeem_channels": ["online"],
        }
        
        # also apply the discount parser if relevant
        combined_text = raw_payload["description"]
        stackable = check_stackable(combined_text)
        channels = extract_redeem_channels(combined_text) or ["online"]
        coupon = extract_coupon(combined_text)
        
        raw_payload.update({
            "stackable": stackable,
            "redeem_channels": channels,
            "coupon_code": coupon,
        })

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
