from __future__ import annotations

import asyncio
import logging
import os

from bs4 import BeautifulSoup

from lessley_deals.enrichment.llm_client import ExtractedDeal, extract_deals_from_content

logger = logging.getLogger(__name__)


def clean_dom(html: str) -> str:
    """Extract body text, drop <script>/<style>, collapse blank lines."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body
    if body is None:
        return ""
    for tag in body(["script", "style"]):
        tag.extract()
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
            return str(driver.page_source)
        finally:
            driver.quit()

    async def fetch_html(self, url: str) -> str:
        """Fetch rendered HTML via Selenium, off the event loop thread."""
        return await asyncio.to_thread(self._fetch_html_sync, url)

    async def extract(self, chunks: list[str], instructions: str) -> list[ExtractedDeal]:
        deals: list[ExtractedDeal] = []
        for i, chunk in enumerate(chunks, start=1):
            try:
                result = await asyncio.to_thread(
                    extract_deals_from_content, chunk, instructions
                )
            except Exception:
                logger.exception("LLM extract failed on chunk %d/%d", i, len(chunks))
                continue
            deals.extend(result.deals)
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
