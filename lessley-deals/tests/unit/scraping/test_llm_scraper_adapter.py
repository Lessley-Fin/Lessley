from __future__ import annotations

from unittest.mock import AsyncMock

from lessley_deals.enrichment.llm_client import ExtractedDeal
from lessley_deals.scraping.base import SourceConfig
from lessley_deals.scraping.sources.llm_scraper import LlmScraperAdapter


def _adapter(engine: object) -> LlmScraperAdapter:
    return LlmScraperAdapter(
        SourceConfig(base_url="https://x.test"),
        site_id="llm:test",
        url="https://x.test/deals",
        instructions="Extract deals",
        engine=engine,  # type: ignore[arg-type]
    )


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
    # one store per unique name
    assert sorted(s.name for s in stores) == ["Adidas", "Nike"]
    assert deals[0].raw_payload["store_name"] == "Nike"


async def test_scrape_returns_empty_on_engine_failure() -> None:
    engine = AsyncMock()
    engine.run.side_effect = RuntimeError("browser crashed")
    stores, deals = await _adapter(engine).scrape()
    assert stores == []
    assert deals == []
