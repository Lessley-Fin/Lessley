"""Hever ("חבר") gift-card store directory scraper.

Unlike ``llm_scraper.py``-backed sources, every field here is already
structured in the site's own JSON — no LLM inference needed, same spirit as
``hot.py``'s API-backed adapter. The only difference from a normal API
adapter is *where* the JSON comes from: hvr.co.il requires a logged-in
session that this adapter doesn't automate, so it reads a locally saved
export instead of fetching live (see ``data/hever_snapshots/README.md``).

Source schema (one object per store in the JSON array), confirmed from a real
saved page's own extraction JS (``getCompanyInfo()`` on a ``gift_card_store``
detail page):

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

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig
from lessley_deals.scraping.sources.llm_scraper import build_discount_logic

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.hvr.co.il"

# Same fixed, program-wide loading bonus for every store in this directory —
# confirmed identical wording on the site's own gift_card_company page, not a
# per-store number. See data/hever_snapshots/README.md for how the source
# file is obtained.
_LOADING_BONUS_TEXT = (
    'ניתן לטעון כרטיס "חבר" הנטען ולקבל 30% הנחה על טעינת 1,000 ₪ ראשונים, '
    '25% הנחה על 1,000 ₪ הבאים ו-20% הנחה על 1,000 ₪ נוספים (עד 3,000 ₪ בסה"כ)'
)
_LOADING_BONUS_PRICE_TEXT = "30% הנחה בטעינה (עד 3,000 ₪)"


def _default_snapshot_path() -> Path:
    # sources/hever.py is at src/lessley_deals/scraping/sources/hever.py
    return (
        Path(__file__).resolve().parents[4]
        / "data"
        / "hever_snapshots"
        / "giftcard.json"
    )


class HeverGiftCardAdapter(BaseSourceAdapter):
    """Deterministic scraper for the Hever gift-card ("של קבע") store directory.

    Reads a locally saved copy of ``/bs2/datasets/giftcard.json`` (no live
    fetch — see module docstring) and maps every field directly; the only
    free text involved is copied verbatim from the source, never generated.
    """

    def __init__(
        self,
        config: SourceConfig | None = None,
        *,
        file_path: str | Path | None = None,
    ) -> None:
        super().__init__(config or SourceConfig(base_url=_BASE_URL))
        self._file_path = Path(file_path) if file_path else _default_snapshot_path()

    @property
    def source_id(self) -> str:
        return "hever_gift_card_company"

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        try:
            records = await asyncio.to_thread(self._read_records_sync)
        except FileNotFoundError:
            logger.warning(
                "[%s] snapshot not found at %s — drop a fresh export there "
                "(see data/hever_snapshots/README.md) and re-run",
                self.source_id,
                self._file_path,
            )
            return [], []
        except ValueError:
            logger.exception("[%s] snapshot at %s is not valid JSON", self.source_id, self._file_path)
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
            self.source_id, len(stores), len(deals), self._file_path,
        )
        return stores, deals

    def _read_records_sync(self) -> list[dict[str, Any]]:
        raw = self._file_path.read_text(encoding="utf-8")
        data = json.loads(raw)
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
        # loading-bonus blurb (previously the whole deal_description) appended
        # as an extra sentence rather than duplicated into deal_description.
        terms = f"{limitations} {loading_bonus_sentence}".strip() if limitations else loading_bonus_sentence
        store_url = self._store_url(record)
        benefit_url = self._benefit_url(record)
        discount_logic, currency = build_discount_logic(_LOADING_BONUS_PRICE_TEXT)

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
            "coupon_code": None,
            "redeem_channels": ["online", "physical_store"] if record.get("is_online") == "Y" else ["physical_store"],
            "stackable": False,
        }
        internal_link = str(record.get("internal_link") or "").strip()
        if internal_link:
            raw_payload["internal_link"] = internal_link

        return RawScrapedRecord(
            id=generate_id(),
            source_id=self.source_id,
            store_name=store_name,
            deal_description=deal_description,
            price_text=_LOADING_BONUS_PRICE_TEXT,
            scraped_at=now,
            # PersistStage sets Deal.url = prec.raw.url directly (no
            # raw_payload lookup) — prefer the merchant's own site over the
            # internal gift_card_store?sn= detail page here so Deal.url ends
            # up pointing at the store, not at Hever's own page.
            url=store_url or benefit_url,
            raw_payload=raw_payload,
        )
