"""Behatsdaa (בהצדעה) loyalty-card scraper adapter.

File-based, same spirit as ``hever.py``'s and ``paisplus_cashcards.py``'s
"loading bonus" model: each Behatsdaa **wallet** (a monthly-loadable
giftcard, e.g. "load up to 500 ₪/month, get 15% off") maps to a flat
percentage discount, shared by every retail chain that wallet accepts.

Unlike Hever/PaisPlus, Behatsdaa's site requires a fresh login every time —
there is no stable public API key, and nothing in this repo ever wired up a
working ``AccessToken`` (see git history for the earlier live-API attempt).
So instead of fetching live, this adapter reads **locally saved** copies of
the wallet's own ``GetWalletChain`` JSON response — the same payload shape
the site's own app calls, just captured by hand after logging in — plus a
small config file giving each wallet's discount economics (which aren't
present in the ``GetWalletChain`` response itself).

Files
-----
- ``data/behatsdaa_snapshots/behatsdaa_giftcards_config.json`` — one entry
  per wallet, keyed by wallet id: ``file`` (the saved chains JSON, relative
  to this config's own directory, i.e. also inside ``behatsdaa_snapshots/``),
  ``name``, ``discount_percent``, ``max_deposit_per_month``, ``currency``,
  ``active``, ``notes``. Keys starting with ``_`` are treated as
  comments/examples and skipped, same convention as
  ``scraping/config/hot_store_groups.json``.
- Each wallet's own JSON file (also in ``data/behatsdaa_snapshots/``) — a
  verbatim saved response of
  ``GET https://back.behatsdaa.org.il/api/cards/GetWalletChain?walletId=<id>``:
  ``{"status": true, "data": [{"walletChainData": [{"chainID", "chainName",
  "webSite", "logoURL", ...}, ...]}, ...]}``.

To refresh: log in on behatsdaa.org.il, hit that endpoint for each wallet
(devtools network tab), and overwrite the matching file in
``data/behatsdaa_snapshots/``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig
from lessley_deals.scraping.helpers.brand_utils import (
    clean_brand,
    is_generic_behatsdaa_brand,
    normalize_website,
)

logger = logging.getLogger(__name__)

_SITE_URL = "https://www.behatsdaa.org.il"


def _lessley_deals_root() -> Path:
    # this file is at src/lessley_deals/scraping/sources/behatsdaa.py
    return Path(__file__).resolve().parents[4]


def _default_config_path() -> Path:
    return _lessley_deals_root() / "data" / "behatsdaa_snapshots" / "behatsdaa_giftcards_config.json"


@dataclass(frozen=True)
class _GiftcardSpec:
    """One validated, ready-to-use entry from ``behatsdaa_giftcards_config.json``."""

    id: str
    file: Path
    name: str
    discount_percent: float
    max_deposit_per_month: float | None
    currency: str
    notes: str


class BehatsdaaAdapter(BaseSourceAdapter):
    """File-based scraper for Behatsdaa's per-wallet giftcard discounts.

    Each configured wallet contributes a flat percentage-off deal to every
    retail chain in its saved chain list; a chain shared by multiple wallets
    yields one deal per wallet (different discount economics, so they are
    genuinely different offers, not duplicates).
    """

    def __init__(
        self,
        config: SourceConfig | None = None,
        *,
        giftcards_config_path: Path | str | None = None,
    ) -> None:
        super().__init__(config or SourceConfig(base_url=_SITE_URL))
        self._giftcards_config_path = (
            Path(giftcards_config_path) if giftcards_config_path else _default_config_path()
        )

    @property
    def source_id(self) -> str:
        return "behatsdaa"

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        specs = self._load_giftcard_specs(self._giftcards_config_path)
        if not specs:
            logger.warning(
                "[%s] no usable giftcards in %s — fill in discount_percent / "
                "max_deposit_per_month for at least one entry",
                self.source_id, self._giftcards_config_path,
            )
            return [], []

        now = datetime.now(timezone.utc)
        seen_stores: dict[str, RawStore] = {}
        stores: list[RawStore] = []
        deals: list[RawScrapedRecord] = []

        for spec in specs:
            chains = self._load_chain_file(spec.file)
            for chain in chains:
                chain_name = clean_brand(str(chain.get("chainName") or ""))
                if not chain_name or is_generic_behatsdaa_brand(chain_name):
                    continue

                if chain_name not in seen_stores:
                    store = self._to_raw_store(chain, chain_name, now)
                    seen_stores[chain_name] = store
                    stores.append(store)

                deals.append(self._to_raw_deal(chain, chain_name, spec, now))

            logger.debug(
                "[%s] giftcard '%s' (%s): %d chains from %s",
                self.source_id, spec.id, spec.name, len(chains), spec.file,
            )

        logger.info(
            "[%s] Parsed %d stores, %d deals from %d giftcard file(s)",
            self.source_id, len(stores), len(deals), len(specs),
        )
        return stores, deals

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    def _load_giftcard_specs(self, config_path: Path) -> list[_GiftcardSpec]:
        if not config_path.exists():
            logger.warning("[%s] giftcards config not found at %s", self.source_id, config_path)
            return []
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
        except ValueError:
            logger.exception("[%s] giftcards config at %s is not valid JSON", self.source_id, config_path)
            return []
        if not isinstance(raw, dict):
            logger.error(
                "[%s] giftcards config must be a JSON object keyed by giftcard id, got %s",
                self.source_id, type(raw).__name__,
            )
            return []

        base_dir = config_path.parent
        specs: list[_GiftcardSpec] = []
        for giftcard_id, entry in raw.items():
            if giftcard_id.startswith("_"):
                continue  # comment / example entry, e.g. "_comment", "_example"
            spec = self._parse_giftcard_entry(giftcard_id, entry, base_dir)
            if spec is not None:
                specs.append(spec)
        return specs

    def _parse_giftcard_entry(
        self, giftcard_id: str, entry: Any, base_dir: Path
    ) -> _GiftcardSpec | None:
        if not isinstance(entry, dict):
            logger.warning("[%s] giftcard '%s' entry is not an object — skipping", self.source_id, giftcard_id)
            return None
        if entry.get("active") is False:
            logger.info("[%s] giftcard '%s' marked inactive — skipping", self.source_id, giftcard_id)
            return None

        file_name = str(entry.get("file") or "").strip()
        if not file_name:
            logger.warning("[%s] giftcard '%s' missing 'file' — skipping", self.source_id, giftcard_id)
            return None
        file_path = base_dir / file_name
        if not file_path.exists():
            logger.warning("[%s] giftcard '%s' file not found: %s — skipping", self.source_id, giftcard_id, file_path)
            return None

        discount_percent = entry.get("discount_percent")
        if (
            not isinstance(discount_percent, (int, float))
            or isinstance(discount_percent, bool)
            or discount_percent <= 0
        ):
            logger.warning(
                "[%s] giftcard '%s' missing/invalid 'discount_percent' — fill it in and re-run",
                self.source_id, giftcard_id,
            )
            return None

        max_deposit = entry.get("max_deposit_per_month")
        max_deposit_val = (
            float(max_deposit)
            if isinstance(max_deposit, (int, float)) and not isinstance(max_deposit, bool) and max_deposit > 0
            else None
        )

        name = str(entry.get("name") or "").strip() or f"בהצדעה {giftcard_id}"
        currency = str(entry.get("currency") or "ILS").strip() or "ILS"
        notes = str(entry.get("notes") or "").strip()

        return _GiftcardSpec(
            id=str(giftcard_id),
            file=file_path,
            name=name,
            discount_percent=float(discount_percent),
            max_deposit_per_month=max_deposit_val,
            currency=currency,
            notes=notes,
        )

    # ------------------------------------------------------------------
    # Chain-file loading
    # ------------------------------------------------------------------

    def _load_chain_file(self, path: Path) -> list[dict[str, Any]]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.exception("[%s] failed to read/parse %s", self.source_id, path)
            return []
        return self._extract_chains(payload)

    @staticmethod
    def _extract_chains(payload: Any) -> list[dict[str, Any]]:
        """Pull the flat chain list out of a saved ``GetWalletChain`` response.

        Same nested shape the live API used to return (see the git history
        of this module): ``{"status": true, "data": [{"walletChainData":
        [...]}]}`` — chains are grouped by tag, we don't care about the
        grouping, just the flattened chain list.
        """
        if not isinstance(payload, dict) or not payload.get("status"):
            return []
        data = payload.get("data", [])
        if not isinstance(data, list):
            return []
        chains: list[dict[str, Any]] = []
        for group in data:
            if not isinstance(group, dict):
                continue
            chain_list = group.get("walletChainData")
            if isinstance(chain_list, list):
                chains.extend(c for c in chain_list if isinstance(c, dict))
        return chains

    # ------------------------------------------------------------------
    # Mapping: one chain (+ the wallet it came from) -> store / deal
    # ------------------------------------------------------------------

    def _to_raw_store(self, chain: dict[str, Any], chain_name: str, now: datetime) -> RawStore:
        website = normalize_website(chain.get("webSite"))
        return RawStore(
            id=generate_id(),
            source_id=self.source_id,
            name=chain_name,
            scraped_at=now,
            url=f"https://{website}" if website else None,
            raw_payload={
                "source": "behatsdaa_giftcard",
                "chainID": chain.get("chainID"),
                "chainName": chain.get("chainName"),
                "webSite": chain.get("webSite"),
            },
        )

    def _to_raw_deal(
        self, chain: dict[str, Any], chain_name: str, spec: _GiftcardSpec, now: datetime
    ) -> RawScrapedRecord:
        website = normalize_website(chain.get("webSite"))
        store_url = f"https://{website}" if website else None

        max_text = f"{spec.max_deposit_per_month:g} ₪ לחודש" if spec.max_deposit_per_month else None
        # Human-facing description -> becomes Deal.deal_description via
        # raw_payload["full_description"] (PersistStage reads it directly,
        # no fallback — see hever.py's _to_raw_deal for the same convention).
        full_description = f'{spec.discount_percent:g}% הנחה בטעינת ארנק "{spec.name}", לשימוש ברשת {chain_name}.'
        bonus_sentence = (
            f'ניתן לטעון עד {max_text} דרך ארנק "{spec.name}" ולקבל {spec.discount_percent:g}% הנחה, '
            f"לשימוש ברשת {chain_name}."
            if max_text
            else f'ניתן לטעון דרך ארנק "{spec.name}" ולקבל {spec.discount_percent:g}% הנחה, לשימוש ברשת {chain_name}.'
        )
        # Own notes first, then the fixed bonus sentence -- same order as
        # hever.py / paisplus_cashcards.py's terms_and_conditions convention.
        terms = f"{spec.notes} {bonus_sentence}".strip() if spec.notes else bonus_sentence

        reward: dict[str, Any] = {"type": "percentage_off", "value": spec.discount_percent / 100.0}
        if spec.max_deposit_per_month:
            reward["max_discount_amount"] = round(spec.max_deposit_per_month * spec.discount_percent / 100.0, 2)
        discount_logic = {
            "type": "percentage",
            "condition": {"type": "min_quantity", "value": 1},
            "reward": reward,
        }

        price_text = f"{spec.discount_percent:g}% הנחה בטעינה"
        if spec.max_deposit_per_month:
            price_text += f" (עד {spec.max_deposit_per_month:g} ₪ לחודש)"
        price_text += f" - {spec.name}"

        # Store name + wallet name folded in (not just chain_name): the same
        # chain can appear under multiple wallets at different discount
        # rates, and RawScrapedRecord.fingerprint is
        # sha256(source_id|deal_description|price_text) -- without the
        # wallet identity here, two wallets sharing both a chain and a
        # discount rate would collide and silently drop one deal. Same fix
        # as hever.py / paisplus_cashcards.py.
        deal_description = f"{chain_name} | {spec.name}"

        raw_payload: dict[str, Any] = {
            "source": "behatsdaa_giftcard",
            "giftcard_id": spec.id,
            "giftcard_name": spec.name,
            "chainID": chain.get("chainID"),
            "chainName": chain.get("chainName"),
            "webSite": chain.get("webSite"),
            "deal_title": chain_name,
            "full_description": full_description,
            "terms_and_conditions": terms,
            "benefit_url": _SITE_URL,
            "store_url": store_url,
            "currency": spec.currency,
            "discount_logic": discount_logic,
            "deal_type": "giftcard_discount",
        }
        logo_url = chain.get("logoURL")
        if logo_url:
            raw_payload["image_url"] = logo_url

        return RawScrapedRecord(
            id=generate_id(),
            source_id=self.source_id,
            store_name=chain_name,
            deal_description=deal_description,
            price_text=price_text,
            scraped_at=now,
            url=store_url or _SITE_URL,
            raw_payload=raw_payload,
        )
