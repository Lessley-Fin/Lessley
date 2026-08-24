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
python -m deals serve                                # Long-running scheduled worker (production)
python -m deals schedules                            # Resolved schedules + next firing times
python -m deals run-source hot                       # One source once, as the scheduler would
python -m deals run-history --source hot             # Recent scheduled runs from the journal
python -m deals deal-history <deal_key>              # Full version history of one deal
python -m deals reconcile-deals                      # Sweep `deals` rows no live offer accounts for (dry run)
python -m deals scrape --all                         # Scrape all sources
python -m deals scrape --source hot                  # Scrape one source
python -m deals process                              # Normalize + match raw data
python -m deals review                               # Interactive TUI for uncertain matches
python -m deals review --pending                     # Show review queue summary
python -m deals discover-stores                      # Analyze raw data for new stores
python -m deals enrich-raw-constraints               # Backfill `constraints` onto already-scraped raw deals
python -m deals propagate-constraints                # Copy raw constraints onto already-built deals (no LLM)
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

The system is a five-stage pipeline: **Scrape → Normalize → Match → Persist → Ingest**,
driven by a scheduler that runs every source independently and concurrently.

### Data Flow
```
SchedulerService (one asyncio loop per source, cron/interval)
    → SourceRunner      → lease lock, timeout, retry w/ backoff, run journal
    → ScrapeStage       → RawScrapedRecord, RawStore (verbatim, frozen)
    → NormalizeStage    → NormalizedRecord with NameForms {normalized, compact, tokens}
    → MatchStage        → MatchVerdict (AUTO_MATCH | REVIEW | NO_MATCH)
    → PersistStage/ReviewQueue → deals or review queue
    → IngestStage       → SCD Type 2 history (deal_versions + deals_current)
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

**`src/lessley_deals/review/`** — Interactive TUI for human review of uncertain matches. `Learner` feeds approved matches back as aliases, so they auto-match on the next run. The `[m]` action tags the store behind an item with MCC categories without resolving the item, and the same prompt fires automatically after `[c]`reate (`--no-mcc-on-create` to skip). See `docs/review.md`.

**MCC categories** — a store's `metadata.mcc_codes` is a ranked list of **category names** (`GROCERIES`, `RESTAURANT`, `CLOTHES_&_ACCESSORIES`, …), never the 4-digit numbers. The closed set of 46 names and the numeric-MCC → category mapping live in `enrichment/mcc_catalog.py`; run everything that writes the field through `normalize_mcc_codes()` so legacy numeric rows and loose spellings resolve to the canonical name. `deals enrich-stores` classifies missing ones via the LLM and converts already-numeric ones without spending a call.

**Deal constraints** — `ConstraintsStage` turns each deal's `terms_and_conditions` into the structured `constraints` block via a local LLM (`enrichment/constaints_parser.py`). The system prompt is **assembled per source**: a shared base (schema + rules + generic Hebrew vocabulary) plus an optional `_SOURCE_PROMPTS[source_id]` terminology block, with the output-discipline reminder kept last. Every site words the same restriction differently and leans on a different instrument (voucher / loadable card / club card), so a source with a block gets its own mappings; one without falls back to the generic prompt unchanged. **Every scraped source has a block** (`behatsdaa`, `hot`, both `hever_*`, all three `paisplus_*`, `mastercard`, `topcash`) — a source added later falls back to the generic prompt until one is written for it. Each block is grounded in that source's real terms text and pins the mapping it gets wrong by default; `tests/unit/enrichment/test_deal_constraints.py` asserts those specific rules survive edits. The recurring trap across sources is a **number that looks like a limit but is not**: a shekel spend ceiling (`עד 1,000 ₪ לעסקה`), a wallet load tier (`30% על טעינת 1,000 ₪ ראשונים`), a per-*member* voucher cap (`מוגבל לתו 1 לעמית מועדון (ת.ז.)`), a day of the month (`תקף ב-10 בחודש`), or a cashback waiting period (`כ-130 ימים`). None of these has a field; all three numeric limits stay null. Only a count scoped to one purchase (`עד 2 תווי קנייה בעסקה`) fills `max_uses_per_transaction`.

  **Which LLM answers these calls** is `LLM_PROVIDER` (`enrichment/llm_client.py`), defaulting to `college` — the faculty's self-hosted `gpt-oss-120b` at `COLLEGE_API_BASE`. The `openai` package is only the client library; nothing reaches OpenAI unless `LLM_PROVIDER=azure`. `COLLEGE_API_BASE` is an internal IP with a self-signed cert, so the caller must be on the college network. A parse that cannot reach a model is logged and skipped, never fatal — which is why a misconfigured deployment scrapes fine and silently leaves `constraints` empty.

  **Identical terms cost one call.** Sources reuse boilerplate heavily — one HOT text covers 6.3k deals, and across all sources 11.4k deals reduce to ~4.3k distinct `(source_id, terms)` pairs. `ConstraintsStage` groups by that exact pair and parses each once. The parser is deterministic (`temperature=0`, `seed=42`) and its prompt depends on nothing else, so the fan-out is byte-identical to parsing each deal separately — it is a 2.6x saving with no accuracy cost. `enrich-raw-constraints` groups the whole backlog *before* chunking, so a boilerplate group is never split across checkpoints and re-billed.

  **Backfilling deals scraped before this stage existed** (or while it was misconfigured): `deals enrich-raw-constraints` parses each stored raw deal's terms and writes the block onto `raw_payload["constraints"]` — exactly where `PersistStage` reads it — so a following `deals process` carries it onto the built deals with no further LLM calls. It checkpoints every `--chunk-size` *distinct texts* and skips anything already enriched, so an interrupted run resumes instead of paying twice.

  **Deals already built** (a `process` run that predates the enrichment) keep `constraints: null` even once the raw records are enriched. `deals propagate-constraints` matches them by `raw_id` and copies the block across — zero LLM calls, seconds to run. Reach for it instead of re-parsing; the answer is already on disk.

**`src/lessley_deals/pipeline/`** — `PipelineOrchestrator` wires `scrape_stage.py`, `normalize_stage.py`, `match_stage.py`, `persist_stage.py`, `ingest_stage.py` via a shared `context.py`. Each stage is independently testable. `factory.py` is the **composition root** — the single place that decides JSON vs MongoDB, which sources are registered, and whether versioning is on. Both the CLI and the worker build from it.

**`src/lessley_deals/scheduling/`** — the worker process. One `asyncio` loop per source (`scheduler.py`), each wrapped by `runner.py` (Mongo lease lock → run journal → hard timeout → exponential backoff + jitter). Schedules come from `data/seed/schedules.json`, overridable per source with `DEALS_SCHEDULE_<SOURCE>` (`off` / cron / `15m`). Cron is parsed in-repo (`schedule.py`) — no `croniter` dependency. Entrypoint: `scheduling/service.py`. See `docs/orchestration.md`.

**`src/lessley_deals/versioning/`** — SCD Type 2 deal history. **Data is never overwritten**: every change appends an immutable `DealVersion`, and a `CurrentDeal` head row (collection `deals_current`, filter `status: "active"`) holds the latest state. Two distinct hashes: `deal_key` (stable identity — must survive edits) and `content_hash` (semantic fields only — must ignore timestamps and URL tracking params). `ingestion.py::plan_ingestion` is a **pure function**, so classification (new/updated/unchanged/expired/reactivated) is fully unit-testable; `IngestionService` only loads, plans and bulk-writes.

  Expiry is guarded on purpose — a deal is only expired when the run had no errors, covered ≥50% of the known active deals, and the deal has been missing for ≥2 runs *and* ≥24h. Never weaken these without reading `docs/orchestration.md#3` first; under-expiring is recoverable, mass false expiry is not.

  `projection.py::DealProjector` is what carries those decisions to the collection consumers actually read — see the storage notes above. One rule when calling the ingestion by hand: a **rebuild** from the raw archive (`deals process`) must pass `allow_reactivation=False`, because that archive still holds the raw record of every offer ever retired and would otherwise bring them all back.

**Group gift cards** — HOT deals are classified as either store-specific or group-wide gift cards (e.g. "קבוצת גולף"). Group deals embed `group_member_stores` on the record so query-time fan-out can surface them for any member.

The Swish (נפשונית) catalogue is auto-synced into `hot_store_groups.json` by `sync_swish_groups()` (`scraping/helpers/swish_group_sync.py`). Swish entries are tagged `managed_by: "swish_scraper"`, store members as structured `{name, store_id, confidence}` dicts (resolved against the canonical stores via the matching pipeline), and push unresolved members to the review queue with `verdict.explanation.details["kind"] == "group_member_match"`. CLI: `python -m deals sync-swish-groups`. See `docs/group-deals.md`.

**`src/lessley_deals/domain/`** — Core dataclasses and enums. Raw/normalized records and verdicts are **frozen**; entities (stores, aliases) are **mutable**. Never mutate frozen records.

### Storage
- Default: JSON files in `data/` (configurable via `DEALS_DATA_DIR`)
- Optional: MongoDB (set `DEALS_STORAGE=mongo`, `MONGO_URI`, `MONGO_DB`)
- Raw scraped data is always preserved verbatim for auditability and replay
- **`deals`, `stores`, `clubs` and `mccs` are the shared read path.** Every consumer
  reads them directly — `deal-optimizer`'s `deals_source`, the Gateway's deal search
  and Personalization's reference data — so they are what a scrape run must leave
  correct.
- **`deals` has a lifecycle.** With `DEALS_PROJECT=1` (default) the versioning layer
  owns the collection: after each run `DealProjector` mirrors the head table onto it,
  upserting every live offer under its **stable** `deal_id` and stamping the ones the
  sources stopped listing `status: "expired"` (or deleting them, with
  `DEALS_DELETE_EXPIRED=1`). That is what makes a retired deal stop being priced and
  shown; before it, `deals` was append-only, so every rewording left an untracked
  duplicate behind and no offer ever went away. Consumers filter
  `status != "expired"` — **never** `== "active"`, because rows predating the field
  carry no status and are live. `python -m deals reconcile-deals` sweeps the duplicates
  the old behaviour left behind.
- `deals_current` (head, one row per deal) + `deal_versions` (append-only history) are
  the pipeline's own change tracking, written when `DEALS_VERSIONING=1`. They carry the
  deal under a `snapshot` sub-document and only cover the sources of whichever run last
  populated them — reading them from a consumer is what once hid every HOT deal from
  the optimizer. See `docs/orchestration.md`.
- Operational collections: `scrape_runs` (run journal, 90-day TTL) and
  `scheduler_locks` (lease locks for multi-replica workers)

### Adding a new scraper
1. Create `src/lessley_deals/scraping/sources/my_source.py` extending `BaseSourceAdapter`
2. Implement `source_id` property and `async def scrape() -> list[RawScrapedRecord]`
3. Register in `src/lessley_deals/scraping/registry.py`
4. Add tests in `tests/unit/scraping/`
5. Optionally add an entry to `data/seed/schedules.json` (otherwise it defaults
   to `0 3 * * *`), and register an identity extractor in
   `pipeline/factory.py::build_identity_resolver` if the source exposes a stable
   primary key — that keeps deal history intact across wording changes.

Existing sources: `hot.py`, `mastercard.py`, `behatsdaa.py`, `isracard_topcash.py`,
`hever.py` (`HeverGiftCardAdapter`, source_id `hever_gift_card_company`) and
`hever_teamim.py` (`HeverTeamimAdapter`, source_id `hever_teamim_card_store`) —
both fetch hvr.co.il's public JSON datasets live, no login required.

### Adding an AI-scraped site (no code)
For sites without a clean API, use the generic AI scraper engine instead of a
hand-coded adapter. Add an entry to `data/seed/llm_sources.json` with `site_id`,
`url`, and `instructions`, then run `python -m deals scrape --source <site_id>`.
The `LlmScraperAdapter` (`scraping/sources/llm_scraper.py`) renders the page with
Selenium (`scraping/engine/llm_scraper.py`), cleans the DOM, chunks it, and uses
the LLM client (`enrichment/llm_client.py::extract_deals_from_content`) to extract
deals into the normal `RawStore`/`RawScrapedRecord` pipeline.

**File-based LLM sources (no live fetch)**: add `"file_path"` (relative to the
`lessley-deals` package root) to a `llm_sources.json` entry and the adapter
reads that local file instead of fetching `url` at all — no Selenium, no
httpx. Set `"is_json": true` when the file is a raw JSON payload rather than
HTML (it's pretty-printed before chunking so `split_content` gets real line
boundaries). This is for sites that require a login the scraper can't
automate — you save the authenticated page/response by hand periodically and
the adapter just parses whatever's currently on disk.

**Prefer a hand-coded adapter over the LLM route whenever the source is
already structured** (a JSON API response, or consistently-shaped HTML with
no real judgment calls) — see `hever.py`'s `HeverGiftCardAdapter` and
`hever_teamim.py`'s `HeverTeamimAdapter`, which fetch hvr.co.il's public JSON
datasets (`/bs2/datasets/giftcard.json`, `/bs2/datasets/teamimcard_branches.json`
— no login needed, despite the site's own pages requiring one) and map every
field directly, same spirit as `hot.py`'s live API adapter. No LLM call, no
inference — `limitations`/`delivery` are copied verbatim into
`terms_and_conditions`. The LLM route is for when fields have to be *found*
in messy freeform text; skip it when they're already named JSON/HTML fields.

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
| `LLM_PROVIDER` | `college` | `college` (self-hosted gpt-oss-120b) or `azure` (OpenAI-compatible, `OPENAI_API_KEY`) |
| `COLLEGE_API_BASE` / `COLLEGE_MODEL_HOST` / `COLLEGE_MODEL_NAME` | — | Required by `LLM_PROVIDER=college`. Internal IP + Run:AI Host header + model id |
| `COLLEGE_API_KEY` | `not-needed` | Optional — the college endpoint does not check it |
| `DEALS_ENRICH_CONSTRAINTS` | — | Worker only: `1` runs the constraints stage on every scrape |
| `MONGO_URI` | — | MongoDB connection string |
| `MONGO_DB` | `lessley` | MongoDB database name |
| `DEALS_VERSIONING` | `1` | SCD Type 2 deal history (see `docs/orchestration.md`) |
| `DEALS_WRITE_LEGACY` | `1` | Write the shared `deals` collection every consumer reads |
| `DEALS_PROJECT` | `1` | Versioning owns `deals`: expired offers stop being served |
| `DEALS_DELETE_EXPIRED` | — | Delete expired rows from `deals` instead of flagging them |
| `DEALS_MAX_CONCURRENCY` | `3` | Sources scraped in parallel by the worker |
| `DEALS_SCHEDULE_<SOURCE>` | — | Per-source override: `off`, a cron string, or `15m`/`6h` |
| `DEALS_ABSENCE_THRESHOLD` / `DEALS_ABSENCE_GRACE_HOURS` | `2` / `24` | Misses + wall-clock before a deal expires |
| `DEALS_MIN_COVERAGE_RATIO` | `0.5` | Skip the expiry sweep on partial scrapes |

## Docker

The `Dockerfile` has three stages: `base` (core deps), `test` (adds dev deps, runs pytest), `browser` (adds Playwright + Chromium for JS-heavy sources). See `docs/container.md`.  A fourth stage, `worker`, is the scheduled scraper
service (`docker-compose.worker.yml`); it runs non-root and handles SIGTERM
gracefully.  See `docs/orchestration.md`.
