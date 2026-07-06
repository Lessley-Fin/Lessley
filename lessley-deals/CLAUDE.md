# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**lessley-deals** is a Python 3.12+ web scraping and store resolution system for Israeli retail deals. It scrapes deal data from Israeli retail sources (HOT, Mastercard, Behatsdaa, Isracard TopCash), normalizes Hebrew/English text (stripping niqqud, final-form letters, legal suffixes), and resolves inconsistent store name variants to canonical store identities through a multi-stage fuzzy matching pipeline.

## Commands

### Setup
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Running the pipeline
```bash
python -m deals scrape --all                         # Scrape all sources
python -m deals scrape --source hot                  # Scrape one source
python -m deals process                              # Normalize + match raw data
python -m deals review                               # Interactive TUI for uncertain matches
python -m deals review --pending                     # Show review queue summary
python -m deals discover-stores                      # Analyze raw data for new stores
python -m deals optimize <store_id> <cart_total>      # Cheapest legal deal stack (needs `pip install -e ../deal-optimizer`)
```

### Tests
```bash
pytest                                               # All tests
pytest -m "not integration"                          # Skip real I/O tests (fast)
pytest tests/unit/matching/                          # Single module
pytest --cov=lessley_deals --cov-report=term-missing # With coverage
```

### Type checking & lint
```bash
mypy src/                   # Strict type checking (Python 3.12)
ruff check src/ tests/      # Lint (line-length: 120)
ruff format src/ tests/     # Format
```

## Architecture

The system is a four-stage pipeline: **Scrape → Normalize → Match → Persist**.

### Data Flow
```
Sources (HTTP/Browser)
    → ScrapeStage       → RawScrapedRecord, RawStore (verbatim, frozen)
    → NormalizeStage    → NormalizedRecord with NameForms {normalized, compact, tokens}
    → MatchStage        → MatchVerdict (AUTO_MATCH | REVIEW | NO_MATCH)
    → PersistStage/ReviewQueue → JSON files or MongoDB
```

### Key Subsystems

**`src/lessley_deals/scraping/`** — Async web scrapers. Each source extends `BaseSourceAdapter` and registers in `registry.py`. Sources use `httpx` (most), `curl-cffi` (JS-bypass), or Playwright (full browser). The `orchestrator.py` fans out to all registered adapters.

**`src/lessley_deals/normalization/`** — 6-step pipeline: text cleanup → Hebrew normalization (niqqud strip, final forms, presentation forms) → store name extraction → price parsing → deal text clean → date parsing. Outputs immutable `NormalizedRecord`.

**`src/lessley_deals/matching/`** — `MatchPipeline` (in `pipeline.py`) runs 6 stages from `matching/stages/`, short-circuiting on the first auto-match (except token-only stages, which never auto-match):
1. `stages/exact_alias.py` — O(1) compact-form lookup against `AliasIndex` (conf 1.0)
2. `stages/domain.py` — URL domain → store_id (conf 0.95)
3. `stages/compact.py` — Jaro-Winkler on compact forms (conf ≤ 0.95)
4. `stages/containment.py` — All canonical tokens ⊆ input tokens (conf ≥ 0.92)
5. `stages/normalized.py` — Jaro-Winkler + Jaccard + containment blend (conf ≤ 1.0)
6. `stages/token.py` — Token Jaccard only, capped at 0.70 (never auto-match)

Thresholds from `MatchConfig`: auto-accept ≥ 0.90, send to review ≥ 0.50, discard below 0.50. Support for `low_information.py` filters short/ambiguous tokens before scoring.

**`src/lessley_deals/persistence/`** — Repository pattern with `typing.Protocol` interfaces. JSON and MongoDB implementations are interchangeable. JSON files use atomic writes (`os.replace()`). Seed data lives in `data/seed/`.

**`src/lessley_deals/review/`** — Interactive TUI for human review of uncertain matches. `Learner` feeds approved matches back as aliases, so they auto-match on the next run.

**`src/lessley_deals/pipeline/`** — `PipelineOrchestrator` wires `scrape_stage.py`, `normalize_stage.py`, `match_stage.py`, `persist_stage.py` via a shared `context.py`. Each stage is independently testable.

**Group gift cards** — HOT deals are classified as either store-specific or group-wide gift cards (e.g. "קבוצת גולף"). Group deals embed `group_member_stores` on the record so query-time fan-out can surface them for any member.

The Swish (נפשונית) catalogue is auto-synced into `hot_store_groups.json` by `sync_swish_groups()` (`scraping/helpers/swish_group_sync.py`). Swish entries are tagged `managed_by: "swish_scraper"`, store members as structured `{name, store_id, confidence}` dicts (resolved against the canonical stores via the matching pipeline), and push unresolved members to the review queue with `verdict.explanation.details["kind"] == "group_member_match"`. CLI: `python -m deals sync-swish-groups`. See `docs/group-deals.md`.

**`src/lessley_deals/domain/`** — Core dataclasses and enums. Raw/normalized records and verdicts are **frozen**; entities (stores, aliases) are **mutable**. Never mutate frozen records.

### Storage
- Default: JSON files in `data/` (configurable via `DEALS_DATA_DIR`)
- Optional: MongoDB (set `DEALS_STORAGE=mongo`, `MONGO_URI`, `MONGO_DB_NAME`)
- Raw scraped data is always preserved verbatim for auditability and replay

### Adding a new scraper
1. Create `src/lessley_deals/scraping/sources/my_source.py` extending `BaseSourceAdapter`
2. Implement `source_id` property and `async def scrape() -> list[RawScrapedRecord]`
3. Register in `src/lessley_deals/scraping/registry.py`
4. Add tests in `tests/unit/scraping/`

Existing sources: `hot.py`, `mastercard.py`, `behatsdaa.py`, `isracard_topcash.py`.

### Adding an AI-scraped site (no code)
For sites without a clean API, use the generic AI scraper engine instead of a
hand-coded adapter. Add an entry to `data/seed/llm_sources.json` with `site_id`,
`url`, and `instructions`, then run `python -m deals scrape --source <site_id>`.
The `LlmScraperAdapter` (`scraping/sources/llm_scraper.py`) renders the page with
Selenium (`scraping/engine/llm_scraper.py`), cleans the DOM, chunks it, and uses
the LLM client (`enrichment/llm_client.py::extract_deals_from_content`) to extract
deals into the normal `RawStore`/`RawScrapedRecord` pipeline.

## Key Design Decisions

- **Conservative matching**: uncertain cases go to human review; false negatives preferred over false positives (silent mismatches)
- **Frozen dataclasses** for point-in-time records (raw, normalized, verdicts); mutable only for accumulating entities
- **Protocol-based boundaries**: subsystems depend on interfaces, not concrete implementations — scrapers never match, matchers never scrape
- **Alias learner feedback loop**: human review decisions immediately strengthen future matching via the alias index

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DEALS_DATA_DIR` | `./data` | Data directory |
| `DEALS_STORAGE` | `json` | `json` or `mongo` |
| `DEALS_AUTO_MATCH_THRESHOLD` | `0.90` | Auto-accept threshold |
| `DEALS_REVIEW_THRESHOLD` | `0.50` | Send-to-review threshold |
| `DEALS_LOG_LEVEL` | `INFO` | Log verbosity |
| `LLM_SCRAPER_REMOTE_URL` | — | Optional remote Selenium/CDP endpoint (e.g. Bright Data scraping browser) for the AI scraper engine; local Chrome if unset |
| `LLM_SCRAPER_VERBOSE` | — | When set (any value), the AI scraper logs the cleaned DOM preview and each extracted deal at INFO. The engine also logs a WARNING when a page looks blocked (captcha/empty/anti-bot markers) |
| `MONGO_URI` | — | MongoDB connection string |
| `MONGO_DB_NAME` | — | MongoDB database name |

## Docker

The `Dockerfile` has three stages: `base` (core deps), `test` (adds dev deps, runs pytest), `browser` (adds Playwright + Chromium for JS-heavy sources). See `docs/container.md`.
