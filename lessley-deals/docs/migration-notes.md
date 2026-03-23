# Migration Notes: Legacy Scraper → New Architecture

## What Changed

### Architecture Shift

| Aspect | Legacy (`lessley-backend/Scraper/`) | New (`lessley-deals/`) |
|--------|--------------------------------------|------------------------|
| Language | Python 3.x, mixed async/sync | Python 3.12, fully async |
| Persistence | MongoDB (motor/pymongo) | JSON files (atomic writes) |
| Normalization | Mixed into scrapers | Separate pipeline stage |
| Base class | `BaseScraper` (iter_offers + normalize_offer) | `BaseSourceAdapter` (scrape → RawStore + RawScrapedRecord) |
| Configuration | `.env` + `Settings` dataclass | `SourceConfig` frozen dataclass + CLI flags |
| LLM enrichment | OpenAI `gpt-4o-mini` normalization | Not included (out of scope) |
| Business import | Direct MongoDB upsert | Seed JSON files + alias matching |

### What Was Preserved

1. **HOT XSRF token dance** — identical handshake logic
2. **HOT pagination** — same page/size/benefit_type parameters
3. **HOT detail endpoint** — same multipart/form-data trick
4. **HOT brand cleaning** — `_N` suffix stripping via `clean_brand()`
5. **HOT discount mechanics** — full 6-level priority cascade from `deduce_discount_mechanics()`
6. **HOT benefit type classification** — cashback/voucher/coupon/discount heuristic
7. **HOT location extraction** — `supplierLocations` dict/list parsing
8. **Mastercard curl_cffi impersonation** — `chrome120` TLS fingerprint
9. **Mastercard DXP parsing** — `dxp-content-item`, `dxp-modal`, script extraction
10. **Mastercard CTA URL extraction** — both flat and nested `ctaData` formats
11. **Mastercard text extraction** — RTL char stripping, block element newlines
12. **Mastercard discount logic** — spend & save + percentage patterns
13. **Behatsdaa wallet/chain iteration** — same API endpoints and data structures
14. **Generic brand filtering** — HOT club names, Behatsdaa club name
15. **Website domain normalization** — `www.` stripping, scheme adding

### What Was Discarded

1. **MongoDB persistence** — replaced by JSON stores with atomic writes
2. **`normalize_offer()` in scrapers** — normalization now in pipeline stage
3. **OpenAI LLM normalizer** — removed (can be added as a normalization step later)
4. **Legacy `GenericBenefit` schema** — replaced by `RawScrapedRecord` + `NormalizedRecord`
5. **Direct file writes in scrapers** — scrapers return data, pipeline handles persistence
6. **Keepalive mechanism** — Behatsdaa keepalive not ported (short scrape sessions)
7. **`import_clubs.py`** — club metadata now in seed JSON files
8. **`export.py` parallel workers** — not needed for MVP (can add later)

### What Was Redesigned

1. **Discount parsing** — extracted to `scraping/helpers/discount_parser.py`, usable by both scrapers and normalization
2. **Brand cleaning** — extracted to `scraping/helpers/brand_utils.py`, shared across all scrapers
3. **HTML cleaning** — extracted to `scraping/helpers/html_utils.py`
4. **Store ↔ deal separation** — scrapers now emit distinct `RawStore` and `RawScrapedRecord` types
5. **Registry pattern** — `SourceRegistry` with `register_defaults()` replaces `ScraperContainer`
6. **Configuration** — per-source `SourceConfig` replaces global `Settings`

## How to Validate Correctness

### Step 1: Scrape and compare counts

```bash
# New architecture
deals scrape --source hot --log-level DEBUG
# Check: data/raw_source_deals.json and data/raw_source_stores.json

# Legacy (for comparison)
cd lessley-backend/Scraper
python -m hot.export benefits --output hot_benefits.json
```

Compare record counts — they should be similar (±5% due to timing / dedup).

### Step 2: Verify brand extraction

```bash
deals discover-stores --source hot
```

Check the unmatched stores list. Common issues:
- Brand names not cleaned (still has `_2` suffix)
- Generic club names appearing as stores

### Step 3: Verify discount mechanics (detail mode)

```bash
deals scrape --source hot --hot-fetch-details --hot-benefit-type 1300
```

Check `raw_payload._discount_mechanics` in the output — compare condition/reward types against legacy `hot_extract_format.py` output.

### Step 4: Verify Mastercard parsing

```bash
deals scrape --source mastercard
```

Check `raw_payload.discount_logic` — should have `type`, `condition`, `reward` keys.

### Step 5: Seed store matching

```bash
deals seed-from-raw --source hot
deals seed-from-raw --source mastercard
```

Verify the unmatched stores make sense and the seed snippets have correct metadata.

## Migration Order

1. ✅ HOT adapter (list API) — **DONE**
2. ✅ HOT detail enrichment — **DONE** (behind `--hot-fetch-details` flag)
3. ✅ Mastercard adapter — **DONE**
4. ✅ Behatsdaa adapter — **DONE**
5. ⬜ Shufersal adapter — stub only
6. ⬜ Rami Levy adapter — stub only
7. ⬜ Parallel detail fetching for HOT (port `export.py` chunked workers)
8. ⬜ Behatsdaa keepalive for long sessions
9. ⬜ LLM enrichment normalization step (optional)
