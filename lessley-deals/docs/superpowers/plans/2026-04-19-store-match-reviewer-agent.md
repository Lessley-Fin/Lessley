# Store Match Reviewer Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Claude Code subagent that processes the store-match review queue in bounded batches, auto-approves high-confidence matches, lets the user pick from LLM-proposed alias variations, and commits everything through one new `deals review-apply-batch` Typer subcommand.

**Architecture:** Subagent (`.claude/agents/store-match-reviewer.md`) reads `data/store_match_review.json`, prompts user as needed, writes `data/.tmp/decisions.json`, then shells out to `python -m deals review-apply-batch <path>`. The CLI loads decisions, validates schema, and delegates to a new `BatchApplier` class that reuses the existing `ReviewActions` methods plus a new alias-dedup/conflict step.

**Tech Stack:** Python 3.12, Typer (CLI), pytest (tests), Click is NOT used — Typer commands are flat with hyphen-separated names (existing convention: `review`, `review-stats`, `discover-stores`, `rematch-reviews`).

**Spec:** [`docs/superpowers/specs/2026-04-19-store-match-reviewer-agent-design.md`](../specs/2026-04-19-store-match-reviewer-agent-design.md)

---

## File Structure

| Path | Action | Responsibility |
|------|--------|----------------|
| `src/lessley_deals/review/batch_apply.py` | NEW | `BatchResult`, `BatchError`, `BatchApplier` — orchestrates a batch of review decisions |
| `src/lessley_deals/review/batch_schema.py` | NEW | `parse_decisions(path)` — loads + validates `decisions.json`, returns typed list |
| `src/lessley_deals/cli/main.py` | EDIT | Add `@app.command(name="review-apply-batch")` |
| `tests/unit/review/test_batch_schema.py` | NEW | Schema validation unit tests |
| `tests/unit/review/test_batch_apply.py` | NEW | `BatchApplier` behavioral unit tests |
| `tests/unit/review/__init__.py` | NEW IF MISSING | Package marker |
| `.gitignore` | EDIT | Add `data/.tmp/` |
| `.claude/agents/store-match-reviewer.md` | NEW | Subagent definition |

`batch_schema.py` is split out so the CLI can validate without instantiating repos (helps `--dry-run` UX and makes schema tests fast/pure).

---

## Task 1: Scaffold `BatchResult` / `BatchError` dataclasses with a smoke test

**Files:**
- Create: `src/lessley_deals/review/batch_apply.py`
- Create: `tests/unit/review/test_batch_apply.py`
- Create if missing: `tests/unit/review/__init__.py`

- [ ] **Step 1: Confirm test package marker exists**

Run: `ls tests/unit/review/__init__.py 2>/dev/null || touch tests/unit/review/__init__.py`
Expected: file exists (empty is fine).

- [ ] **Step 2: Write the failing test**

Create `tests/unit/review/test_batch_apply.py`:

```python
from __future__ import annotations

from lessley_deals.review.batch_apply import BatchError, BatchResult


def test_batch_result_defaults_to_zero_counts():
    result = BatchResult()
    assert result.approved == 0
    assert result.created == 0
    assert result.discarded == 0
    assert result.skipped == 0
    assert result.aliases_added == 0
    assert result.errors == []


def test_batch_error_holds_item_id_and_reason():
    err = BatchError(item_id="abc", reason="not pending")
    assert err.item_id == "abc"
    assert err.reason == "not pending"
```

- [ ] **Step 3: Run test, verify it fails**

Run: `pytest tests/unit/review/test_batch_apply.py -v`
Expected: FAIL — `ModuleNotFoundError: lessley_deals.review.batch_apply`.

- [ ] **Step 4: Implement minimal module**

Create `src/lessley_deals/review/batch_apply.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BatchError:
    item_id: str
    reason: str


@dataclass
class BatchResult:
    approved: int = 0
    created: int = 0
    discarded: int = 0
    skipped: int = 0
    aliases_added: int = 0
    errors: list[BatchError] = field(default_factory=list)
```

- [ ] **Step 5: Run test, verify it passes**

Run: `pytest tests/unit/review/test_batch_apply.py -v`
Expected: PASS, 2 tests.

- [ ] **Step 6: Commit**

```bash
git add src/lessley_deals/review/batch_apply.py tests/unit/review/__init__.py tests/unit/review/test_batch_apply.py
git commit -m "feat(review): scaffold BatchResult and BatchError dataclasses"
```

---

## Task 2: Decisions schema parser — happy path

**Files:**
- Create: `src/lessley_deals/review/batch_schema.py`
- Create: `tests/unit/review/test_batch_schema.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/review/test_batch_schema.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lessley_deals.review.batch_schema import (
    Decision,
    DecisionsFile,
    SchemaError,
    parse_decisions,
)


def _write(tmp_path: Path, payload: dict) -> Path:
    p = tmp_path / "decisions.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_parse_minimal_approve(tmp_path: Path):
    payload = {
        "version": 1,
        "created_at": "2026-04-19T12:00:00+00:00",
        "reviewed_by": "store-match-reviewer-agent",
        "decisions": [
            {
                "item_id": "abc",
                "action": "approve",
                "store_id": "store-1",
                "extra_aliases": ["alt one", "alt two"],
                "note": "auto",
            }
        ],
    }
    parsed = parse_decisions(_write(tmp_path, payload))
    assert isinstance(parsed, DecisionsFile)
    assert parsed.version == 1
    assert parsed.reviewed_by == "store-match-reviewer-agent"
    assert len(parsed.decisions) == 1
    d = parsed.decisions[0]
    assert isinstance(d, Decision)
    assert d.action == "approve"
    assert d.store_id == "store-1"
    assert d.extra_aliases == ["alt one", "alt two"]
    assert d.note == "auto"


def test_parse_create_new_with_metadata(tmp_path: Path):
    payload = {
        "version": 1,
        "created_at": "2026-04-19T12:00:00+00:00",
        "reviewed_by": "agent",
        "decisions": [
            {
                "item_id": "xyz",
                "action": "create_new",
                "new_store_name": "G-Bike",
                "metadata": {"image_urls": []},
                "extra_aliases": ["g bike"],
            }
        ],
    }
    parsed = parse_decisions(_write(tmp_path, payload))
    d = parsed.decisions[0]
    assert d.action == "create_new"
    assert d.new_store_name == "G-Bike"
    assert d.metadata == {"image_urls": []}


def test_parse_discard_and_skip(tmp_path: Path):
    payload = {
        "version": 1,
        "created_at": "2026-04-19T12:00:00+00:00",
        "reviewed_by": "agent",
        "decisions": [
            {"item_id": "a", "action": "discard", "note": "spam"},
            {"item_id": "b", "action": "skip"},
        ],
    }
    parsed = parse_decisions(_write(tmp_path, payload))
    assert [d.action for d in parsed.decisions] == ["discard", "skip"]
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/unit/review/test_batch_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: lessley_deals.review.batch_schema`.

- [ ] **Step 3: Implement schema module**

Create `src/lessley_deals/review/batch_schema.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

VALID_ACTIONS = {"approve", "create_new", "discard", "skip"}
SCHEMA_VERSION = 1


class SchemaError(ValueError):
    """Raised when decisions.json fails schema validation."""


@dataclass(frozen=True)
class Decision:
    item_id: str
    action: str
    store_id: str | None = None
    new_store_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    extra_aliases: list[str] = field(default_factory=list)
    note: str | None = None


@dataclass(frozen=True)
class DecisionsFile:
    version: int
    created_at: str
    reviewed_by: str
    decisions: list[Decision]


def parse_decisions(path: Path) -> DecisionsFile:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SchemaError("Top-level value must be an object")

    version = raw.get("version")
    if version != SCHEMA_VERSION:
        raise SchemaError(f"Unsupported version: {version!r} (expected {SCHEMA_VERSION})")

    if "decisions" not in raw or not isinstance(raw["decisions"], list):
        raise SchemaError("Missing or invalid 'decisions' list")

    decisions = [_parse_decision(i, d) for i, d in enumerate(raw["decisions"])]

    return DecisionsFile(
        version=version,
        created_at=str(raw.get("created_at", "")),
        reviewed_by=str(raw.get("reviewed_by", "")),
        decisions=decisions,
    )


def _parse_decision(index: int, d: Any) -> Decision:
    if not isinstance(d, dict):
        raise SchemaError(f"decisions[{index}] must be an object")

    item_id = d.get("item_id")
    if not isinstance(item_id, str) or not item_id:
        raise SchemaError(f"decisions[{index}]: item_id required (non-empty string)")

    action = d.get("action")
    if action not in VALID_ACTIONS:
        raise SchemaError(
            f"decisions[{index}]: action must be one of {sorted(VALID_ACTIONS)}, got {action!r}"
        )

    return Decision(
        item_id=item_id,
        action=action,
        store_id=d.get("store_id"),
        new_store_name=d.get("new_store_name"),
        metadata=d.get("metadata") or {},
        extra_aliases=list(d.get("extra_aliases") or []),
        note=d.get("note"),
    )
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/unit/review/test_batch_schema.py -v`
Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add src/lessley_deals/review/batch_schema.py tests/unit/review/test_batch_schema.py
git commit -m "feat(review): add decisions.json schema parser"
```

---

## Task 3: Schema validation — per-action constraints

**Files:**
- Modify: `src/lessley_deals/review/batch_schema.py` (add `_validate_action_shape`)
- Modify: `tests/unit/review/test_batch_schema.py` (add failure tests)

- [ ] **Step 1: Write the failing tests (append to existing test file)**

Append to `tests/unit/review/test_batch_schema.py`:

```python
def test_approve_requires_store_id(tmp_path: Path):
    payload = {
        "version": 1,
        "created_at": "now",
        "reviewed_by": "agent",
        "decisions": [{"item_id": "a", "action": "approve"}],
    }
    with pytest.raises(SchemaError, match="store_id"):
        parse_decisions(_write(tmp_path, payload))


def test_create_new_requires_name(tmp_path: Path):
    payload = {
        "version": 1,
        "created_at": "now",
        "reviewed_by": "agent",
        "decisions": [{"item_id": "a", "action": "create_new"}],
    }
    with pytest.raises(SchemaError, match="new_store_name"):
        parse_decisions(_write(tmp_path, payload))


def test_create_new_forbids_store_id(tmp_path: Path):
    payload = {
        "version": 1,
        "created_at": "now",
        "reviewed_by": "agent",
        "decisions": [
            {
                "item_id": "a",
                "action": "create_new",
                "new_store_name": "X",
                "store_id": "should-not-be-here",
            }
        ],
    }
    with pytest.raises(SchemaError, match="store_id"):
        parse_decisions(_write(tmp_path, payload))


def test_discard_forbids_extras(tmp_path: Path):
    payload = {
        "version": 1,
        "created_at": "now",
        "reviewed_by": "agent",
        "decisions": [
            {"item_id": "a", "action": "discard", "extra_aliases": ["x"]}
        ],
    }
    with pytest.raises(SchemaError, match="extra_aliases"):
        parse_decisions(_write(tmp_path, payload))


def test_skip_forbids_store_id(tmp_path: Path):
    payload = {
        "version": 1,
        "created_at": "now",
        "reviewed_by": "agent",
        "decisions": [
            {"item_id": "a", "action": "skip", "store_id": "x"}
        ],
    }
    with pytest.raises(SchemaError, match="store_id"):
        parse_decisions(_write(tmp_path, payload))


def test_unsupported_version_raises(tmp_path: Path):
    payload = {
        "version": 99,
        "created_at": "now",
        "reviewed_by": "agent",
        "decisions": [],
    }
    with pytest.raises(SchemaError, match="Unsupported version"):
        parse_decisions(_write(tmp_path, payload))


def test_invalid_action_raises(tmp_path: Path):
    payload = {
        "version": 1,
        "created_at": "now",
        "reviewed_by": "agent",
        "decisions": [{"item_id": "a", "action": "delete"}],
    }
    with pytest.raises(SchemaError, match="action must be one of"):
        parse_decisions(_write(tmp_path, payload))


def test_extra_alias_must_be_non_empty_string(tmp_path: Path):
    payload = {
        "version": 1,
        "created_at": "now",
        "reviewed_by": "agent",
        "decisions": [
            {
                "item_id": "a",
                "action": "approve",
                "store_id": "s",
                "extra_aliases": ["", "ok"],
            }
        ],
    }
    with pytest.raises(SchemaError, match="extra_aliases"):
        parse_decisions(_write(tmp_path, payload))
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/unit/review/test_batch_schema.py -v`
Expected: 8 new tests FAIL (validation not yet enforced).

- [ ] **Step 3: Add `_validate_action_shape` function and call it from `_parse_decision`**

Edit `src/lessley_deals/review/batch_schema.py`. Replace `_parse_decision` with this version (validation at end):

```python
def _parse_decision(index: int, d: Any) -> Decision:
    if not isinstance(d, dict):
        raise SchemaError(f"decisions[{index}] must be an object")

    item_id = d.get("item_id")
    if not isinstance(item_id, str) or not item_id:
        raise SchemaError(f"decisions[{index}]: item_id required (non-empty string)")

    action = d.get("action")
    if action not in VALID_ACTIONS:
        raise SchemaError(
            f"decisions[{index}]: action must be one of {sorted(VALID_ACTIONS)}, got {action!r}"
        )

    decision = Decision(
        item_id=item_id,
        action=action,
        store_id=d.get("store_id"),
        new_store_name=d.get("new_store_name"),
        metadata=d.get("metadata") or {},
        extra_aliases=list(d.get("extra_aliases") or []),
        note=d.get("note"),
    )
    _validate_action_shape(index, decision)
    return decision


def _validate_action_shape(index: int, d: Decision) -> None:
    prefix = f"decisions[{index}]"

    if d.action == "approve":
        if not d.store_id:
            raise SchemaError(f"{prefix}: 'approve' requires store_id")
        if d.new_store_name is not None:
            raise SchemaError(f"{prefix}: 'approve' forbids new_store_name")
    elif d.action == "create_new":
        if not d.new_store_name:
            raise SchemaError(f"{prefix}: 'create_new' requires new_store_name")
        if d.store_id is not None:
            raise SchemaError(f"{prefix}: 'create_new' forbids store_id")
    elif d.action in ("discard", "skip"):
        if d.store_id is not None:
            raise SchemaError(f"{prefix}: '{d.action}' forbids store_id")
        if d.new_store_name is not None:
            raise SchemaError(f"{prefix}: '{d.action}' forbids new_store_name")
        if d.extra_aliases:
            raise SchemaError(f"{prefix}: '{d.action}' forbids extra_aliases")
        if d.metadata:
            raise SchemaError(f"{prefix}: '{d.action}' forbids metadata")

    for i, alias in enumerate(d.extra_aliases):
        if not isinstance(alias, str) or not alias.strip():
            raise SchemaError(f"{prefix}: extra_aliases[{i}] must be non-empty string")
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/unit/review/test_batch_schema.py -v`
Expected: PASS, 11 tests total.

- [ ] **Step 5: Commit**

```bash
git add src/lessley_deals/review/batch_schema.py tests/unit/review/test_batch_schema.py
git commit -m "feat(review): enforce per-action shape rules in decisions schema"
```

---

## Task 4: `BatchApplier.__init__` + applies one `approve` decision

**Files:**
- Modify: `src/lessley_deals/review/batch_apply.py`
- Modify: `tests/unit/review/test_batch_apply.py`

Reuses `ReviewActions.approve_existing(item, store_id, store_name, reviewed_by, note)` from [`src/lessley_deals/review/actions.py:112-160`](../../src/lessley_deals/review/actions.py#L112-L160).

- [ ] **Step 1: Write the failing test (append to test file)**

Append to `tests/unit/review/test_batch_apply.py`:

```python
import json
from pathlib import Path

import pytest

from lessley_deals.domain.enums import AliasSource, ReviewStatus
from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository
from lessley_deals.review.actions import ReviewActions
from lessley_deals.review.batch_apply import BatchApplier


def _seed_pending_item(reviews_path: Path, *, item_id: str, store_id: str, store_name: str) -> None:
    """Write one pending review item targeting a candidate store."""
    payload = [
        {
            "id": item_id,
            "raw_id": "raw-1",
            "input_name": "test input",
            "input_name_forms": {"normalized": "test input", "compact": "testinput", "tokens": ["input", "test"]},
            "verdict": {
                "record_id": "rec-1",
                "input_name": "test input",
                "decision": "review",
                "candidates": [
                    {"store_id": store_id, "store_name": store_name, "confidence": 0.8, "stage": "compact_form", "matched_alias": store_name}
                ],
                "explanation": {"stages_run": [], "reason": "", "stage_matched": "compact_form", "details": {}},
                "best": {"store_id": store_id, "store_name": store_name, "confidence": 0.8, "stage": "compact_form", "matched_alias": store_name},
            },
            "created_at": "2026-04-19T12:00:00+00:00",
            "raw_input_name": "Test Input",
            "status": "pending",
            "decision": None,
            "reviewed_at": None,
        }
    ]
    reviews_path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_store(stores_path: Path, *, store_id: str, name: str) -> None:
    payload = [
        {
            "id": store_id,
            "name": name,
            "name_forms": {"normalized": name.lower(), "compact": name.lower().replace(" ", ""), "tokens": [name.lower()]},
            "metadata": {},
            "created_at": "2026-04-19T12:00:00+00:00",
            "updated_at": "2026-04-19T12:00:00+00:00",
        }
    ]
    stores_path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def repos(tmp_path: Path):
    """Fresh JSON repos in a tmp dir, plus an applier wired to them."""
    reviews_path = tmp_path / "store_match_review.json"
    stores_path = tmp_path / "stores.json"
    aliases_path = tmp_path / "store_aliases.json"
    deals_path = tmp_path / "deals.json"

    for p in (reviews_path, stores_path, aliases_path, deals_path):
        p.write_text("[]", encoding="utf-8")

    review_repo = ReviewJsonRepository(reviews_path)
    store_repo = CanonicalStoreJsonRepository(stores_path)
    alias_repo = AliasJsonRepository(aliases_path)
    deal_repo = DealJsonRepository(deals_path)
    actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)
    applier = BatchApplier(review_repo, store_repo, alias_repo, deal_repo, actions)
    return {
        "reviews_path": reviews_path,
        "stores_path": stores_path,
        "aliases_path": aliases_path,
        "deals_path": deals_path,
        "review_repo": review_repo,
        "store_repo": store_repo,
        "alias_repo": alias_repo,
        "deal_repo": deal_repo,
        "actions": actions,
        "applier": applier,
    }


def test_apply_approve_marks_status_and_creates_alias(tmp_path: Path, repos):
    _seed_store(repos["stores_path"], store_id="store-1", name="My Store")
    _seed_pending_item(repos["reviews_path"], item_id="item-1", store_id="store-1", store_name="My Store")

    decisions = {
        "version": 1,
        "created_at": "2026-04-19T12:00:00+00:00",
        "reviewed_by": "agent",
        "decisions": [
            {"item_id": "item-1", "action": "approve", "store_id": "store-1", "note": "looks right"}
        ],
    }
    decisions_path = tmp_path / "decisions.json"
    decisions_path.write_text(json.dumps(decisions), encoding="utf-8")

    result = repos["applier"].apply(decisions_path)

    assert result.approved == 1
    assert result.errors == []
    item = repos["review_repo"].get_by_id("item-1")
    assert item is not None and item.status == ReviewStatus.APPROVED

    aliases = repos["alias_repo"].get_by_store("store-1")
    assert len(aliases) == 1
    # Existing approve_existing path uses AliasSource.REVIEW for the canonical input alias
    assert aliases[0].source == AliasSource.REVIEW
```

- [ ] **Step 2: Run test, verify it fails**

Run: `pytest tests/unit/review/test_batch_apply.py::test_apply_approve_marks_status_and_creates_alias -v`
Expected: FAIL — `BatchApplier` has no `apply` method (or wrong constructor).

- [ ] **Step 3: Implement `BatchApplier` with approve path only**

Replace contents of `src/lessley_deals/review/batch_apply.py` with:

```python
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository
from lessley_deals.review.actions import ReviewActions
from lessley_deals.review.batch_schema import Decision, parse_decisions

logger = logging.getLogger(__name__)


@dataclass
class BatchError:
    item_id: str
    reason: str


@dataclass
class BatchResult:
    approved: int = 0
    created: int = 0
    discarded: int = 0
    skipped: int = 0
    aliases_added: int = 0
    errors: list[BatchError] = field(default_factory=list)


class BatchApplier:
    def __init__(
        self,
        review_repo: ReviewJsonRepository,
        store_repo: CanonicalStoreJsonRepository,
        alias_repo: AliasJsonRepository,
        deal_repo: DealJsonRepository,
        actions: ReviewActions,
    ) -> None:
        self._reviews = review_repo
        self._stores = store_repo
        self._aliases = alias_repo
        self._deals = deal_repo
        self._actions = actions

    def apply(self, decisions_path: Path, *, dry_run: bool = False) -> BatchResult:
        decisions_file = parse_decisions(decisions_path)
        result = BatchResult()
        for d in decisions_file.decisions:
            self._apply_one(d, decisions_file.reviewed_by, result, dry_run=dry_run)
        return result

    def _apply_one(
        self,
        d: Decision,
        reviewed_by: str,
        result: BatchResult,
        *,
        dry_run: bool,
    ) -> None:
        item = self._reviews.get_by_id(d.item_id)
        if item is None:
            result.errors.append(BatchError(d.item_id, "item_id not found in review queue"))
            return
        if item.status.value != "pending":
            result.errors.append(
                BatchError(d.item_id, f"item is not pending (status={item.status.value})")
            )
            return

        if d.action == "approve":
            assert d.store_id is not None  # guaranteed by schema
            store = self._stores.get_by_id(d.store_id)
            if store is None:
                result.errors.append(BatchError(d.item_id, f"store_id {d.store_id} not found"))
                return
            if not dry_run:
                self._actions.approve_existing(
                    item=item,
                    store_id=d.store_id,
                    store_name=store.name,
                    reviewed_by=reviewed_by,
                    note=d.note,
                )
            result.approved += 1
        else:
            # Other actions implemented in later tasks.
            result.errors.append(BatchError(d.item_id, f"action {d.action!r} not yet implemented"))
```

- [ ] **Step 4: Run test, verify it passes**

Run: `pytest tests/unit/review/test_batch_apply.py -v`
Expected: PASS — 3 tests (the 2 dataclass tests + the new approve test).

- [ ] **Step 5: Commit**

```bash
git add src/lessley_deals/review/batch_apply.py tests/unit/review/test_batch_apply.py
git commit -m "feat(review): BatchApplier handles approve action via ReviewActions"
```

---

## Task 5: `create_new`, `discard`, `skip` actions

**Files:**
- Modify: `src/lessley_deals/review/batch_apply.py` (extend `_apply_one`)
- Modify: `tests/unit/review/test_batch_apply.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/review/test_batch_apply.py`:

```python
def test_apply_create_new_creates_store_and_alias(tmp_path: Path, repos):
    _seed_pending_item(repos["reviews_path"], item_id="item-2", store_id="ignored", store_name="ignored")
    decisions = {
        "version": 1,
        "created_at": "2026-04-19T12:00:00+00:00",
        "reviewed_by": "agent",
        "decisions": [
            {
                "item_id": "item-2",
                "action": "create_new",
                "new_store_name": "Brand New Store",
                "metadata": {"image_urls": []},
            }
        ],
    }
    decisions_path = tmp_path / "decisions.json"
    decisions_path.write_text(json.dumps(decisions), encoding="utf-8")

    result = repos["applier"].apply(decisions_path)

    assert result.created == 1
    assert result.errors == []
    stores = repos["store_repo"].get_all()
    assert any(s.name == "Brand New Store" for s in stores)
    new_store = next(s for s in stores if s.name == "Brand New Store")
    assert len(repos["alias_repo"].get_by_store(new_store.id)) == 1
    item = repos["review_repo"].get_by_id("item-2")
    assert item.status == ReviewStatus.CREATED


def test_apply_discard_marks_discarded(tmp_path: Path, repos):
    _seed_pending_item(repos["reviews_path"], item_id="item-3", store_id="x", store_name="x")
    decisions = {
        "version": 1,
        "created_at": "2026-04-19T12:00:00+00:00",
        "reviewed_by": "agent",
        "decisions": [{"item_id": "item-3", "action": "discard", "note": "spam"}],
    }
    decisions_path = tmp_path / "decisions.json"
    decisions_path.write_text(json.dumps(decisions), encoding="utf-8")

    result = repos["applier"].apply(decisions_path)
    assert result.discarded == 1
    assert repos["review_repo"].get_by_id("item-3").status == ReviewStatus.DISCARDED


def test_apply_skip_marks_skipped(tmp_path: Path, repos):
    _seed_pending_item(repos["reviews_path"], item_id="item-4", store_id="x", store_name="x")
    decisions = {
        "version": 1,
        "created_at": "2026-04-19T12:00:00+00:00",
        "reviewed_by": "agent",
        "decisions": [{"item_id": "item-4", "action": "skip"}],
    }
    decisions_path = tmp_path / "decisions.json"
    decisions_path.write_text(json.dumps(decisions), encoding="utf-8")

    result = repos["applier"].apply(decisions_path)
    assert result.skipped == 1
    assert repos["review_repo"].get_by_id("item-4").status == ReviewStatus.SKIPPED
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/unit/review/test_batch_apply.py -v`
Expected: 3 new tests FAIL (`action ... not yet implemented`).

- [ ] **Step 3: Extend `_apply_one`**

In `src/lessley_deals/review/batch_apply.py`, replace the `else` branch in `_apply_one` with:

```python
        elif d.action == "create_new":
            assert d.new_store_name is not None
            if not dry_run:
                self._actions.create_new(
                    item=item,
                    store_name=d.new_store_name,
                    reviewed_by=reviewed_by,
                    note=d.note,
                )
            result.created += 1
        elif d.action == "discard":
            if not dry_run:
                self._actions.discard(item=item, reviewed_by=reviewed_by, note=d.note)
            result.discarded += 1
        elif d.action == "skip":
            if not dry_run:
                self._actions.skip(item=item)
            result.skipped += 1
        else:
            result.errors.append(BatchError(d.item_id, f"unknown action {d.action!r}"))
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/unit/review/test_batch_apply.py -v`
Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git add src/lessley_deals/review/batch_apply.py tests/unit/review/test_batch_apply.py
git commit -m "feat(review): BatchApplier handles create_new, discard, skip"
```

---

## Task 6: Save `extra_aliases` after approve / create_new

**Files:**
- Modify: `src/lessley_deals/review/batch_apply.py`
- Modify: `tests/unit/review/test_batch_apply.py`

`AliasJsonRepository.find_by_alias(alias)` ([`src/lessley_deals/persistence/repositories/aliases.py:17-22`](../../src/lessley_deals/persistence/repositories/aliases.py#L17-L22)) matches on the **normalized** form, so we use it for both dedup and conflict detection. New aliases are persisted with `source=AliasSource.MANUAL` (per spec).

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/review/test_batch_apply.py`:

```python
def test_extra_aliases_saved_for_approve(tmp_path: Path, repos):
    _seed_store(repos["stores_path"], store_id="store-x", name="Store X")
    _seed_pending_item(repos["reviews_path"], item_id="item-5", store_id="store-x", store_name="Store X")
    decisions = {
        "version": 1,
        "created_at": "2026-04-19T12:00:00+00:00",
        "reviewed_by": "agent",
        "decisions": [
            {
                "item_id": "item-5",
                "action": "approve",
                "store_id": "store-x",
                "extra_aliases": ["store ex", "store-x.com", "סטור איקס"],
            }
        ],
    }
    decisions_path = tmp_path / "decisions.json"
    decisions_path.write_text(json.dumps(decisions), encoding="utf-8")

    result = repos["applier"].apply(decisions_path)

    assert result.approved == 1
    assert result.aliases_added == 3
    aliases = repos["alias_repo"].get_by_store("store-x")
    # 1 from approve_existing (canonical input) + 3 extras
    assert len(aliases) == 4
    extra = [a for a in aliases if a.source == AliasSource.MANUAL]
    assert len(extra) == 3
    assert {a.alias for a in extra} == {"store ex", "store-x.com", "סטור איקס"}


def test_extra_alias_dedup_to_same_store_silent(tmp_path: Path, repos):
    _seed_store(repos["stores_path"], store_id="store-y", name="Store Y")
    # Pre-seed alias_repo with an alias for "duplicate me" -> store-y
    from datetime import datetime, timezone

    from lessley_deals.domain.models import StoreAlias
    from lessley_deals.review.actions import build_name_forms
    repos["alias_repo"].save(
        StoreAlias(
            id="pre-existing",
            store_id="store-y",
            alias="duplicate me",
            alias_forms=build_name_forms("duplicate me"),
            source=AliasSource.MANUAL,
            created_at=datetime.now(timezone.utc),
        )
    )
    _seed_pending_item(repos["reviews_path"], item_id="item-6", store_id="store-y", store_name="Store Y")

    decisions = {
        "version": 1,
        "created_at": "2026-04-19T12:00:00+00:00",
        "reviewed_by": "agent",
        "decisions": [
            {
                "item_id": "item-6",
                "action": "approve",
                "store_id": "store-y",
                "extra_aliases": ["duplicate me", "fresh one"],
            }
        ],
    }
    decisions_path = tmp_path / "decisions.json"
    decisions_path.write_text(json.dumps(decisions), encoding="utf-8")

    result = repos["applier"].apply(decisions_path)

    assert result.approved == 1
    assert result.errors == []
    assert result.aliases_added == 1  # only "fresh one" newly added
    saved = [a.alias for a in repos["alias_repo"].get_by_store("store-y")]
    # pre-existing + canonical input alias + "fresh one"
    assert "duplicate me" in saved
    assert "fresh one" in saved
    # Ensure no duplicate row for "duplicate me"
    assert sum(1 for a in saved if a == "duplicate me") == 1


def test_extra_alias_conflict_with_other_store_recorded(tmp_path: Path, repos):
    # Two stores; alias pre-mapped to store-a; decision tries to attach it to store-b
    _seed_store(repos["stores_path"], store_id="store-a", name="A")
    # Append a second store
    import json as _json
    data = _json.loads(repos["stores_path"].read_text(encoding="utf-8"))
    data.append(
        {
            "id": "store-b",
            "name": "B",
            "name_forms": {"normalized": "b", "compact": "b", "tokens": ["b"]},
            "metadata": {},
            "created_at": "2026-04-19T12:00:00+00:00",
            "updated_at": "2026-04-19T12:00:00+00:00",
        }
    )
    repos["stores_path"].write_text(_json.dumps(data), encoding="utf-8")

    from datetime import datetime, timezone

    from lessley_deals.domain.models import StoreAlias
    from lessley_deals.review.actions import build_name_forms
    repos["alias_repo"].save(
        StoreAlias(
            id="conflict-existing",
            store_id="store-a",
            alias="contested",
            alias_forms=build_name_forms("contested"),
            source=AliasSource.MANUAL,
            created_at=datetime.now(timezone.utc),
        )
    )
    _seed_pending_item(repos["reviews_path"], item_id="item-7", store_id="store-b", store_name="B")

    decisions = {
        "version": 1,
        "created_at": "2026-04-19T12:00:00+00:00",
        "reviewed_by": "agent",
        "decisions": [
            {
                "item_id": "item-7",
                "action": "approve",
                "store_id": "store-b",
                "extra_aliases": ["contested", "ok-extra"],
            }
        ],
    }
    decisions_path = tmp_path / "decisions.json"
    decisions_path.write_text(json.dumps(decisions), encoding="utf-8")

    result = repos["applier"].apply(decisions_path)

    # Approve still happened; only the contested alias errored, the other extra was added.
    assert result.approved == 1
    assert result.aliases_added == 1
    assert len(result.errors) == 1
    assert result.errors[0].item_id == "item-7"
    assert "contested" in result.errors[0].reason
    saved_for_b = [a.alias for a in repos["alias_repo"].get_by_store("store-b")]
    assert "contested" not in saved_for_b
    assert "ok-extra" in saved_for_b
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/unit/review/test_batch_apply.py -v`
Expected: 3 new tests FAIL (extras not yet saved).

- [ ] **Step 3: Implement extras handling**

Edit `src/lessley_deals/review/batch_apply.py`. Add imports at top:

```python
from datetime import datetime, timezone

from lessley_deals.domain.enums import AliasSource
from lessley_deals.domain.models import StoreAlias
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.review.actions import build_name_forms
```

Then update `_apply_one` so that after a successful `approve` or `create_new`, extras are saved. Replace the approve / create_new branches and add a helper:

```python
        if d.action == "approve":
            assert d.store_id is not None
            store = self._stores.get_by_id(d.store_id)
            if store is None:
                result.errors.append(BatchError(d.item_id, f"store_id {d.store_id} not found"))
                return
            if not dry_run:
                self._actions.approve_existing(
                    item=item,
                    store_id=d.store_id,
                    store_name=store.name,
                    reviewed_by=reviewed_by,
                    note=d.note,
                )
            result.approved += 1
            self._save_extras(d.item_id, d.store_id, d.extra_aliases, result, dry_run=dry_run)
        elif d.action == "create_new":
            assert d.new_store_name is not None
            new_store = None
            if not dry_run:
                item_after = self._actions.create_new(
                    item=item,
                    store_name=d.new_store_name,
                    reviewed_by=reviewed_by,
                    note=d.note,
                )
                # Look up the new store_id from the decision recorded on the item
                assert item_after.decision is not None
                new_store_id = item_after.decision.store_id
                assert new_store_id is not None
                self._save_extras(d.item_id, new_store_id, d.extra_aliases, result, dry_run=dry_run)
            result.created += 1
```

Add helper at the bottom of the class:

```python
    def _save_extras(
        self,
        item_id: str,
        store_id: str,
        extras: list[str],
        result: BatchResult,
        *,
        dry_run: bool,
    ) -> None:
        if dry_run:
            # Count those that would be added (skip dups, skip conflicts)
            for alias_text in extras:
                existing = self._aliases.find_by_alias(alias_text)
                if existing is None:
                    result.aliases_added += 1
                elif existing.store_id != store_id:
                    result.errors.append(
                        BatchError(item_id, f"alias {alias_text!r} maps to different store {existing.store_id}")
                    )
            return

        now = datetime.now(timezone.utc)
        for alias_text in extras:
            existing = self._aliases.find_by_alias(alias_text)
            if existing is not None:
                if existing.store_id == store_id:
                    continue  # silent dedup
                result.errors.append(
                    BatchError(item_id, f"alias {alias_text!r} maps to different store {existing.store_id}")
                )
                continue
            alias = StoreAlias(
                id=generate_id(),
                store_id=store_id,
                alias=alias_text,
                alias_forms=build_name_forms(alias_text),
                source=AliasSource.MANUAL,
                created_at=now,
            )
            self._aliases.save(alias)
            result.aliases_added += 1
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/unit/review/test_batch_apply.py -v`
Expected: PASS, 9 tests.

- [ ] **Step 5: Commit**

```bash
git add src/lessley_deals/review/batch_apply.py tests/unit/review/test_batch_apply.py
git commit -m "feat(review): persist extra_aliases with dedup and conflict detection"
```

---

## Task 7: `dry_run` mode + non-pending guard tests

**Files:**
- Modify: `tests/unit/review/test_batch_apply.py`

The dry_run code path is already implemented in Task 6. This task locks behavior with tests and adds the non-pending guard test.

- [ ] **Step 1: Write the tests**

Append to `tests/unit/review/test_batch_apply.py`:

```python
def test_dry_run_makes_no_writes(tmp_path: Path, repos):
    _seed_store(repos["stores_path"], store_id="store-d", name="Dry Store")
    _seed_pending_item(repos["reviews_path"], item_id="item-8", store_id="store-d", store_name="Dry Store")

    decisions = {
        "version": 1,
        "created_at": "2026-04-19T12:00:00+00:00",
        "reviewed_by": "agent",
        "decisions": [
            {
                "item_id": "item-8",
                "action": "approve",
                "store_id": "store-d",
                "extra_aliases": ["dry alt"],
            }
        ],
    }
    decisions_path = tmp_path / "decisions.json"
    decisions_path.write_text(json.dumps(decisions), encoding="utf-8")

    result = repos["applier"].apply(decisions_path, dry_run=True)

    assert result.approved == 1
    assert result.aliases_added == 1
    # Repos unchanged
    assert repos["review_repo"].get_by_id("item-8").status == ReviewStatus.PENDING
    assert repos["alias_repo"].get_all() == []


def test_item_not_pending_records_error(tmp_path: Path, repos):
    _seed_store(repos["stores_path"], store_id="store-z", name="Z")
    # Seed an item that is already approved
    payload = [
        {
            "id": "item-9",
            "raw_id": "raw-1",
            "input_name": "x",
            "input_name_forms": {"normalized": "x", "compact": "x", "tokens": []},
            "verdict": {
                "record_id": "rec-1",
                "input_name": "x",
                "decision": "review",
                "candidates": [],
                "explanation": {"stages_run": [], "reason": "", "stage_matched": "", "details": {}},
                "best": None,
            },
            "created_at": "2026-04-19T12:00:00+00:00",
            "raw_input_name": "X",
            "status": "approved",
            "decision": None,
            "reviewed_at": "2026-04-19T12:00:00+00:00",
        }
    ]
    repos["reviews_path"].write_text(json.dumps(payload), encoding="utf-8")

    decisions = {
        "version": 1,
        "created_at": "2026-04-19T12:00:00+00:00",
        "reviewed_by": "agent",
        "decisions": [{"item_id": "item-9", "action": "approve", "store_id": "store-z"}],
    }
    decisions_path = tmp_path / "decisions.json"
    decisions_path.write_text(json.dumps(decisions), encoding="utf-8")

    result = repos["applier"].apply(decisions_path)
    assert result.approved == 0
    assert len(result.errors) == 1
    assert "not pending" in result.errors[0].reason


def test_unknown_item_id_records_error(tmp_path: Path, repos):
    _seed_store(repos["stores_path"], store_id="store-q", name="Q")
    decisions = {
        "version": 1,
        "created_at": "2026-04-19T12:00:00+00:00",
        "reviewed_by": "agent",
        "decisions": [{"item_id": "ghost", "action": "approve", "store_id": "store-q"}],
    }
    decisions_path = tmp_path / "decisions.json"
    decisions_path.write_text(json.dumps(decisions), encoding="utf-8")

    result = repos["applier"].apply(decisions_path)
    assert result.approved == 0
    assert len(result.errors) == 1
    assert "not found" in result.errors[0].reason
```

- [ ] **Step 2: Run tests, verify they pass**

Run: `pytest tests/unit/review/test_batch_apply.py -v`
Expected: PASS, 12 tests.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/review/test_batch_apply.py
git commit -m "test(review): cover dry_run and non-pending / unknown item id paths"
```

---

## Task 8: Wire `review-apply-batch` Typer subcommand

**Files:**
- Modify: `src/lessley_deals/cli/main.py` (add new command at end of file)

The CLI uses Typer (not Click) with flat hyphen-separated names — see [`src/lessley_deals/cli/main.py:54`](../../src/lessley_deals/cli/main.py#L54) (`app = typer.Typer(...)`) and existing commands `review-stats`, `discover-stores`, `rematch-reviews`. Repos are wired via `_make_repos(data_dir)` ([`src/lessley_deals/cli/main.py:62`](../../src/lessley_deals/cli/main.py#L62)).

- [ ] **Step 1: Inspect `_make_repos` to confirm attribute names**

Run: `grep -n "review_repo\|store_repo\|alias_repo\|deal_repo" src/lessley_deals/cli/main.py | head -20`
Expected: confirms the `SimpleNamespace` returned by `_make_repos` exposes `.review_repo`, `.store_repo`, `.alias_repo`, `.deal_repo`. If any are named differently, use the actual names in the command body below.

- [ ] **Step 2: Write a quick CLI smoke test**

Create `tests/unit/review/test_cli_apply_batch.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lessley_deals.cli.main import app


def test_review_apply_batch_dry_run_exits_zero(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "store_match_review.json").write_text("[]", encoding="utf-8")
    (data_dir / "stores.json").write_text("[]", encoding="utf-8")
    (data_dir / "store_aliases.json").write_text("[]", encoding="utf-8")
    (data_dir / "deals.json").write_text("[]", encoding="utf-8")

    decisions = {
        "version": 1,
        "created_at": "2026-04-19T12:00:00+00:00",
        "reviewed_by": "agent",
        "decisions": [],
    }
    decisions_path = tmp_path / "decisions.json"
    decisions_path.write_text(json.dumps(decisions), encoding="utf-8")

    monkeypatch.setenv("DEALS_STORAGE", "json")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["review-apply-batch", str(decisions_path), "--data-dir", str(data_dir), "--dry-run"],
    )
    assert result.exit_code == 0, result.stdout
    assert "approved=0" in result.stdout or "Approved: 0" in result.stdout


def test_review_apply_batch_invalid_schema_exits_two(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name in ("store_match_review.json", "stores.json", "store_aliases.json", "deals.json"):
        (data_dir / name).write_text("[]", encoding="utf-8")

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"version": 99, "decisions": []}), encoding="utf-8")

    monkeypatch.setenv("DEALS_STORAGE", "json")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["review-apply-batch", str(bad), "--data-dir", str(data_dir)],
    )
    assert result.exit_code == 2
```

- [ ] **Step 3: Run test, verify it fails**

Run: `pytest tests/unit/review/test_cli_apply_batch.py -v`
Expected: FAIL — command not registered.

- [ ] **Step 4: Add the Typer command**

Append to `src/lessley_deals/cli/main.py`:

```python
@app.command(name="review-apply-batch")
def review_apply_batch(
    decisions_file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Path to decisions.json"),
    data_dir: str = typer.Option("./data", "--data-dir", help="Data directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate + simulate, do not write"),
) -> None:
    """Apply a batch of pre-decided review actions from a JSON file."""
    from lessley_deals.review.actions import ReviewActions
    from lessley_deals.review.batch_apply import BatchApplier
    from lessley_deals.review.batch_schema import SchemaError

    repos = _make_repos(data_dir)
    actions = ReviewActions(
        review_repo=repos.review_repo,
        store_repo=repos.store_repo,
        alias_repo=repos.alias_repo,
        deal_repo=repos.deal_repo,
    )
    applier = BatchApplier(
        review_repo=repos.review_repo,
        store_repo=repos.store_repo,
        alias_repo=repos.alias_repo,
        deal_repo=repos.deal_repo,
        actions=actions,
    )

    try:
        result = applier.apply(decisions_file, dry_run=dry_run)
    except SchemaError as e:
        console.print(f"[red]Schema error:[/red] {e}")
        raise typer.Exit(code=2)
    except (OSError, ValueError) as e:
        console.print(f"[red]IO/parse error:[/red] {e}")
        raise typer.Exit(code=2)

    suffix = " (dry-run)" if dry_run else ""
    console.print(
        f"approved={result.approved} created={result.created} "
        f"discarded={result.discarded} skipped={result.skipped} "
        f"aliases_added={result.aliases_added} errors={len(result.errors)}{suffix}"
    )
    for err in result.errors:
        console.print(f"  [yellow]error[/yellow] item={err.item_id}: {err.reason}")

    if result.errors:
        raise typer.Exit(code=1)
```

- [ ] **Step 5: Run test, verify it passes**

Run: `pytest tests/unit/review/test_cli_apply_batch.py -v`
Expected: PASS, 2 tests.

- [ ] **Step 6: Run full review test suite + ruff + mypy**

```bash
pytest tests/unit/review/ -v
ruff check src/lessley_deals/review/ src/lessley_deals/cli/main.py tests/unit/review/
mypy src/lessley_deals/review/batch_apply.py src/lessley_deals/review/batch_schema.py
```
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add src/lessley_deals/cli/main.py tests/unit/review/test_cli_apply_batch.py
git commit -m "feat(cli): add 'deals review-apply-batch' Typer command"
```

---

## Task 9: Gitignore the agent scratch directory

**Files:**
- Modify: `.gitignore` (repo root)

- [ ] **Step 1: Check current contents**

Run: `cat lessley-deals/.gitignore | grep -E "^data" || echo "no data entries"`

- [ ] **Step 2: Add entry**

Append to `lessley-deals/.gitignore`:

```
# Transient scratch dir used by the store-match-reviewer subagent
data/.tmp/
```

- [ ] **Step 3: Verify git ignores the path**

```bash
mkdir -p lessley-deals/data/.tmp && touch lessley-deals/data/.tmp/probe.json
git -C lessley-deals status --short data/.tmp/probe.json
rm lessley-deals/data/.tmp/probe.json
```
Expected: empty output (path is ignored).

- [ ] **Step 4: Commit**

```bash
git add lessley-deals/.gitignore
git commit -m "chore: gitignore data/.tmp/ used by store-match-reviewer agent"
```

---

## Task 10: Author the subagent definition

**Files:**
- Create: `.claude/agents/store-match-reviewer.md` (in `lessley-deals/.claude/agents/`)

Note: the working tree already has `lessley-deals/.claude/` (untracked per `git status` at branch start). Place the file inside that directory.

- [ ] **Step 1: Confirm directory exists**

Run: `ls lessley-deals/.claude/agents/ 2>/dev/null || mkdir -p lessley-deals/.claude/agents`
Expected: directory exists.

- [ ] **Step 2: Write the subagent file**

Create `lessley-deals/.claude/agents/store-match-reviewer.md` with this exact content:

````markdown
---
name: store-match-reviewer
description: Process pending items in data/store_match_review.json. Auto-approves high-confidence matches, prompts user on ambiguous ones. For each approved/created store, proposes 3-5 alias variations (Hebrew/English/translit/typos) for the user to pick. Writes a decisions JSON and invokes `python -m deals review-apply-batch`. Use when user says "review matches", "process review queue", or invokes the agent directly.
tools: Read, Bash, Write, Grep
model: sonnet
---

# Store Match Reviewer

You process the human-review queue produced by the `lessley-deals` matching pipeline. Each invocation handles a bounded batch of pending items, decides what to do with each, optionally enriches with alias variations, then commits everything through one CLI call.

## Inputs (from caller)

- `batch_size` (default 20) — max pending items to process this run.
- `min_confidence` (optional, default none) — skip items whose `verdict.best.confidence` is below this cutoff (leaves them in pending status).
- `source_filter` (optional) — substring match on `raw_input_name`; only relevant when caller knows their source.

## Protocol

### 1. Read & filter the queue

```
Read data/store_match_review.json
Keep items with status == "pending"
Sort by created_at ascending
Apply min_confidence and source_filter if given
Slice the first `batch_size` items
```

If empty: report `"no pending items"` and stop.

### 2. Per-item decision

For each item:

- **Auto-approve rule** (no prompt): `verdict.best.confidence >= 0.85` AND exactly one candidate AND `verdict.best.stage != "token_overlap"`. Mark as `approve` with `store_id = verdict.best.store_id`, `note = "auto-approved conf=<value>"`.
- **Otherwise** show the user:
  - `input_name`, `raw_input_name`
  - candidate table: `# | store_name | confidence | stage | matched_alias`
  - prompt: `[a]pprove best  [N] approve candidate #N  [c <name>] create new store  [d <reason>] discard  [s] skip`
  - parse the response into a Decision object (validate inputs).

### 3. Alias enrichment (only after approve / create_new)

For the chosen store name, propose up to 5 alias variations:

1. Compact form (no spaces, no punctuation, lowercase).
2. Hebrew↔English transliteration (best effort).
3. Common typo: final-form letter swap (`ך/כ`, `ם/מ`, `ן/נ`, `ף/פ`, `ץ/צ`), missing geresh `'`, missing quote `"`.
4. Token-reordered variant for multi-word names.
5. The original `input_name` if it differs from the chosen store name.

Show the user the proposed list as a checklist. Let them edit/add/remove. Save the final list as `extra_aliases` on the decision.

Skip step 3 entirely for `discard` and `skip` decisions.

### 4. Write decisions.json

Output location: `data/.tmp/decisions.json` (gitignored). Schema:

```json
{
  "version": 1,
  "created_at": "<ISO 8601 UTC now>",
  "reviewed_by": "store-match-reviewer-agent",
  "decisions": [
    {"item_id": "...", "action": "approve|create_new|discard|skip", "...action-specific fields..."}
  ]
}
```

Action-specific fields:
- `approve`: requires `store_id`; optional `extra_aliases`, `note`.
- `create_new`: requires `new_store_name`; optional `metadata`, `extra_aliases`, `note`.
- `discard`: optional `note`. Forbids `store_id`, `new_store_name`, `extra_aliases`, `metadata`.
- `skip`: no extra fields.

### 5. Apply the batch

Run via Bash:

```
python -m deals review-apply-batch data/.tmp/decisions.json
```

Use `--dry-run` first if user asks for a preview, then re-run without `--dry-run` after they confirm.

### 6. Report results

Parse the CLI output. Report:
- `approved`, `created`, `discarded`, `skipped`, `aliases_added` counts.
- Any errors (per-item reason). For each errored `item_id`, show the input_name from the queue for context.

### 7. Failure handling

- Exit code `0`: full success → just report counts.
- Exit code `1`: partial success with per-decision errors → report counts AND list each errored item with its reason. Do NOT auto-retry.
- Exit code `2`: schema or IO failure → nothing was written; surface stderr verbatim and stop.

## Boundaries

- Do NOT modify `data/store_match_review.json`, `data/seed/stores.json`, or `data/seed/store_aliases.json` directly. Only the CLI writes to those.
- Do NOT call any tool outside `Read`, `Bash`, `Write`, `Grep`.
- Do NOT skip auto-approval criteria — single-candidate-and-not-token-overlap is mandatory; review-stage-only matches still need user eyes.
- Bash commands must be executed from the `lessley-deals/` directory (the package root).
````

- [ ] **Step 3: Confirm the agent appears in the agent list**

Open Claude Code in the repo and verify `Task` tool can list `store-match-reviewer`. (Manual; no automated check.)

- [ ] **Step 4: Commit**

```bash
git add lessley-deals/.claude/agents/store-match-reviewer.md
git commit -m "feat(agents): add store-match-reviewer Claude Code subagent"
```

---

## Task 11: End-to-end smoke test on real data slice

**Files:**
- None modified. Manual verification only.

- [ ] **Step 1: Snapshot the live review file**

```bash
cp lessley-deals/data/store_match_review.json /tmp/review-pre.json
```

- [ ] **Step 2: Build a tiny decisions file by hand against 1–3 real pending items**

Pick the first pending items from `lessley-deals/data/store_match_review.json` and craft a `decisions.json` with: 1 approve (using `verdict.best.store_id`), 1 skip, 1 discard. Save to `lessley-deals/data/.tmp/decisions.json`.

- [ ] **Step 3: Dry-run first**

```bash
cd lessley-deals && python -m deals review-apply-batch data/.tmp/decisions.json --dry-run
```
Expected: counts printed, exit 0, no file modifications.

- [ ] **Step 4: Verify nothing changed**

```bash
diff -q /tmp/review-pre.json lessley-deals/data/store_match_review.json
```
Expected: no differences.

- [ ] **Step 5: Real run**

```bash
cd lessley-deals && python -m deals review-apply-batch data/.tmp/decisions.json
```
Expected: counts printed, exit 0, status of the 3 items updated, alias added for the approved one.

- [ ] **Step 6: Decide whether to keep or revert**

If results look right, commit nothing — the data files are already updated. If they look wrong, restore: `cp /tmp/review-pre.json lessley-deals/data/store_match_review.json` and similarly for `store_aliases.json` (use `git restore` if it's tracked; for the data dir, restore by hand).

- [ ] **Step 7: Optional — dispatch the actual subagent on a small batch**

Open the repo in Claude Code, ask: "Use the store-match-reviewer agent on 3 items." Walk through the prompts; verify it writes `data/.tmp/decisions.json` and shells out to `review-apply-batch`.

---

## Self-Review Notes

- All spec requirements covered: subagent file (Task 10), schema parser (Tasks 2-3), `BatchApplier` w/ all 4 actions + extras + dedup/conflict + dry-run (Tasks 4-7), CLI w/ exit codes 0/1/2 (Task 8), gitignore (Task 9), end-to-end (Task 11).
- Type names consistent: `BatchApplier`, `BatchResult`, `BatchError`, `Decision`, `DecisionsFile`, `SchemaError`, `parse_decisions` — same across all tasks.
- No placeholders or TBDs.
- Note: spec mentions "rolled back" for alias conflicts; in implementation we never wrote the conflicting alias (so there's nothing to roll back) — the `approve_existing` itself completes, and the bad extra alias is recorded as an error and skipped. Other valid extras still go through. This matches "decision rolled back" for the alias-level decision, not the parent approve.
