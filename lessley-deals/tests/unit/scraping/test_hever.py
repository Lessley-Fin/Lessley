from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from lessley_deals.scraping.base import SourceConfig
from lessley_deals.scraping.sources.hever import _LOADING_BONUS_TEXT, HeverGiftCardAdapter


def _make_record(
    company: str = "FOX - פוקס",
    company_desc: str = "אופנה ואביזרים לכל המשפחה",
    sn: int = 10,
    website: str = "www.fox.co.il",
    is_online: str = "Y",
    online_limitations: str = "יש ללחוץ על תווי קניה",
    limitations: str = "לא כולל הנחת מועדון ומבצעים בלעדיים",
    **overrides: Any,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "sn": sn,
        "company": company,
        "company_desc": company_desc,
        "company_category": "ביגוד והנעלה",
        "website": website,
        "is_online": is_online,
        "online_limitations": online_limitations,
        "limitations": limitations,
        "logo": "fox.png",
        "internal_link": "",
    }
    record.update(overrides)
    return record


class TestHeverGiftCardAdapter:
    def test_source_id(self) -> None:
        adapter = HeverGiftCardAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        assert adapter.source_id == "hever_gift_card_company"

    def test_to_raw_store(self) -> None:
        adapter = HeverGiftCardAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        record = _make_record()
        now = datetime.now(timezone.utc)
        store = adapter._to_raw_store(record, now)

        assert store.source_id == "hever_gift_card_company"
        assert store.name == "FOX - פוקס"
        assert store.url == "https://www.fox.co.il"

    def test_to_raw_deal_full_description_is_plain_company_desc(self) -> None:
        # raw_payload["full_description"] (what PersistStage reads into the
        # final Deal.deal_description) = the raw company_desc field,
        # verbatim — no loading-bonus blurb prepended (that lives in
        # terms_and_conditions instead).
        adapter = HeverGiftCardAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        record = _make_record(company_desc="אופנה ואביזרים לכל המשפחה")
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)
        assert deal.raw_payload["full_description"] == "אופנה ואביזרים לכל המשפחה"

    def test_to_raw_deal_empty_company_desc_leaves_full_description_empty(self) -> None:
        adapter = HeverGiftCardAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        record = _make_record(company_desc="")
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)
        assert deal.raw_payload["full_description"] == ""

    def test_to_raw_deal_fingerprint_description_includes_store_name(self) -> None:
        # RawScrapedRecord.deal_description feeds fingerprint()
        # (source_id|deal_description|price_text) and price_text is the same
        # fixed string for every store — without the store name folded in,
        # two different stores sharing the same (often empty) company_desc
        # would collide and one could get silently dropped by ScrapeStage's
        # fingerprint dedup on a later re-scrape. Verify it's always unique
        # per store regardless of company_desc.
        adapter = HeverGiftCardAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        now = datetime.now(timezone.utc)
        d1 = adapter._to_raw_deal(_make_record(company="Store A", company_desc=""), now)
        d2 = adapter._to_raw_deal(_make_record(company="Store B", company_desc=""), now)
        assert d1.deal_description != d2.deal_description
        assert d1.fingerprint != d2.fingerprint
        assert "Store A" in d1.deal_description

    def test_to_raw_deal_terms_starts_with_limitations_then_appends_loading_bonus_sentence(self) -> None:
        adapter = HeverGiftCardAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        record = _make_record(
            limitations="לא כולל הנחת מועדון ומבצעים בלעדיים לחברי מועדון של הרשת"
        )
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)
        terms = deal.raw_payload["terms_and_conditions"]

        # limitations text comes first, verbatim and untouched...
        assert terms.startswith("לא כולל הנחת מועדון ומבצעים בלעדיים לחברי מועדון של הרשת")
        # ...then only the fixed default Hever sentence is appended — no
        # company_desc (that's deal_description's job) and no online_limitations.
        assert _LOADING_BONUS_TEXT in terms
        assert "אופנה ואביזרים לכל המשפחה" not in terms  # default company_desc excluded

    def test_to_raw_deal_empty_limitations_terms_is_just_the_loading_bonus_sentence(self) -> None:
        adapter = HeverGiftCardAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        record = _make_record(limitations="")
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)
        terms = deal.raw_payload["terms_and_conditions"]
        assert terms != ""
        assert terms == adapter._loading_bonus_sentence(record)

    def test_to_raw_deal_price_text_is_the_fixed_program_benefit(self) -> None:
        adapter = HeverGiftCardAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        now = datetime.now(timezone.utc)
        d1 = adapter._to_raw_deal(_make_record(company="FOX"), now)
        d2 = adapter._to_raw_deal(_make_record(company="Zara", sn=99), now)
        # Same program-wide loading bonus for every store, not a per-store number
        assert d1.price_text == d2.price_text == "30% הנחה בטעינה (עד 3,000 ₪)"
        assert d1.raw_payload["discount_logic"]["reward"]["value"] == 0.30

    def test_to_raw_deal_type_is_giftcard_discount_and_has_no_legacy_fields(self) -> None:
        adapter = HeverGiftCardAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(_make_record(), now)
        assert deal.raw_payload["deal_type"] == "giftcard_discount"
        assert "constraints" not in deal.raw_payload["discount_logic"]
        assert "stackable" not in deal.raw_payload
        assert "redeem_channels" not in deal.raw_payload
        assert "coupon_code" not in deal.raw_payload

    def test_to_raw_deal_online_limitations_kept_verbatim_in_raw_payload_only(self) -> None:
        # online_limitations isn't a "limitation" in the terms_and_conditions
        # sense and isn't the store description either — it's preserved
        # verbatim in raw_payload for audit but not surfaced into either
        # composed field.
        adapter = HeverGiftCardAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(
            _make_record(is_online="Y", online_limitations="הזמנה אונליין בלבד"), now
        )
        assert deal.raw_payload["online_limitations"] == "הזמנה אונליין בלבד"
        assert "הזמנה אונליין בלבד" not in deal.deal_description
        assert "הזמנה אונליין בלבד" not in deal.raw_payload["terms_and_conditions"]

    def test_to_raw_deal_raw_payload_benefit_url_uses_sn(self) -> None:
        adapter = HeverGiftCardAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(_make_record(sn=10), now)
        assert deal.raw_payload["benefit_url"] == "https://www.hvr.co.il/site/pg/gift_card_store?sn=10"

    def test_to_raw_deal_url_prefers_store_url_over_benefit_url(self) -> None:
        # PersistStage sets Deal.url = prec.raw.url directly with no
        # raw_payload lookup, so the merchant's own site must win here.
        adapter = HeverGiftCardAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(_make_record(website="www.fox.co.il", sn=10), now)
        assert deal.url == "https://www.fox.co.il"

    def test_to_raw_deal_url_falls_back_to_benefit_url_when_no_website(self) -> None:
        adapter = HeverGiftCardAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(_make_record(website="", sn=10), now)
        assert deal.raw_payload["store_url"] is None
        assert deal.url == "https://www.hvr.co.il/site/pg/gift_card_store?sn=10"

    def test_to_raw_deal_raw_payload_carries_title_and_full_description(self) -> None:
        # PersistStage reads deal_title/full_description straight off
        # raw_payload with no fallback (Deal.title/deal_description would be
        # null otherwise) — verify hever.py sets them explicitly.
        adapter = HeverGiftCardAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        record = _make_record(company="FOX - פוקס")
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)
        assert deal.raw_payload["deal_title"] == "FOX - פוקס" == deal.store_name
        assert deal.raw_payload["full_description"] == "אופנה ואביזרים לכל המשפחה"


def _mock_adapter(handler) -> HeverGiftCardAdapter:
    transport = httpx.MockTransport(handler)
    return HeverGiftCardAdapter(SourceConfig(base_url="https://www.hvr.co.il"), transport=transport)


class TestHeverGiftCardAdapterScrape:
    async def test_scrape_fetches_live_dataset_and_dedups_stores(self) -> None:
        payload = [
            _make_record(company="FOX", sn=10),
            _make_record(company="FOX", sn=10),  # duplicate store row
            _make_record(company="Zara", sn=11, website="www.zara.com"),
        ]

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/bs2/datasets/giftcard.json"
            return httpx.Response(200, json=payload)

        adapter = _mock_adapter(handler)
        stores, deals = await adapter.scrape()

        assert sorted(s.name for s in stores) == ["FOX", "Zara"]
        assert len(deals) == 3  # every JSON object still becomes its own deal record

    async def test_scrape_http_error_returns_empty_without_raising(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500)

        adapter = _mock_adapter(handler)
        stores, deals = await adapter.scrape()
        assert stores == []
        assert deals == []

    async def test_scrape_invalid_json_returns_empty_without_raising(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="not json {")

        adapter = _mock_adapter(handler)
        stores, deals = await adapter.scrape()
        assert stores == []
        assert deals == []

    async def test_scrape_non_list_json_returns_empty_without_raising(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"not": "a list"})

        adapter = _mock_adapter(handler)
        stores, deals = await adapter.scrape()
        assert stores == []
        assert deals == []

    async def test_scrape_skips_records_without_company(self) -> None:
        payload = [_make_record(company="FOX"), {"sn": 1, "company": ""}]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        adapter = _mock_adapter(handler)
        stores, deals = await adapter.scrape()
        assert len(stores) == 1
        assert len(deals) == 1


def test_clubs_json_has_a_matching_entry_for_hever_gift_card_company() -> None:
    """PersistStage sets Deal.club_id by looking up Club.source_id (not
    anything in raw_payload) — a clubs.json entry is what actually gives
    Hever deals a club_id, same mechanism as club_topcash etc."""
    clubs_path = Path(__file__).resolve().parents[3] / "data" / "clubs.json"
    clubs = json.loads(clubs_path.read_text(encoding="utf-8"))
    hever_club = next((c for c in clubs if c["source_id"] == "hever_gift_card_company"), None)
    assert hever_club is not None
    assert hever_club["id"] == "club_hever_gift_card_company"


def test_clubs_json_has_a_matching_entry_for_hever_teamim_card_store() -> None:
    clubs_path = Path(__file__).resolve().parents[3] / "data" / "clubs.json"
    clubs = json.loads(clubs_path.read_text(encoding="utf-8"))
    teamim_club = next((c for c in clubs if c["source_id"] == "hever_teamim_card_store"), None)
    assert teamim_club is not None
    assert teamim_club["id"] == "club_hever_teamim_card_store"
