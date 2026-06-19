from __future__ import annotations

from unittest.mock import patch

from lessley_deals.enrichment.llm_client import DealDetail, ExtractedDeal, ExtractedDeals
from lessley_deals.scraping.engine.llm_scraper import (
    LlmScrapeEngine,
    clean_dom,
    detect_block,
    split_content,
)


def test_detect_block_flags_captcha_text() -> None:
    reason = detect_block("Please verify you are a human", "<html>...captcha...</html>")
    assert reason is not None
    assert "captcha" in reason.lower() or "verify" in reason.lower()


def test_detect_block_flags_cloudflare_just_a_moment() -> None:
    assert detect_block("Just a moment...", "<title>Just a moment...</title>") is not None


def test_detect_block_flags_empty_page() -> None:
    reason = detect_block("   ", "<html><body></body></html>")
    assert reason is not None
    assert "empty" in reason.lower()


def test_detect_block_passes_normal_content() -> None:
    text = "Nike 20% off\nAdidas buy one get one\n" + "deal " * 50
    assert detect_block(text, f"<html><body>{text}</body></html>") is None


async def test_run_warns_when_blocked(caplog) -> None:  # type: ignore[no-untyped-def]
    import logging

    engine = LlmScrapeEngine()
    with patch.object(engine, "fetch_html", return_value="<html><body>captcha</body></html>"), patch(
        "lessley_deals.scraping.engine.llm_scraper.extract_deals_from_content",
        return_value=ExtractedDeals(deals=[]),
    ):
        with caplog.at_level(logging.WARNING):
            await engine.run("https://x.test", "Extract")
    assert any("block" in r.message.lower() for r in caplog.records)


async def test_run_verbose_logs_each_deal(caplog) -> None:  # type: ignore[no-untyped-def]
    import logging

    engine = LlmScrapeEngine(verbose=True)
    html = "<html><body><p>Nike 20% off and more text to pass block check " + "x " * 40 + "</p></body></html>"
    with patch.object(engine, "fetch_html", return_value=html), patch(
        "lessley_deals.scraping.engine.llm_scraper.extract_deals_from_content",
        return_value=ExtractedDeals(
            deals=[ExtractedDeal(store_name="Nike", deal_description="20% off", price_text="20%")]
        ),
    ):
        with caplog.at_level(logging.INFO):
            await engine.run("https://x.test", "Extract")
    assert any("Nike" in r.message and "20% off" in r.message for r in caplog.records)


def test_clean_dom_strips_scripts_styles_and_blank_lines() -> None:
    html = (
        "<html><head><style>.a{color:red}</style></head>"
        "<body><h1>Deals</h1><script>track()</script>\n\n   \n<p>50% off</p></body></html>"
    )
    out = clean_dom(html)
    assert "Deals" in out
    assert "50% off" in out
    assert "track()" not in out
    assert "color:red" not in out
    assert "\n\n" not in out  # blank lines collapsed


def test_clean_dom_no_body_returns_empty() -> None:
    assert clean_dom("<html></html>") == ""


def test_clean_dom_keep_links_inlines_urls() -> None:
    html = '<html><body><p>Buy <a href="/store/5">Nike</a> now</p></body></html>'
    out = clean_dom(html, keep_links=True)
    assert "Nike (/store/5)" in out


def test_clean_dom_default_drops_link_urls() -> None:
    html = '<html><body><p>Buy <a href="/store/5">Nike</a> now</p></body></html>'
    out = clean_dom(html)
    assert "Nike" in out
    assert "/store/5" not in out


def test_split_content_chunks_by_max_len() -> None:
    text = "x" * 13000
    chunks = split_content(text, max_len=6000)
    assert len(chunks) == 3
    assert len(chunks[0]) == 6000
    assert len(chunks[2]) == 1000
    assert "".join(chunks) == text


def test_split_content_empty_returns_empty_list() -> None:
    assert split_content("") == []


def test_split_content_does_not_cut_lines_mid_row() -> None:
    # Each line is an atomic "store row"; chunking must not split a line across
    # two chunks, or the LLM sees garbled half-rows at chunk boundaries.
    text = "\n".join(f"Store{i} | חנות{i}" for i in range(100))
    chunks = split_content(text, max_len=40)
    assert "".join(chunks) == text  # lossless
    for i in range(100):
        line = f"Store{i} | חנות{i}"
        assert any(line in c for c in chunks), f"line split across chunks: {line}"


def test_split_content_hard_splits_overlong_single_line() -> None:
    # A single line longer than max_len still has to be hard-split.
    chunks = split_content("x" * 13000, max_len=6000)
    assert [len(c) for c in chunks] == [6000, 6000, 1000]


async def test_extract_aggregates_deals_across_chunks() -> None:
    engine = LlmScrapeEngine()
    side = [
        ExtractedDeals(deals=[ExtractedDeal(store_name="A", deal_description="d1")]),
        ExtractedDeals(deals=[ExtractedDeal(store_name="B", deal_description="d2")]),
    ]
    with patch(
        "lessley_deals.scraping.engine.llm_scraper.extract_deals_from_content",
        side_effect=side,
    ):
        deals = await engine.extract(["chunk1", "chunk2"], "Extract")
    assert [d.store_name for d in deals] == ["A", "B"]


async def test_extract_skips_chunk_that_always_fails() -> None:
    engine = LlmScrapeEngine()

    def fake(chunk: str, instructions: str) -> ExtractedDeals:
        if chunk == "bad":
            raise RuntimeError("llm down")
        return ExtractedDeals(deals=[ExtractedDeal(store_name="B", deal_description="d2")])

    with patch(
        "lessley_deals.scraping.engine.llm_scraper.extract_deals_from_content",
        side_effect=fake,
    ):
        # retries=0 so the bad chunk is dropped without consuming extra calls
        deals = await engine.extract(["bad", "good"], "Extract", retries=0)
    assert [d.store_name for d in deals] == ["B"]


async def test_extract_retries_transient_failure() -> None:
    engine = LlmScrapeEngine()
    calls = {"n": 0}

    def flaky(chunk: str, instructions: str) -> ExtractedDeals:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return ExtractedDeals(deals=[ExtractedDeal(store_name="A", deal_description="d")])

    with patch(
        "lessley_deals.scraping.engine.llm_scraper.extract_deals_from_content",
        side_effect=flaky,
    ):
        deals = await engine.extract(["chunk"], "Extract", retries=2)
    assert [d.store_name for d in deals] == ["A"]
    assert calls["n"] == 2  # failed once, succeeded on retry


async def test_run_pipes_fetch_clean_split_extract() -> None:
    engine = LlmScrapeEngine()
    html = "<html><body><p>Nike 20% off</p></body></html>"
    with patch.object(engine, "fetch_html", return_value=html), patch(
        "lessley_deals.scraping.engine.llm_scraper.extract_deals_from_content",
        return_value=ExtractedDeals(
            deals=[ExtractedDeal(store_name="Nike", deal_description="20% off")]
        ),
    ):
        deals = await engine.run("https://x.test", "Extract")
    assert deals[0].store_name == "Nike"


async def test_fetch_html_fast_falls_back_to_selenium_on_error() -> None:
    engine = LlmScrapeEngine()
    with patch.object(engine, "_fetch_fast_sync", side_effect=RuntimeError("boom")), patch.object(
        engine, "fetch_html", return_value="<html><body>selenium content</body></html>"
    ):
        html = await engine.fetch_html_fast("https://x.test")
    assert "selenium content" in html


async def test_fetch_html_fast_falls_back_when_blocked() -> None:
    engine = LlmScrapeEngine()
    with patch.object(
        engine, "_fetch_fast_sync", return_value="<html><body>Access Denied</body></html>"
    ), patch.object(
        engine, "fetch_html", return_value="<html><body>real store content here and more</body></html>"
    ):
        html = await engine.fetch_html_fast("https://x.test")
    assert "real store content" in html


async def test_run_with_details_two_phase_pairs_listing_and_detail() -> None:
    engine = LlmScrapeEngine()
    deal = ExtractedDeal(store_name="Nike", deal_description="3%", detail_url="/store/5")
    with patch.object(engine, "fetch_html", return_value="<html><body>list</body></html>"), patch.object(
        engine, "fetch_html_fast", return_value="<html><body>blurb</body></html>"
    ), patch(
        "lessley_deals.scraping.engine.llm_scraper.extract_deals_from_content",
        return_value=ExtractedDeals(deals=[deal]),
    ), patch(
        "lessley_deals.scraping.engine.llm_scraper.extract_detail",
        return_value=DealDetail(deal_description="store blurb", terms_and_conditions="rules"),
    ):
        pairs = await engine.run_with_details("https://x.test/list", "list", "detail")
    assert len(pairs) == 1
    d, detail = pairs[0]
    assert d.store_name == "Nike"
    assert detail is not None and detail.deal_description == "store blurb"


async def test_run_with_details_respects_sample_limit() -> None:
    engine = LlmScrapeEngine()
    deals = [
        ExtractedDeal(store_name=f"S{i}", deal_description="3%", detail_url=f"/s/{i}")
        for i in range(10)
    ]
    with patch.object(engine, "fetch_html", return_value="<html><body>list</body></html>"), patch.object(
        engine, "fetch_html_fast", return_value="<html><body>b</body></html>"
    ), patch(
        "lessley_deals.scraping.engine.llm_scraper.extract_deals_from_content",
        return_value=ExtractedDeals(deals=deals),
    ), patch(
        "lessley_deals.scraping.engine.llm_scraper.extract_detail",
        return_value=DealDetail(deal_description="b"),
    ):
        pairs = await engine.run_with_details(
            "https://x.test/list", "list", "detail", sample_limit=3
        )
    assert len(pairs) == 3
