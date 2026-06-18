# AI LLM Scraper Engine — Design

**Date:** 2026-06-17
**Status:** Awaiting user approval
**Source idea:** [Tech With Tim — "AI Web Scraper" tutorial](https://www.youtube.com/watch?v=Oo8-nEuDBkk)

## Goal

Add an AI-powered scraper engine to `lessley-deals` that can extract deals from
*any* website given a URL + a natural-language extraction prompt, instead of
hand-coding a bespoke adapter per site. The engine plugs into the existing
`BaseSourceAdapter` mechanism so its output flows through the unchanged
Normalize → Match → Persist pipeline.

The video's pipeline is: **Selenium render → BeautifulSoup clean → chunk → LLM
extract (prompt + DOM) → structured result**, with an optional Bright-Data
remote browser for captcha/proxy. This design ports that pipeline onto the
project's existing async architecture and LLM backend.

## Decisions (locked)

| Question | Decision |
|----------|----------|
| Integration role | **Both** — reusable engine module + thin `LlmScraperAdapter` |
| Render layer | **Selenium** (match the video), run via `asyncio.to_thread` so it does not block the async orchestrator |
| LLM backend | **Reuse existing** `enrichment/llm_client.py` (College gpt-oss-120b / Azure, selected by `LLM_PROVIDER`) |
| Per-site config | **`data/seed/llm_sources.json`** — add sites without code edits, matches existing seed-data pattern |
| Anti-bot | Optional remote-webdriver hook (`LLM_SCRAPER_REMOTE_URL`), **off by default** |

## Architecture

```
LlmScraperAdapter.scrape()            (scraping/sources/llm_scraper.py)
   └─> LlmScrapeEngine.run(url, instructions)   (scraping/engine/llm_scraper.py)
          ├─ fetch_html(url)      Selenium (sync) via asyncio.to_thread
          ├─ clean_dom(html)      bs4: body, strip script/style, collapse blanks
          ├─ split_content(text)  chunk to max_len
          └─ extract(chunks, …)   -> extract_deals_from_content()  (enrichment/llm_client.py)
   └─> map ExtractedDeal -> RawScrapedRecord (+ dedup RawStore per store_name)
   └─> return (list[RawStore], list[RawScrapedRecord])
```

Boundaries: the engine knows nothing about the deals pipeline (returns plain
`ExtractedDeal` objects); the adapter owns the mapping into domain records; the
LLM client owns the model call. Each unit is independently testable.

## Components

### 1. `scraping/engine/llm_scraper.py` — `LlmScrapeEngine` (new)

Reusable, no pipeline coupling.

- `async fetch_html(url: str) -> str` — headless Chrome via Selenium 4 (built-in
  Selenium Manager resolves the driver — no manual chromedriver download). Sync
  Selenium calls wrapped in `asyncio.to_thread`. If `LLM_SCRAPER_REMOTE_URL` is
  set, connect a `webdriver.Remote` to that CDP/Grid endpoint
  (Bright-Data-style) instead of local Chrome.
- `clean_dom(html: str) -> str` — BeautifulSoup: take `<body>`, `.extract()` all
  `<script>`/`<style>`, `get_text("\n")`, drop blank lines. (Mirrors video.)
- `split_content(text: str, max_len: int = 6000) -> list[str]` — fixed-width
  chunks.
- `async extract(chunks: list[str], instructions: str) -> list[ExtractedDeal]` —
  call `extract_deals_from_content` per chunk, concatenate `.deals`.
- `async run(url: str, instructions: str) -> list[ExtractedDeal]` — orchestrate
  fetch → clean → split → extract.

Failure handling: `fetch_html` errors propagate to the adapter, which converts
them to an empty result (see below). Per-chunk LLM errors are logged and that
chunk is skipped, so one bad chunk never loses the whole page.

### 2. `enrichment/llm_client.py` — `extract_deals_from_content` (changed)

Add alongside `get_store_category`, reusing `_get_client()`:

```python
class ExtractedDeal(BaseModel):
    store_name: str
    deal_description: str
    price_text: str = ""
    url: str | None = None

class ExtractedDeals(BaseModel):
    deals: list[ExtractedDeal]

def extract_deals_from_content(content: str, instructions: str) -> ExtractedDeals:
    """Extract deals from a cleaned DOM chunk per the user's instructions."""
    # client.beta.chat.completions.parse(..., response_format=ExtractedDeals,
    #                                     temperature=0.0, seed=42)
```

System prompt: "You extract retail deals/promotions from messy page text.
Return only deals supported by the content; empty list if none. Follow the
user's extraction instructions." Determinism (`temperature=0.0, seed=42`)
matches existing usage.

### 3. `scraping/sources/llm_scraper.py` — `LlmScraperAdapter` (new)

```python
class LlmScraperAdapter(BaseSourceAdapter):
    def __init__(self, config, *, site_id, url, instructions): ...

    @property
    def source_id(self) -> str:
        return self._site_id          # e.g. "llm:truevalue"

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        try:
            deals = await self._engine.run(self._url, self._instructions)
        except Exception:
            logger.exception("LLM scrape failed for %s", self._site_id)
            return [], []             # graceful skip (Swish pattern)
        # map each ExtractedDeal -> RawScrapedRecord; dedup one RawStore per
        # store_name (Behatsdaa pattern); stamp source_id, scraped_at, raw_payload
```

`raw_payload` keeps the raw `ExtractedDeal` dict for auditability/replay (project
invariant: raw data preserved verbatim).

### 4. `scraping/registry.py` (changed)

`register_defaults()` reads `data/seed/llm_sources.json`:

```json
[
  { "site_id": "llm:example", "url": "https://example.com/deals",
    "instructions": "Extract every product name, its price, and any discount." }
]
```

For each entry, register an `LlmScraperAdapter` configured with that
`(site_id, url, instructions)`. Missing/empty file → register none (no error).

### 5. `pyproject.toml` (changed)

Add `selenium>=4.20,<5.0`. The Dockerfile `browser` stage already provides
Chromium; Selenium Manager handles the driver. Document
`LLM_SCRAPER_REMOTE_URL` in CLAUDE.md's env table.

## Data flow into existing pipeline

`RawScrapedRecord` fields populated: `source_id` (site_id), `store_name`,
`deal_description`, `price_text`, `scraped_at`, `raw_payload`, `url`. These are
exactly what NormalizeStage consumes, so no downstream change is required.

## Error handling summary

| Failure | Behavior |
|---------|----------|
| Page fetch (Selenium) fails | adapter logs, returns `([], [])`; orchestrator continues other sources |
| One LLM chunk fails/invalid | log, skip chunk, keep other chunks' deals |
| LLM returns no deals | empty result, no records (valid outcome) |
| `llm_sources.json` missing | register no LLM adapters |

## Testing

**Unit (fast, `-m "not integration"`):**
- `clean_dom` removes `<script>`/`<style>`, keeps body text.
- `split_content` produces correct chunk count/boundaries at `max_len`.
- `LlmScraperAdapter.scrape` maps `ExtractedDeal`→`RawScrapedRecord` and dedups
  `RawStore` (engine mocked).
- adapter returns `([], [])` when engine raises.
- `extract` aggregates `.deals` across chunks (LLM client mocked).

**Integration (`-m integration`, skipped in fast suite):**
- `fetch_html` against a real simple page returns non-empty HTML.

LLM calls are always mocked in unit tests (no network).

## Out of scope (YAGNI)

- Streamlit interactive UI (chose adapter+engine, not a standalone tool).
- Proxy rotation / captcha solving beyond the optional remote-webdriver hook.
- Async-native Selenium rewrite (thread-offload is sufficient).
- Pagination / multi-page crawl per site (single URL per config entry for now).

## Wiring a new AI-scraped site (end state)

1. Add an entry to `data/seed/llm_sources.json` (`site_id`, `url`,
   `instructions`).
2. `python -m deals scrape --source llm:<site_id>` (or `--all`).

No new Python code per site.
