# Store Match Reviewer Agent — Design

**Date:** 2026-04-19
**Status:** Draft
**Owner:** dor.habasov

## Goal

Automate processing of `data/store_match_review.json` (the human-review queue produced by `MatchPipeline`) through a Claude Code subagent that:

1. Reads pending review items in bounded batches.
2. Auto-approves high-confidence single-candidate matches; prompts the user on ambiguous ones.
3. For each approved or newly-created store, proposes 3–5 alternate aliases (Hebrew, English, transliteration, common typos), letting the user pick which ones to persist.
4. Commits all decisions through a single new Python CLI subcommand (`deals review apply-batch`) backed by the existing `ReviewActions` machinery.

## Non-goals

- Replacing the interactive TUI (`deals review`) — both can coexist.
- Auto-approving low-confidence matches without user confirmation.
- Generating aliases via runtime regex/heuristics outside the agent (the agent's LLM does the proposing; rule-based variants supplement it).
- Modifying the matching pipeline itself.

## Architecture

### Files touched / created

| Path | Action | Purpose |
|------|--------|---------|
| `.claude/agents/store-match-reviewer.md` | NEW | Subagent definition (prompt + frontmatter) |
| `src/lessley_deals/review/batch_apply.py` | NEW | `BatchApplier` class — applies decisions atomically |
| `src/lessley_deals/cli/main.py` | EDIT | Add `review apply-batch` Click subcommand |
| `tests/unit/review/test_batch_apply.py` | NEW | Unit tests for `BatchApplier` |
| `data/.tmp/decisions.json` | RUNTIME | Transient agent output, consumed by CLI |
| `.gitignore` | EDIT | Add `data/.tmp/` (transient agent scratch) |

Read-only inputs: `data/store_match_review.json`.
Write targets via existing repos: `data/seed/stores.json`, `data/seed/store_aliases.json`, deals storage, review status.

### Flow

```
User → Task tool → store-match-reviewer subagent
  ├─ Read store_match_review.json (filter status="pending", apply optional --source / --min-confidence)
  ├─ Pick first N (default 20)
  ├─ For each item:
  │    if best.confidence ≥ 0.85 AND single candidate AND stage != "token_overlap":
  │        decision = approve
  │    else:
  │        prompt user → [a]pprove / [c]reate-new / [d]iscard / [s]kip
  │    if approve | create_new:
  │        propose 3–5 extra aliases → user picks subset
  ├─ Write data/.tmp/decisions.json
  ├─ Bash: python -m deals review apply-batch data/.tmp/decisions.json
  └─ Report stdout (counts approved/created/aliases-saved/errors) to user
```

### Subagent (`.claude/agents/store-match-reviewer.md`)

**Frontmatter:**

```yaml
---
name: store-match-reviewer
description: Process pending items in data/store_match_review.json. Auto-approves high-confidence matches, prompts user on ambiguous ones. For each approved/created store, proposes 3-5 alias variations (Hebrew/English/translit/typos) for user to pick. Writes decisions and invokes `deals review apply-batch`. Use when user says "review matches", "process review queue", or invokes the agent directly.
tools: Read, Bash, Write, Grep
model: sonnet
---
```

**Body sections (numbered protocol):**

1. **Inputs** — `batch_size` (default 20), optional `source` filter (matches `raw_input_name` source if traceable), optional `min_confidence` cutoff for inclusion.
2. **Read & filter queue** — load JSON, keep `status == "pending"`, sort by `created_at`, slice first N.
3. **Auto-approve rule** — `verdict.best.confidence ≥ 0.85` AND exactly one candidate AND `stage != "token_overlap"` → mark `approve` with `store_id = verdict.best.store_id`. Otherwise prompt.
4. **Manual prompt template** — show:
   - `input_name` and `raw_input_name`
   - candidate table: `store_name | confidence | stage | matched_alias`
   - prompt: `[a]pprove [n]=N approve other candidate / [c]reate-new <name> / [d]iscard / [s]kip`
5. **Alias generation rules** — for the chosen store name, propose up to 5 variants:
   - Compact form (no spaces/punctuation)
   - Hebrew↔English transliteration (best effort)
   - Common typo (final-form letter swap, missing geresh `'`, missing quote `"`)
   - Token-reordered variant for multi-word names
   - The original `input_name` (always included if it differs from store name)
   - User can edit/add/remove before save.
6. **Output** — write `data/.tmp/decisions.json`, run `python -m deals review apply-batch data/.tmp/decisions.json` via Bash.
7. **Failure handling** — interpret CLI exit code:
   - `0` (full success): report counts to user.
   - `1` (partial success / per-decision errors): report counts AND list errored item_ids with reasons; do NOT retry automatically.
   - `2` (schema or IO failure): nothing was written; surface stderr verbatim and stop.

### Python: `BatchApplier`

```python
# src/lessley_deals/review/batch_apply.py

@dataclass(frozen=True)
class BatchResult:
    approved: int
    created: int
    discarded: int
    skipped: int
    aliases_added: int
    errors: list[BatchError]

@dataclass(frozen=True)
class BatchError:
    item_id: str
    reason: str

class BatchApplier:
    def __init__(self,
                 reviews: ReviewRepository,
                 stores: CanonicalStoreRepository,
                 aliases: AliasRepository,
                 deals: DealRepository,
                 actions: ReviewActions): ...

    def apply(self, decisions_path: Path, *, dry_run: bool = False) -> BatchResult:
        # 1. Load + validate decisions.json (schema check, unknown keys rejected)
        # 2. For each decision:
        #    - "approve":     actions.approve_existing(item, store_id)
        #    - "create_new":  actions.create_new(item, new_store_name, metadata)
        #    - "discard":     actions.discard(item)
        #    - "skip":        actions.skip(item)
        # 3. For each "approve"/"create_new": save extra_aliases (one StoreAlias each, source="manual")
        #    - dedup: if alias's compact form already maps to same store_id → skip silently
        #    - conflict: if it maps to a *different* store_id → record BatchError, do NOT save
        # 4. dry_run: validate + simulate, no writes; return BatchResult counts as if applied
        # 5. Return BatchResult
```

### CLI

```python
# src/lessley_deals/cli/main.py (under existing `review` group)

@review.command("apply-batch")
@click.argument("decisions_file", type=click.Path(exists=True, path_type=Path))
@click.option("--dry-run", is_flag=True, help="Validate + preview, do not write")
def apply_batch(decisions_file: Path, dry_run: bool):
    """Apply a batch of pre-decided review actions from a JSON file."""
    # Wire repos via existing factory; instantiate BatchApplier; print BatchResult summary
    # Exit 0 on full success; exit 1 if any BatchError; exit 2 on schema/IO failure
```

## Data Contract: `decisions.json`

```json
{
  "version": 1,
  "created_at": "2026-04-19T12:00:00+00:00",
  "reviewed_by": "store-match-reviewer-agent",
  "decisions": [
    {
      "item_id": "019d88a2c469_13d0361b63a33b68",
      "action": "approve",
      "store_id": "019d3538629b_c56afab5f29c117a",
      "extra_aliases": ["דוח בלקר", "doh balak'r", "דוחבלקר"],
      "note": "auto-approved conf=0.95"
    },
    {
      "item_id": "019d88a2c46a_ed78337943ce76cd",
      "action": "create_new",
      "new_store_name": "G-Bike",
      "metadata": {"image_urls": []},
      "extra_aliases": ["g bike", "ג'י בייק", "gbike"],
      "note": "user created"
    },
    {
      "item_id": "019d88a2c46b_xxx",
      "action": "discard",
      "note": "spam entry"
    }
  ]
}
```

### Validation rules

- `version == 1` (reject otherwise).
- `action ∈ {approve, create_new, discard, skip}`.
- `approve` requires `store_id`; `extra_aliases` optional list of non-empty strings.
- `create_new` requires `new_store_name`; forbids `store_id`; `metadata` optional dict; `extra_aliases` optional.
- `discard` / `skip` forbid `store_id`, `new_store_name`, `extra_aliases`, `metadata`.
- `item_id` must resolve to an existing review item with `status == "pending"`. Items in any other status → `BatchError`, decision rejected.
- Unknown top-level keys or per-decision keys → schema error (exit 2).

## Error handling

- **Per-decision errors** (alias conflict, item not pending, store_id not found): collected into `BatchResult.errors`. The errored decision is rolled back individually (review status not updated, alias not saved). Other decisions proceed.
- **Batch-level errors** (schema invalid, decisions file unreadable, repo IO failure): raise, exit 2, no writes.
- CLI prints summary table + error list, returns nonzero exit if any errors occurred.

## Testing strategy

`tests/unit/review/test_batch_apply.py`:

1. `test_apply_approve_marks_status_and_creates_alias` — single approve, verify status=approved, deal linked, one alias for `input_name` saved.
2. `test_apply_create_new_creates_store_and_aliases` — one create_new with 3 extra_aliases, verify store + 4 aliases (canonical input + 3 extras) saved with `source="manual"`.
3. `test_extra_alias_dedup_to_same_store_silent` — extra_alias compact form already maps to the chosen store_id → no error, no duplicate row.
4. `test_extra_alias_conflict_with_different_store_records_error` — extra_alias maps to a different store → `BatchError` recorded, decision rolled back, store/status unchanged.
5. `test_dry_run_no_writes` — apply with `dry_run=True` → BatchResult populated as if applied, repos confirmed unchanged.
6. `test_invalid_schema_raises` — missing `version` → ValueError; CLI exits 2.
7. `test_item_not_pending_records_error` — decision targets an item with `status="approved"` → BatchError, no mutation.

Subagent smoke test (manual): run agent on a 3-item slice of real `store_match_review.json`, mock Bash invocation, inspect generated `decisions.json` against schema.

## Open questions

None remaining — all clarified during brainstorming (subagent type=A, alias gen=B (LLM-proposed), autonomy=B (auto ≥0.85), scope=B (bounded batch), commit=B (batch JSON + CLI)).

## Out of scope / future

- Persisting agent-proposed but rejected aliases as negative training data for the matcher.
- A `--auto-yes` flag to also auto-pick suggested extra aliases (would void the human-in-the-loop check on alias quality).
- Rerun-safety beyond per-decision rollback (full transactional batch with abort-all-on-any-error).
