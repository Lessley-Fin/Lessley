from __future__ import annotations

import pytest

from lessley_deals.scraping.engine.llm_scraper import LlmScrapeEngine, clean_dom

pytestmark = pytest.mark.integration


async def test_fetch_html_returns_body_text() -> None:
    engine = LlmScrapeEngine()
    html = await engine.fetch_html("https://example.com")
    cleaned = clean_dom(html)
    assert "Example Domain" in cleaned
