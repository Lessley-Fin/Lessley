# Swish (נפשונית) Automation Design

**Date:** 2026-04-21
**Branch:** feature/New_Scraper

---

## Purpose

Swish (נפשונית) is a multi-brand gift card platform. Its scrape is fundamentally different from other sources:

- **Not a deal source** — Swish produces no purchasable deals. It is a catalog of gift cards, each redeemable at a list of retailers.
- **Enrichment source** — When consumer clubs (HOT, Mastercard, etc.) list "נפשונית" as a brand, the Swish catalog tells us which retailers are covered.
- **Store discovery source** — Swish member businesses that are not yet in the canonical store catalog are pushed to the review queue for human approval.

The goal of this design is to:
1. Automate monthly catalog refresh via Docker container + internal cron.
2. Guarantee completeness — every gift card is captured, none missing.
3. Decouple Swish from the main scraper pipeline while still contributing to store discovery.
4. Expose granular CLI commands for manual control of each stage.

---

## Architecture Overview

```
┌─────────────── Docker: Dockerfile.swish ───────────────┐
│  Image: Python 3.12 + Playwright/Chromium + crond       │
│  Entrypoint: starts crond, optionally runs swish-all    │
│                                                          │
│  Volumes:                                                │
│   - /app/data/swish/      (scan_state.json, swish_database.json, session/)   │
│   - /app/data/            (review.json, stores, aliases)                     │
│   - /app/src/.../config/  (hot_store_groups.json)                            │
│                                                          │
│  Env: SWISH_CRON (default "0 3 1 * *")                  │
│  Cron: → python -m deals swish-all                      │
└─────────────────────────────────────────────────────────┘

CLI stages:
  swish-catalog → swish-scan → swish-retry → sync-swish-groups
       └─────────── swish-all (umbrella, shared browser) ──────────┘

File changes:
  NEW:  src/lessley_deals/scraping/helpers/swish_scanner.py
  MOD:  src/lessley_deals/scraping/helpers/swish_group_sync.py  (dedup)
  MOD:  src/lessley_deals/scraping/sources/swish.py             (RawStore only)
  MOD:  src/lessley_deals/cli/main.py                           (+4 commands)
  NEW:  Dockerfile.swish
  NEW:  docker/swish-crontab
  NEW:  docker/swish-entrypoint.sh
  DEL:  test_swish.py                                           (rewritten into swish_scanner.py)
```

---

## Component: `SwishScanner` class

**Location:** `src/lessley_deals/scraping/helpers/swish_scanner.py`

Single class holding one Playwright persistent context for the duration of a run. This avoids the cost of launching/closing Chromium between stages when `swish-all` runs all stages in sequence.

### Data structures

```python
@dataclass
class SwishPaths:
    data_dir: Path            # default: data/swish/
    database: Path            # {data_dir}/swish_database.json
    state: Path               # {data_dir}/scan_state.json
    session: Path             # {data_dir}/session/  (Playwright persistent context)

    @classmethod
    def from_env(cls) -> "SwishPaths":
        root = Path(os.getenv("SWISH_DATA_DIR", "data/swish"))
        return cls(data_dir=root, database=root / "swish_database.json",
                   state=root / "scan_state.json", session=root / "session")


@dataclass
class ScanState:
    processed: list[str]           # IDs fully scraped
    blocked: list[str]             # IDs hit block popup
    queue: list[str]               # IDs pending scrape
    last_catalog_count: int | None  # for two-phase stability check


@dataclass
class CatalogResult:
    ids_found: list[str]   # union of both catalog passes
    new_ids: list[str]     # not yet in processed
    stable: bool           # True if both passes returned identical ID sets


@dataclass
class SwishRunSummary:
    catalog_stable: bool
    ids_total: int
    records_new: int
    records_retried: int
    still_missing: list[str]
    attempts: int
```

### Class interface

```python
class SwishScanner:
    def __init__(self, paths: SwishPaths, *, scan_limit: int | None = None) -> None: ...

    def __enter__(self) -> "SwishScanner": ...   # launches persistent_context + stealth
    def __exit__(self, *exc) -> None: ...        # closes browser

    def catalog(self) -> CatalogResult:
        """Two-phase catalog scrape.

        Pass 1: goto CATALOG_URL, extract product IDs via regex.
        Sleep 30s (configurable via SWISH_CATALOG_SLEEP_S).
        Pass 2: repeat extraction.
        stable = (pass1_ids == pass2_ids).
        If unstable after 2 passes: take union, log warning, continue.
        Updates state.queue with new IDs not yet in processed.
        """

    def scan(self) -> int:
        """Scrape each ID in state.queue → append to swish_database.json.

        Respects block detection: on "אוי" popup → add to state.blocked,
        apply randomised cooldown (20–60s), continue.
        Returns count of new records saved.
        """

    def retry(self) -> int:
        """Scrape state.blocked + any ID that is not in processed and has no record.

        Prioritises blocked list (attempted first), then missing unprocessed.
        Returns count recovered.
        """

    def verify_complete(self) -> tuple[bool, list[str]]:
        """Check every catalog ID has an entry in swish_database.json.

        Returns (True, []) if complete; (False, missing_ids) otherwise.
        """

    def run_all(self, *, max_attempts: int = 3) -> SwishRunSummary:
        """Full run: catalog → (scan → retry → verify) loop.

        Loops scan+retry until verify_complete is True or max_attempts reached.
        Runs sync-swish-groups at the end via sync_swish_groups() directly.
        """
```

### Two-phase catalog verification

```
Pass 1 → extract IDs → count C1
Sleep 30s (SWISH_CATALOG_SLEEP_S env)
Pass 2 → extract IDs → count C2

if C1 == C2 and ids1 == ids2:
    stable = True, use ids1
else:
    stable = False, ids = union(ids1, ids2)
    log WARNING: "Catalog unstable: {C1} vs {C2} IDs"
```

Rationale: lazy-loaded catalogs may render different counts depending on network timing. Two stable passes gives high confidence in completeness.

### Retry / completeness loop in `run_all`

```
catalog()
attempt = 0
while attempt < max_attempts:
    scan()
    retry()
    ok, missing = verify_complete()
    if ok:
        break
    attempt += 1
    log WARNING: f"Attempt {attempt}: {len(missing)} IDs still missing"
sync_swish_groups(...)
```

---

## Component: CLI commands

**Location:** `src/lessley_deals/cli/main.py`

All new commands accept `--data-dir PATH` (overrides `$SWISH_DATA_DIR`).

| Command | What it does | Exit codes |
|---|---|---|
| `swish-catalog` | Map all gift card IDs, two-phase verify | 0=stable, 2=unstable-continued |
| `swish-scan` | Scrape pending queue IDs → `swish_database.json` | 0=success, 1=fatal |
| `swish-retry` | Retry blocked/failed IDs | 0=success, 1=fatal |
| `sync-swish-groups` | Push catalog → config + review queue (existing, enhanced) | 0=success, 1=fatal |
| `swish-all` | Umbrella: all stages in sequence, shared browser | 0=complete, 2=still_missing |

Exit code 2 = partial success (pipeline continues, human action may be needed).

### `swish-all` sequence

```bash
python -m deals swish-all
# Equivalent to (but with one browser context):
python -m deals swish-catalog
python -m deals swish-scan
python -m deals swish-retry  # repeated up to 3×
python -m deals sync-swish-groups
```

---

## Component: SwishAdapter (modified)

**Location:** `src/lessley_deals/scraping/sources/swish.py`

Remains registered in `registry.py` — `python -m deals scrape --all` still runs it.

**Change:** `scrape()` emits `(stores, [])` — `RawStore` per Swish member, zero `RawScrapedRecord`.

- One `RawStore` per unique member `storeName` across all `swish_database.json` records.
- Deduplicates by normalized store name within the same scrape run.
- Feeds into the normal `ScrapeStage → NormalizeStage → MatchStage → PersistStage` pipeline.
- No fake deals appear in the deal database from Swish.

---

## Component: Review queue dedup (enhanced)

**Location:** `src/lessley_deals/scraping/helpers/swish_group_sync.py`

### Current dedup (replaced)

```python
# OLD — only checks swish items by raw_id prefix
def _existing_pending_review_keys(queue: ReviewQueue) -> set[str]:
    return {item.raw_id for item in queue.get_pending()
            if item.raw_id.startswith(SWISH_GROUP_PREFIX)}
```

### New dedup

```python
def _existing_pending_names(queue: ReviewQueue) -> set[str]:
    """Exact raw_input_name of every pending queue item, regardless of source/kind."""
    return {item.raw_input_name for item in queue.get_pending()}
```

### Member resolution flow

For every `storeName` in every Swish benefit:

```
raw_name = "רנואר"
│
├── Step 1: MatchPipeline.match() vs AliasIndex
│     AUTO_MATCH (≥0.90) → {store_id, confidence} → done ✓
│     REVIEW / NO_MATCH ↓
│
├── Step 2: raw_name in _existing_pending_names(queue)?  (exact string)
│     Yes → skip (dedup) ✓
│     No  ↓
│
└── Step 3: push ReviewItem
      raw_id         = "swish:{benefit_id}::{raw_name}"
      raw_input_name = raw_name
      kind           = "group_member_match"  (existing, TUI handles it)
      TUI "c" → create new Store + alias
      TUI "l" → link to existing store → alias only
```

### Cross-benefit dedup example

- benefit 101: "רנואר" → not canonical, not in queue → push item. Queue now has "רנואר".
- benefit 202: "רנואר" → not canonical, **exact match in queue → skip**.
- Human approves → Store created, alias added.
- Next sync run: "רנואר" → canonical auto-match → no review item.

---

## Docker

### `Dockerfile.swish`

```dockerfile
FROM python:3.12-slim AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron tini ca-certificates && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e ".[browser]"
RUN playwright install --with-deps chromium

COPY docker/swish-crontab /etc/cron.d/swish
RUN chmod 0644 /etc/cron.d/swish && crontab /etc/cron.d/swish
COPY docker/swish-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV SWISH_DATA_DIR=/app/data/swish
ENV DEALS_DATA_DIR=/app/data
ENV SWISH_CRON="0 3 1 * *"
ENV SWISH_RUN_ON_START=0

VOLUME ["/app/data"]
ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
```

### `docker/swish-entrypoint.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

sed -i "s|SWISH_CRON_PLACEHOLDER|${SWISH_CRON}|" /etc/cron.d/swish
crontab /etc/cron.d/swish

touch /var/log/swish.log
mkdir -p "$SWISH_DATA_DIR" "$DEALS_DATA_DIR"

if [ "${SWISH_RUN_ON_START}" = "1" ]; then
    python -m deals swish-all >> /var/log/swish.log 2>&1 &
fi

cron
exec tail -F /var/log/swish.log
```

### `docker/swish-crontab`

```
SWISH_CRON_PLACEHOLDER  cd /app && python -m deals swish-all >> /var/log/swish.log 2>&1
```

### `docker-compose.yml` service

```yaml
services:
  swish-scanner:
    build:
      context: .
      dockerfile: Dockerfile.swish
    environment:
      SWISH_CRON: "0 3 1 * *"
      SWISH_DATA_DIR: /app/data/swish
      DEALS_DATA_DIR: /app/data
      DEALS_STORAGE: json
      SWISH_RUN_ON_START: "0"
    volumes:
      - ./data:/app/data
      - ./src/lessley_deals/scraping/config:/app/src/lessley_deals/scraping/config
    restart: unless-stopped
```

**Key points:**
- `tini` as PID 1 — prevents Chromium zombie processes.
- `tail -F` on log — `docker logs swish-scanner` shows all cron output.
- `SWISH_RUN_ON_START=1` — force immediate run: `docker run -e SWISH_RUN_ON_START=1 ...`.
- Single `./data` volume — sync-swish-groups can access review.json, stores, aliases.
- Separate config volume — hot_store_groups.json writable from container.

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `SWISH_DATA_DIR` | `data/swish` | Root for swish_database.json, scan_state.json, session/ |
| `SWISH_CRON` | `0 3 1 * *` | Cron schedule for monthly run |
| `SWISH_RUN_ON_START` | `0` | Set to `1` to run swish-all immediately on container start |
| `SWISH_CATALOG_SLEEP_S` | `30` | Seconds between two-phase catalog passes |

---

## Testing Strategy

### Unit tests (no browser required)

```
tests/unit/scraping/
  test_swish_scanner.py       # SwishScanner with mocked Playwright
  test_swish_group_sync.py    # extended: cross-benefit dedup, exact-string match
  test_swish_adapter.py       # SwishAdapter emits RawStore only, never deals
```

**`test_swish_scanner.py` cases:**
- `catalog()`: fake HTML with N product links → `ids_found == N`
- Two-phase stable: identical IDs both passes → `stable=True`
- Two-phase unstable: different IDs → `stable=False`, union taken
- Block detection: `BLOCK_TEXT` in HTML → ID enters `blocked`
- `verify_complete()`: all IDs in database → `(True, [])`
- `run_all()`: loop exits when `verify_complete` returns True

**`test_swish_group_sync.py` additions:**
- Same `raw_input_name` already pending → no new item pushed
- Same name in 2 benefits → single review item total
- Canonical match → no review item (existing test)

**`test_swish_adapter.py`:**
- `scrape()` returns `(stores, [])` always
- Store count matches config entries with `managed_by=swish_scraper`

### Integration tests (marked `integration`)

```
tests/integration/scraping/
  test_swish_full_run.py    # fixture swish_database.json → sync → assertions
```

- 2-benefit fixture, known member names (one canonical, one unknown, one duplicate across benefits).
- Asserts: review items created correctly, dedup holds, config written atomically.

---

## Files Changed Summary

| Action | Path |
|---|---|
| NEW | `src/lessley_deals/scraping/helpers/swish_scanner.py` |
| MOD | `src/lessley_deals/scraping/helpers/swish_group_sync.py` |
| MOD | `src/lessley_deals/scraping/sources/swish.py` |
| MOD | `src/lessley_deals/cli/main.py` |
| NEW | `Dockerfile.swish` |
| NEW | `docker/swish-crontab` |
| NEW | `docker/swish-entrypoint.sh` |
| MOD | `docker-compose.yml` (add swish-scanner service) |
| DEL | `test_swish.py` |
| NEW | `tests/unit/scraping/test_swish_scanner.py` |
| MOD | `tests/unit/scraping/test_swish_group_sync.py` |
| NEW | `tests/unit/scraping/test_swish_adapter.py` |
| NEW | `tests/integration/scraping/test_swish_full_run.py` |
