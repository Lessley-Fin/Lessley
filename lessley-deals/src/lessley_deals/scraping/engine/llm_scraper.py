from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from lessley_deals.enrichment.llm_client import (
    DealDetail,
    ExtractedDeal,
    extract_deals_from_content,
    extract_detail,
)

logger = logging.getLogger(__name__)

_FAST_FETCH_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def clean_dom(html: str, keep_links: bool = False) -> str:
    """Extract body text, drop <script>/<style>, collapse blank lines.

    When ``keep_links`` is True, each ``<a href>`` is rendered inline as
    ``text (href)`` so the LLM can pair a row with its link (needed for
    detail-page crawling). Default drops links entirely.
    """
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body
    if body is None:
        return ""
    for tag in body(["script", "style"]):
        tag.extract()
    if keep_links:
        for a in body.find_all("a"):
            href = a.get("href")
            text = a.get_text(" ").strip()
            if href and text:
                a.replace_with(f"{text} ({href})")
    text = body.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def split_content(text: str, max_len: int = 6000) -> list[str]:
    """Split text into chunks of at most ``max_len`` chars on line boundaries.

    Each line is kept whole so a logical row (e.g. one store entry) is never cut
    across two chunks — that would feed the LLM garbled half-rows. A single line
    longer than ``max_len`` is hard-split as a fallback.
    """
    if not text:
        return []

    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(line) > max_len:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(line), max_len):
                chunks.append(line[i : i + max_len])
            continue
        if current and len(current) + len(line) > max_len:
            chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks


# Markers that strongly suggest an anti-bot / captcha / block page rather than
# real content. Matched case-insensitively against cleaned text and raw HTML.
_BLOCK_MARKERS: tuple[str, ...] = (
    "captcha",
    "are you a robot",
    "verify you are a human",
    "verify you are human",
    "just a moment",  # Cloudflare interstitial
    "cf-browser-verification",
    "attention required",
    "access denied",
    "请开启 javascript",
    "enable javascript",
    "unusual traffic",
    "אימות",  # Hebrew: verification
    "רובוט",  # Hebrew: robot
    "הגישה נחסמה",  # Hebrew: access blocked
)

_MIN_CONTENT_CHARS = 50


def detect_block(cleaned: str, html: str) -> str | None:
    """Return a human-readable reason if the page looks blocked, else None.

    Heuristics: near-empty cleaned content, or a known anti-bot/captcha marker
    in the cleaned text or raw HTML.
    """
    haystack = f"{cleaned}\n{html}".lower()
    for marker in _BLOCK_MARKERS:
        if marker in haystack:
            return f"block marker found: {marker!r}"
    if len(cleaned.strip()) < _MIN_CONTENT_CHARS:
        return f"page is empty or near-empty ({len(cleaned.strip())} chars)"
    return None


class LlmScrapeEngine:
    """Render a page with Selenium, clean it, chunk it, and LLM-extract deals."""

    def __init__(
        self,
        *,
        remote_url: str | None = None,
        timeout_seconds: float = 30.0,
        max_len: int = 6000,
        verbose: bool | None = None,
        render_wait_seconds: float = 0.0,
        wait_selector: str | None = None,
    ) -> None:
        self._remote_url = (
            remote_url
            if remote_url is not None
            else os.environ.get("LLM_SCRAPER_REMOTE_URL")
        )
        self._timeout_seconds = timeout_seconds
        self._max_len = max_len
        self._verbose = (
            verbose
            if verbose is not None
            else bool(os.environ.get("LLM_SCRAPER_VERBOSE"))
        )
        self._render_wait_seconds = render_wait_seconds
        self._wait_selector = wait_selector

    def _fetch_html_sync(self, url: str) -> str:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        if self._remote_url:
            driver = webdriver.Remote(command_executor=self._remote_url, options=options)
        else:
            driver = webdriver.Chrome(options=options)
        try:
            driver.set_page_load_timeout(self._timeout_seconds)
            driver.get(url)
            self._await_render(driver)
            return str(driver.page_source)
        finally:
            driver.quit()

    def _await_render(self, driver: object) -> None:
        """Give a JS SPA time to hydrate before reading page_source.

        Waits for an optional CSS selector to appear, then an optional fixed
        settle delay. No-op when neither is configured (server-rendered sites).
        """
        import time

        if self._wait_selector:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as ec
            from selenium.webdriver.support.ui import WebDriverWait

            try:
                WebDriverWait(driver, self._timeout_seconds).until(
                    ec.presence_of_element_located((By.CSS_SELECTOR, self._wait_selector))
                )
            except Exception:
                logger.info("wait_selector %r not found before timeout", self._wait_selector)
        if self._render_wait_seconds > 0:
            time.sleep(self._render_wait_seconds)

    async def fetch_html(self, url: str) -> str:
        """Fetch rendered HTML via Selenium, off the event loop thread."""
        return await asyncio.to_thread(self._fetch_html_sync, url)

    async def extract(
        self, chunks: list[str], instructions: str, *, retries: int = 2
    ) -> list[ExtractedDeal]:
        deals: list[ExtractedDeal] = []
        failed = 0
        for i, chunk in enumerate(chunks, start=1):
            result = None
            for attempt in range(retries + 1):
                try:
                    result = await asyncio.to_thread(
                        extract_deals_from_content, chunk, instructions
                    )
                    break
                except Exception:
                    if attempt < retries:
                        logger.info(
                            "LLM extract failed on chunk %d/%d; retrying (%d)",
                            i,
                            len(chunks),
                            attempt + 1,
                        )
                        continue
                    logger.exception(
                        "LLM extract failed on chunk %d/%d after retries", i, len(chunks)
                    )
            if result is None:
                failed += 1
                continue
            deals.extend(result.deals)
        if failed:
            logger.warning(
                "extract: %d/%d chunks failed after retries — some rows were dropped",
                failed,
                len(chunks),
            )
        return deals

    def _fetch_fast_sync(self, url: str) -> str:
        """Plain httpx GET for server-rendered pages (no browser)."""
        import httpx

        resp = httpx.get(
            url,
            headers={"User-Agent": _FAST_FETCH_UA},
            follow_redirects=True,
            timeout=self._timeout_seconds,
        )
        resp.raise_for_status()
        return resp.text

    async def fetch_html_fast(self, url: str) -> str:
        """Fetch via httpx; fall back to Selenium if it errors or looks blocked."""
        try:
            html = await asyncio.to_thread(self._fetch_fast_sync, url)
        except Exception:
            logger.info("Fast fetch failed for %s; falling back to Selenium", url)
            return await self.fetch_html(url)
        if detect_block(clean_dom(html), html):
            logger.info("Fast fetch blocked for %s; falling back to Selenium", url)
            return await self.fetch_html(url)
        return html

    async def _extract_one_detail(
        self, content: str, instructions: str, *, retries: int = 2
    ) -> DealDetail | None:
        for attempt in range(retries + 1):
            try:
                return await asyncio.to_thread(extract_detail, content, instructions)
            except Exception:
                if attempt < retries:
                    logger.info("Detail LLM extract failed; retrying (%d)", attempt + 1)
                    continue
                logger.exception("Detail LLM extract failed after retries")
                return None
        return None

    async def run_with_details(
        self,
        list_url: str,
        list_instructions: str,
        detail_instructions: str,
        *,
        sample_limit: int | None = None,
        concurrency: int = 5,
    ) -> list[tuple[ExtractedDeal, DealDetail | None]]:
        """Two-phase crawl: extract a listing, then enrich each row from its
        detail page.

        Phase 1 renders ``list_url`` with links preserved and LLM-extracts rows
        (each ideally carrying a ``detail_url``). Phase 2 fetches each detail
        page (httpx-fast, Selenium fallback) and LLM-extracts rich fields,
        concurrently. Returns ``(listing_deal, detail_or_None)`` pairs.
        """
        html = await self.fetch_html(list_url)
        cleaned = clean_dom(html, keep_links=True)
        chunks = split_content(cleaned, max_len=self._max_len)
        deals = await self.extract(chunks, list_instructions)
        if sample_limit is not None:
            deals = deals[:sample_limit]
        logger.info("run_with_details: %d listing rows; crawling details", len(deals))

        semaphore = asyncio.Semaphore(concurrency)

        async def enrich(deal: ExtractedDeal) -> tuple[ExtractedDeal, DealDetail | None]:
            if not deal.detail_url:
                return deal, None
            url = urljoin(list_url, deal.detail_url)
            async with semaphore:
                try:
                    dhtml = await self.fetch_html_fast(url)
                except Exception:
                    logger.exception("Detail fetch failed for %s", url)
                    return deal, None
            detail = await self._extract_one_detail(
                clean_dom(dhtml), detail_instructions
            )
            return deal, detail

        return list(await asyncio.gather(*[enrich(d) for d in deals]))

    def _read_file_sync(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    async def fetch_local_file(self, path: str) -> str:
        """Read a locally saved snapshot (HTML page or raw JSON) off the event loop thread."""
        return await asyncio.to_thread(self._read_file_sync, path)

    async def run_from_file(
        self, file_path: str, instructions: str, *, is_json: bool = False
    ) -> list[ExtractedDeal]:
        """Extract deals from a locally saved snapshot instead of a live fetch.

        For periodically-refreshed manual exports (e.g. a logged-in page saved
        by hand, or a raw JSON API response) where no network request — and no
        Selenium/httpx fetch — is involved at all. ``is_json`` pretty-prints the
        parsed JSON before chunking so ``split_content`` gets real line
        boundaries between records instead of one giant minified line.
        """
        raw = await self.fetch_local_file(file_path)
        if is_json:
            try:
                cleaned = json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
            except ValueError:
                logger.warning("run_from_file: %s is not valid JSON; using raw text", file_path)
                cleaned = raw
        else:
            cleaned = clean_dom(raw)

        if not cleaned.strip():
            logger.warning("run_from_file: %s produced no content", file_path)
            return []

        chunks = split_content(cleaned, max_len=self._max_len)
        deals = await self.extract(chunks, instructions)
        logger.info("Extracted %d deals from local file %s", len(deals), file_path)
        return deals

    async def run(self, url: str, instructions: str) -> list[ExtractedDeal]:
        html = await self.fetch_html(url)
        cleaned = clean_dom(html)

        blocked = detect_block(cleaned, html)
        if blocked:
            logger.warning("Possible scrape block on %s: %s", url, blocked)

        if self._verbose:
            logger.info(
                "Cleaned content from %s (%d chars):\n%s",
                url,
                len(cleaned),
                cleaned[:2000],
            )

        chunks = split_content(cleaned, max_len=self._max_len)
        deals = await self.extract(chunks, instructions)

        if self._verbose:
            for d in deals:
                logger.info(
                    "DEAL | %s | %s | %s", d.store_name, d.deal_description, d.price_text
                )
        logger.info("Extracted %d deals from %s", len(deals), url)
        return deals
