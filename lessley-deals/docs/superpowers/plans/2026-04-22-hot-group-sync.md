# sync-hot-groups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `sync-hot-groups` CLI command that resolves plain-string member names in non-Swish HOT gift-card groups against canonical stores, writes `store_id` back to `hot_store_groups.json`, and pushes unresolved names to the review queue.

**Architecture:** New `hot_group_sync.py` helper module following the same pattern as `swish_group_sync.py`. Reads all non-Swish entries from `hot_store_groups.json`, resolves each member name (top-level `stores` and `sub_groups`) via `MatchPipeline`, upgrades plain strings to `{name, store_id, confidence}` dicts, atomically writes result, returns a summary dataclass. CLI command wires `AliasIndex` + `ReviewQueue` the same way `sync-swish-groups` does.

**Tech Stack:** Python 3.12, existing `MatchPipeline`, `AliasIndex`, `ReviewQueue`, `ReviewItem`, `MatchConfig` from `lessley_deals.*`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/lessley_deals/scraping/helpers/hot_group_sync.py` | **CREATE** | All sync logic — helpers, `_resolve_member_list`, `sync_hot_groups` |
| `tests/unit/scraping/test_hot_group_sync.py` | **CREATE** | Unit tests (mocked pipeline/queue/index) |
| `src/lessley_deals/cli/main.py` | **MODIFY** | Add `sync-hot-groups` command (~20 lines) |

---

## Reference: Key Signatures From Existing Code

```python
# lessley_deals/matching/pipeline.py
def match(self, normalized: NormalizedRecord, index: AliasIndex) -> MatchVerdict: ...

# lessley_deals/domain/models.py — MatchVerdict fields used
verdict.decision   # MatchDecision.AUTO_MATCH | REVIEW | NO_MATCH
verdict.best       # MatchCandidate | None  (.store_id, .confidence)
verdict.input_name # str
verdict.candidates # tuple[MatchCandidate, ...]
verdict.explanation # Explanation(.stages_run, .reason, .stage_matched, .details)

# lessley_deals/review/queue.py
queue.get_pending() -> list[ReviewItem]
queue.add(item: ReviewItem) -> None

# lessley_deals/matching/index.py
AliasIndex(aliases: list[Alias], stores: list[CanonicalStore])

# lessley_deals/cli/main.py — how sync-swish-groups wires deps (copy this pattern)
repos = _make_repos(data_dir)
index = AliasIndex(aliases=repos.alias_repo.get_all(), stores=repos.store_repo.get_all())
queue = ReviewQueue(repos.review_repo)
```

---

## Task 1: Module skeleton, helpers, and their tests

**Files:**
- Create: `src/lessley_deals/scraping/helpers/hot_group_sync.py`
- Create: `tests/unit/scraping/test_hot_group_sync.py`

- [ ] **Step 1: Write failing tests for helpers**

Create `tests/unit/scraping/test_hot_group_sync.py`:

```python
from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lessley_deals.domain.enums import MatchDecision
from lessley_deals.domain.models import (
    Explanation,
    MatchCandidate,
    MatchVerdict,
    NameForms,
    NormalizedRecord,
    ReviewItem,
)
from lessley_deals.scraping.helpers.hot_group_sync import (
    HotGroupSyncSummary,
    _build_name_forms,
    _existing_pending_names,
    _make_review_verdict,
    _resolve_member,
    _resolve_member_list,
    _to_normalized_record,
    sync_hot_groups,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

HOT_SOURCE_ID = "hot_groups"


def _make_verdict(decision: MatchDecision, store_id: str | None = None, conf: float = 0.95) -> MatchVerdict:
    best = None
    if store_id:
        best = MatchCandidate(store_id=store_id, store_name="dummy", confidence=conf)
    return MatchVerdict(
        record_id="test::name",
        input_name="name",
        decision=decision,
        candidates=(best,) if best else (),
        explanation=Explanation(stages_run=("exact_alias",), reason="test", stage_matched=None, details={}),
        best=best,
    )


def _make_pipeline(verdict: MatchVerdict) -> MagicMock:
    pipeline = MagicMock()
    pipeline.match.return_value = verdict
    return pipeline


def _make_queue(pending: list[str] | None = None) -> MagicMock:
    queue = MagicMock()
    items = []
    if pending:
        for name in pending:
            item = MagicMock()
            item.raw_input_name = name
            items.append(item)
    queue.get_pending.return_value = items
    queue.add = MagicMock()
    return queue


# ── Helper tests ──────────────────────────────────────────────────────────────

def test_build_name_forms_returns_name_forms():
    forms = _build_name_forms("Fox Home")
    assert isinstance(forms, NameForms)
    assert forms.normalized == "fox home"
    assert forms.compact == "foxhome"
    assert "fox" in forms.tokens
    assert "home" in forms.tokens


def test_to_normalized_record_uses_hot_source_id():
    record = _to_normalized_record("Super-Pharm", "my_group")
    assert record.source_id == HOT_SOURCE_ID
    assert record.raw_id == "my_group::Super-Pharm"
    assert isinstance(record.store_name_forms, NameForms)


def test_make_review_verdict_adds_source_and_kind():
    verdict = _make_verdict(MatchDecision.NO_MATCH)
    stamped = _make_review_verdict("קבוצת פוקס", "fox", verdict)
    assert stamped.explanation.details["kind"] == "group_member_match"
    assert stamped.explanation.details["source"] == "hot_groups"
    assert stamped.explanation.details["group_key"] == "קבוצת פוקס"
    assert stamped.record_id == "קבוצת פוקס::fox"


def test_resolve_member_auto_match_returns_store_id():
    verdict = _make_verdict(MatchDecision.AUTO_MATCH, store_id="abc_123", conf=0.97)
    pipeline = _make_pipeline(verdict)
    index = MagicMock()

    member, returned_verdict = _resolve_member("fox", "group_key", pipeline, index)

    assert member == {"name": "fox", "store_id": "abc_123", "confidence": 0.97}
    assert returned_verdict is None


def test_resolve_member_no_match_returns_null_store_id():
    verdict = _make_verdict(MatchDecision.NO_MATCH)
    pipeline = _make_pipeline(verdict)
    index = MagicMock()

    member, returned_verdict = _resolve_member("unknown store", "group_key", pipeline, index)

    assert member == {"name": "unknown store", "store_id": None, "confidence": None}
    assert returned_verdict is verdict


def test_existing_pending_names_returns_raw_input_names():
    queue = _make_queue(pending=["fox", "mango"])
    names = _existing_pending_names(queue)
    assert names == {"fox", "mango"}
```

- [ ] **Step 2: Run tests — verify they all FAIL (module doesn't exist yet)**

```bash
cd lessley-deals && pytest tests/unit/scraping/test_hot_group_sync.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError` or `ImportError` — that's correct.

- [ ] **Step 3: Create `hot_group_sync.py` with helpers only (no `sync_hot_groups` yet)**

Create `src/lessley_deals/scraping/helpers/hot_group_sync.py`:

```python
"""Sync HOT store-group member names against the canonical store database.

Reads manually maintained HOT gift-card group entries from
``hot_store_groups.json``, resolves each plain-string member name via the
matching pipeline, writes ``store_id`` back for auto-matched members, and
pushes unresolved members to the review queue.

Only entries WITHOUT ``managed_by: "swish_scraper"`` are processed.
Swish-managed entries are left untouched (owned by ``sync-swish-groups``).
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lessley_deals.domain.enums import MatchDecision
from lessley_deals.domain.models import (
    Explanation,
    MatchVerdict,
    NameForms,
    NormalizedRecord,
    ReviewItem,
)
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.pipeline import MatchPipeline
from lessley_deals.normalization.hebrew_utils import normalize_final_forms, normalize_hebrew
from lessley_deals.normalization.text import collapse_whitespace
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.review.queue import ReviewQueue
from lessley_deals.scraping.helpers.brand_utils import _DEFAULT_GROUPS_PATH

logger = logging.getLogger(__name__)

HOT_SOURCE_ID = "hot_groups"
SWISH_MANAGED_BY = "swish_scraper"


@dataclass
class HotGroupSyncSummary:
    groups_processed: int = 0
    members_resolved: int = 0
    members_pending: int = 0
    review_items_created: int = 0
    pre_existing_review_skipped: int = 0


def _build_name_forms(name: str) -> NameForms:
    normalized = collapse_whitespace(normalize_hebrew(name)).lower()
    compact = re.sub(r"[\s\W]+", "", normalized)
    compact = normalize_final_forms(compact)
    tokens = tuple(sorted({w for w in normalized.split() if len(w) > 1}))
    return NameForms(normalized=normalized, compact=compact, tokens=tokens)


def _to_normalized_record(name: str, group_key: str) -> NormalizedRecord:
    return NormalizedRecord(
        raw_id=f"{group_key}::{name}",
        source_id=HOT_SOURCE_ID,
        store_name_forms=_build_name_forms(name),
        deal_description="",
        normalized_at=datetime.now(timezone.utc),
        price=None,
        domain=None,
    )


def _make_review_verdict(
    group_key: str,
    raw_name: str,
    verdict: MatchVerdict,
) -> MatchVerdict:
    return MatchVerdict(
        record_id=f"{group_key}::{raw_name}",
        input_name=verdict.input_name,
        decision=verdict.decision,
        candidates=verdict.candidates,
        explanation=Explanation(
            stages_run=verdict.explanation.stages_run,
            reason=f"group-member resolution: {verdict.explanation.reason}",
            stage_matched=verdict.explanation.stage_matched,
            details={
                **verdict.explanation.details,
                "group_key": group_key,
                "kind": "group_member_match",
                "source": "hot_groups",
            },
        ),
        best=verdict.best,
    )


def _resolve_member(
    raw_name: str,
    group_key: str,
    pipeline: MatchPipeline,
    index: AliasIndex,
) -> tuple[dict[str, Any], MatchVerdict | None]:
    normalized = _to_normalized_record(raw_name, group_key)
    verdict = pipeline.match(normalized, index)

    if verdict.decision == MatchDecision.AUTO_MATCH and verdict.best is not None:
        return {
            "name": raw_name,
            "store_id": verdict.best.store_id,
            "confidence": round(verdict.best.confidence, 4),
        }, None

    return {"name": raw_name, "store_id": None, "confidence": None}, verdict


def _existing_pending_names(queue: ReviewQueue) -> set[str]:
    return {item.raw_input_name for item in queue.get_pending() if item.raw_input_name}


# _resolve_member_list and sync_hot_groups added in Task 2
```

- [ ] **Step 4: Run helper tests — verify they PASS**

```bash
cd lessley-deals && pytest tests/unit/scraping/test_hot_group_sync.py::test_build_name_forms_returns_name_forms tests/unit/scraping/test_hot_group_sync.py::test_to_normalized_record_uses_hot_source_id tests/unit/scraping/test_hot_group_sync.py::test_make_review_verdict_adds_source_and_kind tests/unit/scraping/test_hot_group_sync.py::test_resolve_member_auto_match_returns_store_id tests/unit/scraping/test_hot_group_sync.py::test_resolve_member_no_match_returns_null_store_id tests/unit/scraping/test_hot_group_sync.py::test_existing_pending_names_returns_raw_input_names -v
```

Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/lessley_deals/scraping/helpers/hot_group_sync.py tests/unit/scraping/test_hot_group_sync.py
git commit -m "feat: add hot_group_sync helpers and tests"
```

---

## Task 2: `_resolve_member_list` + tests

**Files:**
- Modify: `src/lessley_deals/scraping/helpers/hot_group_sync.py` (append function)
- Modify: `tests/unit/scraping/test_hot_group_sync.py` (append tests)

- [ ] **Step 1: Append `_resolve_member_list` tests to the test file**

Append to `tests/unit/scraping/test_hot_group_sync.py`:

```python
# ── _resolve_member_list tests ────────────────────────────────────────────────

def test_plain_string_auto_match_upgrades_to_dict():
    verdict = _make_verdict(MatchDecision.AUTO_MATCH, store_id="abc_123", conf=0.97)
    pipeline = _make_pipeline(verdict)
    queue = _make_queue()
    summary = HotGroupSyncSummary()

    result = _resolve_member_list(
        members=["fox"],
        group_key="קבוצת פוקס",
        pending_names=set(),
        pipeline=pipeline,
        index=MagicMock(),
        review_queue=queue,
        summary=summary,
        now=datetime.now(timezone.utc),
    )

    assert result == [{"name": "fox", "store_id": "abc_123", "confidence": 0.97}]
    assert summary.members_resolved == 1
    assert summary.members_pending == 0
    queue.add.assert_not_called()


def test_plain_string_no_match_pushed_to_review():
    verdict = _make_verdict(MatchDecision.NO_MATCH)
    pipeline = _make_pipeline(verdict)
    queue = _make_queue()
    summary = HotGroupSyncSummary()

    result = _resolve_member_list(
        members=["unknown store"],
        group_key="קבוצת פוקס",
        pending_names=set(),
        pipeline=pipeline,
        index=MagicMock(),
        review_queue=queue,
        summary=summary,
        now=datetime.now(timezone.utc),
    )

    assert result == [{"name": "unknown store", "store_id": None, "confidence": None}]
    assert summary.members_pending == 1
    assert summary.review_items_created == 1
    queue.add.assert_called_once()
    added_item = queue.add.call_args[0][0]
    assert isinstance(added_item, ReviewItem)
    assert added_item.raw_input_name == "unknown store"
    assert added_item.verdict.explanation.details["kind"] == "group_member_match"
    assert added_item.verdict.explanation.details["source"] == "hot_groups"


def test_dict_with_store_id_skipped():
    pipeline = _make_pipeline(_make_verdict(MatchDecision.AUTO_MATCH, store_id="abc_123"))
    queue = _make_queue()
    summary = HotGroupSyncSummary()
    already_resolved = {"name": "fox", "store_id": "abc_123", "confidence": 1.0}

    result = _resolve_member_list(
        members=[already_resolved],
        group_key="קבוצת פוקס",
        pending_names=set(),
        pipeline=pipeline,
        index=MagicMock(),
        review_queue=queue,
        summary=summary,
        now=datetime.now(timezone.utc),
    )

    assert result == [already_resolved]
    pipeline.match.assert_not_called()
    assert summary.members_resolved == 0
    assert summary.members_pending == 0


def test_dict_with_null_store_id_reprocessed():
    verdict = _make_verdict(MatchDecision.AUTO_MATCH, store_id="new_id", conf=0.92)
    pipeline = _make_pipeline(verdict)
    queue = _make_queue()
    summary = HotGroupSyncSummary()
    unresolved = {"name": "fox", "store_id": None, "confidence": None}

    result = _resolve_member_list(
        members=[unresolved],
        group_key="קבוצת פוקס",
        pending_names=set(),
        pipeline=pipeline,
        index=MagicMock(),
        review_queue=queue,
        summary=summary,
        now=datetime.now(timezone.utc),
    )

    assert result[0]["store_id"] == "new_id"
    assert summary.members_resolved == 1
    pipeline.match.assert_called_once()


def test_dedup_already_pending_not_pushed_twice():
    verdict = _make_verdict(MatchDecision.NO_MATCH)
    pipeline = _make_pipeline(verdict)
    queue = _make_queue()
    summary = HotGroupSyncSummary()
    pending = {"unknown store"}  # already in queue

    _resolve_member_list(
        members=["unknown store"],
        group_key="קבוצת פוקס",
        pending_names=pending,
        pipeline=pipeline,
        index=MagicMock(),
        review_queue=queue,
        summary=summary,
        now=datetime.now(timezone.utc),
    )

    queue.add.assert_not_called()
    assert summary.pre_existing_review_skipped == 1
    assert summary.review_items_created == 0
```

- [ ] **Step 2: Run new tests — verify they FAIL (function not implemented yet)**

```bash
cd lessley-deals && pytest tests/unit/scraping/test_hot_group_sync.py::test_plain_string_auto_match_upgrades_to_dict -v 2>&1 | tail -5
```

Expected: `ImportError: cannot import name '_resolve_member_list'`

- [ ] **Step 3: Append `_resolve_member_list` to `hot_group_sync.py`**

Replace the comment `# _resolve_member_list and sync_hot_groups added in Task 2` at the bottom of `hot_group_sync.py` with:

```python
def _resolve_member_list(
    members: list[str | dict],
    group_key: str,
    pending_names: set[str],
    pipeline: MatchPipeline,
    index: AliasIndex,
    review_queue: ReviewQueue,
    summary: HotGroupSyncSummary,
    now: datetime,
) -> list[dict[str, Any]]:
    """Resolve a list of member entries (strings or dicts) for one group."""
    result: list[dict[str, Any]] = []
    for entry in members:
        if isinstance(entry, str):
            raw_name = entry.strip()
        elif isinstance(entry, dict):
            if entry.get("store_id"):
                result.append(entry)
                continue
            raw_name = str(entry.get("name") or "").strip()
        else:
            continue
        if not raw_name:
            continue

        member, verdict = _resolve_member(raw_name, group_key, pipeline, index)
        result.append(member)

        if member["store_id"]:
            summary.members_resolved += 1
            continue

        summary.members_pending += 1
        if raw_name in pending_names:
            summary.pre_existing_review_skipped += 1
            continue
        if verdict is None:
            continue

        review_item = ReviewItem(
            id=generate_id(),
            raw_id=f"{group_key}::{raw_name}",
            input_name=raw_name,
            input_name_forms=_build_name_forms(raw_name),
            raw_input_name=raw_name,
            verdict=_make_review_verdict(group_key, raw_name, verdict),
            created_at=now,
        )
        review_queue.add(review_item)
        pending_names.add(raw_name)
        summary.review_items_created += 1

    return result


# sync_hot_groups added in Task 3
```

- [ ] **Step 4: Run `_resolve_member_list` tests — verify they PASS**

```bash
cd lessley-deals && pytest tests/unit/scraping/test_hot_group_sync.py -k "member_list or dedup" -v
```

Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/lessley_deals/scraping/helpers/hot_group_sync.py tests/unit/scraping/test_hot_group_sync.py
git commit -m "feat: implement _resolve_member_list for hot group sync"
```

---

## Task 3: `sync_hot_groups` + tests

**Files:**
- Modify: `src/lessley_deals/scraping/helpers/hot_group_sync.py` (replace trailing comment, append function)
- Modify: `tests/unit/scraping/test_hot_group_sync.py` (append tests)

- [ ] **Step 1: Append `sync_hot_groups` tests**

Append to `tests/unit/scraping/test_hot_group_sync.py`:

```python
# ── sync_hot_groups tests ─────────────────────────────────────────────────────

def _write_groups_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_sync_hot_groups_skips_swish_entries(tmp_path):
    groups_file = tmp_path / "groups.json"
    _write_groups_json(groups_file, {
        "swish:12345": {
            "managed_by": "swish_scraper",
            "stores": [{"name": "fox", "store_id": None, "confidence": None}],
        },
        "קבוצת פוקס": {
            "stores": ["mango"],
        },
    })
    verdict = _make_verdict(MatchDecision.AUTO_MATCH, store_id="mango_id", conf=0.95)
    pipeline = _make_pipeline(verdict)
    queue = _make_queue()

    result = sync_hot_groups(
        alias_index=MagicMock(),
        review_queue=queue,
        groups_config_path=groups_file,
        pipeline=pipeline,
    )

    updated = json.loads(groups_file.read_text(encoding="utf-8"))
    # Swish entry untouched
    assert updated["swish:12345"]["stores"][0]["store_id"] is None
    # HOT entry resolved
    assert updated["קבוצת פוקס"]["stores"][0]["store_id"] == "mango_id"
    assert result.groups_processed == 1
    assert result.members_resolved == 1


def test_sync_hot_groups_resolves_sub_groups(tmp_path):
    groups_file = tmp_path / "groups.json"
    _write_groups_json(groups_file, {
        "קבוצת פוקס": {
            "stores": ["fox"],
            "sub_groups": {
                "dream card family": ["fox home"],
            },
        },
    })
    verdict = _make_verdict(MatchDecision.AUTO_MATCH, store_id="store_id_x", conf=0.98)
    pipeline = _make_pipeline(verdict)
    queue = _make_queue()

    sync_hot_groups(
        alias_index=MagicMock(),
        review_queue=queue,
        groups_config_path=groups_file,
        pipeline=pipeline,
    )

    updated = json.loads(groups_file.read_text(encoding="utf-8"))
    sub = updated["קבוצת פוקס"]["sub_groups"]["dream card family"]
    assert sub[0]["store_id"] == "store_id_x"


def test_sync_hot_groups_unresolved_pushed_to_review(tmp_path):
    groups_file = tmp_path / "groups.json"
    _write_groups_json(groups_file, {
        "קבוצת פוקס": {"stores": ["mystery store"]},
    })
    verdict = _make_verdict(MatchDecision.NO_MATCH)
    pipeline = _make_pipeline(verdict)
    queue = _make_queue()

    result = sync_hot_groups(
        alias_index=MagicMock(),
        review_queue=queue,
        groups_config_path=groups_file,
        pipeline=pipeline,
    )

    queue.add.assert_called_once()
    assert result.review_items_created == 1
    assert result.members_pending == 1


def test_sync_hot_groups_summary_counts(tmp_path):
    groups_file = tmp_path / "groups.json"
    _write_groups_json(groups_file, {
        "group_a": {"stores": ["fox", "unknown"]},
        "group_b": {"stores": [{"name": "already", "store_id": "sid", "confidence": 1.0}]},
    })

    def match_side_effect(normalized, index):
        if "unknown" in normalized.raw_id:
            return _make_verdict(MatchDecision.NO_MATCH)
        return _make_verdict(MatchDecision.AUTO_MATCH, store_id="id_x", conf=0.95)

    pipeline = MagicMock()
    pipeline.match.side_effect = match_side_effect
    queue = _make_queue()

    result = sync_hot_groups(
        alias_index=MagicMock(),
        review_queue=queue,
        groups_config_path=groups_file,
        pipeline=pipeline,
    )

    assert result.groups_processed == 2
    assert result.members_resolved == 1   # "fox" resolved
    assert result.members_pending == 1    # "unknown" pending
    assert result.review_items_created == 1
    # "already" has store_id — skipped by _resolve_member_list
```

- [ ] **Step 2: Run new tests — verify they FAIL**

```bash
cd lessley-deals && pytest tests/unit/scraping/test_hot_group_sync.py -k "sync_hot_groups" -v 2>&1 | tail -8
```

Expected: `ImportError: cannot import name 'sync_hot_groups'`

- [ ] **Step 3: Replace the trailing comment with `sync_hot_groups` + `_load_groups_config` + `_atomic_write_json`**

Replace `# sync_hot_groups added in Task 3` at the bottom of `hot_group_sync.py` with:

```python
def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _load_groups_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}, got {type(data).__name__}")
    return data


def sync_hot_groups(
    alias_index: AliasIndex,
    review_queue: ReviewQueue,
    *,
    groups_config_path: Path | None = None,
    match_config: MatchConfig | None = None,
    pipeline: MatchPipeline | None = None,
) -> HotGroupSyncSummary:
    """Resolve HOT store-group members against the canonical store database.

    Skips Swish-managed entries (``managed_by: "swish_scraper"``).
    Upgrades plain-string member names to ``{name, store_id, confidence}`` dicts.
    Pushes unresolved names to ``review_queue``.
    Writes the updated config back atomically.
    """
    config_path = groups_config_path or _DEFAULT_GROUPS_PATH
    cfg = match_config or MatchConfig()
    match_pipeline = pipeline or MatchPipeline(config=cfg)

    groups = _load_groups_config(config_path)
    summary = HotGroupSyncSummary()
    pending_names = _existing_pending_names(review_queue)
    now = datetime.now(timezone.utc)

    for group_key, group_entry in groups.items():
        if group_key.startswith("_"):
            continue
        if not isinstance(group_entry, dict):
            continue
        if group_entry.get("managed_by") == SWISH_MANAGED_BY:
            continue

        summary.groups_processed += 1

        group_entry["stores"] = _resolve_member_list(
            members=group_entry.get("stores", []),
            group_key=group_key,
            pending_names=pending_names,
            pipeline=match_pipeline,
            index=alias_index,
            review_queue=review_queue,
            summary=summary,
            now=now,
        )

        sub_groups = group_entry.get("sub_groups", {})
        if isinstance(sub_groups, dict):
            for sub_key, sub_members in sub_groups.items():
                if isinstance(sub_members, list):
                    sub_groups[sub_key] = _resolve_member_list(
                        members=sub_members,
                        group_key=f"{group_key}/{sub_key}",
                        pending_names=pending_names,
                        pipeline=match_pipeline,
                        index=alias_index,
                        review_queue=review_queue,
                        summary=summary,
                        now=now,
                    )

    _atomic_write_json(config_path, groups)
    logger.info(
        "HOT groups sync: %d groups, %d resolved, %d pending, %d review items created",
        summary.groups_processed,
        summary.members_resolved,
        summary.members_pending,
        summary.review_items_created,
    )
    return summary
```

- [ ] **Step 4: Run all tests — verify they all PASS**

```bash
cd lessley-deals && pytest tests/unit/scraping/test_hot_group_sync.py -v
```

Expected: All tests PASS (12+)

- [ ] **Step 5: Run full test suite — verify no regressions**

```bash
cd lessley-deals && pytest -m "not integration" -q 2>&1 | tail -10
```

Expected: same number of failures as before this branch (15 pre-existing), no new failures.

- [ ] **Step 6: Commit**

```bash
git add src/lessley_deals/scraping/helpers/hot_group_sync.py tests/unit/scraping/test_hot_group_sync.py
git commit -m "feat: implement sync_hot_groups with sub_groups support"
```

---

## Task 4: CLI command `sync-hot-groups`

**Files:**
- Modify: `src/lessley_deals/cli/main.py`

- [ ] **Step 1: Locate the `sync-swish-groups` command in `main.py`**

Open `src/lessley_deals/cli/main.py` and find the block starting with:
```python
@app.command(name="sync-swish-groups")
def sync_swish_groups_cmd(
```
Note its line number. The new command goes immediately after it.

- [ ] **Step 2: Add `sync-hot-groups` command**

Insert the following after the closing of `sync_swish_groups_cmd` (after its last line):

```python
@app.command(name="sync-hot-groups")
def sync_hot_groups_cmd(
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    groups_file: Optional[str] = typer.Option(
        None,
        "--groups-file",
        help="Path to hot_store_groups.json. Defaults to bundled config.",
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Resolve HOT store-group member names against the canonical store database.

    Upgrades plain-string member names to {name, store_id, confidence} dicts.
    Auto-matched members get their store_id written into the config; unresolved
    members are pushed to the review queue.

    Skips Swish-managed entries (use sync-swish-groups for those).
    """
    _setup_logging(log_level)

    from lessley_deals.matching.index import AliasIndex
    from lessley_deals.scraping.helpers.hot_group_sync import sync_hot_groups

    repos = _make_repos(data_dir)
    index = AliasIndex(
        aliases=repos.alias_repo.get_all(),
        stores=repos.store_repo.get_all(),
    )
    queue = ReviewQueue(repos.review_repo)

    groups_path = Path(groups_file) if groups_file else None

    result = sync_hot_groups(
        alias_index=index,
        review_queue=queue,
        groups_config_path=groups_path,
    )
    console.print(
        f"HOT groups sync: {result.groups_processed} groups processed, "
        f"[green]{result.members_resolved} resolved[/green], "
        f"[yellow]{result.members_pending} pending[/yellow], "
        f"{result.review_items_created} new review items."
    )
```

- [ ] **Step 3: Verify CLI help shows the new command**

```bash
cd lessley-deals && python -m deals --help 2>&1 | grep sync
```

Expected output includes:
```
sync-hot-groups    Resolve HOT store-group member names...
sync-swish-groups  Refresh hot_store_groups.json with...
```

- [ ] **Step 4: Smoke-test with `--help`**

```bash
cd lessley-deals && python -m deals sync-hot-groups --help
```

Expected: prints usage with `--data-dir`, `--groups-file`, `--log-level` options. No errors.

- [ ] **Step 5: Run linter and type check**

```bash
cd lessley-deals && ruff check src/lessley_deals/scraping/helpers/hot_group_sync.py src/lessley_deals/cli/main.py && ruff check tests/unit/scraping/test_hot_group_sync.py
```

Fix any reported issues before committing.

```bash
cd lessley-deals && mypy src/lessley_deals/scraping/helpers/hot_group_sync.py
```

Fix any type errors before committing.

- [ ] **Step 6: Commit**

```bash
git add src/lessley_deals/cli/main.py
git commit -m "feat: add sync-hot-groups CLI command"
```

---

## Self-Review Checklist

After writing, verify against spec `docs/superpowers/specs/2026-04-22-hot-group-sync-design.md`:

- [x] `HotGroupSyncSummary` dataclass with `groups_processed`, `members_resolved`, `members_pending` fields → Task 1
- [x] Skip entries with `managed_by: "swish_scraper"` → `sync_hot_groups` Task 3
- [x] Skip already-resolved (`store_id != null`) → `_resolve_member_list` Task 2
- [x] Plain string or `store_id: null` → run MatchPipeline → Task 2
- [x] Auto-match → write `{name, store_id, confidence}` → Task 2
- [x] Below threshold → push `ReviewItem` with `kind=group_member_match`, `source=hot_groups`, `group_key` → Task 2
- [x] `sub_groups` resolved same path as top-level stores → Task 3
- [x] Dedup: exact `raw_input_name` in pending → skip → Task 2
- [x] Atomic write → `_atomic_write_json` Task 3
- [x] CLI command `sync-hot-groups` with `--groups-file` option → Task 4
- [x] All tests from spec testing table → Tasks 1–3
