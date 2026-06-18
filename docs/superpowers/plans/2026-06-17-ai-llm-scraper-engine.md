# AI LLM Scraper Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an AI-powered scraper engine (Selenium render → bs4 clean → chunk → LLM extract) that plugs into the existing `BaseSourceAdapter` mechanism and emits standard `RawStore`/`RawScrapedRecord`.

**Architecture:** A reusable `LlmScrapeEngine` (no pipeline coupling) does fetch/clean/chunk/extract. A thin generic `LlmScraperAdapter` configured per-site with `(site_id, url, instructions)` wraps the engine and maps results into domain records. Per-site configs live in `data/seed/llm_sources.json`, loaded by the registry. The LLM call reuses the existing `enrichment/llm_client.py` (College/Azure).

**Tech Stack:** Python 3.12, Selenium 4 (headless Chrome, Selenium Manager), BeautifulSoup4, OpenAI SDK structured output (pydantic), asyncio.

## Global Constraints

- Python 3.12+; mypy strict must pass (`mypy src/`); ruff line-length 120.
- `from __future__ import annotations` at top of every new module.
- Frozen domain records (`RawScrapedRecord`, `RawStore`) — never mutate; always build new.
- Generate ids via `from lessley_deals.persistence.id_gen import generate_id` (`generate_id() -> str`).
- Timestamps: `datetime.now(timezone.utc)`.
- LLM determinism: `temperature=0.0, seed=42` (match existing `get_store_category`).
- Adapter must never raise out of `scrape()` — return `([], [])` on failure (Swish pattern).
- Tests that hit a real browser/network use `@pytest.mark.integration`; unit tests mock all I/O.
- Dependency floor: `selenium>=4.20,<5.0`.

---

### Task 1: LLM extraction function in the LLM client

**Files:**
- Modify: `lessley-deals/src/lessley_deals/enrichment/llm_client.py`
- Test: `lessley-deals/tests/unit/enrichment/test_extract_deals.py`

**Interfaces:**
- Consumes: existing `_get_client() -> tuple[OpenAI, str]` in the same module.
- Produces:
  - `class ExtractedDeal(BaseModel)` with `store_name: str`, `deal_description: str`, `price_text: str = ""`, `url: str | None = None`.
  - `class ExtractedDeals(BaseModel)` with `deals: list[ExtractedDeal]`.
  - `extract_deals_from_content(content: str, instructions: str) -> ExtractedDeals`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/enrichment/test_extract_deals.py
from __future__ import annotations

from unittest.mock import MagicMock, patch

from lessley_deals.enrichment.llm_client import (
    ExtractedDeal,
    ExtractedDeals,
    extract_deals_from_content,
)


def test_extract_deals_returns_parsed_model() -> None:
    fake_parsed = ExtractedDeals(
        deals=[ExtractedDeal(store_name="Nike", deal_description="20% off", price_text="20%")]
    )
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(parsed=fake_parsed))]
    fake_client = MagicMock()
    fake_client.beta.chat.completions.parse.return_value = fake_completion

    with patch(
        "lessley_deals.enrichment.llm_client._get_client",
        return_value=(fake_client, "test-model"),
    ):
        result = extract_deals_from_content("Nike 20% off", "Extract deals")

    assert isinstance(result, ExtractedDeals)
    assert result.deals[0].store_name == "Nike"
    # Verify deterministic call params
    _, kwargs = fake_client.beta.chat.completions.parse.call_args
    assert kwargs["temperature"] == 0.0
    assert kwargs["seed"] == 42
    assert kwargs["response_format"] is ExtractedDeals
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lessley-deals && pytest tests/unit/enrichment/test_extract_deals.py -v`
Expected: FAIL with `ImportError` / `cannot import name 'extract_deals_from_content'`.

- [ ] **Step 3: Write minimal implementation**

Append to `llm_client.py` (after `get_store_category`):

```python
class ExtractedDeal(BaseModel):
    store_name: str
    deal_description: str
    price_text: str = ""
    url: str | None = None


class ExtractedDeals(BaseModel):
    deals: List[ExtractedDeal]


def extract_deals_from_content(content: str, instructions: str) -> ExtractedDeals:
    """Extract retail deals from one cleaned DOM chunk per the user's instructions."""
    client, model = _get_client()
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract retail deals/promotions from messy web page text. "
                    "Return ONLY deals that are clearly supported by the content; if none, "
                    "return an empty list. Each deal needs a store_name and a deal_description; "
                    "include price_text (price, percent, or '') and url when present. "
                    "Follow the user's extraction instructions."
                ),
            },
            {
                "role": "user",
                "content": f"Instructions: {instructions}\n\nPage content:\n{content}",
            },
        ],
        response_format=ExtractedDeals,
        temperature=0.0,
        seed=42,
    )
    parsed = completion.choices[0].message.parsed
    return parsed if parsed is not None else ExtractedDeals(deals=[])
```

(`List` is already imported from `typing` in this file.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lessley-deals && pytest tests/unit/enrichment/test_extract_deals.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lessley-deals/src/lessley_deals/enrichment/llm_client.py lessley-deals/tests/unit/enrichment/test_extract_deals.py
git commit -m "feat(enrichment): add extract_deals_from_content LLM extraction"
```

---

### Task 2: Engine pure helpers — clean_dom + split_content

**Files:**
- Create: `lessley-deals/src/lessley_deals/scraping/engine/__init__.py` (empty)
- Create: `lessley-deals/src/lessley_deals/scraping/engine/llm_scraper.py`
- Test: `lessley-deals/tests/unit/scraping/test_llm_engine.py`

**Interfaces:**
- Produces (module-level functions):
  - `clean_dom(html: str) -> str`
  - `split_content(text: str, max_len: int = 6000) -> list[str]`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/scraping/test_llm_engine.py
from __future__ import annotations

from lessley_deals.scraping.engine.llm_scraper import clean_dom, split_content


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


def test_split_content_chunks_by_max_len() -> None:
    text = "x" * 13000
    chunks = split_content(text, max_len=6000)
    assert len(chunks) == 3
    assert len(chunks[0]) == 6000
    assert len(chunks[2]) == 1000
    assert "".join(chunks) == text


def test_split_content_empty_returns_empty_list() -> None:
    assert split_content("") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lessley-deals && pytest tests/unit/scraping/test_llm_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: lessley_deals.scraping.engine.llm_scraper`.

- [ ] **Step 3: Write minimal implementation**

Create `engine/__init__.py` empty. Create `engine/llm_scraper.py`:

```python
from __future__ import annotations

from bs4 import BeautifulSoup


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
    """Split text into fixed-width chunks of at most max_len characters."""
    return [text[i : i + max_len] for i in range(0, len(text), max_len)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lessley-deals && pytest tests/unit/scraping/test_llm_engine.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add lessley-deals/src/lessley_deals/scraping/engine/
git add lessley-deals/tests/unit/scraping/test_llm_engine.py
git commit -m "feat(scraping): add LLM engine DOM clean + chunk helpers"
```

---

### Task 3: Engine class — fetch_html (Selenium) + extract + run

**Files:**
- Modify: `lessley-deals/src/lessley_deals/scraping/engine/llm_scraper.py`
- Modify: `lessley-deals/tests/unit/scraping/test_llm_engine.py`
- Modify: `lessley-deals/pyproject.toml` (add `selenium>=4.20,<5.0` to dependencies)

**Interfaces:**
- Consumes: `clean_dom`, `split_content` (Task 2); `extract_deals_from_content`, `ExtractedDeal` (Task 1).
- Produces:
  - `class LlmScrapeEngine` with constructor `__init__(self, *, remote_url: str | None = None, timeout_seconds: float = 30.0, max_len: int = 6000)`.
  - `async fetch_html(self, url: str) -> str`
  - `async extract(self, chunks: list[str], instructions: str) -> list[ExtractedDeal]`
  - `async run(self, url: str, instructions: str) -> list[ExtractedDeal]`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/scraping/test_llm_engine.py`:

```python
import pytest
from unittest.mock import patch

from lessley_deals.enrichment.llm_client import ExtractedDeal, ExtractedDeals
from lessley_deals.scraping.engine.llm_scraper import LlmScrapeEngine


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_extract_skips_failing_chunk() -> None:
    engine = LlmScrapeEngine()
    side = [
        RuntimeError("llm down"),
        ExtractedDeals(deals=[ExtractedDeal(store_name="B", deal_description="d2")]),
    ]
    with patch(
        "lessley_deals.scraping.engine.llm_scraper.extract_deals_from_content",
        side_effect=side,
    ):
        deals = await engine.extract(["bad", "good"], "Extract")
    assert [d.store_name for d in deals] == ["B"]


@pytest.mark.asyncio
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lessley-deals && pytest tests/unit/scraping/test_llm_engine.py -k "extract or run" -v`
Expected: FAIL with `ImportError: cannot import name 'LlmScrapeEngine'`.

- [ ] **Step 3: Write minimal implementation**

Add to the top imports of `engine/llm_scraper.py`:

```python
import asyncio
import logging
import os

from lessley_deals.enrichment.llm_client import ExtractedDeal, extract_deals_from_content

logger = logging.getLogger(__name__)
```

Append the class:

```python
class LlmScrapeEngine:
    """Render a page with Selenium, clean it, chunk it, and LLM-extract deals."""

    def __init__(
        self,
        *,
        remote_url: str | None = None,
        timeout_seconds: float = 30.0,
        max_len: int = 6000,
    ) -> None:
        self._remote_url = (
            remote_url
            if remote_url is not None
            else os.environ.get("LLM_SCRAPER_REMOTE_URL")
        )
        self._timeout_seconds = timeout_seconds
        self._max_len = max_len

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
            return driver.page_source
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
        chunks = split_content(cleaned, max_len=self._max_len)
        return await self.extract(chunks, instructions)
```

Add `selenium>=4.20,<5.0` to the `[project] dependencies` list in `lessley-deals/pyproject.toml`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lessley-deals && pytest tests/unit/scraping/test_llm_engine.py -v && mypy src/lessley_deals/scraping/engine/`
Expected: PASS (all tests); mypy clean.

- [ ] **Step 5: Commit**

```bash
git add lessley-deals/src/lessley_deals/scraping/engine/llm_scraper.py
git add lessley-deals/tests/unit/scraping/test_llm_engine.py lessley-deals/pyproject.toml
git commit -m "feat(scraping): add LlmScrapeEngine Selenium fetch + run pipeline"
```

---

### Task 4: LlmScraperAdapter — map engine output to domain records

**Files:**
- Create: `lessley-deals/src/lessley_deals/scraping/sources/llm_scraper.py`
- Test: `lessley-deals/tests/unit/scraping/test_llm_scraper_adapter.py`

**Interfaces:**
- Consumes: `LlmScrapeEngine` (Task 3); `ExtractedDeal` (Task 1); `BaseSourceAdapter`, `SourceConfig` (`scraping/base.py`); `RawStore`, `RawScrapedRecord` (`domain/models.py`); `generate_id` (`persistence/id_gen.py`).
- Produces:
  - `class LlmScraperAdapter(BaseSourceAdapter)` constructor:
    `__init__(self, config: SourceConfig, *, site_id: str, url: str, instructions: str, engine: LlmScrapeEngine | None = None)`.
  - `source_id` property returns `site_id`.
  - `async scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/scraping/test_llm_scraper_adapter.py
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from lessley_deals.enrichment.llm_client import ExtractedDeal
from lessley_deals.scraping.base import SourceConfig
from lessley_deals.scraping.sources.llm_scraper import LlmScraperAdapter


def _adapter(engine) -> LlmScraperAdapter:
    return LlmScraperAdapter(
        SourceConfig(base_url="https://x.test"),
        site_id="llm:test",
        url="https://x.test/deals",
        instructions="Extract deals",
        engine=engine,
    )


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_scrape_returns_empty_on_engine_failure() -> None:
    engine = AsyncMock()
    engine.run.side_effect = RuntimeError("browser crashed")
    stores, deals = await _adapter(engine).scrape()
    assert stores == []
    assert deals == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lessley-deals && pytest tests/unit/scraping/test_llm_scraper_adapter.py -v`
Expected: FAIL with `ModuleNotFoundError: ...sources.llm_scraper`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/lessley_deals/scraping/sources/llm_scraper.py
from __future__ import annotations

import logging
from datetime import datetime, timezone

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig
from lessley_deals.scraping.engine.llm_scraper import LlmScrapeEngine

logger = logging.getLogger(__name__)


class LlmScraperAdapter(BaseSourceAdapter):
    """Generic AI scraper: render a configured URL and LLM-extract its deals."""

    def __init__(
        self,
        config: SourceConfig,
        *,
        site_id: str,
        url: str,
        instructions: str,
        engine: LlmScrapeEngine | None = None,
    ) -> None:
        super().__init__(config)
        self._site_id = site_id
        self._url = url
        self._instructions = instructions
        self._engine = engine or LlmScrapeEngine(
            timeout_seconds=config.timeout_seconds
        )

    @property
    def source_id(self) -> str:
        return self._site_id

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        try:
            extracted = await self._engine.run(self._url, self._instructions)
        except Exception:
            logger.exception("LLM scrape failed for %s (%s)", self._site_id, self._url)
            return [], []

        now = datetime.now(timezone.utc)
        seen_stores: set[str] = set()
        stores: list[RawStore] = []
        deals: list[RawScrapedRecord] = []

        for item in extracted:
            name = item.store_name.strip()
            if not name:
                continue
            if name not in seen_stores:
                seen_stores.add(name)
                stores.append(
                    RawStore(
                        id=generate_id(),
                        source_id=self._site_id,
                        name=name,
                        scraped_at=now,
                        url=item.url,
                        raw_payload={"source": "llm_scraper", "url": self._url},
                    )
                )
            deals.append(
                RawScrapedRecord(
                    id=generate_id(),
                    source_id=self._site_id,
                    store_name=name,
                    deal_description=item.deal_description.strip(),
                    price_text=item.price_text.strip(),
                    scraped_at=now,
                    url=item.url,
                    raw_payload=item.model_dump(),
                )
            )

        logger.info(
            "LLM adapter %s emitted %d stores, %d deals",
            self._site_id,
            len(stores),
            len(deals),
        )
        return stores, deals
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lessley-deals && pytest tests/unit/scraping/test_llm_scraper_adapter.py -v && mypy src/lessley_deals/scraping/sources/llm_scraper.py`
Expected: PASS (2 tests); mypy clean.

- [ ] **Step 5: Commit**

```bash
git add lessley-deals/src/lessley_deals/scraping/sources/llm_scraper.py
git add lessley-deals/tests/unit/scraping/test_llm_scraper_adapter.py
git commit -m "feat(scraping): add LlmScraperAdapter mapping engine output to records"
```

---

### Task 5: Register configured LLM sites from data/seed/llm_sources.json

**Files:**
- Modify: `lessley-deals/src/lessley_deals/scraping/registry.py`
- Create: `lessley-deals/data/seed/llm_sources.json`
- Test: `lessley-deals/tests/unit/scraping/test_registry_llm_sources.py`

**Interfaces:**
- Consumes: `LlmScraperAdapter` (Task 4); `SourceRegistry`, `register` (`registry.py`).
- Produces:
  - module function `load_llm_site_configs(path: Path | None = None) -> list[dict[str, str]]` in `registry.py`.
  - `SourceRegistry.register_llm_sites(self, path: Path | None = None) -> None`, also called at the end of `register_defaults()`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/scraping/test_registry_llm_sources.py
from __future__ import annotations

import json
from pathlib import Path

from lessley_deals.scraping.registry import SourceRegistry


def test_register_llm_sites_from_file(tmp_path: Path) -> None:
    cfg = tmp_path / "llm_sources.json"
    cfg.write_text(
        json.dumps(
            [
                {
                    "site_id": "llm:demo",
                    "url": "https://demo.test/deals",
                    "instructions": "Extract every product and price.",
                }
            ]
        ),
        encoding="utf-8",
    )
    registry = SourceRegistry()
    registry.register_llm_sites(cfg)
    assert "llm:demo" in registry.list_all()


def test_register_llm_sites_missing_file_is_noop(tmp_path: Path) -> None:
    registry = SourceRegistry()
    registry.register_llm_sites(tmp_path / "nope.json")
    assert registry.list_all() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lessley-deals && pytest tests/unit/scraping/test_registry_llm_sources.py -v`
Expected: FAIL with `AttributeError: 'SourceRegistry' object has no attribute 'register_llm_sites'`.

- [ ] **Step 3: Write minimal implementation**

Add imports at top of `registry.py`:

```python
import json
from pathlib import Path

from lessley_deals.domain.models import RawScrapedRecord  # noqa: F401  (none needed; see below)
```

(Remove that last import if unused — only `json`/`Path` are required.)

Add module function and methods:

```python
def _default_llm_sources_path() -> Path:
    # registry.py is at src/lessley_deals/scraping/registry.py
    return Path(__file__).resolve().parents[3] / "data" / "seed" / "llm_sources.json"


def load_llm_site_configs(path: Path | None = None) -> list[dict[str, str]]:
    """Load per-site LLM scraper configs. Returns [] if the file is absent."""
    cfg_path = path or _default_llm_sources_path()
    if not cfg_path.exists():
        return []
    with cfg_path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        logger.error("llm_sources.json must be a list, got %s", type(data).__name__)
        return []
    return [c for c in data if {"site_id", "url", "instructions"} <= c.keys()]
```

Add methods inside `SourceRegistry`:

```python
    def register_llm_sites(self, path: Path | None = None) -> None:
        """Register an LlmScraperAdapter per entry in llm_sources.json."""
        from lessley_deals.scraping.sources.llm_scraper import LlmScraperAdapter

        for cfg in load_llm_site_configs(path):
            try:
                instance = LlmScraperAdapter(
                    SourceConfig(base_url=cfg["url"]),
                    site_id=cfg["site_id"],
                    url=cfg["url"],
                    instructions=cfg["instructions"],
                )
                self._adapters[instance.source_id] = instance
                logger.info("Registered LLM source adapter: %s", instance.source_id)
            except ValueError:
                pass
```

At the end of `register_defaults()`, after the loop, add:

```python
        self.register_llm_sites()
```

- [ ] **Step 4: Create the seed file**

Create `lessley-deals/data/seed/llm_sources.json` with an empty list (no sites enabled by default):

```json
[]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd lessley-deals && pytest tests/unit/scraping/test_registry_llm_sources.py -v && mypy src/lessley_deals/scraping/registry.py`
Expected: PASS (2 tests); mypy clean.

- [ ] **Step 6: Commit**

```bash
git add lessley-deals/src/lessley_deals/scraping/registry.py
git add lessley-deals/data/seed/llm_sources.json
git add lessley-deals/tests/unit/scraping/test_registry_llm_sources.py
git commit -m "feat(scraping): register LLM scraper sites from seed config"
```

---

### Task 6: Docs + integration smoke test

**Files:**
- Modify: `lessley-deals/CLAUDE.md` (env var table + "Adding a new scraper" note)
- Test: `lessley-deals/tests/integration/test_llm_engine_live.py`

**Interfaces:**
- Consumes: `LlmScrapeEngine` (Task 3).

- [ ] **Step 1: Write the integration test (marked, skipped in fast suite)**

```python
# tests/integration/test_llm_engine_live.py
from __future__ import annotations

import pytest

from lessley_deals.scraping.engine.llm_scraper import LlmScrapeEngine, clean_dom

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_fetch_html_returns_body_text() -> None:
    engine = LlmScrapeEngine()
    html = await engine.fetch_html("https://example.com")
    cleaned = clean_dom(html)
    assert "Example Domain" in cleaned
```

- [ ] **Step 2: Verify it is skipped in the fast suite**

Run: `cd lessley-deals && pytest tests/integration/test_llm_engine_live.py -m "not integration" -v`
Expected: collected 0 / deselected 1 (no browser launched).

- [ ] **Step 3: Update CLAUDE.md**

In the Environment Variables table add a row:

```
| `LLM_SCRAPER_REMOTE_URL` | — | Optional remote Selenium/CDP endpoint (e.g. Bright Data scraping browser) for the AI scraper engine; local Chrome if unset |
```

Under "Adding a new scraper", append a short note:

```
### Adding an AI-scraped site (no code)
Add an entry to `data/seed/llm_sources.json` with `site_id`, `url`, and
`instructions`, then run `python -m deals scrape --source <site_id>`. The
generic `LlmScraperAdapter` renders the page with Selenium, cleans it, and
uses the LLM client to extract deals.
```

- [ ] **Step 4: Commit**

```bash
git add lessley-deals/tests/integration/test_llm_engine_live.py lessley-deals/CLAUDE.md
git commit -m "docs: document AI scraper engine + add live engine smoke test"
```

---

### Task 7: Full-suite verification

- [ ] **Step 1: Run the fast test suite**

Run: `cd lessley-deals && pytest -m "not integration" -q`
Expected: PASS (all existing + new unit tests).

- [ ] **Step 2: Type-check and lint**

Run: `cd lessley-deals && mypy src/ && ruff check src/ tests/`
Expected: no errors.

- [ ] **Step 3: Commit any lint fixes**

```bash
git add -A
git commit -m "chore: lint/type fixes for AI scraper engine" || echo "nothing to commit"
```

---

## Self-Review

**Spec coverage:**
- Reusable engine module → Tasks 2+3. ✓
- Thin `LlmScraperAdapter` → Task 4. ✓
- Selenium render via `asyncio.to_thread` → Task 3 (`fetch_html`/`_fetch_html_sync`). ✓
- bs4 clean (body, strip script/style, collapse blanks) → Task 2 (`clean_dom`). ✓
- Chunking → Task 2 (`split_content`). ✓
- Reuse LLM client, structured output, temp 0 seed 42 → Task 1. ✓
- Per-chunk error skip → Task 3 (`extract`). ✓
- Adapter graceful skip `([], [])` → Task 4. ✓
- RawStore dedup per store_name → Task 4. ✓
- `data/seed/llm_sources.json` config + registry load → Task 5. ✓
- Optional remote-webdriver hook (`LLM_SCRAPER_REMOTE_URL`) → Task 3: ctor defaults `remote_url` from env, so registry (which passes no `remote_url`) picks it up automatically. Documented Task 6. ✓
- selenium dep → Task 3. ✓
- Tests (unit + integration-marked) → Tasks 1–6. ✓

**Placeholder scan:** none — all steps contain concrete code/commands.

**Type consistency:** `LlmScrapeEngine.run` / `fetch_html` / `extract` signatures match across Tasks 3–4; `ExtractedDeal`/`ExtractedDeals` consistent Tasks 1–4; `register_llm_sites` consistent Task 5.
