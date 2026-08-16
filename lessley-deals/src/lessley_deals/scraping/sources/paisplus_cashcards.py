"""PaisPlus loadable cash-card scrapers (food-chains + networks).

Two monthly-loadable "chit" (תו) card programs, structurally like
``hever.py``'s loading-bonus model rather than ``paisplus.py``'s per-product
one: you load money onto the card and get a program-wide percentage
discount on the load itself, redeemable across many merchants.

Both programs are driven by the same CSRF-protected JSON API (Laravel
session, no login) confirmed live:

- ``POST /cashcards/binding-chit/cards/get`` with ``{"chit_group_id": <id>}``
  returns a list of "chits". ``chit_group_id=200`` is the food-chains
  program (20 chits, one per food chain -- e.g. Carrefour, Victory, Tiv
  Taam); ``chit_group_id=201`` is the networks program (exactly 1 chit, a
  single universal card).
- ``POST /cashcards/binding-chit/merchants`` with ``{"chit_id": <id>}``
  returns that chit's merchant list. Confirmed empty (``[]``) for every
  food-chains chit (each chit *is* its own store already) and 140 entries
  for the networks chit (the universal card's real redemption targets).

So both programs reduce to the same shape: chit -> merchants (empty or
not) -> stores. When merchants is empty the chit itself is the one store;
otherwise each merchant is a store sharing that chit's discount economics.

Each chit carries ``topup_rules``: two membership tiers (``"regular"`` for
silver/gold, ``"vip"`` for gold+/platinum), each with its own amount-bracket
discounts. Confirmed live: every store within a chit_group shares identical
bracket numbers -- it's one program-wide bonus per group, same spirit as
hever's own loading bonus, just split by membership tier.

A cardholder has exactly one tier, so the tiers are **separate sources**, not
two deals on one card: there is one adapter per (program, tier), each with its
own ``source_id`` and its own club. That is what lets a user say which tier
they hold and have the optimizer prune the other -- eligibility keys on
``source_id``, so a tier that isn't its own source can't be selected against.
Each store therefore yields **one deal per adapter**.

Unlike hever's single flat rate, each tier's amount brackets are a real
two-stage ladder with a hard ceiling (networks/regular: 25% on the first
600 ILS, then 15% up to 1500). They're emitted structurally as
``discount_logic.reward.tiers`` so the optimizer can route part of a bill
through each rung, alongside a ``max_discount_amount`` that keeps
ladder-unaware consumers from applying the headline rate to an unbounded
cart. The human-readable breakdown still goes into ``terms_and_conditions``,
same "own text first, then the fixed bonus sentence" convention as
:func:`lessley_deals.scraping.sources.hever.HeverGiftCardAdapter._loading_bonus_sentence`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, ClassVar
from urllib.parse import unquote

import httpx

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig
from lessley_deals.scraping.helpers.html_utils import clean_html

logger = logging.getLogger(__name__)

_BASE_URL = "https://paisplus.co.il"
_CARDS_GET_URL = f"{_BASE_URL}/cashcards/binding-chit/cards/get"
_MERCHANTS_URL = f"{_BASE_URL}/cashcards/binding-chit/merchants"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_MAX_CONCURRENT_MERCHANT_FETCHES = 5

_TIER_LABELS = {"regular": "רגיל", "vip": "VIP"}


def _build_tiers(brackets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The amount-bracket ladder as structured ``reward.tiers`` entries.

    ``brackets`` arrives sorted by ``from_amount``. The rungs are contiguous
    (bracket N starts where N-1 ends), so a bracket missing any of its three
    numbers can't be dropped in isolation without silently misstating the
    ones after it -- the whole ladder is discarded instead, leaving the
    caller with the flat headline rate.
    """
    tiers: list[dict[str, Any]] = []
    for bracket in brackets:
        from_amount = bracket.get("from_amount")
        to_amount = bracket.get("to_amount")
        percent = bracket.get("w_eligibility_discount_percent")
        if from_amount is None or to_amount is None or percent is None or to_amount <= from_amount:
            return []
        tiers.append(
            {
                "from_amount": from_amount,
                "to_amount": to_amount,
                "percentage_off": percent / 100.0,
            }
        )
    return tiers


class _PaisPlusCashcardAdapterBase(BaseSourceAdapter):
    """Shared engine for the PaisPlus loadable cash-card programs.

    Subclasses only need to set ``_chit_group_id``/``_category_path``/
    ``_source_id`` -- the fetch, CSRF handshake, and chit/merchant fan-out
    logic is identical for both programs.
    """

    _chit_group_id: ClassVar[int]
    _category_path: ClassVar[str]
    _source_id: ClassVar[str]
    # Which ``topup_rules[].rule_member`` this adapter emits. The membership
    # tier is an entitlement, not a variant of one deal: a cardholder is either
    # regular (silver/gold) or vip (gold+/platinum), never both. Eligibility is
    # keyed on ``source_id`` (see deal_optimizer's ``deal_eligibility``), so
    # each tier needs its own source_id and its own club to be selectable —
    # hence one adapter per (program, tier) rather than one emitting both.
    _member_tier: ClassVar[str]

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
        return self._source_id

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        async with httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": _USER_AGENT,
                "Origin": _BASE_URL,
                "Referer": f"{_BASE_URL}{self._category_path}",
            },
            transport=self._transport,
        ) as client:
            try:
                await self._handshake(client)
            except (httpx.HTTPError, ValueError):
                logger.exception("[%s] CSRF handshake failed", self.source_id)
                return [], []

            try:
                chits = await self._fetch_chits(client)
            except (httpx.HTTPError, ValueError):
                logger.exception("[%s] failed to fetch chits", self.source_id)
                return [], []

            semaphore = asyncio.Semaphore(_MAX_CONCURRENT_MERCHANT_FETCHES)
            merchants_lists = await asyncio.gather(
                *[self._fetch_merchants_safe(client, chit, semaphore) for chit in chits]
            )

        now = datetime.now(timezone.utc)
        seen_stores: dict[str, RawStore] = {}
        stores: list[RawStore] = []
        deals: list[RawScrapedRecord] = []

        for chit, merchants in zip(chits, merchants_lists, strict=True):
            if merchants is None:
                # Merchants fetch failed for this chit -- skip it entirely
                # rather than falling back to "chit-as-its-own-store": for
                # a chit that genuinely has real merchants (networks), that
                # fallback would fabricate a bogus deal for the umbrella
                # card itself instead of its actual redemption targets.
                continue
            for store, deal in self._to_raw_records(chit, merchants, now):
                if store.fingerprint not in seen_stores:
                    seen_stores[store.fingerprint] = store
                    stores.append(store)
                deals.append(deal)

        logger.info(
            "[%s] Parsed %d stores, %d deals from %d chit(s)",
            self.source_id, len(stores), len(deals), len(chits),
        )
        return stores, deals

    # ------------------------------------------------------------------
    # Fetch helpers
    # ------------------------------------------------------------------

    async def _handshake(self, client: httpx.AsyncClient) -> None:
        """GET the cashcard page once to pick up the XSRF-TOKEN cookie.

        Laravel session; confirmed live that a POST without this token
        returns HTTP 419 "CSRF token mismatch".
        """
        resp = await client.get(f"{_BASE_URL}{self._category_path}")
        resp.raise_for_status()
        token = client.cookies.get("XSRF-TOKEN")
        if not token:
            raise ValueError("XSRF-TOKEN cookie not found after handshake GET")
        client.headers["x-xsrf-token"] = unquote(token)
        client.headers["Content-Type"] = "application/json"
        client.headers["X-Requested-With"] = "XMLHttpRequest"

    async def _fetch_chits(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        resp = await client.post(_CARDS_GET_URL, json={"chit_group_id": self._chit_group_id})
        resp.raise_for_status()
        data = resp.json()
        chits = data.get("chits")
        if not isinstance(chits, list):
            raise ValueError(f"expected 'chits' list, got {type(chits).__name__}")
        return chits

    async def _fetch_merchants_safe(
        self, client: httpx.AsyncClient, chit: dict[str, Any], semaphore: asyncio.Semaphore
    ) -> list[dict[str, Any]] | None:
        """Returns ``None`` on fetch failure (caller skips the chit entirely),
        as distinct from a confirmed-empty ``[]`` merchants list (caller
        treats the chit as its own store)."""
        chit_id = chit.get("chit_id")
        async with semaphore:
            try:
                resp = await client.post(_MERCHANTS_URL, json={"chit_id": chit_id})
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, ValueError):
                logger.exception("[%s] failed to fetch merchants for chit %s", self.source_id, chit_id)
                return None
        merchants = data.get("merchants")
        return merchants if isinstance(merchants, list) else []

    # ------------------------------------------------------------------
    # Mapping: one chit (+ its merchants, if any) -> stores x tiers
    # ------------------------------------------------------------------

    def _tier_bonus_sentence(self, brackets: list[dict[str, Any]], store_name: str) -> str:
        """The ladder as a Hebrew sentence, appended to the store's own terms.

        Only called for a ladder that :func:`_build_tiers` already validated,
        so every bracket is known to carry all three numbers.
        """
        parts = []
        for i, bracket in enumerate(brackets):
            amount = bracket["to_amount"] - bracket["from_amount"]
            pct = bracket["w_eligibility_discount_percent"]
            ordinal = "ראשונים" if i == 0 else "הנוספים"
            parts.append(f"{pct}% הנחה על טעינת {amount} ₪ {ordinal}")
        total = brackets[-1]["to_amount"]
        joined = " ו-".join(parts)
        return (
            f"ניתן לטעון ולקבל {joined} "
            f"(עד {total} ₪ בסה\"כ), לשימוש ברשת {store_name}."
        )

    def _to_raw_records(
        self, chit: dict[str, Any], merchants: list[dict[str, Any]], now: datetime
    ) -> list[tuple[RawStore, RawScrapedRecord]]:
        chit_id = chit.get("chit_id")
        chit_name = str(chit.get("marketing_name") or chit.get("chit_name") or "").strip()
        category_url = f"{_BASE_URL}{self._category_path}"

        # merchants == [] -> the chit itself is the one store (food-chains);
        # merchants non-empty -> each merchant is its own store sharing this
        # chit's discount economics (networks).
        targets: list[dict[str, Any] | None] = list(merchants) if merchants else [None]

        results: list[tuple[RawStore, RawScrapedRecord]] = []

        for merchant in targets:
            if merchant is not None:
                store_name = str(merchant.get("commercial_name") or "").strip()
                constraints_html = merchant.get("limitations_text")
                store_url = merchant.get("site_url") or merchant.get("branches_page_url")
                merchant_id = merchant.get("merchant_id")
                image_url = merchant.get("logo_url")
            else:
                store_name = chit_name
                constraints_html = chit.get("short_description")
                store_url = None
                merchant_id = None
                image_url = chit.get("image_url")

            if not store_name:
                continue

            own_constraints = clean_html(constraints_html)

            store = RawStore(
                id=generate_id(),
                source_id=self.source_id,
                name=store_name,
                scraped_at=now,
                url=store_url,
                raw_payload={
                    "source": self.source_id,
                    "chit_id": chit_id,
                    "merchant_id": merchant_id,
                },
            )

            for rule in chit.get("topup_rules") or []:
                tier = rule.get("rule_member")
                if tier != self._member_tier:
                    continue
                discounts = rule.get("topup_rule_discounts") or []
                if not discounts:
                    continue
                brackets = sorted(discounts, key=lambda d: d.get("from_amount", 0))
                headline_pct = brackets[0].get("w_eligibility_discount_percent")
                if headline_pct is None:
                    continue
                max_amount = brackets[-1].get("to_amount")

                tiers = _build_tiers(brackets)
                reward: dict[str, Any] = {
                    "type": "percentage_off",
                    "value": headline_pct / 100.0,
                }
                if tiers:
                    # Savings if the card is loaded all the way to its ceiling.
                    # Emitted alongside ``tiers`` on purpose: consumers that
                    # don't walk the ladder still clamp here instead of applying
                    # the headline rate to an unbounded cart, and for a
                    # well-formed ladder the two agree at the ceiling.
                    reward["max_discount_amount"] = round(
                        sum((t["to_amount"] - t["from_amount"]) * t["percentage_off"] for t in tiers),
                        2,
                    )
                    reward["tiers"] = tiers

                discount_logic = {
                    "type": "percentage",
                    "condition": {"type": "min_quantity", "value": 1},
                    "reward": reward,
                    # "regular" and "vip" are the same physical card -- a holder
                    # has one tier, never both. Without this the optimizer would
                    # happily allocate both tiers' ladders to one cart and claim
                    # savings the card can't pay out.
                    #
                    # Deliberately keyed on the chit rather than ``source_id``:
                    # the two tiers now come from different adapters with
                    # different source_ids, so a source-scoped key would never
                    # match across them and the guard would silently do nothing.
                    # Clubs should already keep a wallet to one tier; this is
                    # the backstop for a user who ticks both.
                    "exclusive_group": f"paisplus:chit-{chit_id}",
                }
                tier_label = _TIER_LABELS[tier]
                price_text = (
                    f"{headline_pct}% הנחה בטעינה (עד {max_amount} ₪) - {tier_label}"
                    if max_amount is not None
                    else f"{headline_pct}% הנחה בטעינה - {tier_label}"
                )
                # A ladder that didn't validate can't be described accurately
                # either, so the sentence is skipped rather than half-rendered;
                # the store's own terms still go through untouched.
                bonus_sentence = self._tier_bonus_sentence(brackets, store_name) if tiers else ""
                # Store's own constraints first, then the fixed bonus
                # sentence -- same order as hever._to_raw_deal's terms.
                terms = f"{own_constraints} {bonus_sentence}".strip() if own_constraints else bonus_sentence
                # Tier folded into deal_description (not just store_name):
                # confirmed live every store in a chit_group shares
                # identical bracket numbers, so price_text alone can't
                # disambiguate stores -- same fingerprint-collision fix as
                # hever.py/paisplus.py.
                deal_description = (
                    f"{store_name} | {tier_label} | {own_constraints}"
                    if own_constraints
                    else f"{store_name} | {tier_label}"
                )

                raw_payload: dict[str, Any] = {
                    "source": self.source_id,
                    "chit_id": chit_id,
                    "merchant_id": merchant_id,
                    "member_tier": tier,
                    "deal_title": store_name,
                    "full_description": own_constraints,
                    "terms_and_conditions": terms,
                    "benefit_url": category_url,
                    "store_url": store_url,
                    "currency": "ILS",
                    "discount_logic": discount_logic,
                    # Loadable "chit" cards are rechargeable balances, same
                    # program shape as hever.py — tagged uniformly as
                    # "giftcard_discount" for now (see hever.py).
                    "deal_type": "giftcard_discount",
                    "image_url": image_url,
                }

                deal = RawScrapedRecord(
                    id=generate_id(),
                    source_id=self.source_id,
                    store_name=store_name,
                    deal_description=deal_description,
                    price_text=price_text,
                    scraped_at=now,
                    url=category_url,
                    raw_payload=raw_payload,
                )
                results.append((store, deal))

        return results


class _FoodChainsBase(_PaisPlusCashcardAdapterBase):
    """PaisPlus loadable food-chain cash card (chit_group_id=200)."""

    _chit_group_id = 200
    _category_path = "/cashcards/food-chains"


class _NetworksBase(_PaisPlusCashcardAdapterBase):
    """PaisPlus loadable networks/shops cash card (chit_group_id=201)."""

    _chit_group_id = 201
    _category_path = "/cashcards/networks"


# One adapter per (program, membership tier). Each fetches its program's chit
# list independently -- two extra HTTP calls in exchange for every tier being a
# first-class source_id, which is what makes it selectable as its own club and
# prunable by the optimizer's wallet check.


class PaisPlusFoodChainsRegularAdapter(_FoodChainsBase):
    """Food-chain card, regular tier (silver/gold)."""

    _source_id = "paisplus_food_chains_regular"
    _member_tier = "regular"


class PaisPlusFoodChainsVipAdapter(_FoodChainsBase):
    """Food-chain card, VIP tier (gold+/platinum)."""

    _source_id = "paisplus_food_chains_vip"
    _member_tier = "vip"


class PaisPlusNetworksRegularAdapter(_NetworksBase):
    """Networks card, regular tier (silver/gold)."""

    _source_id = "paisplus_networks_regular"
    _member_tier = "regular"


class PaisPlusNetworksVipAdapter(_NetworksBase):
    """Networks card, VIP tier (gold+/platinum)."""

    _source_id = "paisplus_networks_vip"
    _member_tier = "vip"
