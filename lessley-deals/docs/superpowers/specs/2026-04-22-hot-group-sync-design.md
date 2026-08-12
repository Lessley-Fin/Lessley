# Design: sync-hot-groups — HOT Store Group Member Resolution

**Date:** 2026-04-22  
**Branch:** feature/New_Scraper  
**Status:** Approved

---

## Overview

`sync-hot-groups` resolves the plain-string store member names in the non-Swish entries of `hot_store_groups.json` against the canonical store database via the MatchPipeline, writes resolved `store_id` values back into the JSON, and pushes unresolved names to the review queue.

This mirrors the existing `sync-swish-groups` command but targets the manually maintained HOT gift-card groups (e.g., "קבוצת פוקס", "קבוצת קסטרו") rather than Swish-scraped benefit entries.

---

## Background

`hot_store_groups.json` has two entry shapes:

**Regular (manual) groups** — stores as plain strings:
```json
"קבוצת פוקס - תווים": {
    "title_prefix": "תו קניה",
    "stores": ["fox", "mango", "terminal x"],
    "sub_groups": { "dream card family": ["fox", "fox home"] }
}
```

**Swish groups** — stores as structured dicts (managed by `sync-swish-groups`):
```json
"swish:103567": {
    "managed_by": "swish_scraper",
    "stores": [{"name": "שילב", "store_id": "019d...", "confidence": 1.0}]
}
```

`_normalize_member_entries()` in `brand_utils.py` already handles both formats. Upgrading plain strings to dicts is backward-compatible.

---

## Data Format Upgrade

After `sync-hot-groups` runs, regular groups store members as structured dicts:

```json
"קבוצת פוקס - תווים": {
    "title_prefix": "תו קניה",
    "stores": [
        {"name": "fox",        "store_id": "019d...", "confidence": 1.0},
        {"name": "mango",      "store_id": "019e...", "confidence": 0.93},
        {"name": "terminal x", "store_id": null,      "confidence": null}
    ],
    "sub_groups": {
        "dream card family": [
            {"name": "fox",      "store_id": "019d...", "confidence": 1.0},
            {"name": "fox home", "store_id": "019f...", "confidence": 0.95}
        ]
    }
}
```

**Re-run behavior:** entries with `store_id != null` are skipped — only plain strings and dicts with `store_id: null` are processed.

---

## Architecture

### New file: `src/lessley_deals/scraping/helpers/hot_group_sync.py`

Single public function:

```python
def sync_hot_groups(
    groups_path: Path,
    store_repo: CanonicalStoreRepository,
    review_queue: ReviewQueue,
    match_pipeline: MatchPipeline,
) -> HotGroupSyncSummary
```

**Internal flow:**

1. Load `hot_store_groups.json`
2. Skip entries where `entry.get("managed_by") == "swish_scraper"`
3. Load `_existing_pending_names(review_queue)` → `set[str]` (dedup guard)
4. For each remaining group key:
   - Resolve `stores` list via `_resolve_member_list()`
   - Resolve each `sub_groups[sub_key]` list via `_resolve_member_list()`
   - Write resolved members back into the group dict
5. Atomic write of updated JSON
6. Return `HotGroupSyncSummary`

**Private helpers:**

```python
@dataclass
class HotGroupSyncSummary:
    groups_processed: int
    members_resolved: int
    members_pending: int

def _existing_pending_names(queue: ReviewQueue) -> set[str]:
    return {item.raw_input_name for item in queue.get_pending() if item.raw_input_name}

def _resolve_member_list(
    members: list[str | dict],
    group_key: str,
    pending_names: set[str],
    store_repo, review_queue, match_pipeline,
    summary: HotGroupSyncSummary,
) -> list[dict]
```

**Resolution logic per member name:**

| Condition | Action |
|-----------|--------|
| Dict with `store_id != null` | Skip — already resolved |
| Plain string or dict with `store_id: null` | Run MatchPipeline |
| MatchPipeline → auto-match (conf ≥ 0.90) | Write `{name, store_id, confidence}` back |
| MatchPipeline → below threshold | Push `ReviewItem` to queue (if not already pending) |

**ReviewItem fields for unresolved members:**
```python
ReviewItem(
    kind="group_member_match",
    raw_input_name=name,
    details={
        "source": "hot_groups",
        "group_key": group_key,
    }
)
```

Dedup rule: if `name` already in `pending_names` set → skip push, do not create duplicate review item.

---

## CLI Command

Added to `src/lessley_deals/cli/main.py`:

```
python -m deals sync-hot-groups [--groups-file PATH]
```

- `--groups-file` defaults to the bundled `hot_store_groups.json` path
- Wires `CanonicalStoreRepository`, `ReviewQueue`, `MatchPipeline` from shared context
- Prints summary on completion:
  ```
  HOT groups sync: 5 groups processed, 38 members resolved, 4 pushed to review
  ```
- Kept separate from `sync-swish-groups` — two distinct commands, two distinct scopes

---

## Testing

New file: `tests/unit/scraping/test_hot_group_sync.py`

| Test | Verifies |
|------|----------|
| Plain string → auto-match | Upgraded to `{name, store_id, confidence}` dict |
| Plain string → no match | Pushed to review queue with `kind=group_member_match`, `source=hot_groups` |
| Dict with `store_id != null` | Skipped entirely |
| Dict with `store_id: null` | Re-processed |
| Sub-group member resolved | Same resolution path as top-level store |
| Dedup: name already pending | Not pushed twice |
| Swish entry present | Skipped (`managed_by: "swish_scraper"`) |
| Summary counts | Accurate after mixed run |

All tests use mocked `MatchPipeline`, `CanonicalStoreRepository`, `ReviewQueue` — no real I/O.

---

## What Changes

| File | Change |
|------|--------|
| `src/lessley_deals/scraping/helpers/hot_group_sync.py` | **NEW** |
| `src/lessley_deals/cli/main.py` | Add `sync-hot-groups` command |
| `tests/unit/scraping/test_hot_group_sync.py` | **NEW** |
| `src/lessley_deals/scraping/config/hot_store_groups.json` | Updated at runtime by command |

No changes to `swish_group_sync.py`, `brand_utils.py`, or any consumer of `hot_store_groups.json`.
