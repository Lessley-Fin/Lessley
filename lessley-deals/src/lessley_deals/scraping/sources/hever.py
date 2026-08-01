"""Hever ("חבר") gift-card store directory scraper.

Every field here is already structured in the site's own JSON — no LLM
inference needed, same spirit as ``hot.py``'s API-backed adapter. Unlike
``hever_teamim.py``'s dataset, this one turned out to require no login at
all: ``/bs2/datasets/giftcard.json`` is a plain public endpoint, so this
adapter fetches it live.

Source schema (one object per store in the JSON array), confirmed from a real
saved page's own extraction JS (``getCompanyInfo()`` on a ``gift_card_store``
detail page) and from the live JSON response itself:

- ``company``            store name
- ``company_desc``       short description
- ``company_category``   comma-separated categories
- ``sn``                 numeric store id -> ``gift_card_store?sn=<sn>``
- ``website``             bare domain, no scheme
- ``is_online``           "Y" / "N"
- ``online_limitations``  free text, only meaningful when is_online == "Y"
- ``limitations``         the store's own redemption constraints — copied
                           verbatim into ``terms_and_conditions``, no inference
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.hvr.co.il"
_DATASET_URL = f"{_BASE_URL}/bs2/datasets/giftcard.json?_"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Same fixed, program-wide loading bonus for every store in this directory —
# confirmed identical wording on the site's own gift_card_company page, not a
# per-store number.
_LOADING_BONUS_TEXT = (
    'ניתן לטעון כרטיס "חבר" הנטען ולקבל 30% הנחה על טעינת 1,000 ₪ ראשונים, '
    '25% הנחה על 1,000 ₪ הבאים ו-20% הנחה על 1,000 ₪ נוספים (עד 3,000 ₪ בסה"כ)'
)
_LOADING_BONUS_PRICE_TEXT = "30% הנחה בטעינה (עד 3,000 ₪)"


def _loading_bonus_discount_logic() -> dict[str, Any]:
    """The fixed Hever loading-bonus reward, hand-built rather than parsed
    from ``_LOADING_BONUS_PRICE_TEXT`` via ``build_discount_logic`` — that
    generic parser only extracts a single number and drops the "(עד 3,000
    ₪)" cap entirely. Real terms are 3 tiers (30% on the first 1,000 ₪
    loaded, 25% on the next 1,000, 20% on the next 1,000, 3,000 ₪ total —
    see ``_LOADING_BONUS_TEXT``); approximated here as a single flat 30%
    rate capped at the first 1,000 ₪ tier, since deal_optimizer's reward
    schema doesn't yet support multi-tier rewards. Returns a fresh dict per
    call so raw records never share a mutable nested dict by reference.
    """
    return {
        "type": "percentage",
        "condition": {"type": "min_quantity", "value": 1},
        "reward": {"type": "percentage_off", "value": 0.3, "max_discount_amount": 300},
    }


class HeverGiftCardAdapter(BaseSourceAdapter):
    """Deterministic scraper for the Hever gift-card ("של קבע") store directory.

    Fetches ``giftcard.json`` live (public endpoint, no login required) and
    maps every field directly; the only free text involved is copied
    verbatim from the source, never generated.
    """

    def __init__(
        self,
        config: SourceConfig | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(config or SourceConfig(base_url=_BASE_URL))
        self._transport = transport

    @property
    def source_id(self) -> str:
        return "hever_gift_card_company"

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        try:
            records = await self._fetch_records()
        except httpx.HTTPError:
            logger.exception("[%s] failed to fetch %s", self.source_id, _DATASET_URL)
            return [], []
        except ValueError:
            logger.exception("[%s] response from %s was not valid JSON", self.source_id, _DATASET_URL)
            return [], []

        now = datetime.now(timezone.utc)
        seen_stores: dict[str, RawStore] = {}
        stores: list[RawStore] = []
        deals: list[RawScrapedRecord] = []

        for record in records:
            if not isinstance(record, dict) or not record.get("company"):
                continue
            store = self._to_raw_store(record, now)
            if store.name not in seen_stores:
                seen_stores[store.name] = store
                stores.append(store)
            deals.append(self._to_raw_deal(record, now))

        logger.info(
            "[%s] Parsed %d stores, %d deals from %s",
            self.source_id, len(stores), len(deals), _DATASET_URL,
        )
        return stores, deals

    async def _fetch_records(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
            transport=self._transport,
        ) as client:
            resp = await client.get(_DATASET_URL)
            resp.raise_for_status()
            data = resp.json()
        if not isinstance(data, list):
            raise ValueError(f"expected a JSON array, got {type(data).__name__}")
        return data

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _store_url(record: dict[str, Any]) -> str | None:
        website = str(record.get("website") or "").strip()
        return f"https://{website}" if website else None

    @staticmethod
    def _benefit_url(record: dict[str, Any]) -> str | None:
        sn = record.get("sn")
        return f"{_BASE_URL}/site/pg/gift_card_store?sn={sn}" if sn is not None else None

    def _loading_bonus_sentence(self, record: dict[str, Any]) -> str:
        """The fixed Hever loading-bonus sentence, naming the store.

        Appended to ``terms_and_conditions`` after the store's own
        ``limitations`` text — see ``_to_raw_deal``. Deliberately excludes
        ``company_desc``/``online_limitations``: those aren't limitations,
        so they don't belong in terms_and_conditions (company_desc feeds
        ``deal_description`` instead; online_limitations is kept verbatim in
        raw_payload for audit but not surfaced into either composed field).
        """
        company = str(record.get("company") or "").strip()
        return f"{_LOADING_BONUS_TEXT}, לשימוש ברשת {company}."

    def _to_raw_store(self, record: dict[str, Any], now: datetime) -> RawStore:
        return RawStore(
            id=generate_id(),
            source_id=self.source_id,
            name=str(record["company"]).strip(),
            scraped_at=now,
            url=self._store_url(record),
            raw_payload={"source": "hever_gift_card", "sn": record.get("sn")},
        )

    def _to_raw_deal(self, record: dict[str, Any], now: datetime) -> RawScrapedRecord:
        store_name = str(record["company"]).strip()
        deal_description = str(record.get("company_desc") or "").strip()
        limitations = str(record.get("limitations") or "").strip()
        loading_bonus_sentence = self._loading_bonus_sentence(record)
        # terms_and_conditions = the store's own limitations text, with the
        # fixed loading-bonus blurb appended as an extra sentence.
        terms = f"{limitations} {loading_bonus_sentence}".strip() if limitations else loading_bonus_sentence
        store_url = self._store_url(record)
        benefit_url = self._benefit_url(record)
        discount_logic = _loading_bonus_discount_logic()
        currency = "ILS"

        raw_payload: dict[str, Any] = {
            "source": "hever_gift_card",
            "sn": record.get("sn"),
            "category": record.get("company_category"),
            "logo": record.get("logo"),
            "is_online": record.get("is_online"),
            # Kept verbatim for audit — no longer folded into
            # terms_and_conditions or deal_description (see
            # _loading_bonus_sentence's docstring).
            "online_limitations": str(record.get("online_limitations") or "").strip(),
            # PersistStage (pipeline/persist_stage.py) reads deal_title /
            # full_description straight off raw_payload with no fallback —
            # set them explicitly so Deal.title/deal_description aren't left
            # null, same convention as hot.py / llm_scraper.py.
            "deal_title": store_name,
            "full_description": deal_description,
            "terms_and_conditions": terms,
            "benefit_url": benefit_url,
            "store_url": store_url,
            "currency": currency,
            "discount_logic": discount_logic,
            # Hever's card is a rechargeable/loadable balance, not a one-time
            # voucher — but for now every hever/pais deal is tagged uniformly
            # as "giftcard_discount" (deal-optimizer's DealType); a finer
            # rechargeable-vs-voucher split can follow later.
            "deal_type": "giftcard_discount",
        }
        internal_link = str(record.get("internal_link") or "").strip()
        if internal_link:
            raw_payload["internal_link"] = internal_link

        return RawScrapedRecord(
            id=generate_id(),
            source_id=self.source_id,
            store_name=store_name,
            # NOT plain `deal_description` — RawScrapedRecord.fingerprint is
            # sha256(source_id|deal_description|price_text), and price_text
            # is the same fixed string for every store while `company_desc`
            # is sometimes empty or a generic phrase shared by unrelated
            # companies. Without the store name folded in, ScrapeStage's
            # fingerprint dedup would treat a brand-new store as "already
            # scraped" whenever it collides with some other store's
            # fingerprint from an earlier run, silently dropping it. This is
            # fingerprint-only — raw_payload["full_description"] above stays
            # the plain `company_desc` text that PersistStage reads into the
            # final Deal.deal_description.
            deal_description=f"{store_name} | {deal_description}" if deal_description else store_name,
            price_text=_LOADING_BONUS_PRICE_TEXT,
            scraped_at=now,
            # PersistStage sets Deal.url = prec.raw.url directly (no
            # raw_payload lookup) — prefer the merchant's own site over the
            # internal gift_card_store?sn= detail page here so Deal.url ends
            # up pointing at the store, not at Hever's own page.
            url=store_url or benefit_url,
            raw_payload=raw_payload,
        )
