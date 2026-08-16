from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from lessley_deals.scraping.base import SourceConfig
from lessley_deals.scraping.sources.paisplus_cashcards import (
    PaisPlusFoodChainsRegularAdapter,
    PaisPlusFoodChainsVipAdapter,
    PaisPlusNetworksRegularAdapter,
    PaisPlusNetworksVipAdapter,
)

# Real bracket numbers confirmed live on chit_group_id=200 (food-chains).
_REGULAR_RULE: dict[str, Any] = {
    "rule_member": "regular",
    "topup_rule_discounts": [
        {"from_amount": 0, "to_amount": 400, "w_eligibility_discount_percent": 7.5},
        {"from_amount": 400, "to_amount": 2200, "w_eligibility_discount_percent": 5},
    ],
}
_VIP_RULE: dict[str, Any] = {
    "rule_member": "vip",
    "topup_rule_discounts": [
        {"from_amount": 0, "to_amount": 600, "w_eligibility_discount_percent": 10},
        {"from_amount": 600, "to_amount": 3000, "w_eligibility_discount_percent": 5},
    ],
}
_TOPUP_RULES = [_REGULAR_RULE, _VIP_RULE]


def _food_chit(**overrides: Any) -> dict[str, Any]:
    chit: dict[str, Any] = {
        "chit_id": 1020,
        "chit_name": "קרפור",
        "marketing_name": "קרפור",
        "image_url": "https://media.dolcemaster.co.il/viper/logos/carrefour.png",
        "short_description": "לא כולל אתר סחר.<br/>לא ניתן לשלם בקופות עצמיות.",
        "topup_rules": _TOPUP_RULES,
        "parent_id": 1000,
    }
    chit.update(overrides)
    return chit


def _networks_chit(**overrides: Any) -> dict[str, Any]:
    chit: dict[str, Any] = {
        "chit_id": 5001,
        "chit_name": "תו פיס רשתות",
        "marketing_name": "תו נטען רשתות ומסעדות",
        "image_url": None,
        "short_description": None,
        "topup_rules": _TOPUP_RULES,
        "parent_id": 1000,
    }
    chit.update(overrides)
    return chit


def _merchant(merchant_id: int, commercial_name: str, **overrides: Any) -> dict[str, Any]:
    merchant: dict[str, Any] = {
        "merchant_id": merchant_id,
        "chit_id": 5001,
        "commercial_name": commercial_name,
        "site_url": None,
        "branches_page_url": None,
        "logo_url": f"https://media.dolcemaster.co.il/viper/logos/{merchant_id}.png",
        "limitations_text": "כולל כפל מבצעים והנחות.<br>\nלא ניתן להמרה למזומן.",
    }
    merchant.update(overrides)
    return merchant


def _make_adapter(cls, handler=None):
    transport = httpx.MockTransport(handler) if handler else None
    return cls(SourceConfig(base_url="https://paisplus.co.il"), transport=transport)


class TestTierDiscountDerivation:
    def test_each_adapter_emits_only_its_own_tier(self) -> None:
        # A cardholder has one tier, so each tier is its own source and its own
        # club. One chit therefore yields one deal per adapter, not two.
        chit = _food_chit()
        now = datetime.now(timezone.utc)

        regular = _make_adapter(PaisPlusFoodChainsRegularAdapter)._to_raw_records(chit, [], now)
        vip = _make_adapter(PaisPlusFoodChainsVipAdapter)._to_raw_records(chit, [], now)

        assert len(regular) == 1
        assert len(vip) == 1
        assert regular[0][1].raw_payload["member_tier"] == "regular"
        assert vip[0][1].raw_payload["member_tier"] == "vip"
        # Same underlying store either way — the tier changes the ladder, not
        # which merchant accepts the card.
        assert regular[0][0].name == vip[0][0].name

    def test_each_tier_carries_its_own_source_id(self) -> None:
        chit = _food_chit()
        now = datetime.now(timezone.utc)

        regular = _make_adapter(PaisPlusFoodChainsRegularAdapter)._to_raw_records(chit, [], now)
        vip = _make_adapter(PaisPlusFoodChainsVipAdapter)._to_raw_records(chit, [], now)

        assert regular[0][1].source_id == "paisplus_food_chains_regular"
        assert vip[0][1].source_id == "paisplus_food_chains_vip"
        # Eligibility keys on source_id, so distinct ids are what makes the
        # wallet able to prune the tier the user doesn't hold.
        assert regular[0][1].source_id != vip[0][1].source_id

    def test_regular_tier_uses_entry_bracket_as_headline_discount(self) -> None:
        adapter = _make_adapter(PaisPlusFoodChainsRegularAdapter)
        chit = _food_chit()
        now = datetime.now(timezone.utc)
        (_store, regular_deal), = adapter._to_raw_records(chit, [], now)

        assert regular_deal.raw_payload["discount_logic"]["reward"]["value"] == 0.075
        assert "2200" in regular_deal.price_text  # max loadable amount for this tier
        assert "7.5" in regular_deal.price_text

    def test_vip_tier_uses_its_own_entry_bracket(self) -> None:
        adapter = _make_adapter(PaisPlusFoodChainsVipAdapter)
        chit = _food_chit()
        now = datetime.now(timezone.utc)
        (_store, vip_deal), = adapter._to_raw_records(chit, [], now)

        assert vip_deal.raw_payload["discount_logic"]["reward"]["value"] == 0.10
        assert "3000" in vip_deal.price_text  # max loadable amount for this tier

    def test_terms_include_own_constraints_then_bonus_sentence(self) -> None:
        adapter = _make_adapter(PaisPlusFoodChainsRegularAdapter)
        chit = _food_chit()
        now = datetime.now(timezone.utc)
        _store, deal = adapter._to_raw_records(chit, [], now)[0]
        terms = deal.raw_payload["terms_and_conditions"]
        assert "לא כולל אתר סחר" in terms
        assert "ניתן לטעון ולקבל" in terms
        assert "קרפור" in terms

    def test_store_name_and_url_from_chit_when_no_merchants(self) -> None:
        adapter = _make_adapter(PaisPlusFoodChainsRegularAdapter)
        chit = _food_chit()
        now = datetime.now(timezone.utc)
        store, deal = adapter._to_raw_records(chit, [], now)[0]
        assert store.name == "קרפור"
        assert store.url is None
        assert deal.raw_payload["deal_type"] == "giftcard_discount"
        assert deal.raw_payload["benefit_url"] == "https://paisplus.co.il/cashcards/food-chains"
        assert "constraints" not in deal.raw_payload["discount_logic"]
        assert "stackable" not in deal.raw_payload
        assert "redeem_channels" not in deal.raw_payload
        assert "coupon_code" not in deal.raw_payload


class TestBracketLadder:
    """``reward.tiers`` — the structured ladder the optimizer routes money through.

    Before this existed the brackets were collapsed to the entry rate with no
    ceiling at all, so a 10,000 ILS cart claimed the headline percentage of the
    whole cart from a card that tops out at 2,200.
    """

    def _reward(self, cls, chit) -> dict[str, Any]:
        adapter = _make_adapter(cls)
        (_store, deal), = adapter._to_raw_records(chit, [], datetime.now(timezone.utc))
        return deal.raw_payload["discount_logic"]["reward"]

    def test_regular_tier_emits_both_rungs_in_order(self) -> None:
        reward = self._reward(PaisPlusFoodChainsRegularAdapter, _food_chit())
        assert reward["tiers"] == [
            {"from_amount": 0, "to_amount": 400, "percentage_off": 0.075},
            {"from_amount": 400, "to_amount": 2200, "percentage_off": 0.05},
        ]

    def test_vip_tier_emits_its_own_rungs(self) -> None:
        reward = self._reward(PaisPlusFoodChainsVipAdapter, _food_chit())
        assert reward["tiers"] == [
            {"from_amount": 0, "to_amount": 600, "percentage_off": 0.10},
            {"from_amount": 600, "to_amount": 3000, "percentage_off": 0.05},
        ]

    def test_max_discount_amount_is_the_fully_loaded_card(self) -> None:
        # regular: 400 * 7.5% + 1800 * 5% = 30 + 90
        assert self._reward(PaisPlusFoodChainsRegularAdapter, _food_chit())["max_discount_amount"] == 120.0
        # vip: 600 * 10% + 2400 * 5% = 60 + 120
        assert self._reward(PaisPlusFoodChainsVipAdapter, _food_chit())["max_discount_amount"] == 180.0

    def test_headline_value_and_price_text_are_unchanged(self) -> None:
        # The flat fields stay put so ladder-unaware consumers still degrade to
        # a bounded (if pessimistic) number rather than the old runaway.
        reward = self._reward(PaisPlusFoodChainsRegularAdapter, _food_chit())
        assert reward["type"] == "percentage_off"
        assert reward["value"] == 0.075

    def test_ladder_is_dropped_whole_when_a_bracket_is_malformed(self) -> None:
        chit = _food_chit(
            topup_rules=[
                {
                    "rule_member": "regular",
                    "topup_rule_discounts": [
                        {"from_amount": 0, "to_amount": 400, "w_eligibility_discount_percent": 7.5},
                        {"from_amount": 400, "w_eligibility_discount_percent": 5},  # no to_amount
                    ],
                }
            ]
        )
        reward = self._reward(PaisPlusFoodChainsRegularAdapter, chit)

        # Rung 2 can't be priced, and rung 1 alone would understate the card —
        # so neither the ladder nor a bogus cap is emitted.
        assert "tiers" not in reward
        assert "max_discount_amount" not in reward
        assert reward["value"] == 0.075


class TestExclusiveGroup:
    def test_both_tiers_of_one_chit_share_a_group_across_adapters(self) -> None:
        # The two tiers now come from different adapters with different
        # source_ids, so the key must be chit-scoped: a source-scoped one would
        # never match across them and the guard would silently do nothing.
        now = datetime.now(timezone.utc)
        regular = _make_adapter(PaisPlusFoodChainsRegularAdapter)._to_raw_records(_food_chit(), [], now)
        vip = _make_adapter(PaisPlusFoodChainsVipAdapter)._to_raw_records(_food_chit(), [], now)

        groups = {d.raw_payload["discount_logic"]["exclusive_group"] for _s, d in regular + vip}
        assert groups == {"paisplus:chit-1020"}

    def test_every_store_under_one_chit_shares_the_group(self) -> None:
        # The networks chit fans out to many merchants; they're separate stores,
        # and the optimizer only ever loads one store's deals, so a chit-scoped
        # key is enough to keep regular and vip apart.
        adapter = _make_adapter(PaisPlusNetworksRegularAdapter)
        pairs = adapter._to_raw_records(
            _networks_chit(), [_merchant(1, "מקדונלד'ס"), _merchant(2, "American Eagle")], datetime.now(timezone.utc)
        )

        groups = {d.raw_payload["discount_logic"]["exclusive_group"] for _s, d in pairs}
        assert groups == {"paisplus:chit-5001"}

    def test_different_chits_get_different_groups(self) -> None:
        adapter = _make_adapter(PaisPlusFoodChainsRegularAdapter)
        now = datetime.now(timezone.utc)
        a = adapter._to_raw_records(_food_chit(chit_id=1020), [], now)
        b = adapter._to_raw_records(_food_chit(chit_id=1021), [], now)

        group_a = a[0][1].raw_payload["discount_logic"]["exclusive_group"]
        group_b = b[0][1].raw_payload["discount_logic"]["exclusive_group"]
        assert group_a != group_b


class TestMerchantFanOut:
    def test_three_merchants_yield_one_deal_each_for_this_tier(self) -> None:
        adapter = _make_adapter(PaisPlusNetworksRegularAdapter)
        chit = _networks_chit()
        merchants = [
            _merchant(1, "מקדונלד'ס"),
            _merchant(2, "דומינו'ס פיצה"),
            _merchant(3, "American Eagle"),
        ]
        now = datetime.now(timezone.utc)
        pairs = adapter._to_raw_records(chit, merchants, now)

        assert len(pairs) == 3  # 3 merchants, this adapter's tier only
        stores = {s.fingerprint for s, _d in pairs}
        assert len(stores) == 3

    def test_merchant_store_url_prefers_site_url_over_branches_page(self) -> None:
        adapter = _make_adapter(PaisPlusNetworksRegularAdapter)
        chit = _networks_chit()
        merchants = [
            _merchant(1, "American Eagle", site_url="https://ae.co.il", branches_page_url="https://ae.co.il/branches")
        ]
        now = datetime.now(timezone.utc)
        store, deal = adapter._to_raw_records(chit, merchants, now)[0]
        assert store.url == "https://ae.co.il"

    def test_merchant_terms_come_from_limitations_text_not_chit(self) -> None:
        adapter = _make_adapter(PaisPlusNetworksRegularAdapter)
        chit = _networks_chit(short_description=None)
        merchants = [_merchant(1, "מקדונלד'ס", limitations_text="לא ניתן להמרה למזומן.")]
        now = datetime.now(timezone.utc)
        _store, deal = adapter._to_raw_records(chit, merchants, now)[0]
        assert "לא ניתן להמרה למזומן" in deal.raw_payload["terms_and_conditions"]

    def test_fingerprint_unique_across_identically_priced_merchants(self) -> None:
        # Confirmed live: every merchant under a chit shares identical
        # bracket numbers, so price_text alone can't disambiguate stores.
        adapter = _make_adapter(PaisPlusNetworksRegularAdapter)
        chit = _networks_chit()
        merchants = [_merchant(i, f"Store {i}") for i in range(5)]
        now = datetime.now(timezone.utc)
        pairs = adapter._to_raw_records(chit, merchants, now)
        fingerprints = {d.fingerprint for _s, d in pairs}
        assert len(fingerprints) == 5  # 5 merchants, one tier each


def _cookie_response(body_text: str = "<html></html>") -> httpx.Response:
    return httpx.Response(
        200, text=body_text, headers={"set-cookie": "XSRF-TOKEN=abc%3D123; Path=/"}
    )


class TestScrape:
    async def test_scrape_food_chains_end_to_end(self) -> None:
        seen_tokens = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET" and request.url.path == "/cashcards/food-chains":
                return _cookie_response()
            if request.method == "POST" and request.url.path == "/cashcards/binding-chit/cards/get":
                seen_tokens.append(request.headers.get("x-xsrf-token"))
                body = json.loads(request.content)
                assert body == {"chit_group_id": 200}
                return httpx.Response(200, json={"status_code": 0, "chits": [_food_chit()]})
            if request.method == "POST" and request.url.path == "/cashcards/binding-chit/merchants":
                return httpx.Response(200, json={"status_code": 0, "merchants": []})
            raise AssertionError(f"unexpected request: {request.method} {request.url}")

        adapter = _make_adapter(PaisPlusFoodChainsRegularAdapter, handler)
        stores, deals = await adapter.scrape()

        assert seen_tokens == ["abc=123"]
        assert len(stores) == 1
        assert len(deals) == 1  # this adapter's tier only

    async def test_scrape_networks_end_to_end(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET" and request.url.path == "/cashcards/networks":
                return _cookie_response()
            if request.method == "POST" and request.url.path == "/cashcards/binding-chit/cards/get":
                body = json.loads(request.content)
                assert body == {"chit_group_id": 201}
                return httpx.Response(200, json={"status_code": 0, "chits": [_networks_chit()]})
            if request.method == "POST" and request.url.path == "/cashcards/binding-chit/merchants":
                body = json.loads(request.content)
                assert body == {"chit_id": 5001}
                merchants = [_merchant(1, "מקדונלד'ס"), _merchant(2, "דומינו'ס פיצה")]
                return httpx.Response(200, json={"status_code": 0, "merchants": merchants})
            raise AssertionError(f"unexpected request: {request.method} {request.url}")

        adapter = _make_adapter(PaisPlusNetworksRegularAdapter, handler)
        stores, deals = await adapter.scrape()

        assert len(stores) == 2
        assert len(deals) == 2  # 2 merchants, this adapter's tier only

    async def test_scrape_missing_csrf_cookie_returns_empty_without_raising(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<html>no cookie set</html>")

        adapter = _make_adapter(PaisPlusFoodChainsRegularAdapter, handler)
        stores, deals = await adapter.scrape()
        assert stores == []
        assert deals == []

    async def test_scrape_cards_get_http_error_returns_empty_without_raising(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return _cookie_response()
            return httpx.Response(419, json={"message": "CSRF token mismatch."})

        adapter = _make_adapter(PaisPlusFoodChainsRegularAdapter, handler)
        stores, deals = await adapter.scrape()
        assert stores == []
        assert deals == []

    async def test_scrape_one_bad_chit_merchants_fetch_does_not_drop_others(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return _cookie_response()
            if request.url.path == "/cashcards/binding-chit/cards/get":
                chits = [_food_chit(chit_id=1), _food_chit(chit_id=2, chit_name="ויקטורי", marketing_name="ויקטורי")]
                return httpx.Response(200, json={"status_code": 0, "chits": chits})
            if request.url.path == "/cashcards/binding-chit/merchants":
                body = json.loads(request.content)
                if body["chit_id"] == 1:
                    return httpx.Response(500)
                return httpx.Response(200, json={"status_code": 0, "merchants": []})
            raise AssertionError(f"unexpected request: {request.url}")

        adapter = _make_adapter(PaisPlusFoodChainsRegularAdapter, handler)
        stores, deals = await adapter.scrape()

        # chit 1's merchants fetch fails (500) -> skipped entirely, no deals.
        # chit 2's merchants fetch succeeds with [] -> chit-as-store, 1 deal.
        assert len(stores) == 1
        assert len(deals) == 1


def test_clubs_json_has_one_entry_per_cashcard_tier_source() -> None:
    # Deal.club_id is looked up by source_id, and the club is what a user ticks
    # to declare their tier — a missing entry leaves the deals unattributable
    # and the tier unselectable.
    clubs_path = Path(__file__).resolve().parents[3] / "data" / "seed" / "clubs.json"
    clubs = json.loads(clubs_path.read_text(encoding="utf-8"))
    by_source = {c["source_id"]: c for c in clubs}

    for adapter in (
        PaisPlusFoodChainsRegularAdapter,
        PaisPlusFoodChainsVipAdapter,
        PaisPlusNetworksRegularAdapter,
        PaisPlusNetworksVipAdapter,
    ):
        source_id = adapter._source_id
        club = by_source.get(source_id)
        assert club is not None, f"no club for {source_id}"
        assert club["id"] == f"club_{source_id}"
        assert club["metadata"]["member_tier"] == adapter._member_tier

    # The pre-split combined clubs are gone; their source_ids no longer exist.
    assert "paisplus_food_chains" not in by_source
    assert "paisplus_networks" not in by_source
