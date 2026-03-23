# Behatsdaa (בהצדעה) Loyalty Card Scraper

## Overview

Scrapes wallet and chain data from the **Behatsdaa** discount card API.  Unlike HOT and Mastercard which provide *deals*, Behatsdaa provides *discount wallets* — prepaid wallets loaded at a discount, each mapped to a set of retail chains where the card is accepted.

**Source ID:** `behatsdaa`

## How It Works

### Authentication

- **Base URL:** `https://back.behatsdaa.org.il`
- **Required headers:** `organizationid` (default `"20"`), `native` (default `"true"`)
- **Optional headers:** `AccessToken`, `cookie` (for authenticated endpoints)
- **Origin/Referer:** `https://www.behatsdaa.org.il`

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cards/GetCardGeneralInfo` | GET | List all wallets |
| `/api/cards/GetWalletChain?walletId=X` | GET | List chains for a wallet |

### Data Model

**Wallet** = a prepaid discount card category:
```json
{
  "walletID": "123",
  "walletName": "ארנק מזון",
  "discountRate": 7.5,
  "maxDepositForMonth": 2000,
  "walletBalance": 500.0
}
```

**Chain** = a retail chain where the wallet is accepted:
```json
{
  "chainID": "456",
  "chainName": "שופרסל",
  "webSite": "www.shufersal.co.il"
}
```

### Mapping to Domain

- Each **chain** → `RawStore` (deduplicated by name)
- Each **wallet × chain** → `RawScrapedRecord` (the discount relationship)
- Description: "הנחה 7.5% בשופרסל" (discount rate at chain)
- Price text: "7.5%" (the wallet discount rate)
- Generic brands filtered: "בהצדעה", "behatsdaa"

## CLI Usage

```bash
# Scrape Behatsdaa (requires access token)
deals scrape --source behatsdaa
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BEHATSDAA_ACCESS_TOKEN` | *(empty)* | API authentication token |
| `BEHATSDAA_COOKIE` | *(empty)* | Session cookie if required |
| `BEHATSDAA_ORGANIZATION_ID` | `20` | Organization header |
| `BEHATSDAA_NATIVE` | `true` | Native header flag |
| `BEHATSDAA_ORIGIN` | `https://www.behatsdaa.org.il` | Origin header |
| `BEHATSDAA_REFERER` | `https://www.behatsdaa.org.il/` | Referer header |

## Known Quirks

1. **Authentication required:** Most endpoints need a valid `AccessToken`
2. **Session timeout:** Sessions expire — legacy code had a keepalive ping mechanism
3. **Nested chain data:** Chains are nested inside `walletChainData` arrays within group objects
4. **Wallet balance is user-specific:** The `walletBalance` field reflects the authenticated user's balance

## Extension Points

- Implement keepalive ping (`/api/category/GetCategoryHeader`) for long-running sessions
- Add wallet balance tracking for user-specific features
- Map chains to existing canonical stores via website domain matching

## Legacy Code Lineage

| New Module | Legacy Source |
|-----------|--------------|
| `behatsdaa.py` | `behatsdaa/behatsdaa_scraper.py` |
| `brand_utils.py` | `import_businesses.py :: BehatsdaaBusinessImporter` |
