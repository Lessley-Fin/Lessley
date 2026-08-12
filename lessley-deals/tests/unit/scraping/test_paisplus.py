from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from lessley_deals.scraping.base import SourceConfig
from lessley_deals.scraping.sources.paisplus import (
    PaisPlusAdapter,
    _extract_branch,
    _extract_brand,
    _extract_preloaded_state,
)


def _price_entry(
    branch_city: str = "עכו",
    # Real pricelist_name text uses just the short brand token ("BULLS"),
    # not the full product-title brand ("BULLS שף בורגר") -- this
    # deliberately differs from _bulls_product's brand to exercise the
    # word-prefix-stripping logic in _extract_branch (see the regression
    # test for the bug this masked when both used the same full string).
    pricelist_brand: str = "BULLS",
    club_price: int = 109,
    discounted_price: int = 129,
    market_price: int = 150,
    **overrides: Any,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "pricelist_name": f"תו קנייה בשווי {market_price} ₪ לסניף {pricelist_brand} {branch_city}",
        "club_price": club_price,
        "discounted_price": discounted_price,
        "market_price": market_price,
        "provider_id": 2356,
        "provider_bn": "516338837",
        "display_provider_address": f"כתובת ב{branch_city}",
        "display_provider_name": "י.נ אור ניהול בע\"מ",
        "display_provider_phone": "1700700722",
    }
    entry.update(overrides)
    return entry


_BULLS_BRANCHES = ["עכו", "נשר", "קריית חיים חיפה", "נהריה", "אפקה קריית ביאליק"]


def _bulls_product(**overrides: Any) -> dict[str, Any]:
    product: dict[str, Any] = {
        "product_id": 32051,
        "product_name": "תו קנייה בשווי 150 ₪ לרשת BULLS שף בורגר",
        "short_description": "<p>להזמנה בסניפים</p>",
        "restriction_description": "<p>יש לרכוש תו ייעודי לסניף הרלוונטי.</p>",
        "merchant_site_url": None,
        "images": [
            {"image_url": "https://media.dolcemaster.co.il/bulls.jpg", "main_image": "Y"},
        ],
        "prices": [_price_entry(branch_city=city) for city in _BULLS_BRANCHES],
    }
    product.update(overrides)
    return product


def _html_with_state(state: dict[str, Any]) -> str:
    return (
        "<html><body><script>\n"
        f"window.__PRELOADED_STATE__ = {json.dumps(state, ensure_ascii=False)};\n"
        "</script></body></html>"
    )


def _category_state(products: list[dict[str, Any]], has_more: str = "N") -> dict[str, Any]:
    return {
        "dataApi": {
            "category": {
                "category_id": 1697,
                "products": products,
                "has_more": has_more,
            }
        }
    }


def _product_state(product: dict[str, Any]) -> dict[str, Any]:
    return {"dataApi": {"product": {"product": product}}}


class TestExtractPreloadedState:
    def test_happy_path(self) -> None:
        html = _html_with_state({"dataApi": {"foo": "בדיקה"}})
        state = _extract_preloaded_state(html)
        assert state == {"dataApi": {"foo": "בדיקה"}}

    def test_missing_script_raises(self) -> None:
        try:
            _extract_preloaded_state("<html><body>no state here</body></html>")
        except ValueError as exc:
            assert "not found" in str(exc)
        else:
            raise AssertionError("expected ValueError")

    def test_trailing_content_after_json_is_ignored(self) -> None:
        html = (
            "<script>window.__PRELOADED_STATE__ = {\"a\": 1};    "
            "console.log('other stuff');</script>"
        )
        state = _extract_preloaded_state(html)
        assert state == {"a": 1}


class TestBrandAndBranchExtraction:
    def test_extract_brand_lerreshet_pattern(self) -> None:
        assert _extract_brand("תו קנייה בשווי 150 ₪ לרשת BULLS שף בורגר") == "BULLS שף בורגר"

    def test_extract_brand_bereshet_pattern(self) -> None:
        assert _extract_brand("תו קנייה בשווי 100 ₪ למימוש ברשת JUST MEAT") == "JUST MEAT"

    def test_extract_brand_no_match_falls_back_to_full_title(self) -> None:
        assert _extract_brand("תווים לחנות מיוחדת") == "תווים לחנות מיוחדת"

    def test_extract_branch_strips_shared_prefix_and_brand(self) -> None:
        branch = _extract_branch("תו קנייה בשווי 150 ₪ לסניף BULLS עכו", "BULLS")
        assert branch == "עכו"

    def test_extract_branch_when_brand_has_trailing_marketing_words(self) -> None:
        # Regression: confirmed live on product 32051 -- pricelist_name uses
        # just "BULLS", but the product-title-derived brand is "BULLS שף
        # בורגר" (extra words). A full-string startswith(brand) never
        # matches here, so branch must strip only the shared leading words.
        branch = _extract_branch("תו קנייה בשווי 150 ₪ לסניף BULLS עכו", "BULLS שף בורגר")
        assert branch == "עכו"

    def test_extract_branch_falls_back_to_full_name_when_no_prefix(self) -> None:
        assert _extract_branch("סניף מרכזי", "BULLS") == "סניף מרכזי"


def _make_adapter(handler=None) -> PaisPlusAdapter:
    transport = httpx.MockTransport(handler) if handler else None
    return PaisPlusAdapter(
        SourceConfig(base_url="https://paisplus.co.il"),
        category_ids=[1697],
        transport=transport,
    )


class TestToRawRecordsFanOut:
    def test_five_branches_two_tiers_yields_five_stores_ten_deals(self) -> None:
        adapter = _make_adapter()
        product = _bulls_product()
        now = datetime.now(timezone.utc)
        pairs = adapter._to_raw_records(product, now)

        assert len(pairs) == 10  # 5 branches * 2 tiers

        stores = {s.fingerprint: s for s, _d in pairs}
        assert len(stores) == 5

        branches = {s.branch for s, _d in pairs}
        assert branches == set(_BULLS_BRANCHES)

        tiers = {d.raw_payload["price_tier"] for _s, d in pairs}
        assert tiers == {"club", "discounted"}

    def test_store_name_and_address_per_branch(self) -> None:
        adapter = _make_adapter()
        product = _bulls_product()
        now = datetime.now(timezone.utc)
        store, _deal = adapter._to_raw_records(product, now)[0]

        assert store.name == "BULLS שף בורגר"
        assert store.branch == "עכו"
        assert store.address == "כתובת בעכו"

    def test_fingerprint_unique_across_identically_priced_branches(self) -> None:
        # Confirmed live: BULLS' 5 branches all share club_price=109,
        # discounted_price=129, market_price=150 -- price_text alone can't
        # disambiguate them, so branch must be folded into deal_description.
        adapter = _make_adapter()
        product = _bulls_product()
        now = datetime.now(timezone.utc)
        pairs = adapter._to_raw_records(product, now)

        fingerprints = {d.fingerprint for _s, d in pairs}
        assert len(fingerprints) == 10

    def test_price_text_and_discount_logic_use_tier_specific_price(self) -> None:
        adapter = _make_adapter()
        product = _bulls_product()
        now = datetime.now(timezone.utc)
        pairs = adapter._to_raw_records(product, now)

        club_deal = next(d for _s, d in pairs if d.raw_payload["price_tier"] == "club")
        discounted_deal = next(d for _s, d in pairs if d.raw_payload["price_tier"] == "discounted")

        assert club_deal.price_text == "109 ₪ (מחיר מלא 150 ₪)"
        assert club_deal.raw_payload["discount_logic"]["reward"]["value"] == 41

        assert discounted_deal.price_text == "129 ₪ (מחיר מלא 150 ₪)"
        assert discounted_deal.raw_payload["discount_logic"]["reward"]["value"] == 21

    def test_terms_and_conditions_come_from_restriction_description_stripped_of_html(self) -> None:
        adapter = _make_adapter()
        product = _bulls_product(
            restriction_description="<p>יש לרכוש תו ייעודי <b>לסניף הרלוונטי</b>.</p>"
        )
        now = datetime.now(timezone.utc)
        _store, deal = adapter._to_raw_records(product, now)[0]
        terms = deal.raw_payload["terms_and_conditions"]
        assert "יש לרכוש תו ייעודי" in terms
        assert "לסניף הרלוונטי" in terms
        assert "<" not in terms and ">" not in terms

    def test_deal_type_is_giftcard_discount_and_has_no_legacy_fields(self) -> None:
        adapter = _make_adapter()
        product = _bulls_product()
        now = datetime.now(timezone.utc)
        _store, deal = adapter._to_raw_records(product, now)[0]
        assert deal.raw_payload["deal_type"] == "giftcard_discount"
        assert "constraints" not in deal.raw_payload["discount_logic"]
        assert "stackable" not in deal.raw_payload
        assert "redeem_channels" not in deal.raw_payload
        assert "coupon_code" not in deal.raw_payload

    def test_entry_with_missing_prices_is_skipped(self) -> None:
        adapter = _make_adapter()
        product = _bulls_product(prices=[_price_entry(club_price=None)])
        now = datetime.now(timezone.utc)
        pairs = adapter._to_raw_records(product, now)
        # club tier skipped (None price), discounted tier still produced
        assert len(pairs) == 1
        assert pairs[0][1].raw_payload["price_tier"] == "discounted"


class TestScrape:
    async def test_scrape_end_to_end_single_category_single_product(self) -> None:
        product = _bulls_product()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/category/1697":
                return httpx.Response(
                    200, text=_html_with_state(_category_state([{"product_id": 32051}]))
                )
            if request.url.path == "/product/32051":
                return httpx.Response(200, text=_html_with_state(_product_state(product)))
            raise AssertionError(f"unexpected request: {request.url}")

        adapter = _make_adapter(handler)
        stores, deals = await adapter.scrape()

        assert len(stores) == 5
        assert len(deals) == 10

    async def test_scrape_paginates_category_via_has_more(self) -> None:
        page_calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/category/1697":
                skip = request.url.params.get("skip")
                page_calls.append(skip or "0")
                if not skip:
                    return httpx.Response(
                        200,
                        text=_html_with_state(
                            _category_state([{"product_id": 1}], has_more="Y")
                        ),
                    )
                return httpx.Response(
                    200, text=_html_with_state(_category_state([{"product_id": 2}], has_more="N"))
                )
            if request.url.path in ("/product/1", "/product/2"):
                pid = int(request.url.path.rsplit("/", 1)[-1])
                return httpx.Response(
                    200,
                    text=_html_with_state(_product_state(_bulls_product(product_id=pid))),
                )
            raise AssertionError(f"unexpected request: {request.url}")

        adapter = _make_adapter(handler)
        stores, deals = await adapter.scrape()

        assert page_calls == ["0", "1"]
        assert len(deals) == 20  # 2 products * 10 deals each

    async def test_scrape_category_http_error_returns_empty_without_raising(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500)

        adapter = _make_adapter(handler)
        stores, deals = await adapter.scrape()
        assert stores == []
        assert deals == []

    async def test_scrape_one_bad_product_does_not_drop_siblings(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/category/1697":
                return httpx.Response(
                    200,
                    text=_html_with_state(
                        _category_state([{"product_id": 1}, {"product_id": 2}])
                    ),
                )
            if request.url.path == "/product/1":
                return httpx.Response(500)
            if request.url.path == "/product/2":
                return httpx.Response(
                    200,
                    text=_html_with_state(_product_state(_bulls_product(product_id=2))),
                )
            raise AssertionError(f"unexpected request: {request.url}")

        adapter = _make_adapter(handler)
        stores, deals = await adapter.scrape()

        assert len(deals) == 10  # only product 2 succeeded

    async def test_scrape_malformed_html_skips_without_raising(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<html>no preloaded state</html>")

        adapter = _make_adapter(handler)
        stores, deals = await adapter.scrape()
        assert stores == []
        assert deals == []

    async def test_scrape_no_categories_configured_returns_empty(self) -> None:
        adapter = PaisPlusAdapter(
            SourceConfig(base_url="https://paisplus.co.il"),
            category_ids=[],
        )
        stores, deals = await adapter.scrape()
        assert stores == []
        assert deals == []


def test_clubs_json_has_a_matching_entry_for_paisplus() -> None:
    clubs_path = Path(__file__).resolve().parents[3] / "data" / "seed" / "clubs.json"
    clubs = json.loads(clubs_path.read_text(encoding="utf-8"))
    club = next((c for c in clubs if c["source_id"] == "paisplus"), None)
    assert club is not None
    assert club["id"] == "club_paisplus"
