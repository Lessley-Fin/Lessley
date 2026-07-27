"""PaisPlus (paisplus.co.il — "Mifal HaPais" subscriber benefits) scraper.

Server-rendered site: every category page and every product page embeds its
full API response inline in a ``window.__PRELOADED_STATE__ = {...}`` script
tag (confirmed live against ``/category/<id>`` and ``/product/<id>``). A
single ``httpx`` GET per page is enough to get the same JSON the site's own
frontend consumes — no Selenium, no LLM inference, same "structured JSON"
spirit as ``hever.py``.

Two-stage fetch, both mandatory:

1. **Category page** (``dataApi.category.products``) — used *only* to
   enumerate ``product_id``s via the listing's own ``skip``/``show``/
   ``has_more`` pagination. Its ``club_price``/``discounted_price``/
   ``market_price`` are aggregates only (confirmed
   ``category_page_price_type_name == "המחיר הנמוך ביותר"`` — "the lowest
   price"), representing whichever branch is cheapest — never used as deal
   data.
2. **Product detail page** (``dataApi.product.product``) — the real deal
   source. ``restriction_description`` is the product's actual
   terms-and-conditions text (only present here, not on the listing).
   ``prices`` is a list of *branches*, each carrying its own
   ``display_provider_name``/``display_provider_address`` **and two
   purchasable price tiers** — ``club_price`` and ``discounted_price``,
   both redeemable against the same ``market_price`` face value. Confirmed
   live on product 32051 ("BULLS"): 5 branches, each with both tiers ->
   5 * 2 = 10 distinct deals for that one product. The two tiers are two
   discount depths of the same Pais Plus membership (not member vs.
   non-member), so no eligibility text is invented for either — the site's
   own ``restriction_description`` is copied verbatim into
   ``terms_and_conditions`` for both.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig
from lessley_deals.scraping.helpers.html_utils import clean_html

logger = logging.getLogger(__name__)

_BASE_URL = "https://paisplus.co.il"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_DEFAULT_CATEGORIES_PATH = Path(__file__).parent.parent / "config" / "paisplus_categories.json"

# Matches the "window.__PRELOADED_STATE__ = {...}" assignment; the JSON
# itself is parsed with json.JSONDecoder.raw_decode from right after the
# "=" so it's robust to whatever trailing JS/whitespace follows.
_STATE_RE = re.compile(r"window\.__PRELOADED_STATE__\s*=\s*")

# Best-effort brand extraction from the product's own title, e.g.
# "תו קנייה בשווי 150 ₪ לרשת BULLS שף בורגר" -> "BULLS שף בורגר".
# Falls back to the full title when no pattern matches — the downstream
# matching pipeline (matching/stages/*) is what actually resolves raw
# names to canonical stores, so this only needs to be "reasonable", not
# perfect.
_BRAND_RE = re.compile(r"(?:ל|ב)(?:רשת|מסעדת|מועדון)\s+(.+)$")

# Strips the shared "... לסניף <BRAND> " prefix off a prices[] entry's
# pricelist_name, leaving just the branch/locality, e.g.
# "תו קנייה בשווי 150 ₪ לסניף BULLS עכו" -> "עכו".
_BRANCH_PREFIX_RE = re.compile(r"^.*?לסניף\s+")

_MAX_CONCURRENT_CATEGORIES = 3
_MAX_CONCURRENT_DETAIL = 5
_DETAIL_REQUEST_DELAY = 0.5
_MAX_CATEGORY_PAGES = 20  # safety cap in case has_more/skip pagination misbehaves

_PRICE_TIERS: tuple[tuple[str, str], ...] = (
    ("club", "club_price"),
    ("discounted", "discounted_price"),
)


def _load_category_ids(path: Path | None = None) -> list[int]:
    """Load the configured category ids, cached-free (small file, read once at init)."""
    target = path or _DEFAULT_CATEGORIES_PATH
    try:
        with target.open(encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.warning("paisplus categories config not found at %s", target)
        return []
    except (json.JSONDecodeError, OSError):
        logger.exception("Failed to load paisplus categories from %s", target)
        return []
    if not isinstance(data, list):
        logger.error("paisplus_categories.json must be a list, got %s", type(data).__name__)
        return []
    return [int(c) for c in data if isinstance(c, (int, str)) and str(c).strip()]


def _extract_preloaded_state(html: str) -> dict[str, Any]:
    match = _STATE_RE.search(html)
    if not match:
        raise ValueError("__PRELOADED_STATE__ script not found on page")
    decoder = json.JSONDecoder()
    state, _end = decoder.raw_decode(html, match.end())
    if not isinstance(state, dict):
        raise ValueError("__PRELOADED_STATE__ did not decode to a JSON object")
    return state


def _extract_brand(product_name: str) -> str:
    match = _BRAND_RE.search(product_name or "")
    return match.group(1).strip() if match else (product_name or "").strip()


def _extract_branch(pricelist_name: str, brand: str) -> str:
    name = (pricelist_name or "").strip()
    match = _BRANCH_PREFIX_RE.match(name)
    remainder = name[match.end() :] if match else name

    # Strip only the leading words remainder shares with brand, not a full
    # startswith(brand) match -- confirmed live that a branch's own name
    # (e.g. "BULLS עכו") uses just the short brand token, while the
    # product-title-derived brand can carry trailing marketing words (e.g.
    # "BULLS שף בורגר"), so a full-string prefix never matches and the
    # branch name would wrongly include the brand token.
    remainder_words = remainder.split()
    brand_words = brand.split()
    i = 0
    while i < len(remainder_words) and i < len(brand_words) and remainder_words[i] == brand_words[i]:
        i += 1
    remainder = " ".join(remainder_words[i:]).strip(" -")

    return remainder or name


class PaisPlusAdapter(BaseSourceAdapter):
    """Scraper for the PaisPlus subscriber-benefits site.

    Category ids are config-driven (``scraping/config/paisplus_categories.json``)
    since the site has far more categories than any one scrape needs to
    cover — add more ids to that file to widen coverage.
    """

    def __init__(
        self,
        config: SourceConfig | None = None,
        *,
        category_ids: list[int] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(config or SourceConfig(base_url=_BASE_URL))
        self._category_ids = category_ids if category_ids is not None else _load_category_ids()
        self._transport = transport

    @property
    def source_id(self) -> str:
        return "paisplus"

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        if not self._category_ids:
            logger.warning("[%s] no categories configured, nothing to scrape", self.source_id)
            return [], []

        async with httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
            transport=self._transport,
        ) as client:
            cat_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_CATEGORIES)
            product_id_lists = await asyncio.gather(
                *[
                    self._fetch_category_product_ids(client, category_id, cat_semaphore)
                    for category_id in self._category_ids
                ]
            )

            product_ids: list[int] = []
            seen_ids: set[int] = set()
            for ids in product_id_lists:
                for pid in ids:
                    if pid not in seen_ids:
                        seen_ids.add(pid)
                        product_ids.append(pid)

            logger.info(
                "[%s] discovered %d unique product(s) across %d categor(y/ies)",
                self.source_id, len(product_ids), len(self._category_ids),
            )

            detail_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_DETAIL)
            details = await asyncio.gather(
                *[self._fetch_product_detail(client, pid, detail_semaphore) for pid in product_ids]
            )

        now = datetime.now(timezone.utc)
        seen_stores: dict[str, RawStore] = {}
        stores: list[RawStore] = []
        deals: list[RawScrapedRecord] = []

        for detail in details:
            if detail is None:
                continue
            for store, deal in self._to_raw_records(detail, now):
                if store.fingerprint not in seen_stores:
                    seen_stores[store.fingerprint] = store
                    stores.append(store)
                deals.append(deal)

        logger.info(
            "[%s] Parsed %d stores, %d deals from %d product(s)",
            self.source_id, len(stores), len(deals), len(product_ids),
        )
        return stores, deals

    # ------------------------------------------------------------------
    # Fetch helpers
    # ------------------------------------------------------------------

    async def _fetch_category_product_ids(
        self, client: httpx.AsyncClient, category_id: int, semaphore: asyncio.Semaphore
    ) -> list[int]:
        ids: list[int] = []
        url = f"{_BASE_URL}/category/{category_id}"
        skip = 0

        for _page in range(_MAX_CATEGORY_PAGES):
            params = {"skip": skip} if skip else None
            async with semaphore:
                try:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    state = _extract_preloaded_state(resp.text)
                except (httpx.HTTPError, ValueError):
                    logger.exception(
                        "[%s] failed to fetch category %s (skip=%d)", self.source_id, category_id, skip
                    )
                    break

            category = state.get("dataApi", {}).get("category", {})
            products = category.get("products") or []
            if not products:
                break

            new_ids = [pid for p in products if isinstance(pid := p.get("product_id"), int)]
            ids.extend(new_ids)

            if category.get("has_more") != "Y" or not new_ids:
                break
            skip += len(products)

        return ids

    async def _fetch_product_detail(
        self, client: httpx.AsyncClient, product_id: int, semaphore: asyncio.Semaphore
    ) -> dict[str, Any] | None:
        url = f"{_BASE_URL}/product/{product_id}"
        async with semaphore:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                state = _extract_preloaded_state(resp.text)
            except (httpx.HTTPError, ValueError):
                logger.exception("[%s] failed to fetch product %s", self.source_id, product_id)
                return None
            finally:
                await asyncio.sleep(_DETAIL_REQUEST_DELAY)

        product = state.get("dataApi", {}).get("product", {}).get("product")
        return product if isinstance(product, dict) else None

    # ------------------------------------------------------------------
    # Mapping: one product detail -> branch x tier fan-out
    # ------------------------------------------------------------------

    def _to_raw_records(
        self, product: dict[str, Any], now: datetime
    ) -> list[tuple[RawStore, RawScrapedRecord]]:
        product_id = product.get("product_id")
        product_name = str(product.get("product_name") or product.get("name") or "").strip()
        brand = _extract_brand(product_name)
        short_description = clean_html(product.get("short_description"))
        terms = clean_html(product.get("restriction_description"))
        images = product.get("images") or []
        main_image = next((img for img in images if img.get("main_image") == "Y"), None)
        image_url = (main_image or (images[0] if images else {})).get("image_url")
        benefit_url = f"{_BASE_URL}/product/{product_id}"
        online_hint = bool(product.get("merchant_site_url")) or any(
            kw in short_description for kw in ("באתר", "באפליקציה")
        )
        redeem_channels = ["physical_store", "online"] if online_hint else ["physical_store"]

        results: list[tuple[RawStore, RawScrapedRecord]] = []

        for entry in product.get("prices") or []:
            if not isinstance(entry, dict):
                continue
            market_price = entry.get("market_price")
            pricelist_name = str(entry.get("pricelist_name") or "")
            display_provider_name = str(entry.get("display_provider_name") or "").strip()
            branch = _extract_branch(pricelist_name, brand) or display_provider_name
            store_name = brand or display_provider_name
            if not store_name:
                continue

            store = RawStore(
                id=generate_id(),
                source_id=self.source_id,
                name=store_name,
                scraped_at=now,
                branch=branch or None,
                address=entry.get("display_provider_address"),
                url=None,
                raw_payload={
                    "source": "paisplus",
                    "product_id": product_id,
                    "provider_id": entry.get("provider_id"),
                    "provider_bn": entry.get("provider_bn"),
                    "display_provider_name": display_provider_name,
                    "display_provider_phone": entry.get("display_provider_phone"),
                },
            )

            for tier, price_key in _PRICE_TIERS:
                tier_price = entry.get(price_key)
                if tier_price is None or market_price is None:
                    continue
                discount_amount = market_price - tier_price
                discount_logic = (
                    {
                        "type": "fixed_discount",
                        "condition": {"type": "min_quantity", "value": 1},
                        "reward": {"type": "fixed_discount_amount", "value": discount_amount},
                        "constraints": {},
                    }
                    if discount_amount > 0
                    else None
                )
                price_text = f"{tier_price} ₪ (מחיר מלא {market_price} ₪)"
                # Branch folded into deal_description (not just store_name)
                # because RawScrapedRecord.fingerprint is
                # sha256(source_id|deal_description|price_text), and
                # confirmed live: sibling branches of the same product can
                # share identical club/discounted/market prices (BULLS: all
                # 5 branches had 109/129/150) — without the branch name
                # folded in, ScrapeStage's fingerprint dedup would collapse
                # distinct branches into "already scraped", silently
                # dropping real deals. Mirrors hever.py's identical fix for
                # store_name (see hever.py's _to_raw_deal docstring).
                deal_description = (
                    f"{store_name} | {branch} | {short_description}"
                    if branch
                    else f"{store_name} | {short_description}"
                )

                raw_payload: dict[str, Any] = {
                    "source": "paisplus",
                    "product_id": product_id,
                    "price_tier": tier,
                    "branch": branch,
                    "deal_title": product_name,
                    "full_description": short_description,
                    "terms_and_conditions": terms,
                    "benefit_url": benefit_url,
                    "store_url": None,
                    "currency": "ILS",
                    "discount_logic": discount_logic,
                    "coupon_code": None,
                    "redeem_channels": redeem_channels,
                    "stackable": False,
                    "image_url": image_url,
                }

                deal = RawScrapedRecord(
                    id=generate_id(),
                    source_id=self.source_id,
                    store_name=store_name,
                    deal_description=deal_description,
                    price_text=price_text,
                    scraped_at=now,
                    url=benefit_url,
                    raw_payload=raw_payload,
                )
                results.append((store, deal))

        return results
