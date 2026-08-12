# MongoDB Storage

## Why MongoDB?

The original storage backend was local JSON files (`data/*.json`). This worked fine for a single developer but broke down when multiple people review stores at the same time — everyone edits the same file and git creates conflicts on every push/pull.

MongoDB solves this: all reviewers connect to the same shared database instance. Writes are atomic per document, so two people working in parallel never collide.

---

## What is stored where

| Data | Backend | Why |
|------|---------|-----|
| `stores` | **MongoDB** | Shared canonical store list — everyone reads the same truth |
| `store_aliases` | **MongoDB** | Shared alias index used by the matcher |
| `deals` | **MongoDB** | Resolved deals written by the pipeline |
| `raw_source_deals` | **MongoDB** | Raw scraped records (deduplication by fingerprint) |
| `raw_source_stores` | **MongoDB** | Raw scraped store names |
| `store_match_review` | **Local JSON** | Per-user review queue — each reviewer works their own copy |

The review queue stays local intentionally: two people reviewing the same ambiguous item would just do duplicate work. Each person runs `deals review` locally and their approvals write back to the shared MongoDB `store_aliases` and `deals` collections.

---

## How the pipeline works end-to-end

Running `deals scrape --all` executes four stages in sequence:

```
┌─────────┐     ┌───────────┐     ┌─────────┐     ┌─────────┐
│  Scrape │ --> │ Normalize │ --> │  Match  │ --> │ Persist │
└─────────┘     └───────────┘     └─────────┘     └─────────┘
```

### Stage 1 — Scrape

Fetches raw deals from all configured sources (HOT, Mastercard, Isracard, Behatsdaa).  
Each deal is saved to `raw_source_deals` using a fingerprint (`source|description|price`).  
**Duplicates are skipped** — if a deal with the same fingerprint already exists in MongoDB it is not re-inserted.

### Stage 2 — Normalize

Cleans each raw deal:
- Strips HTML, collapses whitespace
- Removes Hebrew niqqud and normalises final letter forms
- Parses price expressions into structured `PriceInfo`
- Produces three name forms: `normalized`, `compact`, `tokens`

### Stage 3 — Match

Runs a 5-stage matching pipeline against the canonical stores and aliases already in MongoDB:

| Stage | Method | Auto-save threshold | Review threshold |
|-------|--------|-------------------|-----------------|
| 1. ExactAlias | Exact string lookup against all known aliases | 100% | — |
| 2. Compact | Exact match after stripping spaces/punctuation | 100% | — |
| 3. Normalized | Jaro-Winkler + Token Jaccard blend | ≥ 0.90 | ≥ 0.50 |
| 4. Domain | Domain-specific heuristics | ≥ 0.90 | ≥ 0.50 |
| 5. Token | Token set overlap (Jaccard), capped at 0.70 | capped 0.70 | ≥ 0.50 |

The first stage that reaches a threshold wins. If no stage matches, the deal is discarded.

### Stage 4 — Persist

Each deal is routed based on the match verdict:

```
confidence ≥ 0.90  →  AUTO_MATCH  →  saved to MongoDB deals collection ✓
confidence 0.50–0.89  →  REVIEW  →  added to local store_match_review.json (human needed)
confidence < 0.50  →  NO_MATCH  →  discarded
                                     (or sent to review with --review-no-match flag)
```

For AUTO_MATCH deals, the pipeline also:
- Checks for duplicate by fingerprint — skips if the deal is already in MongoDB
- Updates the store's `metadata.image_urls` if the source provided an image

---

## First-time setup

### 1. Start MongoDB

```bash
cd lessley-cd
docker compose up mongodb -d
```

### 2. Migrate existing data into MongoDB (one-time)

```bash
cd lessley-deals
DEALS_STORAGE=mongo deals seed --from-live
```

This reads all current `data/*.json` files and upserts them into MongoDB.  
Safe to run multiple times — existing documents are never overwritten.

### 3. Verify in Mongo Express

Open http://localhost:8081 (credentials from `.env`).  
Check the `lessley` database has the `stores`, `store_aliases`, `deals` collections populated.

---

## Running the pipeline

```bash
# Run all scrapers — deals for known stores go straight to MongoDB
DEALS_STORAGE=mongo deals scrape --all

# Run just one source
DEALS_STORAGE=mongo deals scrape --source hot

# After scraping: review uncertain matches (writes approvals back to MongoDB)
DEALS_STORAGE=mongo deals review

# After adding new stores/aliases: re-run matching on the existing review queue
DEALS_STORAGE=mongo deals rematch-reviews
```

Via Docker (friends connecting to shared MongoDB):

```bash
cd lessley-cd

# Scrape all
docker compose --profile tools run --rm deals-pipeline

# Interactive review session
docker compose --profile tools run -it deals-review
```

---

## Multi-user review workflow

The problem: store "בוז׳ה" scraped from HOT doesn't confidently match any canonical store → sent to review.

```
Person A opens:  deals review   (reads store_match_review.json)
Person B opens:  deals review   (reads same local file independently)

Person A approves item #1 → writes alias + deal to MongoDB ✓
Person B approves item #2 → writes alias + deal to MongoDB ✓

No conflict — MongoDB handles concurrent writes atomically.
```

If two people accidentally review the same item, the second approval just updates the same alias/deal record — no data loss.

---

## Adding new stores

When a store name consistently gets NO_MATCH or REVIEW, add it to the canonical list:

```bash
# Find unmatched store names and generate seed snippets
DEALS_STORAGE=mongo deals discover-stores --export new_stores.json

# Or scan raw scraped stores directly
DEALS_STORAGE=mongo deals seed-from-raw --export new_stores.json
```

Edit `new_stores.json`, correct the `metadata.category`, then load into MongoDB:

```bash
# Append to seed files and upsert into MongoDB
DEALS_STORAGE=mongo deals seed-from-raw --write
```

Then re-run matching on the pending review queue to auto-approve items that now match:

```bash
DEALS_STORAGE=mongo deals rematch-reviews
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEALS_STORAGE` | `json` | Set to `mongo` to use MongoDB |
| `MONGO_URI` | `mongodb://guest:guest@localhost:27017/lessley?authSource=admin` | Full connection string |
| `MONGO_DB` | `lessley` | Database name (extracted from URI if omitted) |
| `DEALS_AUTO_MATCH_THRESHOLD` | `0.90` | Minimum confidence for AUTO_MATCH |
| `DEALS_REVIEW_THRESHOLD` | `0.50` | Minimum confidence to queue for review |
