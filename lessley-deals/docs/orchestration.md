# Orchestration, scheduling and deal history

How scrapers get run on a schedule, concurrently and safely, and how their
output becomes an append-only history instead of an overwritten table.

---

## 1. Architecture

```
┌──────────────────────────── scraper worker (container) ─────────────────────────────┐
│                                                                                     │
│  SchedulerService — one asyncio loop per source                                     │
│    ├─ loop(hot)          sleep until cron ─┐                                        │
│    ├─ loop(mastercard)   sleep until cron ─┤→ semaphore(DEALS_MAX_CONCURRENCY)      │
│    └─ loop(behatsdaa)    sleep until cron ─┘                                        │
│                        │                                                            │
│                        ▼                                                            │
│  SourceRunner — lease lock → journal → timeout → retry w/ backoff → journal         │
│                        │                                                            │
│                        ▼                                                            │
│  PipelineOrchestrator                                                               │
│    ScrapeStage ─► NormalizeStage ─► MatchStage ─► [ConstraintsStage] ─► PersistStage │
│                                                                    │                │
│                                                                    ▼                │
│                                                            IngestStage              │
│                                                     (SCD Type 2 versioning)         │
└─────────────────────────────────────────────────────────────────────────────────────┘
                    │                                    │
                    ▼                                    ▼
        MongoDB: raw_*, stores, aliases        MongoDB: deal_versions, deals_current
                                                        scrape_runs, scheduler_locks
```

**No external broker.** Every source already runs as an independent `asyncio`
task inside one process, and the workload is I/O-bound HTTP/browser work — the
event loop is the natural concurrency primitive. RabbitMQ (used elsewhere in
Lessley for cross-service messaging) would add an operational dependency without
buying anything here: there is no fan-out to other consumers and no work that
outlives the run. Horizontal scaling is handled by the Mongo lease lock instead.

### Why a loop per source

* Sources are genuinely independent — a 40-minute Selenium crawl must not delay
  a 2-second JSON fetch.
* The next fire time is computed *after* the previous run finishes, so a run
  that overruns its interval can never pile up on itself.
* One source failing, hanging or being disabled touches nothing else.

### Components

| Module | Responsibility |
|---|---|
| `scheduling/schedule.py` | `ScheduleSpec`, `RetryPolicy`, dependency-free cron parser |
| `scheduling/config.py` | `schedules.json` + `DEALS_SCHEDULE_*` env overrides |
| `scheduling/scheduler.py` | Per-source loops, concurrency cap, graceful shutdown |
| `scheduling/runner.py` | Lock → journal → timeout → retry/backoff → journal |
| `scheduling/locks.py` | Mongo lease lock (multi-replica safety) |
| `scheduling/journal.py` | `scrape_runs` audit trail + staleness detection |
| `scheduling/service.py` | Worker entrypoint, signal handling |
| `versioning/hashing.py` | `deal_key` (identity) and `content_hash` (change detection) |
| `versioning/ingestion.py` | Pure classification + bulk apply |
| `pipeline/factory.py` | Composition root — the one place wiring lives |

---

## 2. Data model (SCD Type 2)

### `deal_versions` — append-only history

| Field | Notes |
|---|---|
| `_id` | Generated version id |
| `deal_key` | **Stable business key**, identical across all versions |
| `version` | 1-based, monotonic per `deal_key` |
| `content_hash` | Hash of the semantic fields only |
| `change_type` | `new` \| `updated` \| `expired` \| `reactivated` |
| `status` | `active` \| `expired` — what the deal *was* during this window |
| `valid_from` / `valid_to` | Validity window; `valid_to: null` ⇒ still open |
| `is_current` | Exactly one true row per `deal_key` (DB-enforced) |
| `snapshot` | Full `Deal` as observed at `valid_from` |
| `changed_fields` | Which fields changed vs the previous version |
| `run_id` | Scrape run that produced this row |
| `source_expires_at` | End date the source itself declared |

Indexes:

```js
{ deal_key: 1, version: 1 }                 // unique — replays are idempotent
{ deal_key: 1, is_current: 1 }              // unique, partial {is_current: true}
{ source_id: 1, valid_from: -1 }            // "what changed for this source"
{ store_id: 1, status: 1 }
```

The partial unique index is the important one: the "at most one current version"
invariant is enforced by MongoDB, not by application discipline.

### `deals_current` — head table (pipeline history, not the consumer read path)

> Consumers read the shared `deals` collection, not this one. `deals_current` keys on
> `deal_key` and carries the deal under `snapshot`, and it only covers the sources of
> whichever run last populated it — pointing the optimizer at it once hid every HOT deal.
> Use it for lifecycle questions (what changed, what expired), not to serve deals.

One document per `deal_key` (`_id = deal_key`), always the latest state, plus
`first_seen_at`, `last_seen_at`, `missing_runs`, `missing_since`,
`raw_fingerprint` and the full `snapshot`.

```js
// Live deals for a store
db.deals_current.find({ store_id: "S123", status: "active" })

// Everything that changed for a source in the last day
db.deal_versions.find({ source_id: "hot", valid_from: { $gte: yesterday } })

// What did this deal look like on a given date? (point-in-time)
db.deal_versions.findOne({
  deal_key: key,
  valid_from: { $lte: t },
  $or: [{ valid_to: null }, { valid_to: { $gt: t } }],
})
```

### The two hashes

Mixing these up breaks the history, so they are separate on purpose:

* **`deal_key` — identity.** `sha256(source_id | store_id | deal_type | external_id)`.
  Must stay stable while wording, price and terms change, otherwise every edit
  looks like a brand-new deal. Register a per-source extractor in
  `pipeline/factory.py::build_identity_resolver` whenever a source exposes a
  real primary key; the fallback (canonical URL → title → description prefix) is
  a guess.
* **`content_hash` — change detection.** Covers only the fields a user would
  care about, after canonicalisation: whitespace collapsed, Hebrew normalized,
  URL tracking params stripped, dict key order ignored. Timestamps, run ids and
  regenerated `Deal.id`s are excluded — otherwise every scrape would look like
  an update.

`Deal.id` is assigned once, on version 1, and carried forward. Downstream
references (saved deals, notifications) survive content changes.

---

## 3. Expiry — and why it is guarded so heavily

Nothing is ever deleted. A deal that disappears gets an `expired` version row,
so the gap is queryable and a return is a `reactivated` row afterwards.

The dangerous part is deciding a deal *is* gone. Expiring everything missing
from a run would wipe the catalogue the first time a source rate-limits us or
changes its HTML. A deal is only expired when **all** of these hold:

1. the run reported no scraper errors;
2. the run covered at least `DEALS_MIN_COVERAGE_RATIO` (default 50%) of the
   active deals we hold for that source;
3. it has been missing for `DEALS_ABSENCE_THRESHOLD` consecutive runs (2) **and**
   at least `DEALS_ABSENCE_GRACE_HOURS` (24h).

Otherwise the sweep is skipped entirely and logged at WARNING. Under-expiring is
recoverable; mass false expiry is not.

One subtlety worth knowing about: `ScrapeStage` drops raw records that are
byte-identical to a previous run, so a steady-state run passes **zero** deals
downstream. The ingestion therefore also receives every scraped record's
fingerprint (`ScrapeOutcome.seen_fingerprints`) and matches it against each
head's `raw_fingerprint`. Without that, a perfectly healthy quiet run would look
like a total scrape failure.

Deals also expire when their own declared end date passes, even if the source
still lists them (`DEALS_EXPIRE_ON_SOURCE_DATE`).

---

## 4. Running it

```bash
# The worker (production entrypoint — standalone, expects an external MONGO_URI)
docker compose -f docker-compose.worker.yml up -d --build

# Local dev: the same worker wired into the shared lessley-cd environment,
# against the mongodb container the other services already use
(cd ../lessley-cd && docker compose up -d --build deals-worker)

# Locally
deals serve

# Inspect and operate
deals schedules                      # resolved schedule + next firing times
deals run-source hot                 # one source, once, exactly as the scheduler would
deals run-history --source hot -n 20 # recent runs: status, duration, counters
deals deal-history <deal_key>        # every version of one deal
```

### Schedules

`data/seed/schedules.json`, one entry per source. The file is located via
`DEALS_DATA_DIR` first (`$DEALS_DATA_DIR/seed/schedules.json`), falling back to
the source-tree layout — walking up from `__file__` only resolves in a checkout,
so in a container the env var is what finds it.

The shipped cadence is **biweekly**: every source fires on the 1st and 15th, at
its own staggered slot.

```json
{
  "source_id": "hot",
  "cron": "0 2 1,15 * *",
  "timeout_seconds": 3600,
  "jitter_seconds": 120,
  "retry": { "max_attempts": 3, "base_delay_seconds": 30, "max_delay_seconds": 600 }
}
```

Day-of-month cron rather than a `14d` interval on purpose: interval schedules
are anchored on process start (the scheduler recomputes `now + interval` each
loop and persists nothing), so a worker restarting more often than its interval
would never fire at all. Cron is wall-clock anchored and survives restarts. The
trade-off is spacing that alternates 14 days (1st → 15th) and 16–17 days
(15th → 1st) rather than a strict fortnight.

Sources missing from the file default to `0 3 * * *`, so a newly registered
scraper starts running without a config change. Override without a redeploy:

```bash
DEALS_SCHEDULE_HOT="0 */6 * * *"     # re-schedule
DEALS_SCHEDULE_BEHATSDAA="off"       # disable
DEALS_SCHEDULE_LLM_TOPCASH="15m"     # interval instead of cron
```

(Source ids are upper-cased with non-alphanumerics turned into underscores:
`llm:topcash` → `DEALS_SCHEDULE_LLM_TOPCASH`.)

### Failure handling

| Failure | Behaviour |
|---|---|
| Transient scrape error | Retried up to `max_attempts` with exponential backoff + jitter |
| Source hangs | Killed at `timeout_seconds`, counts as a failed attempt |
| Source partially fails | `PARTIAL` — not retried (the site answered), expiry sweep disabled |
| All attempts fail | `FAILED` in the journal; the loop continues to the next slot |
| Two replicas, same source | Lease lock — the loser records `SKIPPED` |
| Worker crashes mid-run | Lease expires; version writes are upserts, so the replay is a no-op |
| SIGTERM | Loops wake immediately, in-flight runs get `DEALS_SHUTDOWN_GRACE`, then cancel |

Write order inside a run is deliberately replay-safe: close old version rows →
append new ones (upsert on `deal_key + version`) → update heads last. A crash
between steps leaves the head pointing at the old version, and the next run
simply redoes the same work.

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DEALS_STORAGE` | `json` | `json` \| `mongo` |
| `DEALS_DATA_DIR` | `./data` | Data dir; also where `seed/schedules.json` is looked up first |
| `DEALS_VERSIONING` | `1` | Enable SCD2 ingestion |
| `DEALS_WRITE_LEGACY` | `1` | Write the shared `deals` collection every consumer reads |
| `DEALS_MAX_CONCURRENCY` | `3` | Sources in flight at once |
| `DEALS_SHUTDOWN_GRACE` | `30` | Seconds to let in-flight runs finish |
| `DEALS_SCHEDULE_<SOURCE>` | — | `off` \| cron \| interval (`15m`, `6h`) |
| `DEALS_ABSENCE_THRESHOLD` | `2` | Consecutive misses before expiry |
| `DEALS_ABSENCE_GRACE_HOURS` | `24` | ...and this much wall-clock time |
| `DEALS_MIN_COVERAGE_RATIO` | `0.5` | Skip the sweep below this coverage |
| `DEALS_EXPIRE_ON_SOURCE_DATE` | `1` | Honour source-declared end dates |
| `DEALS_EXPIRY_SWEEP` | `1` | Master switch for absence-based expiry |
| `DEALS_RUN_JOURNAL` | `on` | `off` disables run journaling |
| `DEALS_RUN_RETENTION_DAYS` | `90` | TTL on `scrape_runs` |

---

## 5. What consumers read

`deals` — flat documents, one per deal, written on every run while
`DEALS_WRITE_LEGACY=1` (the default). `deal-optimizer`, the Gateway's deal search and
Personalization's reference data all bind it directly, alongside `stores`, `clubs` and
`mccs`. There is no projected copy of any of them.

Versioning is additive to that: `deals_current` and `deal_versions` answer "what changed,
when, and what is live", and they are the only place lifecycle metadata (`status`,
`missing_runs`, `valid_from`) exists. A consumer that wants to hide expired deals filters
`deals_current` for the `deal_key`s it cares about — it does not switch its read path
over, because `deals_current` only covers the sources of whichever run last populated it.

Backfill of existing `deals` documents into the versioned collections is not
included — the first worker run recreates every currently-listed deal as
version 1, which is usually the simpler path. If the existing `deals` rows need
to become history, write a one-off script that calls
`IngestionService.ingest(..., run_ok=False)` per source (that flag keeps the
expiry sweep off while backfilling a partial view).
