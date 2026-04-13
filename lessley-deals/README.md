# lessley-deals

Deals scraping and store resolution system for Israeli retail chains.
Scrapes publicly available store and deal data from Israeli retail sources,
normalizes Hebrew and English store names, and resolves name variants to
canonical store identities through a multi-stage matching pipeline.

## Why

Israeli retail data arrives with inconsistent naming -- Hebrew niqqud,
final-form letters, legal suffixes, and free-text branch descriptions all
vary across sources. This project ingests raw data verbatim, then applies
deterministic normalization and fuzzy matching so downstream consumers get
clean, deduplicated store records.

---

## Quick start

### Prerequisites

- Python 3.12+
- Docker and Docker Compose (the existing `lessley-cd/docker-compose.yaml`
  stack provides MongoDB, RabbitMQ, and the gateway)
- (Optional) `uv` or `pip` for local development outside Docker

### Setup

```bash
cd lessley-deals

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -e ".[dev]"
```

### Configuration

Copy the example env file and fill in values:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `DEALS_DATA_DIR` | Directory for JSON persistence files | `./data` |
| `DEALS_AUTO_MATCH_THRESHOLD` | Minimum score for automatic match | `0.90` |
| `DEALS_REVIEW_THRESHOLD` | Minimum score to enter review queue | `0.50` |
| `DEALS_LOG_LEVEL` | Logging level | `INFO` |
| `MONGO_URI` | MongoDB connection string (future) | -- |
| `MONGO_DB_NAME` | MongoDB database name (future) | -- |

---

## Architecture overview

The system is built around three main layers:

1. **Scrapers** -- async HTTP fetchers (httpx + selectolax) that pull raw
   store/deal data from retail sources and persist it verbatim.
2. **Normalization** -- deterministic text transforms for Hebrew (niqqud
   stripping, final-form unification, legal suffix removal, branch
   extraction) and English names.
3. **Store resolution** -- a 5-stage matching pipeline that maps scraped
   store name variants to canonical store identities:
   - **ExactAlias** -- known alias lookup
   - **Compact** -- whitespace/punctuation-stripped exact match
   - **Normalized fuzzy** -- fuzzy comparison on normalized forms
   - **Domain** -- domain-specific heuristics
   - **Token** -- token-set overlap scoring

Conservative thresholds control automation:
- `auto_match >= 0.90` -- accepted without review
- `review >= 0.50` -- queued for manual review
- `< 0.50` -- treated as a new store

Uncertain matches enter a manual review flow with a learning feedback loop
that feeds confirmed decisions back into the alias table.

### Group gift cards

Some HOT deals are group-level gift cards (e.g. "קבוצת גולף") redeemable at
any member store.  The scraper classifies these automatically:

- **Store-specific deals** → attributed directly to the sub-store (e.g. "sabon")
- **Group-wide gift cards** → attributed to the group and `group_member_stores`
  is embedded in the record so query-time fan-out can surface them for any member

See [docs/group-deals.md](docs/group-deals.md) for the full reference.

See [docs/architecture.md](docs/architecture.md) for the full design.

---

## Project structure

```
lessley-deals/
├── README.md
├── pyproject.toml
├── Dockerfile
├── .env.example
├── docs/
│   ├── architecture.md
│   ├── scraper.md
│   ├── resolution.md
│   └── mongodb-migration.md
├── src/
│   └── deals/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py            # typer app entry point
│       │   ├── scrape.py          # scrape sub-commands
│       │   └── review.py          # review sub-commands
│       ├── scrapers/
│       │   ├── __init__.py
│       │   ├── base.py            # typing.Protocol for scrapers
│       │   └── ...                # one module per retail source
│       ├── normalization/
│       │   ├── __init__.py
│       │   ├── hebrew.py          # niqqud, final forms, legal suffixes
│       │   └── english.py
│       ├── resolution/
│       │   ├── __init__.py
│       │   ├── pipeline.py        # 5-stage orchestrator
│       │   ├── stages.py          # individual stage implementations
│       │   └── review.py          # manual review logic
│       ├── models/
│       │   ├── __init__.py
│       │   ├── store.py           # dataclasses for store entities
│       │   └── deal.py            # dataclasses for deal entities
│       └── persistence/
│           ├── __init__.py
│           ├── json_store.py      # JSON file backend
│           └── mongo_store.py     # MongoDB backend (future)
├── tests/
│   ├── conftest.py
│   ├── test_normalization/
│   ├── test_resolution/
│   └── test_scrapers/
└── data/                          # runtime JSON storage (git-ignored)
```

---

## Running the pipeline

### With Docker

The deals service runs alongside the existing infrastructure defined in
`lessley-cd/docker-compose.yaml`.

```bash
# From the repo root -- start all services
cd lessley-cd
docker compose up -d

# Run a full scrape + resolve cycle
docker compose run --rm deals python -m deals scrape --all
docker compose run --rm deals python -m deals resolve
```

### Locally (CLI)

```bash
# Scrape all configured sources
python -m deals scrape --all

# Scrape a specific source
python -m deals scrape --source <source-name>

# Run store resolution on scraped data
python -m deals resolve

# Scrape and resolve in one step
python -m deals run
```

---

## Review CLI

After resolution, uncertain matches (score between 0.50 and 0.90) are
queued for manual review.

```bash
# Launch the interactive review TUI
python -m deals review

# Show pending review queue summary
python -m deals review --pending
```

The review interface (built with typer + rich) presents each candidate
match with its score and asks for confirmation. Confirmed decisions are
fed back into the alias table so future runs resolve them automatically.

---

## Adding a new scraper

1. Create a new module under `src/deals/scrapers/`.
2. Implement the scraper `Protocol` defined in `scrapers/base.py`.
3. Register the scraper in `scrapers/__init__.py`.
4. Add tests under `tests/test_scrapers/`.

See [docs/scraper.md](docs/scraper.md) for the full guide, including
async HTTP patterns with httpx and HTML parsing with selectolax.

---

## Running tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=deals --cov-report=term-missing

# Run a specific test module
pytest tests/test_normalization/
```

---

## Future: MongoDB migration

The persistence layer is designed behind a `Protocol` interface so the
JSON file backend can be swapped for MongoDB without changing business
logic. The MongoDB connection will use the same instance already running
in `lessley-cd/docker-compose.yaml`.

See [docs/mongodb-migration.md](docs/mongodb-migration.md) for the
migration plan and schema design.

---

## Documentation

- [Architecture](docs/architecture.md) -- system design and data flow
- [Scraper guide](docs/scraper.md) -- how to add a new retail source
- [Resolution pipeline](docs/resolution.md) -- matching stages and thresholds
- [MongoDB migration](docs/mongodb-migration.md) -- migration plan and schema
