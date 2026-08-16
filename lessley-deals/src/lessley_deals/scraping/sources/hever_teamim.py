"""Hever ("חבר") "טעמים" (Taste) restaurant-card directory scraper.

Sibling of ``hever.py``'s gift-card adapter, split into its own source
because the two card programs are separate JSON datasets with different
shapes: this one is a public, ungrouped list of restaurant *branches* (a
chain with several locations appears once per branch), not one row per
company. No login required — same as the gift-card dataset.

The underlying deal (fixed loading bonus) is identical for every branch of a
restaurant, so branches are grouped into a single deal per restaurant — same
convention as ``hot.py``'s ``_locations`` handling for multi-branch brands.
Per-branch address/hours/etc. go into ``raw_payload["_locations"]``; fields
that can legitimately differ between branches of the same restaurant
(``delivery`` mode, ``desc``) are merged rather than arbitrarily taking the
first branch's value.

Branches are grouped by ``img`` (the chain's logo filename) *and* by ``name``,
taking the transitive closure of both — not by ``name`` alone. The site bakes
the branch into the name for some chains, so name alone splits one restaurant
into several: "פיצה עגבניה גן העיר" / "פיצה עגבניה שינקין" / … became six
separate deals carrying one benefit, and the optimizer stacked them as if they
were six independent ones. ``img`` is also the *better* separator — it keeps
"מאמא גרג" apart from "קפה גרג", which name-token matching merges. Logo alone
isn't enough either: a handful of chains were uploaded with two logo files
("בני הדייג"), and those are only caught by the shared name. See
``_group_branches``.

Source schema (one object per branch in ``data["branch"]``), confirmed from
the live JSON response:

- ``img``             chain logo filename, e.g. "logo_agvania.jpg" — the
                        grouping key, identical across a chain's branches
- ``name``            restaurant name, sometimes with the branch appended
- ``desc``             short description (e.g. "מסעדה איטלקית")
- ``category``/``type`` cuisine classification
- ``area``/``city``/``address``/``phone``/``latitude``/``longitude`` branch location
- ``hours``            opening hours, free text
- ``kosher``           kosher certification text, may be empty
- ``handicap``         "Y"/"N" wheelchair accessibility
- ``website``          bare domain, no scheme, may be empty
- ``delivery``         comma-separated redemption modes, e.g.
                        "ישיבה במסעדה,איסוף עצמי,משלוחים" (dine-in/pickup/delivery)
- ``limitations``       free-text branch-specific constraints, often empty —
                        copied verbatim into ``terms_and_conditions``
- ``internal_link``     optional "more details" page id, e.g. "mcc_item_new,384198"
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
_DATASET_URL = f"{_BASE_URL}/bs2/datasets/teamimcard_branches.json?_"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Same fixed, program-wide loading bonus as the gift-card program, worded for
# the "טעמים" (Taste) card specifically — confirmed identical across
# restaurants, not a per-branch number.
_LOADING_BONUS_TEXT = (
    'ניתן לטעון כרטיס "חבר" טעמים הנטען ולקבל 30% הנחה על טעינת 1,000 ₪ ראשונים, '
    '25% הנחה על 1,000 ₪ הבאים ו-20% הנחה על 1,000 ₪ נוספים (עד 3,000 ₪ בסה"כ)'
)
_LOADING_BONUS_PRICE_TEXT = "30% הנחה בטעינה (עד 3,000 ₪)"

# Placeholder logos — shared by unrelated businesses, so they identify nothing.
# A branch carrying one of these is grouped by ``name`` instead. Compared
# case-insensitively; keep the entries lowercase.
_PLACEHOLDER_IMAGES = frozenset({"teamim_default.jpg"})

# Trailing punctuation left behind when a chain's branch suffix is stripped off
# the shared name prefix ("הוט סינמה - גרנד קניון" -> "הוט סינמה -" -> "הוט סינמה").
_NAME_EDGE_CHARS = " -–—|,:;"


def _loading_bonus_discount_logic() -> dict[str, Any]:
    """The fixed Hever Taste-card loading-bonus reward — see hever.py's
    identical helper for why this is hand-built rather than parsed from
    ``_LOADING_BONUS_PRICE_TEXT``, and why it approximates the real 3-tier
    terms as a single flat 30% rate capped at the first 1,000 ₪ tier.
    Returns a fresh dict per call so raw records never share a mutable
    nested dict by reference.
    """
    return {
        "type": "percentage",
        "condition": {"type": "min_quantity", "value": 1},
        "reward": {"type": "percentage_off", "value": 0.3, "max_discount_amount": 300},
    }


class HeverTeamimAdapter(BaseSourceAdapter):
    """Deterministic scraper for the Hever "טעמים" restaurant-card directory.

    Fetches ``teamimcard_branches.json`` live (public endpoint, no login
    required), groups branches by restaurant name, and maps every field
    directly — no LLM, no inference.
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
        return "hever_teamim_card_store"

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
        groups = self._group_branches(records)

        stores = [self._to_raw_store(branches, now) for branches in groups]
        deals = [self._to_raw_deal(branches, now) for branches in groups]

        logger.info(
            "[%s] Parsed %d restaurants (%d branches) from %s",
            self.source_id, len(stores), len(records), _DATASET_URL,
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
        if not isinstance(data, dict):
            raise ValueError(f"expected a JSON object, got {type(data).__name__}")
        branches = data.get("branch")
        if not isinstance(branches, list):
            raise ValueError("expected a 'branch' array in the response")
        return branches

    # ------------------------------------------------------------------
    # Branch-group merge helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _group_branches(records: list[Any]) -> list[list[dict[str, Any]]]:
        """The feed's branches split into one group per restaurant.

        Two branches are the same restaurant when they share a logo *or* share
        a name, and grouping takes the transitive closure of both links —
        neither signal is sufficient alone:

        - **shared ``img``** catches chains whose ``name`` embeds the branch
          ("פיצה עגבניה גן העיר" / "פיצה עגבניה שינקין" / …). Name alone
          splits those into a deal per branch, which is what let the optimizer
          stack one chain's benefit against itself.
        - **shared ``name``** catches chains the site uploaded a logo twice
          for ("בני הדייג" under both ``logo_benny_dayag.png`` and
          ``logo_benihadayag.jpg``). Logo alone splits those.

        Placeholder logos link nothing — they are shared by unrelated
        businesses — so a branch carrying one groups by name only.

        Verified against the live feed: 1583 branches, 514 distinct names,
        480 logo groups, 476 groups once both links are applied.
        """
        parent: dict[str, str] = {}

        def find(node: str) -> str:
            parent.setdefault(node, node)
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        def union(left: str, right: str) -> None:
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[left_root] = right_root

        branches: list[tuple[str, dict[str, Any]]] = []
        for index, record in enumerate(records):
            if not isinstance(record, dict) or not record.get("name"):
                continue
            node = f"branch:{index}"
            union(node, f"name:{str(record['name']).strip()}")
            image = str(record.get("img") or "").strip()
            if image and image.lower() not in _PLACEHOLDER_IMAGES:
                union(node, f"img:{image.lower()}")
            branches.append((node, record))

        # Resolved only now that every union is in — a root read mid-loop can
        # still be merged into another by a later branch.
        groups: dict[str, list[dict[str, Any]]] = {}
        for node, record in branches:
            groups.setdefault(find(node), []).append(record)
        return list(groups.values())

    @staticmethod
    def _canonical_name(branches: list[dict[str, Any]]) -> str:
        """The chain's name, with any per-branch suffix removed.

        Grouping by ``img`` collects names that differ by branch ("פיצה עגבניה
        גן העיר", "פיצה עגבניה שינקין", …), so the group needs one name that
        isn't an arbitrary branch's. That is the longest *whole-word* prefix
        every name shares — word-wise rather than character-wise so a shared
        prefix can never cut mid-word ("אנגוס"/"אנגוסרי" share five characters
        but no word, and must not collapse to a truncation).

        Falls back to the shortest name when the group shares no leading word,
        which is what a logo grouping two spellings of one restaurant looks
        like ("Moon"/"moon", "kampai street wok"/"קאמפיי סטריט ווק").
        """
        names = list(dict.fromkeys(str(b["name"]).strip() for b in branches if str(b.get("name") or "").strip()))
        if len(names) == 1:
            return names[0]

        shared: list[str] = []
        # strict=False on purpose: names have different word counts ("פיצה
        # עגבניה" vs "פיצה עגבניה גן העיר") and the shared prefix ends at the
        # shortest of them, which is exactly what truncating zip gives.
        for position in zip(*(name.split() for name in names), strict=False):
            if len(set(position)) != 1:
                break
            shared.append(position[0])

        return " ".join(shared).strip(_NAME_EDGE_CHARS) or min(names, key=len)

    @staticmethod
    def _first_nonempty(branches: list[dict[str, Any]], key: str) -> str:
        for branch in branches:
            value = str(branch.get(key) or "").strip()
            if value:
                return value
        return ""

    @staticmethod
    def _merge_delivery_modes(branches: list[dict[str, Any]]) -> str:
        """Union of every distinct redemption mode across branches.

        ``delivery`` is a comma-separated set per branch (e.g. "ישיבה
        במסעדה,איסוף עצמי"), and different branches of the same restaurant
        can support different modes — picking just one branch's value would
        silently drop modes another branch offers.
        """
        modes: dict[str, None] = {}
        for branch in branches:
            for part in str(branch.get("delivery") or "").split(","):
                part = part.strip()
                if part:
                    modes.setdefault(part, None)
        return ",".join(modes)

    @staticmethod
    def _merge_limitations(branches: list[dict[str, Any]]) -> str:
        """Every distinct non-empty ``limitations`` text across branches, verbatim."""
        seen: list[str] = []
        for branch in branches:
            text = str(branch.get("limitations") or "").strip()
            if text and text not in seen:
                seen.append(text)
        return " ".join(seen)

    @staticmethod
    def _branch_locations(branches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "area": branch.get("area"),
                "city": branch.get("city"),
                "address": branch.get("address"),
                "phone": branch.get("phone"),
                "hours": branch.get("hours"),
                "kosher": branch.get("kosher"),
                "handicap": branch.get("handicap"),
                "latitude": branch.get("latitude"),
                "longitude": branch.get("longitude"),
            }
            for branch in branches
        ]

    def _store_url(self, branches: list[dict[str, Any]]) -> str | None:
        website = self._first_nonempty(branches, "website")
        return f"https://{website}" if website else None

    def _benefit_url(self, branches: list[dict[str, Any]]) -> str | None:
        internal_link = self._first_nonempty(branches, "internal_link")
        return f"{_BASE_URL}/site/pg/{internal_link}" if internal_link else None

    def _loading_bonus_sentence(self, store_name: str) -> str:
        """The fixed Hever Taste-card loading-bonus sentence, naming the restaurant.

        Appended to ``terms_and_conditions`` after the restaurant's merged
        ``delivery``/``limitations`` text — see ``_to_raw_deal``. Deliberately
        excludes ``desc``: that isn't a limitation, it feeds ``deal_description``
        instead.
        """
        return f"{_LOADING_BONUS_TEXT}, למימוש ב{store_name}."

    def _to_raw_store(self, branches: list[dict[str, Any]], now: datetime) -> RawStore:
        store_name = self._canonical_name(branches)
        return RawStore(
            id=generate_id(),
            source_id=self.source_id,
            name=store_name,
            scraped_at=now,
            url=self._store_url(branches),
            raw_payload={
                "source": "hever_teamim",
                "internal_link": self._first_nonempty(branches, "internal_link") or None,
                # The grouping key — kept so a merged chain can be traced back
                # to the logo that merged it.
                "img": self._first_nonempty(branches, "img") or None,
                "branch_qty": len(branches),
            },
        )

    def _to_raw_deal(self, branches: list[dict[str, Any]], now: datetime) -> RawScrapedRecord:
        store_name = self._canonical_name(branches)
        deal_description = self._first_nonempty(branches, "desc")
        delivery = self._merge_delivery_modes(branches)
        limitations = self._merge_limitations(branches)
        loading_bonus_sentence = self._loading_bonus_sentence(store_name)

        # terms_and_conditions = the merged redemption-mode + constraints
        # text across all branches, verbatim, with the fixed loading-bonus
        # blurb appended.
        own_terms = " ".join(part for part in (delivery, limitations) if part)
        terms = f"{own_terms} {loading_bonus_sentence}".strip() if own_terms else loading_bonus_sentence

        store_url = self._store_url(branches)
        benefit_url = self._benefit_url(branches)
        discount_logic = _loading_bonus_discount_logic()
        currency = "ILS"

        raw_payload: dict[str, Any] = {
            "source": "hever_teamim",
            "category": self._first_nonempty(branches, "category") or None,
            "type": self._first_nonempty(branches, "type") or None,
            "delivery": delivery,
            "_locations": self._branch_locations(branches),
            # PersistStage (pipeline/persist_stage.py) reads deal_title /
            # full_description straight off raw_payload with no fallback —
            # set them explicitly so Deal.title/deal_description aren't left
            # null, same convention as hever.py / hot.py.
            "deal_title": store_name,
            "full_description": deal_description,
            "terms_and_conditions": terms,
            "benefit_url": benefit_url,
            "store_url": store_url,
            "currency": currency,
            "discount_logic": discount_logic,
            # Same rechargeable "חבר" loading-bonus card program as hever.py,
            # tagged uniformly as "giftcard_discount" for now (see hever.py).
            "deal_type": "giftcard_discount",
        }
        internal_link = self._first_nonempty(branches, "internal_link")
        if internal_link:
            raw_payload["internal_link"] = internal_link

        return RawScrapedRecord(
            id=generate_id(),
            source_id=self.source_id,
            store_name=store_name,
            # NOT plain `deal_description` — RawScrapedRecord.fingerprint is
            # sha256(source_id|deal_description|price_text), and price_text
            # is the same fixed string for every restaurant while `desc` is
            # often empty or a generic category phrase ("בית קפה") shared by
            # many unrelated restaurants. Without the store name folded in,
            # ScrapeStage's fingerprint dedup would treat a brand-new
            # restaurant as "already scraped" whenever it collides with some
            # other restaurant's fingerprint from an earlier run, silently
            # dropping it. This is fingerprint-only — raw_payload["full_description"]
            # above stays the plain `desc` text that PersistStage reads into
            # the final Deal.deal_description.
            deal_description=f"{store_name} | {deal_description}" if deal_description else store_name,
            price_text=_LOADING_BONUS_PRICE_TEXT,
            scraped_at=now,
            # PersistStage sets Deal.url = prec.raw.url directly (no
            # raw_payload lookup) — prefer the restaurant's own site over the
            # internal mcc_item_new detail page here.
            url=store_url or benefit_url,
            raw_payload=raw_payload,
        )
