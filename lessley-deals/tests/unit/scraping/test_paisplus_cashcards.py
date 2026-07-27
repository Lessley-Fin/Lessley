from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from lessley_deals.scraping.base import SourceConfig
from lessley_deals.scraping.sources.paisplus_cashcards import (
    PaisPlusFoodChainsAdapter,
    PaisPlusNetworksAdapter,
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
    def test_food_chit_as_store_yields_two_deals_regular_and_vip(self) -> None:
        adapter = _make_adapter(PaisPlusFoodChainsAdapter)
        chit = _food_chit()
        now = datetime.now(timezone.utc)
        pairs = adapter._to_raw_records(chit, [], now)

        assert len(pairs) == 2
        stores = {s.fingerprint for s, _d in pairs}
        assert len(stores) == 1  # same store, two tier-deals

        tiers = {d.raw_payload["member_tier"] for _s, d in pairs}
        assert tiers == {"regular", "vip"}

    def test_regular_tier_uses_entry_bracket_as_headline_discount(self) -> None:
        adapter = _make_adapter(PaisPlusFoodChainsAdapter)
        chit = _food_chit()
        now = datetime.now(timezone.utc)
        pairs = adapter._to_raw_records(chit, [], now)

        regular_deal = next(d for _s, d in pairs if d.raw_payload["member_tier"] == "regular")
        assert regular_deal.raw_payload["discount_logic"]["reward"]["value"] == 0.075
        assert "2200" in regular_deal.price_text  # max loadable amount for this tier
        assert "7.5" in regular_deal.price_text

    def test_vip_tier_uses_its_own_entry_bracket(self) -> None:
        adapter = _make_adapter(PaisPlusFoodChainsAdapter)
        chit = _food_chit()
        now = datetime.now(timezone.utc)
        pairs = adapter._to_raw_records(chit, [], now)

        vip_deal = next(d for _s, d in pairs if d.raw_payload["member_tier"] == "vip")
        assert vip_deal.raw_payload["discount_logic"]["reward"]["value"] == 0.10
        assert "3000" in vip_deal.price_text  # max loadable amount for this tier

    def test_terms_include_own_constraints_then_bonus_sentence(self) -> None:
        adapter = _make_adapter(PaisPlusFoodChainsAdapter)
        chit = _food_chit()
        now = datetime.now(timezone.utc)
        _store, deal = adapter._to_raw_records(chit, [], now)[0]
        terms = deal.raw_payload["terms_and_conditions"]
        assert "לא כולל אתר סחר" in terms
        assert "ניתן לטעון ולקבל" in terms
        assert "קרפור" in terms

    def test_store_name_and_url_from_chit_when_no_merchants(self) -> None:
        adapter = _make_adapter(PaisPlusFoodChainsAdapter)
        chit = _food_chit()
        now = datetime.now(timezone.utc)
        store, deal = adapter._to_raw_records(chit, [], now)[0]
        assert store.name == "קרפור"
        assert store.url is None
        assert deal.raw_payload["redeem_channels"] == ["physical_store"]
        assert deal.raw_payload["benefit_url"] == "https://paisplus.co.il/cashcards/food-chains"


class TestMerchantFanOut:
    def test_three_merchants_share_chit_tiers_yields_six_deals(self) -> None:
        adapter = _make_adapter(PaisPlusNetworksAdapter)
        chit = _networks_chit()
        merchants = [
            _merchant(1, "מקדונלד'ס"),
            _merchant(2, "דומינו'ס פיצה"),
            _merchant(3, "American Eagle"),
        ]
        now = datetime.now(timezone.utc)
        pairs = adapter._to_raw_records(chit, merchants, now)

        assert len(pairs) == 6  # 3 merchants * 2 tiers
        stores = {s.fingerprint for s, _d in pairs}
        assert len(stores) == 3

    def test_merchant_store_url_prefers_site_url_over_branches_page(self) -> None:
        adapter = _make_adapter(PaisPlusNetworksAdapter)
        chit = _networks_chit()
        merchants = [
            _merchant(1, "American Eagle", site_url="https://ae.co.il", branches_page_url="https://ae.co.il/branches")
        ]
        now = datetime.now(timezone.utc)
        store, deal = adapter._to_raw_records(chit, merchants, now)[0]
        assert store.url == "https://ae.co.il"
        assert deal.raw_payload["redeem_channels"] == ["physical_store", "online"]

    def test_merchant_terms_come_from_limitations_text_not_chit(self) -> None:
        adapter = _make_adapter(PaisPlusNetworksAdapter)
        chit = _networks_chit(short_description=None)
        merchants = [_merchant(1, "מקדונלד'ס", limitations_text="לא ניתן להמרה למזומן.")]
        now = datetime.now(timezone.utc)
        _store, deal = adapter._to_raw_records(chit, merchants, now)[0]
        assert "לא ניתן להמרה למזומן" in deal.raw_payload["terms_and_conditions"]

    def test_fingerprint_unique_across_identically_priced_merchants(self) -> None:
        # Confirmed live: every merchant under a chit shares identical
        # bracket numbers, so price_text alone can't disambiguate stores.
        adapter = _make_adapter(PaisPlusNetworksAdapter)
        chit = _networks_chit()
        merchants = [_merchant(i, f"Store {i}") for i in range(5)]
        now = datetime.now(timezone.utc)
        pairs = adapter._to_raw_records(chit, merchants, now)
        fingerprints = {d.fingerprint for _s, d in pairs}
        assert len(fingerprints) == 10  # 5 merchants * 2 tiers


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

        adapter = _make_adapter(PaisPlusFoodChainsAdapter, handler)
        stores, deals = await adapter.scrape()

        assert seen_tokens == ["abc=123"]
        assert len(stores) == 1
        assert len(deals) == 2

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

        adapter = _make_adapter(PaisPlusNetworksAdapter, handler)
        stores, deals = await adapter.scrape()

        assert len(stores) == 2
        assert len(deals) == 4

    async def test_scrape_missing_csrf_cookie_returns_empty_without_raising(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<html>no cookie set</html>")

        adapter = _make_adapter(PaisPlusFoodChainsAdapter, handler)
        stores, deals = await adapter.scrape()
        assert stores == []
        assert deals == []

    async def test_scrape_cards_get_http_error_returns_empty_without_raising(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return _cookie_response()
            return httpx.Response(419, json={"message": "CSRF token mismatch."})

        adapter = _make_adapter(PaisPlusFoodChainsAdapter, handler)
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

        adapter = _make_adapter(PaisPlusFoodChainsAdapter, handler)
        stores, deals = await adapter.scrape()

        # chit 1's merchants fetch fails (500) -> skipped entirely, no deals.
        # chit 2's merchants fetch succeeds with [] -> chit-as-store, 2 deals.
        assert len(stores) == 1
        assert len(deals) == 2


def test_clubs_json_has_matching_entries_for_both_cashcard_sources() -> None:
    clubs_path = Path(__file__).resolve().parents[3] / "data" / "clubs.json"
    clubs = json.loads(clubs_path.read_text(encoding="utf-8"))

    food_club = next((c for c in clubs if c["source_id"] == "paisplus_food_chains"), None)
    assert food_club is not None
    assert food_club["id"] == "club_paisplus_food_chains"

    networks_club = next((c for c in clubs if c["source_id"] == "paisplus_networks"), None)
    assert networks_club is not None
    assert networks_club["id"] == "club_paisplus_networks"
