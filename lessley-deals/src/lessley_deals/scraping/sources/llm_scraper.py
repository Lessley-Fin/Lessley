from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.enrichment.llm_client import DealDetail, ExtractedDeal
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig
from lessley_deals.scraping.engine.llm_scraper import LlmScrapeEngine

logger = logging.getLogger(__name__)

_NUM_RE = re.compile(r"([\d.]+)")


def build_discount_logic(price_text: str) -> tuple[dict[str, Any] | None, str]:
    """Derive a structured discount_logic dict + currency from price text.

    Deterministic (not LLM): mirrors the hand-coded adapters' logic so the AI
    scraper produces the same shape. Returns ``(logic_or_None, currency)``.
    """
    text = price_text or ""
    currency = "USD" if "$" in text else "ILS"
    match = _NUM_RE.search(text)
    value = float(match.group(1)) if match else None
    if value is None:
        return None, currency
    if "%" in text:
        return {
            "type": "percentage",
            "condition": {"type": "min_quantity", "value": 1},
            "reward": {"type": "percentage_off", "value": value / 100.0},
            "constraints": {},
        }, currency
    if "₪" in text or "$" in text:
        return {
            "type": "fixed_discount",
            "condition": {"type": "min_quantity", "value": 1},
            "reward": {"type": "fixed_discount_amount", "value": value},
            "constraints": {},
        }, currency
    return None, currency


class LlmScraperAdapter(BaseSourceAdapter):
    """Generic AI scraper: render a configured URL and LLM-extract its deals.

    Two modes:
    * default — single page, emit one record per extracted row.
    * ``crawl_details`` — follow each row's ``detail_url`` to its detail page and
      LLM-extract a rich blurb + terms, producing records that mirror the
      hand-coded adapters (title, discount_logic, terms, coupon, ...).
    """

    def __init__(
        self,
        config: SourceConfig,
        *,
        site_id: str,
        url: str,
        instructions: str,
        max_len: int = 6000,
        crawl_details: bool = False,
        detail_instructions: str = "",
        sample_limit: int | None = None,
        detail_concurrency: int = 3,
        render_wait_seconds: float = 0.0,
        wait_selector: str | None = None,
        file_path: str | None = None,
        is_json: bool = False,
        engine: LlmScrapeEngine | None = None,
    ) -> None:
        super().__init__(config)
        self._site_id = site_id
        self._url = url
        self._instructions = instructions
        self._crawl_details = crawl_details
        self._detail_instructions = detail_instructions
        self._sample_limit = sample_limit
        self._detail_concurrency = detail_concurrency
        self._file_path = file_path
        self._is_json = is_json
        self._engine = engine or LlmScrapeEngine(
            timeout_seconds=config.timeout_seconds,
            max_len=max_len,
            render_wait_seconds=render_wait_seconds,
            wait_selector=wait_selector,
        )

    @property
    def source_id(self) -> str:
        return self._site_id

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        try:
            pairs: list[tuple[ExtractedDeal, DealDetail | None]]
            if self._file_path:
                deals = await self._engine.run_from_file(
                    self._file_path, self._instructions, is_json=self._is_json
                )
                pairs = [(d, None) for d in deals]
            elif self._crawl_details:
                pairs = await self._engine.run_with_details(
                    self._url,
                    self._instructions,
                    self._detail_instructions,
                    sample_limit=self._sample_limit,
                    concurrency=self._detail_concurrency,
                )
            else:
                deals = await self._engine.run(self._url, self._instructions)
                pairs = [(d, None) for d in deals]
        except Exception:
            logger.exception("LLM scrape failed for %s (%s)", self._site_id, self._url)
            return [], []

        now = datetime.now(timezone.utc)
        seen_stores: set[str] = set()
        stores: list[RawStore] = []
        deals_out: list[RawScrapedRecord] = []

        for item, detail in pairs:
            name = item.store_name.strip()
            if not name:
                continue
            record = self._build_record(item, detail, now)
            if name not in seen_stores:
                seen_stores.add(name)
                stores.append(
                    RawStore(
                        id=generate_id(),
                        source_id=self._site_id,
                        name=name,
                        scraped_at=now,
                        url=record.url,
                        raw_payload={"source": "llm_scraper", "url": self._url},
                    )
                )
            deals_out.append(record)

        logger.info(
            "LLM adapter %s emitted %d stores, %d deals",
            self._site_id,
            len(stores),
            len(deals_out),
        )
        return stores, deals_out

    def _build_record(
        self, item: ExtractedDeal, detail: DealDetail | None, now: datetime
    ) -> RawScrapedRecord:
        """Assemble a RawScrapedRecord with an adapter-shaped rich raw_payload."""
        name = item.store_name.strip()
        price_text = item.price_text.strip()
        store_url = urljoin(self._url, item.detail_url) if item.detail_url else item.url

        discount_logic, currency = build_discount_logic(price_text)

        # store_id / external_id from the detail URL tail (…/store_id/external_id)
        store_id = external_id = None
        if store_url:
            parts = store_url.rstrip("/").split("/")
            if len(parts) >= 2:
                store_id, external_id = parts[-2], parts[-1]

        blurb = (detail.deal_description.strip() if detail and detail.deal_description else "")
        terms = (
            detail.terms_and_conditions.strip()
            if detail and detail.terms_and_conditions
            else item.terms_and_conditions.strip()
        )
        coupon = detail.coupon_code if detail else None
        description = blurb or item.deal_description.strip()
        title = f"{price_text} באתר {name}".strip()

        raw_payload: dict[str, Any] = {
            "source": "llm_scraper",
            "external_id": external_id,
            "store_id": store_id,
            "club_id": self._site_id,
            "title": title,
            "deal_title": title,
            "description": description,
            "full_description": description,
            "terms_and_conditions": terms,
            "benefit_url": store_url,
            "store_url": store_url,
            "currency": currency,
            "discount_logic": discount_logic,
            "coupon_code": coupon,
            "redeem_channels": ["online"],
            "stackable": False,
        }

        return RawScrapedRecord(
            id=generate_id(),
            source_id=self._site_id,
            store_name=name,
            deal_description=description,
            price_text=price_text,
            scraped_at=now,
            url=store_url,
            raw_payload=raw_payload,
        )
