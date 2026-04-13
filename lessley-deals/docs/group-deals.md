# Group Gift Cards

## Problem Statement

Some HOT Mobile deals have an `item_brand` that refers to a *retail group* rather
than a specific store.  Two very different situations are collapsed under the same
brand name:

| Situation | Example title | What it means |
|---|---|---|
| **Store-specific deal** | `תו קניה sabon` | Discount/gift card valid only at sabon |
| **Group-wide gift card** | `תו קניה קבוצת גולף - תווים` | Gift card redeemable at *any* store in the group |

Without disambiguation:
1. Store-specific deals are wrongly attributed to the group entity.
2. When a user looks up deals for "sabon", group-wide gift cards (which are
   perfectly valid at sabon) are invisible.

---

## Solution Overview

The resolution happens in two places:

```
Scraping time   ─▶  classify_group_deal()  ─▶  raw_payload["group_member_stores"]
Query time      ─▶  get_deals_for_store()  ─▶  union(direct + group-wide) 
```

---

## `classify_group_deal()` — at scrape time

**Location:** `src/lessley_deals/scraping/helpers/brand_utils.py`

```python
def classify_group_deal(
    brand: str,
    title: str,
    groups: dict[str, dict] | None = None,
) -> tuple[str, bool, list[str]]:
    ...
```

### Returns

`(resolved_store_name, is_group_wide, group_member_stores)`

| Return field | Type | Description |
|---|---|---|
| `resolved_store_name` | `str` | Sub-store name (specific deal) or group brand (group-wide) |
| `is_group_wide` | `bool` | `True` for group-wide gift cards |
| `group_member_stores` | `list[str]` | All member stores; empty for non-group / specific deals |

### Classification logic

1. Look up `brand` (case-insensitive) in the groups config.
2. Strip `title_prefix` from `title` to get a **candidate** sub-store name.
3. Check candidate against the group's `stores` whitelist (case-insensitive).
   - **Matches** → store-specific deal → `(candidate, False, [])`
   - **Does not match but candidate exists** → unknown sub-store, treated as
     store-specific → `(candidate, False, [])`
   - **No candidate** (prefix not in title) → group-wide → `(group_brand, True, members)`

### Examples

```python
# Store-specific (canonical name is returned from the whitelist)
classify_group_deal("קבוצת גולף - תווים", "תו קניה sabon")
# → ("sabon", False, [])

# Store-specific with trailing title content — trailing text is stripped
classify_group_deal("קבוצת גולף - תווים", "תו קניה sabon 200 ₪")
# → ("sabon", False, [])

# Group-wide gift card
classify_group_deal("קבוצת גולף - תווים", "תו קניה קבוצת גולף - תווים")
# → ("קבוצת גולף - תווים", True, ["kitan", "sabon", "golf&co", "golf", "polgat"])

# Non-group brand
classify_group_deal("AHAVA", "הנחה 20% באתר AHAVA")
# → ("AHAVA", False, [])
```

---

## `hot_store_groups.json` — configuration

**Location:** `src/lessley_deals/scraping/config/hot_store_groups.json`

```json
{
  "קבוצת גולף - תווים": {
    "title_prefix": "תו קניה",
    "stores": ["kitan", "sabon", "golf&co", "golf", "polgat"]
  }
}
```

| Field | Purpose |
|---|---|
| Key | Group brand name as returned by HOT API (`item_brand`) |
| `title_prefix` | String stripped from deal title to expose sub-store name |
| `stores` | **Whitelist** of known sub-store names; used for classification |

To add a new group, simply add an entry here — no code change required.

---

## `raw_payload["group_member_stores"]` — data contract

When `hot.py` produces a `RawScrapedRecord` for a group-wide deal, it injects:

```json
{
  "group_member_stores": ["sabon", "kitan", "golf&co", "golf", "polgat"]
}
```

This key is **absent** for store-specific deals (field injection only on group-wide).

---

## `get_deals_for_store()` — at query time

**Location:** `src/lessley_deals/scraping/helpers/group_deal_query.py`

```python
def get_deals_for_store(
    store_name: str,
    all_deals: list[RawScrapedRecord],
) -> list[RawScrapedRecord]:
    ...
```

Returns all deals where:
- `deal.store_name` matches `store_name` (direct match), **or**
- `store_name` appears in `deal.raw_payload["group_member_stores"]` (fan-out)

Deduplicates by `deal.id` and preserves original order.

### Example

```python
from lessley_deals.scraping.helpers.group_deal_query import get_deals_for_store

all_deals = [...]  # list[RawScrapedRecord]
sabon_deals = get_deals_for_store("sabon", all_deals)
# Includes:
#   - Direct sabon deals
#   - "קבוצת גולף - תווים" group-wide gift card
```

### Additional helpers

```python
from lessley_deals.scraping.helpers.group_deal_query import (
    is_group_wide_deal,        # bool — True if deal has group_member_stores
    get_group_member_stores,   # list[str] — returns the members list
)
```

---

## Backward Compatibility

`resolve_group_store()` is kept as a thin wrapper around `classify_group_deal()`:

```python
# Old code still works:
store_name = resolve_group_store(brand, title)

# New code gets more info:
store_name, is_group_wide, members = classify_group_deal(brand, title)
```

---

## Adding New Groups

1. Open `src/lessley_deals/scraping/config/hot_store_groups.json`.
2. Add an entry:
   ```json
   "נופשונית": {
     "title_prefix": "תו קניה",
     "stores": ["store-a", "store-b", "store-c"]
   }
   ```
3. Re-run the scraper — no code changes needed.
