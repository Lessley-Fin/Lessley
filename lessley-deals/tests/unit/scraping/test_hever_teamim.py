from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from lessley_deals.scraping.base import SourceConfig
from lessley_deals.scraping.sources.hever_teamim import _LOADING_BONUS_TEXT, HeverTeamimAdapter


def _make_record(
    name: str = "אנג'לינה פיצה ופסטה",
    desc: str = "מסעדה איטלקית",
    website: str = "angelinapizzapasta.rest.co.il",
    delivery: str = "ישיבה במסעדה",
    limitations: str = "",
    internal_link: str = "mcc_item_new,384198",
    **overrides: Any,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "img": "logo_angelina.jpg",
        "name": name,
        "desc": desc,
        "area": "אילת",
        "city": "אילת",
        "address": "טיילת המלך",
        "phone": "08-6363439",
        "category": "מסעדה",
        "type": "איטלקי",
        "hours": "א-ה: 19:00-23:00",
        "kosher": "כשר",
        "handicap": "Y",
        "website": website,
        "delivery": delivery,
        "internal_link": internal_link,
        "is_new": "N",
        "limitations": limitations,
        "latitude": "29.557669",
        "longitude": "34.951925",
    }
    record.update(overrides)
    return record


def _mock_adapter(handler) -> HeverTeamimAdapter:
    transport = httpx.MockTransport(handler)
    return HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"), transport=transport)


class TestHeverTeamimAdapter:
    def test_source_id(self) -> None:
        adapter = HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        assert adapter.source_id == "hever_teamim_card_store"

    def test_to_raw_store(self) -> None:
        adapter = HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        record = _make_record()
        now = datetime.now(timezone.utc)
        store = adapter._to_raw_store(record, now)

        assert store.source_id == "hever_teamim_card_store"
        assert store.name == "אנג'לינה פיצה ופסטה"
        assert store.url == "https://angelinapizzapasta.rest.co.il"

    def test_to_raw_deal_full_description_is_plain_desc(self) -> None:
        adapter = HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        record = _make_record(desc="מסעדה איטלקית")
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)
        assert deal.raw_payload["full_description"] == "מסעדה איטלקית"

    def test_to_raw_deal_empty_desc_leaves_full_description_empty(self) -> None:
        adapter = HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        record = _make_record(desc="")
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)
        assert deal.raw_payload["full_description"] == ""

    def test_to_raw_deal_fingerprint_description_includes_store_name(self) -> None:
        # RawScrapedRecord.deal_description feeds fingerprint()
        # (source_id|deal_description|price_text) and price_text is the same
        # fixed string for every restaurant — without the name folded in,
        # two different restaurants sharing the same (often empty/generic)
        # desc would collide and one could get silently dropped by
        # ScrapeStage's fingerprint dedup on a later re-scrape.
        adapter = HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        now = datetime.now(timezone.utc)
        d1 = adapter._to_raw_deal(_make_record(name="Restaurant A", desc=""), now)
        d2 = adapter._to_raw_deal(_make_record(name="Restaurant B", desc=""), now)
        assert d1.deal_description != d2.deal_description
        assert d1.fingerprint != d2.fingerprint
        assert "Restaurant A" in d1.deal_description

    def test_to_raw_deal_terms_starts_with_delivery_mode_then_appends_loading_bonus_sentence(self) -> None:
        adapter = HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        record = _make_record(delivery="ישיבה במסעדה,איסוף עצמי")
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)
        terms = deal.raw_payload["terms_and_conditions"]

        assert terms.startswith("ישיבה במסעדה,איסוף עצמי")
        assert _LOADING_BONUS_TEXT in terms
        assert "מסעדה איטלקית" not in terms  # desc excluded, that's deal_description's job

    def test_to_raw_deal_terms_includes_limitations_when_present(self) -> None:
        adapter = HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        record = _make_record(delivery="ישיבה במסעדה", limitations="לא כולל ימי שישי")
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)
        terms = deal.raw_payload["terms_and_conditions"]

        assert "ישיבה במסעדה" in terms
        assert "לא כולל ימי שישי" in terms

    def test_to_raw_deal_empty_delivery_and_limitations_terms_is_just_the_loading_bonus_sentence(self) -> None:
        adapter = HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        record = _make_record(delivery="", limitations="")
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)
        terms = deal.raw_payload["terms_and_conditions"]
        assert terms != ""
        assert terms == adapter._loading_bonus_sentence(record)

    def test_to_raw_deal_price_text_is_the_fixed_program_benefit(self) -> None:
        adapter = HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        now = datetime.now(timezone.utc)
        d1 = adapter._to_raw_deal(_make_record(name="Restaurant A"), now)
        d2 = adapter._to_raw_deal(_make_record(name="Restaurant B"), now)
        assert d1.price_text == d2.price_text == "30% הנחה בטעינה (עד 3,000 ₪)"
        assert d1.raw_payload["discount_logic"]["reward"]["value"] == 0.30

    def test_to_raw_deal_raw_payload_benefit_url_uses_internal_link(self) -> None:
        adapter = HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(_make_record(internal_link="mcc_item_new,384198"), now)
        assert deal.raw_payload["benefit_url"] == "https://www.hvr.co.il/site/pg/mcc_item_new,384198"

    def test_to_raw_deal_no_benefit_url_when_no_internal_link(self) -> None:
        adapter = HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(_make_record(internal_link=""), now)
        assert deal.raw_payload["benefit_url"] is None

    def test_to_raw_deal_url_prefers_store_url_over_benefit_url(self) -> None:
        adapter = HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(_make_record(website="angelinapizzapasta.rest.co.il"), now)
        assert deal.url == "https://angelinapizzapasta.rest.co.il"

    def test_to_raw_deal_url_falls_back_to_benefit_url_when_no_website(self) -> None:
        adapter = HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(
            _make_record(website="", internal_link="mcc_item_new,384198"), now
        )
        assert deal.raw_payload["store_url"] is None
        assert deal.url == "https://www.hvr.co.il/site/pg/mcc_item_new,384198"

    def test_to_raw_deal_raw_payload_carries_title_and_full_description(self) -> None:
        adapter = HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        record = _make_record(name="אנג'לינה פיצה ופסטה")
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)
        assert deal.raw_payload["deal_title"] == "אנג'לינה פיצה ופסטה" == deal.store_name
        assert deal.raw_payload["full_description"] == "מסעדה איטלקית"

    def test_to_raw_deal_redeem_channels_is_always_physical_store(self) -> None:
        adapter = HeverTeamimAdapter(SourceConfig(base_url="https://www.hvr.co.il"))
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(_make_record(delivery="משלוחים"), now)
        assert deal.raw_payload["redeem_channels"] == ["physical_store"]


class TestHeverTeamimAdapterScrape:
    async def test_scrape_fetches_live_dataset_and_dedups_stores_across_branches(self) -> None:
        payload = {
            "branch": [
                _make_record(name="קפה קפה", city="דימונה"),
                _make_record(name="קפה קפה", city="נתיבות"),  # same chain, different branch
                _make_record(name="קאזה דו ברזיל", city="אילת"),
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/bs2/datasets/teamimcard_branches.json"
            return httpx.Response(200, json=payload)

        adapter = _mock_adapter(handler)
        stores, deals = await adapter.scrape()

        assert sorted(s.name for s in stores) == ["קאזה דו ברזיל", "קפה קפה"]
        assert len(deals) == 3  # every branch still becomes its own deal record

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

    async def test_scrape_missing_branch_key_returns_empty_without_raising(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"not": "branch"})

        adapter = _mock_adapter(handler)
        stores, deals = await adapter.scrape()
        assert stores == []
        assert deals == []

    async def test_scrape_skips_records_without_name(self) -> None:
        payload = {"branch": [_make_record(name="קפה קפה"), {"city": "אילת", "name": ""}]}

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        adapter = _mock_adapter(handler)
        stores, deals = await adapter.scrape()
        assert len(stores) == 1
        assert len(deals) == 1
