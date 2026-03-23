# Mastercard Day Promotions Scraper

## Overview

Scrapes deals from the **Mastercard Day** promotions page — a periodic event where Mastercard Israel offers discounts at participating retailers.

**Source ID:** `mastercard`

## How It Works

### Page Fetching

- **URL:** `https://www.mastercard.co.il/he-il/personal/offers-and-promotions/mastercard-day.html`
- **Anti-bot bypass:** Uses `curl_cffi` with `impersonate="chrome120"` to match Chrome's TLS fingerprint
- **Wrapped in `asyncio.to_thread()`** since `curl_cffi` is synchronous

### DXP Component Parsing

Mastercard uses a custom **DXP (Dynamic Xperience Platform)** rendering system with non-standard HTML tags:

- `<dxp-content-item>` — each deal block
- `<dxp-modal>` — detailed terms popup
- Categories from `inPageNavItemsData` JavaScript variable

### Extraction Pipeline (per block)

1. **Description:** Parse `description` attribute HTML → clean text
2. **Image:** `src` attribute, normalize to absolute URL
3. **Modal ID:** Extract from embedded `<script>` → `"modal-target": "id"`
4. **Store URL:** Two CTA data formats:
   - **Flat:** `ctaData = [{ctaText: "לאתר", ctaLink: "..."}]`
   - **Nested:** `dxpSelector.ctaData = [{ctaList: [{text: "לאתר", href: "..."}]}]`
   - **Fallback:** Links inside `<dxp-modal>` (excluding javascript, PDF, mastercard.co.il)
5. **Modal text:** Full terms from `.text-editor` inside `<dxp-modal>`
6. **Title:** Split on period or Hebrew keywords (תקף, המבצע, כולל כפל, etc.)
7. **Discount logic:**
   - Spend & Save: `₪X הנחה ברכישת ₪Y` → `min_spend` + `fixed_discount_amount`
   - Percentage: `X%` → `percentage_off`
   - Skip block if no pattern matches
8. **Ancillary fields:** stackable, redeem channels, coupon code
9. **Category:** Walk up the DOM tree to find parent `<div id="category_id">`

## Data Output

Each block produces:
- `RawScrapedRecord` with `store_name` = extracted title
- `RawStore` per unique store name
- `raw_payload` contains: image, modal_id, modal_text, store_url, category, discount_logic, stackable, channels, coupon

## CLI Usage

```bash
# Scrape Mastercard Day page
deals scrape --source mastercard
```

## Known Quirks

1. **TLS fingerprinting:** Standard `httpx`/`requests` get blocked; must use `curl_cffi`
2. **DXP custom tags:** Not standard HTML; BeautifulSoup handles them but lxml may not
3. **Page structure changes:** Mastercard may restructure the DXP layout between events
4. **Single-page scraper:** No pagination — everything is on one HTML page
5. **Event timing:** Page content only populated during Mastercard Day events
6. **RTL text:** Hebrew text contains invisible RTL markers (U+200E, U+200F, U+202A, U+202B) that must be stripped

## Extension Points

- Cache the HTML page to avoid re-fetching during development
- Add support for multiple Mastercard promo pages (if they create per-category pages)
- Detect "event not active" state and return empty gracefully

## Legacy Code Lineage

| New Module | Legacy Source |
|-----------|--------------|
| `mastercard.py` | `mastercard/mastercard_scraper.py :: scrape_dxp_fast` |
| `_extract_store_url()` | `extract_store_url_from_script()` + `extract_store_url_from_modal()` |
| `_extract_modal_text()` | `extract_modal_text()` |
| `_parse_discount_logic()` | `parse_discount_logic()` |
| `discount_parser.py` | Unified condition/reward/constraints schema |
