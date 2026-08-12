from __future__ import annotations

from unittest.mock import AsyncMock

from lessley_deals.enrichment.llm_client import DealDetail, ExtractedDeal
from lessley_deals.scraping.base import SourceConfig
from lessley_deals.scraping.sources.llm_scraper import (
    LlmScraperAdapter,
    build_discount_logic,
)


def _adapter(engine: object, **kw: object) -> LlmScraperAdapter:
    return LlmScraperAdapter(
        SourceConfig(base_url="https://x.test"),
        site_id="llm:test",
        url="https://x.test/deals",
        instructions="Extract deals",
        engine=engine,  # type: ignore[arg-type]
        **kw,  # type: ignore[arg-type]
    )


# --------------------------------------------------------------------------
# discount logic derivation
# --------------------------------------------------------------------------

def test_build_discount_logic_percentage() -> None:
    logic, currency = build_discount_logic("עד 9% קאשבק")
    assert currency == "ILS"
    assert logic is not None
    assert logic["type"] == "percentage"
    assert logic["reward"]["value"] == 0.09


def test_build_discount_logic_fixed_shekel() -> None:
    logic, currency = build_discount_logic("100₪")
    assert currency == "ILS"
    assert logic is not None
    assert logic["type"] == "fixed_discount"
    assert logic["reward"]["value"] == 100.0


def test_build_discount_logic_dollar_currency() -> None:
    logic, currency = build_discount_logic("5$ הנחה")
    assert currency == "USD"
    assert logic is not None
    assert logic["reward"]["value"] == 5.0


def test_build_discount_logic_empty() -> None:
    logic, currency = build_discount_logic("")
    assert logic is None
    assert currency == "ILS"


# --------------------------------------------------------------------------
# default (single-page) mode
# --------------------------------------------------------------------------

async def test_scrape_maps_deals_and_dedups_stores() -> None:
    engine = AsyncMock()
    engine.run.return_value = [
        ExtractedDeal(store_name="Nike", deal_description="20% off", price_text="20%"),
        ExtractedDeal(store_name="Nike", deal_description="BOGO", price_text=""),
        ExtractedDeal(store_name="Adidas", deal_description="50 ILS", price_text="50 ₪"),
    ]
    adapter = _adapter(engine)
    stores, deals = await adapter.scrape()

    assert adapter.source_id == "llm:test"
    assert len(deals) == 3
    assert {d.store_name for d in deals} == {"Nike", "Adidas"}
    assert all(d.source_id == "llm:test" for d in deals)
    assert sorted(s.name for s in stores) == ["Adidas", "Nike"]
    # rich payload: percentage discount_logic derived from price_text
    nike = next(d for d in deals if d.store_name == "Nike" and d.price_text == "20%")
    assert nike.raw_payload["discount_logic"]["reward"]["value"] == 0.20
    assert nike.raw_payload["title"] == "20% באתר Nike"


async def test_scrape_returns_empty_on_engine_failure() -> None:
    engine = AsyncMock()
    engine.run.side_effect = RuntimeError("browser crashed")
    stores, deals = await _adapter(engine).scrape()
    assert stores == []
    assert deals == []


# --------------------------------------------------------------------------
# file-based mode (local snapshot, no live fetch)
# --------------------------------------------------------------------------

async def test_scrape_file_path_uses_run_from_file_not_run() -> None:
    engine = AsyncMock()
    engine.run_from_file.return_value = [
        ExtractedDeal(
            store_name="FOX",
            deal_description="30% loading bonus",
            price_text="30%",
            terms_and_conditions="no club discount",
        ),
    ]
    adapter = _adapter(engine, file_path="/snapshots/giftcard.json", is_json=True)
    stores, deals = await adapter.scrape()

    engine.run_from_file.assert_awaited_once_with(
        "/snapshots/giftcard.json", "Extract deals", is_json=True
    )
    engine.run.assert_not_called()
    assert len(deals) == 1
    assert deals[0].store_name == "FOX"
    # terms_and_conditions from the plain (non-detail) ExtractedDeal flows into raw_payload
    assert deals[0].raw_payload["terms_and_conditions"] == "no club discount"


async def test_scrape_file_path_returns_empty_on_engine_failure() -> None:
    engine = AsyncMock()
    engine.run_from_file.side_effect = FileNotFoundError("no snapshot yet")
    stores, deals = await _adapter(engine, file_path="/snapshots/missing.json").scrape()
    assert stores == []
    assert deals == []


# --------------------------------------------------------------------------
# detail-crawl mode
# --------------------------------------------------------------------------

async def test_scrape_crawl_details_builds_rich_record() -> None:
    engine = AsyncMock()
    deal = ExtractedDeal(
        store_name="AliExpress | אליאקספרס",
        deal_description="עד 9% קאשבק",
        price_text="עד 9% קאשבק",
        detail_url="/store/Aliexpress/1786",
    )
    detail = DealDetail(
        deal_description="אלי אקספרס - אתר מסחר סיני",
        terms_and_conditions="תנאים לקבלת הקאשבק",
        coupon_code="ISRACARDAFF8",
    )
    engine.run_with_details.return_value = [(deal, detail)]

    adapter = _adapter(engine, crawl_details=True, detail_instructions="blurb+terms")
    stores, deals = await adapter.scrape()

    assert len(deals) == 1
    rec = deals[0]
    assert rec.store_name == "AliExpress | אליאקספרס"
    assert rec.url == "https://x.test/store/Aliexpress/1786"
    assert rec.deal_description == "אלי אקספרס - אתר מסחר סיני"  # from detail blurb
    pay = rec.raw_payload
    assert pay["terms_and_conditions"] == "תנאים לקבלת הקאשבק"
    assert pay["coupon_code"] == "ISRACARDAFF8"
    assert pay["store_id"] == "Aliexpress"
    assert pay["external_id"] == "1786"
    assert pay["discount_logic"]["reward"]["value"] == 0.09
    assert pay["currency"] == "ILS"
    # engine called in detail mode
    engine.run_with_details.assert_awaited_once()
