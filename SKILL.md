# Lessley — Project Skill Guide

This file gives Claude context about the Lessley workspace so it can assist effectively.

---

## Workspace Layout

```
d:\Lessley\
├── lessley-deals/      # Python scraping & store-resolution pipeline
├── lessley-cd/         # Docker Compose infrastructure (MongoDB, RabbitMQ, Grafana, …)
├── lessley-backend/    # .NET gateway + personalization service
└── main/               # (other)
```

---

## lessley-deals — Python Pipeline

**Tech stack:** Python 3.12, pymongo 4.8, httpx, rapidfuzz, typer, rich  
**Entry point:** `deals` CLI (`python -m lessley_deals.cli.main`)

### Architecture (pipeline stages)

```
Scrape → Normalize → Match → Persist (→ Review queue for uncertain matches)
```

| Stage | Key files |
|-------|-----------|
| Scraping | `scraping/sources/` (hot, mastercard, isracard_topcash, behatsdaa) |
| Normalization | `normalization/pipeline.py`, `normalization/steps/` |
| Matching | `matching/pipeline.py` — 5 stages: exact alias → compact → normalized → domain → token |
| Persistence | `persistence/repositories/` — JSON (default) or MongoDB (`mongo/` subdirectory) |
| Review | `review/` + interactive CLI (`deals review`) |

### Storage backends

Controlled by the `DEALS_STORAGE` env var:

| Value | Backend | When to use |
|-------|---------|-------------|
| `json` (default) | Local JSON files in `data/` | Solo dev, no Docker |
| `mongo` | MongoDB via `MONGO_URI` | Shared/multi-user, production |

**Switch to MongoDB:** set `DEALS_STORAGE=mongo` and `MONGO_URI=mongodb://guest:guest@localhost:27017/lessley?authSource=admin`

### Key CLI commands

```bash
# Scrape all sources and run full pipeline
deals scrape --all

# Run normalize→match→persist on existing raw data (no HTTP)
deals process

# Interactive review session (uncertain store matches)
deals review

# Seed MongoDB from data/seed/ JSON files (idempotent)
DEALS_STORAGE=mongo deals seed

# One-time migration: copy current data/*.json files → MongoDB
DEALS_STORAGE=mongo deals seed --from-live

# Re-run matching on pending review items after adding new stores
deals rematch-reviews

# Show review queue stats
deals review-stats

# List canonical stores (optionally filter)
deals list-stores [query]

# Discover unmatched store names and generate seed snippets
deals discover-stores --export unmatched.json
```

### Domain models (`domain/models.py`)

| Model | Type | Purpose |
|-------|------|---------|
| `RawScrapedRecord` | frozen dataclass | Verbatim scraped deal |
| `RawStore` | frozen dataclass | Verbatim scraped store |
| `NormalizedRecord` | frozen dataclass | Cleaned output of normalization |
| `CanonicalStore` | mutable dataclass | Single source of truth for a store |
| `StoreAlias` | mutable dataclass | Alternative name → store mapping |
| `Deal` | mutable dataclass | Resolved deal linked to canonical store |
| `ReviewItem` | mutable dataclass | Item in the human review queue |

### Repository protocols (`domain/protocols.py`)

All repositories are behind `typing.Protocol` interfaces — JSON and MongoDB implementations are interchangeable. Never import a concrete repo class in business logic; always depend on the protocol.

### MongoDB collections

| Collection | Model | Shared? |
|-----------|-------|---------|
| `deals` | Deal | **Yes** — Gateway deal search, Personalization, deal-optimizer |
| `stores` | CanonicalStore | **Yes** — same three |
| `clubs` | Club | **Yes** — Gateway `/api/v1/clubs`, Personalization, deal-optimizer |
| `mccs` | MCC catalogue | **Yes** — Gateway category filter, Personalization |
| `store_aliases` | StoreAlias | pipeline only |
| `raw_source_deals` | RawScrapedRecord | pipeline only |
| `raw_source_stores` | RawStore | pipeline only |
| `store_match_review` | ReviewItem | pipeline only |
| `external_refs` | ExternalReference | pipeline only |
| `deals_current` / `deal_versions` | CurrentDeal / DealVersion | pipeline change history — **not** a read path |

Document `_id` = entity `.id` (string format: `{timestamp_hex}_{random_hex}`).

The four shared collections are read directly by every service — there is no projected copy,
so a change to what the pipeline writes is immediately a change to what the API serves. Rows
loaded by `mongoimport` instead carry an ObjectId `_id` with the business key in `id`; all
readers accept either, but the pipeline upserts on `_id`, so importing over scraped data
duplicates rather than updates it.

### Seed data

- `data/seed/stores.json` — ~965 bootstrap canonical stores
- `data/seed/store_aliases.json` — ~16,853 aliases

Seed files are **read-only references** — do not commit live review decisions back to them. Use `deals seed` to load them into MongoDB once.

---

## lessley-cd — Infrastructure

**File:** `docker-compose.yaml`  
**Env config:** `.env` (copy from `.env.template`, fill in passwords)

### Services

| Service | Port | Purpose |
|---------|------|---------|
| mongodb | 27017 | MongoDB 8.0 (auth: DB_USER/DB_PASS) |
| mongo-express | 8081 | Web GUI for MongoDB |
| rabbitmq | 5672 / 15672 | Message broker |
| gateway | 5001 | .NET API gateway |
| personalization | 5002 | Python personalization service |
| loki | 3100 | Log aggregation |
| grafana | 3000 | Metrics dashboard |
| deals-pipeline | — | `profiles: ["tools"]` — on-demand scrape |
| deals-review | — | `profiles: ["tools"]` — interactive review |

### Common commands

```bash
# Start core infrastructure
docker compose up -d

# Run the deals scraper
docker compose --profile tools run --rm deals-pipeline

# Start interactive review session
docker compose --profile tools run -it deals-review

# One-time seed after fresh MongoDB
docker compose --profile tools run --rm deals-pipeline seed --from-live

# Open MongoDB GUI
open http://localhost:8081   # user/pass = DB_USER/DB_PASS from .env
```

### Key env vars (`.env`)

```
DB_NAME=lessley
DB_USER=guest
DB_PASS=...
DEALS_STORAGE=mongo
MONGO_URI=mongodb://${DB_USER}:${DB_PASS}@localhost:27017/${DB_NAME}?authSource=admin
```

---

## Multi-friend review workflow

Problem solved: multiple people reviewing stores simultaneously used to cause git conflicts on JSON files.

Solution: all reviewers connect to the shared MongoDB instance.  
- Each `deals review` session writes only the decision fields via `$set` (atomic, partial update)  
- No file locking, no git conflicts, no coordination needed  
- Reviewers can run in parallel from different machines (VPN/SSH tunnel to port 27017)

---

## Conventions

- **Do not change `domain/models.py` or `domain/protocols.py`** without a clear reason — they are the stable contract between all subsystems.
- **Prefer `$set` / `upsert=True`** in any new MongoDB write — never do a full replace.
- **Seed data is immutable** — `$setOnInsert` only; do not overwrite existing documents.
- **JSON repos stay** — kept for offline/local dev. Never delete them.
- Serialization helpers live in `persistence/serialization.py` — reuse `to_dict` / `from_dict` functions, do not write new ones.
- ID format: `persistence/id_gen.py` — always use this, never `uuid4()` or raw timestamps.
