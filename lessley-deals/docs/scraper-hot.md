# HOT Mobile Benefits Scraper

## Overview

Scrapes deals from the **HOT Mobile loyalty club** public API.  HOT is one of Israel's major cellular providers offering a consumer benefits program with ~7 categories of deals.

**Source ID:** `hot`

## How It Works

### Session Initialization

1. GET `https://www.hot.co.il` to acquire session cookies
2. Extract `XSRF-TOKEN` from the cookie jar
3. Set `x-xsrf-token` header for all subsequent API calls
4. **Fallback:** If no XSRF cookie is found, use `"1"` (the API accepts it)

### Benefit List API

- **Endpoint:** `POST https://api.hot.co.il/api/website/2.0/getAllBenefits/`
- **Pagination:** 50 items/page, iterates until empty response
- **Form data:** `radius=0&page=N&platform=web&size=50`
- **Query param:** `benefitType=<type>` to filter by category

### Benefit Detail API

- **Endpoint:** `POST https://api.hot.co.il/api/website/2.0/getDetailedBenefitByIdForWeb/`
- **Encoding:** multipart/form-data (uses `files={k: (None, v)}` trick)
- **Returns:** Full deal data including terms, conditions, locations, pricing

### Benefit Types

| Code | Description |
|------|-------------|
| 100  | General benefits |
| 300  | Food & restaurants |
| 700  | Fashion & lifestyle |
| 800  | Beauty & wellness |
| 1100 | Home & electronics |
| 1200 | Travel & leisure |
| 1300 | Vouchers (special pricing logic) |

## Data Extraction

### Store Names
- Field: `item_brand`
- Cleaning: Strip `_N` suffixes (HOT's internal dedup), collapse whitespace
- Generic filtering: Skip "מועדון הוט", "הוט מועדון צרכנות", "HOT club"

### Group Brand Resolution

Some brands refer to a **retail group** (e.g. `"קבוצת גולף"`) rather than a
specific store.  The scraper calls `classify_group_deal()` to distinguish two cases:

| Case | Title example | Result |
|---|---|---|
| **Store-specific deal** | `"תו קניה sabon"` | `store_name = "sabon"` |
| **Group-wide gift card** | `"תו קניה קבוצת גולף - תווים"` | `store_name = "קבוצת גולף"` + `raw_payload["group_member_stores"]` injected |

The member-store list in `raw_payload["group_member_stores"]` enables
query-time fan-out via `get_deals_for_store()` — see
[docs/group-deals.md](group-deals.md) for the full reference.

### Deal Description
- Combined from `title` + `description`
- Price text from `value` field, fallback to `small_text`

### Discount Mechanics (Detail Mode)

When `--hot-fetch-details` is enabled, the scraper fetches the detail endpoint for each benefit and applies a **6-level priority cascade**:

1. **Voucher 1300 + prices:** `exact_spend` + `fixed_total_amount`
2. **Voucher 1300 + title ₪ + percentage:** Calculated voucher value
3. **"שווי X ב Y" pattern:** Hebrew voucher idiom
4. **Percentage in text:** `percentage_off`
5. **Spend & Save:** `min_spend` + `fixed_discount_amount`
6. **Price fallback:** Before/after prices from the record

Additional fields extracted in detail mode:
- `_terms_text`: Cleaned terms & conditions (from HTML)
- `_details_text`: Cleaned offer details
- `_stackable`: Whether deal stacks with other promotions
- `_redeem_channels`: `["online", "mobile_app", "physical_store"]`
- `_coupon`: Coupon code if present
- `_locations`: Branch addresses with city/lat/lng

## CLI Usage

```bash
# Scrape all benefit types (fast, list data only)
deals scrape --source hot

# Scrape specific types
deals scrape --source hot --hot-benefit-type 1100 --hot-benefit-type 1300

# Scrape with full detail enrichment (slower, richer data)
deals scrape --source hot --hot-fetch-details

# Combined
deals scrape --source hot --hot-benefit-type 1300 --hot-fetch-details
```

## Known Quirks

1. **XSRF token dance:** Some environments don't set the cookie; the `"1"` fallback works
2. **Brand naming:** HOT appends `_2`, `_3` to distinguish branches — stripped by `clean_brand()`
3. **HTTP/2 required:** The API works best with HTTP/2 (`httpx[http2]`)
4. **Rate limiting:** Default 0.7s between requests; too fast = HTTP 429

## Extension Points

- Add new benefit types if HOT introduces them
- Implement parallel detail fetching (legacy `export.py` had chunked workers)
- Add location geocoding in the normalization pipeline

## Legacy Code Lineage

| New Module | Legacy Source |
|-----------|--------------|
| `hot.py` | `hot/hot_scraper.py` |
| `discount_parser.py` | `hot/hot_extract_format.py :: deduce_discount_mechanics` |
| `brand_utils.py` | `import_businesses.py :: normalize_brand, is_generic_brand` |
| `html_utils.py` | `hot/hot_extract_format.py :: clean_html` |
