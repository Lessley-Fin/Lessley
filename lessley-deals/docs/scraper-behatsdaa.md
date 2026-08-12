# Behatsdaa (בהצדעה) Loyalty Card Scraper

## Overview

Scrapes Behatsdaa's per-wallet giftcard discounts. Behatsdaa provides
*discount wallets* — monthly-loadable giftcards, each with its own flat
discount rate and monthly deposit cap (e.g. "load up to 500 ₪/month, get
15% off"), each accepted at a set of retail chains.

**Source ID:** `behatsdaa`

## Why file-based, not live

The Behatsdaa site requires a fresh login every time — there's no stable API
key, and a bare live-API adapter (fetching `GetCardGeneralInfo` /
`GetWalletChain` with an `AccessToken` header) can't authenticate without one.
Instead, this adapter reads **locally saved** copies of each wallet's own
`GetWalletChain` response, refreshed by hand after logging in.

## How It Works

### Files

- `data/behatsdaa_snapshots/behatsdaa_giftcards_config.json` — one entry per wallet, keyed by
  wallet id, giving the economics that aren't in the chains response itself:

  ```json
  {
    "2110": {
      "file": "behatsdaa_15_perc_2110.json",
      "name": "15% ארנק",
      "discount_percent": 15,
      "max_deposit_per_month": 500,
      "currency": "ILS",
      "active": true,
      "notes": ""
    }
  }
  ```

  - `file` — the wallet's saved chains JSON, resolved relative to this
    config file's own directory (currently `data/behatsdaa_snapshots/`).
  - `discount_percent` is required; entries missing it are skipped with a
    warning (not an error), so a partially-filled-in config doesn't break
    `scrape --all`.
  - `max_deposit_per_month` is optional — omit/null it for an uncapped
    wallet.
  - `active: false` disables a wallet without deleting its entry/file.
  - Keys starting with `_` (e.g. `_comment`, `_example`) are treated as
    comments and skipped — same convention as
    `scraping/config/hot_store_groups.json`.

- Each wallet's own JSON file (also in `data/behatsdaa_snapshots/`) — a **verbatim saved response** of
  `GET https://back.behatsdaa.org.il/api/cards/GetWalletChain?walletId=<id>`:

  ```json
  {
    "status": true,
    "data": [
      {
        "tagName": "רשתות שיווק מזון ופארמה",
        "walletChainData": [
          {"chainID": "107", "chainName": "קינג סטור", "webSite": "https://www.kingstore.co.il", "logoURL": "..."}
        ]
      }
    ]
  }
  ```

### Refreshing a wallet's chain list

1. Log in on behatsdaa.org.il.
2. Open devtools → Network, find the `GetWalletChain?walletId=<id>` request.
3. Save the response body over the matching file in `data/behatsdaa_snapshots/`.
4. Re-run `deals scrape --source behatsdaa`.

### Mapping to Domain

- Each **chain** → `RawStore` (deduplicated by cleaned chain name — a chain
  shared by multiple wallets is still a single store).
- Each **wallet × chain** → `RawScrapedRecord` (one deal per wallet a chain
  is accepted under — different wallets are different discount economics,
  not duplicates).
- `discount_logic.reward.value` = `discount_percent / 100`; `max_discount_amount`
  (when a deposit cap is set) = the real max monthly benefit, `max_deposit_per_month * discount_percent / 100`.
- Generic brand names filtered via `is_generic_behatsdaa_brand` (e.g. "בהצדעה" itself).

## CLI Usage

```bash
deals scrape --source behatsdaa
```

## Legacy Code Lineage

An earlier version of this module (`behatsdaa.py`) called the live API
directly with an `AccessToken` header. It was never actually wired up to a
real token anywhere in the codebase and its club had 0 stores — replaced by
this file-based adapter. See git history for the old implementation.
