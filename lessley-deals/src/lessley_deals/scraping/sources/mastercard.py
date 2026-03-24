from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup, Tag

from curl_cffi import requests as curl_requests

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig

logger = logging.getLogger(__name__)

_MC_URL = (
    "https://www.mastercard.co.il/he-il/personal/offers-and-promotions/"
    "mastercard-day.html"
)

# Characters to strip from extracted text (RTL markers + NBSP).
_JUNK_CHARS = str.maketrans("", "", "\xa0\u200e\u200f\u202a\u202b")

# Hebrew keywords used to split the title from the rest of the description.
_TITLE_SPLIT_RE = re.compile(
    r"[.]|\s+(?:תקף|תקפה|המבצע|ההטבה|כולל כפל|לא כולל|בלעדי)"
)

# Discount patterns.
_SPEND_SAVE_RE = re.compile(
    r"(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?.*?"
    r"(?:ברכישת|בקניית|מעל).*?"
    r"(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?"
)
_PERCENT_RE = re.compile(r"(\d+)%")

# Coupon code pattern.
_COUPON_RE = re.compile(r"קוד קופון[א-ת\s]*:?\s*([a-zA-Z0-9]{4,})")

# Stackable indicators.
_NOT_STACKABLE_RE = re.compile(r"לא כולל כפל מבצעים")
_STACKABLE_RE = re.compile(r"כולל כפל")

# Redeem channel indicators.
_ONLINE_RE = re.compile(r"באתר|אונליין")
_APP_RE = re.compile(r"באפליקציית")
_PHYSICAL_RE = re.compile(r"בחנויות|בסניפי")

# Block-level elements that should have a trailing newline when extracting text.
_BLOCK_TAGS = {"p", "div", "li", "h1", "h2", "h3"}


class MastercardAdapter(BaseSourceAdapter):
    """Scraper for the Mastercard Day promotions page.

    Uses *curl_cffi* with Chrome 120 impersonation to bypass TLS fingerprint
    checks on the Mastercard DXP-rendered page.
    """

    def __init__(self, config: SourceConfig | None = None) -> None:
        super().__init__(
            config
            or SourceConfig(
                base_url=_MC_URL,
                rate_limit_rps=1.0,
                timeout_seconds=30.0,
            )
        )

    # ------------------------------------------------------------------
    # BaseSourceAdapter interface
    # ------------------------------------------------------------------

    @property
    def source_id(self) -> str:
        return "mastercard"

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        """Fetch and parse the Mastercard Day promotions page."""
        logger.info("[%s] Starting scrape", self.source_id)

        html = await asyncio.to_thread(self._fetch_page)
        soup = BeautifulSoup(html, "html.parser")

        categories = self._extract_categories(soup)
        logger.info("[%s] Found %d categories", self.source_id, len(categories))

        now = datetime.now(timezone.utc)
        stores_map: dict[str, RawStore] = {}
        deals: list[RawScrapedRecord] = []

        blocks = soup.find_all("dxp-content-item")
        logger.info("[%s] Found %d content blocks", self.source_id, len(blocks))

        for block in blocks:
            try:
                record = self._process_block(block, soup, categories, now)
            except Exception:
                logger.warning(
                    "[%s] Failed to process a content block, skipping",
                    self.source_id,
                    exc_info=True,
                )
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
                    raw_payload={"source_page": _MC_URL},
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
        """Quick connectivity check against the Mastercard page."""
        try:
            resp = await asyncio.to_thread(
                curl_requests.head,
                _MC_URL,
                headers=self._default_headers(),
                impersonate="chrome120",
                timeout=10,
            )
            return resp.status_code < 400
        except Exception:
            logger.debug(
                "[%s] Health check failed", self.source_id, exc_info=True
            )
            return False

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _default_headers(self) -> dict[str, str]:
        return {
            "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            **self.config.headers,
        }

    def _fetch_page(self) -> str:
        """Synchronous HTTP GET via *curl_cffi* with browser impersonation."""
        logger.debug("[%s] Fetching %s", self.source_id, _MC_URL)
        resp = curl_requests.get(
            _MC_URL,
            headers=self._default_headers(),
            impersonate="chrome120",
            timeout=int(self.config.timeout_seconds),
        )
        resp.raise_for_status()
        return resp.text

    # ------------------------------------------------------------------
    # Category extraction
    # ------------------------------------------------------------------

    def _extract_categories(self, soup: BeautifulSoup) -> set[str]:
        """Extract validated category IDs from in-page navigation scripts."""
        categories: set[str] = set()
        for script in soup.find_all("script"):
            text = script.string or ""
            if "inPageNavItemsData" not in text:
                continue
            for match in re.findall(r'"href":"#(.*?)"', text):
                if soup.find("div", id=match):
                    categories.add(match)
        return categories

    # ------------------------------------------------------------------
    # Block processing (single dxp-content-item)
    # ------------------------------------------------------------------

    def _process_block(
        self,
        block: Tag,
        soup: BeautifulSoup,
        categories: set[str],
        now: datetime,
    ) -> RawScrapedRecord | None:
        """Parse one ``<dxp-content-item>`` and return a record, or *None*."""
        # --- Description text ---
        desc_html = block.get("description", "")
        if not desc_html:
            return None
        desc_soup = BeautifulSoup(str(desc_html), "html.parser")
        clean_text = desc_soup.get_text().translate(_JUNK_CHARS).strip()
        if not clean_text:
            return None

        # --- Image ---
        image_url: str | None = block.get("src")  # type: ignore[assignment]
        if image_url and not image_url.startswith("http"):
            image_url = f"https://www.mastercard.co.il{image_url}"

        # --- Modal ID (from embedded script) ---
        modal_id = self._extract_modal_id(block)

        # --- Store URL ---
        store_url = self._extract_store_url(block, modal_id, soup)

        # --- Modal full text ---
        modal_text = self._extract_modal_text(modal_id, soup) if modal_id else None

        # --- Title ---
        title = self._extract_title(clean_text)

        # --- Discount logic ---
        combined_text = f"{clean_text} {modal_text or ''}"
        logic = self._parse_discount_logic(combined_text, title)
        if logic is None:
            logger.debug(
                "[%s] No discount pattern matched for '%s', skipping",
                self.source_id,
                title[:60],
            )
            return None

        price_text = self._extract_price_text(logic)

        # --- Additional fields ---
        full_text = combined_text
        stackable = self._check_stackable(full_text)
        channels = self._extract_redeem_channels(full_text)
        coupon = self._extract_coupon(full_text)

        # --- Determine which category this block belongs to ---
        block_category: str | None = None
        parent = block.parent
        while parent:
            pid = parent.get("id") if isinstance(parent, Tag) else None
            if pid and pid in categories:
                block_category = str(pid)
                break
            parent = parent.parent  # type: ignore[assignment]

        raw_payload: dict[str, Any] = {
            "image_url": image_url,
            "modal_id": modal_id,
            "modal_text": modal_text,
            "store_url": store_url,
            "category": block_category,
            "discount_logic": logic,
            "stackable": stackable,
            "redeem_channels": channels,
            "coupon_code": coupon,
            "full_description": clean_text,
        }

        return RawScrapedRecord(
            id=generate_id(),
            source_id=self.source_id,
            store_name=modal_id,
            deal_description=clean_text,
            price_text=price_text,
            scraped_at=now,
            url=store_url or _MC_URL,
            raw_payload=raw_payload,
        )

    # ------------------------------------------------------------------
    # Modal extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_modal_id(block: Tag) -> str | None:
        """Extract the modal-target ID from an embedded script inside the block."""
        for script in block.find_all("script"):
            text = script.string or ""
            m = re.search(r'"modal-target"\s*:\s*"([^"]+)"', text)
            if m:
                return m.group(1)
        return None

    def _extract_modal_text(self, modal_id: str, soup: BeautifulSoup) -> str | None:
        """Extract cleaned plain text from a ``<dxp-modal>`` element."""
        modal = soup.find("dxp-modal", attrs={"modal-id": modal_id})
        if not modal or not isinstance(modal, Tag):
            return None

        container = modal.find(class_="text-editor")
        if not isinstance(container, Tag):
            container = modal

        # Replace <br> with newlines.
        for br in container.find_all("br"):
            br.replace_with("\n")

        # Append newlines after block-level elements.
        for tag in container.find_all(_BLOCK_TAGS):
            if isinstance(tag, Tag):
                tag.append("\n")

        raw = container.get_text(" ")
        # Clean RTL chars and collapse whitespace.
        text = raw.translate(_JUNK_CHARS)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() or None

    # ------------------------------------------------------------------
    # Store URL extraction
    # ------------------------------------------------------------------

    def _extract_store_url(
        self, block: Tag, modal_id: str | None, soup: BeautifulSoup
    ) -> str | None:
        """Extract the store URL from CTA script data or modal links.

        Handles two DXP CTA data formats observed in production:

        1. **Flat format** — ``ctaData = [{ctaText, ctaLink}]``
        2. **Nested format** — ``dxpSelector.ctaData = [{ctaList: [{text, href}]}]``
           (legacy Mastercard page variant)
        """
        store_url = None
        script_tag = block.find('script')
        if script_tag and script_tag.string:
            modal_match = re.search(r'"modal-target"\s*:\s*"([^"]+)"', script_tag.string)
            if modal_match:
                modal_id = modal_match.group(1)
            store_url = self.extract_store_url_from_script(script_tag.string)

            if not store_url and modal_id:
                modal = soup.find('dxp-modal', {'modal-id': modal_id})
                store_url = self.extract_store_url_from_modal(modal)
            
        return store_url

        # for script in block.find_all("script"):
        #     text = script.string or ""

        #     # --- Format 2: dxpSelector.ctaData = [{ctaList: [{text, href}]}] ---
        #     # Do this first as it is more specific and common.
        #     sel_match = re.search(r"dxpSelector\.ctaData\s*=\s*", text)
        #     if sel_match:
        #         url = self._parse_nested_cta(text, sel_match.end())
        #         if url:
        #             return url

        #     # --- Format 1: flat ctaData [{ctaText, ctaLink}] ---
        #     # Try flat ctaData using a safer extraction (finding where it ends instead of just .*?)
        #     cta_match = re.search(r"\bctaData\s*[:=]\s*(\[.*?\])\s*(?:;|,|\n|$)", text, re.DOTALL)
        #     if cta_match:
        #         url = self._parse_flat_cta(cta_match.group(1))
        #         if url:
        #             return url
            
        #     # Additional fallback: manually extract from string without regex just in case
        #     idx = text.find('dxpSelector.ctaData=')
        #     if idx != -1:
        #         url = self._parse_nested_cta(text, idx + len('dxpSelector.ctaData='))
        #         if url:
        #             return url

        # # Fallback: links inside the modal.
        # if modal_id:
        #     modal = soup.find("dxp-modal", attrs={"modal-id": modal_id})
        #     if modal and isinstance(modal, Tag):
        #         for a_tag in modal.find_all("a", href=True):
        #             href = a_tag["href"]
        #             if not isinstance(href, str):
        #                 continue
        #             if any(
        #                 skip in href.lower()
        #                 for skip in ("javascript:", ".pdf", "mastercard")
        #             ):
        #                 continue
        #             if href.startswith("http"):
        #                 return href

        # return None

    @staticmethod
    def extract_store_url_from_script(script_text):
        if not script_text:
            return None
        try:
            start_idx = script_text.find('dxpSelector.ctaData=')
            if start_idx != -1:
                array_str = script_text[start_idx:].split('dxpSelector.ctaData=')[1]
                end_idx = array_str.find('dxpSelector.actionList')
                if end_idx != -1:
                    array_str = array_str[:end_idx].strip()
                
                array_str = array_str.rstrip(';, \n')
                cta_data = json.loads(array_str)
                
                for group in cta_data:
                    for cta in group.get('ctaList', []):
                        if 'לאתר' in cta.get('text', ''):
                            return cta.get('href')
        except Exception:
            pass
        return None

    @staticmethod
    def extract_store_url_from_modal(modal):
        if modal:
            for a_tag in modal.find_all('a', href=True):
                href = a_tag['href']
                if "javascript" not in href.lower() and ".pdf" not in href.lower() and "mastercard" not in href.lower():
                    return href
        return None


    # @staticmethod
    # def _parse_flat_cta(json_str: str) -> str | None:
    #     """Parse flat ``[{ctaText, ctaLink}]`` format."""
    #     try:
    #         cta_list = json.loads(json_str)
    #         for cta in cta_list:
    #             if isinstance(cta, dict) and "לאתר" in cta.get("ctaText", ""):
    #                 url = cta.get("ctaLink", "")
    #                 if url:
    #                     return url
    #     except (json.JSONDecodeError, TypeError):
    #         pass
    #     return None

    # @staticmethod
    # def _parse_nested_cta(script_text: str, start: int) -> str | None:
    #     """Parse nested ``dxpSelector.ctaData = [{ctaList: [{text, href}]}]`` format.

    #     Ported from legacy ``mastercard_scraper.py :: extract_store_url_from_script``.
    #     """
    #     try:
    #         remainder = script_text[start:]
    #         # Find the end of the array (before dxpSelector.actionList or ;)
    #         end_idx = remainder.find("dxpSelector.actionList")
    #         if end_idx != -1:
    #             remainder = remainder[:end_idx]
    #         remainder = remainder.rstrip("; \n,")
    #         cta_data = json.loads(remainder)
    #         for group in cta_data:
    #             if not isinstance(group, dict):
    #                 continue
    #             for cta in group.get("ctaList", []):
    #                 if isinstance(cta, dict) and "לאתר" in cta.get("text", ""):
    #                     href = cta.get("href", "")
    #                     if href:
    #                         return href
    #     except (json.JSONDecodeError, TypeError, ValueError):
    #         pass
    #     return None

    # ------------------------------------------------------------------
    # Title extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_title(clean_text: str) -> str:
        """Extract the store/offer title from the beginning of the text."""
        parts = _TITLE_SPLIT_RE.split(clean_text, maxsplit=1)
        title = parts[0].strip()
        # If the split produced nothing useful, fall back to first 80 chars.
        if not title:
            title = clean_text[:80].strip()
        return title

    # ------------------------------------------------------------------
    # Discount logic
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_discount_logic(
        clean_text: str, title: str
    ) -> dict[str, Any] | None:
        """Return a structured discount dict, or *None* if no pattern matches.

        Returns a dict with ``type``, ``condition``, ``reward``, ``constraints``
        keys (matching the unified discount schema), plus ``matched_text``
        for traceability.

        Priority:
        1. Spend & Save (₪X הנחה ברכישת ₪Y)
        2. Percentage (X%)
        """
        from lessley_deals.scraping.helpers.discount_parser import deduce_mastercard_discount

        result = deduce_mastercard_discount(clean_text, title)
        if result is not None:
            return result

        # Legacy compat: also try the simpler regexes directly
        ss = _SPEND_SAVE_RE.search(clean_text)
        if ss:
            reward_raw = ss.group(1).replace(",", "")
            condition_raw = ss.group(2).replace(",", "")
            return {
                "type": "spend_and_save",
                "condition": {"type": "min_spend", "value": int(condition_raw)},
                "reward": {"type": "fixed_discount_amount", "value": int(reward_raw)},
                "constraints": {},
                "reward_amount": int(reward_raw),
                "condition_amount": int(condition_raw),
                "currency": "ILS",
                "matched_text": ss.group(0),
            }

        pct = _PERCENT_RE.search(title) or _PERCENT_RE.search(clean_text)
        if pct:
            return {
                "type": "percentage",
                "condition": {"type": "min_quantity", "value": 1},
                "reward": {"type": "percentage_off", "value": int(pct.group(1)) / 100.0},
                "constraints": {},
                "percent": int(pct.group(1)),
                "matched_text": pct.group(0),
            }

        return None

    @staticmethod
    def _extract_price_text(logic: dict[str, Any]) -> str:
        """Build a human-readable price/discount summary."""
        if logic["type"] == "spend_and_save":
            reward = logic.get("reward_amount") or logic.get("reward", {}).get("value", "")
            cond = logic.get("condition_amount") or logic.get("condition", {}).get("value", "")
            return f"{reward} ₪ הנחה ברכישה מעל {cond} ₪"
        if logic["type"] == "percentage":
            percent = logic.get("percent") or int(logic.get("reward", {}).get("value", 0.0) * 100)
            return f"{percent}% הנחה"
        return ""

    # ------------------------------------------------------------------
    # Ancillary field extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _check_stackable(text: str) -> bool:
        """Determine whether the deal is stackable with other promotions."""
        if _NOT_STACKABLE_RE.search(text):
            return False
        if _STACKABLE_RE.search(text):
            return True
        # Default: unknown / assume not stackable.
        return False

    @staticmethod
    def _extract_redeem_channels(text: str) -> list[str]:
        """Identify where the deal can be redeemed."""
        channels: list[str] = []
        if _ONLINE_RE.search(text):
            channels.append("online")
        if _APP_RE.search(text):
            channels.append("mobile_app")
        if _PHYSICAL_RE.search(text):
            channels.append("physical_store")
        return channels

    @staticmethod
    def _extract_coupon(text: str) -> str | None:
        """Extract a coupon code if present."""
        m = _COUPON_RE.search(text)
        return m.group(1) if m else None
