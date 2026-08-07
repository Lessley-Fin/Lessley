# Manual Review Subsystem

## Overview

The manual review subsystem provides a CLI-based human review workflow for uncertain store matches. When the matching pipeline produces a **REVIEW** verdict -- meaning the best candidate scored between 0.50 and 0.89 confidence -- the match is not automatically accepted or rejected. Instead, it enters a review queue where a human operator makes the final decision.

This is the human-in-the-loop component of the matching pipeline. It sits between the automated matcher and the canonical store database, ensuring that ambiguous matches are handled correctly while simultaneously training the system to handle similar cases automatically in the future.

---

## Review Queue (`queue.py`)

The `ReviewQueue` class manages the lifecycle of review items. Items are persisted in `store_match_review.json`.

### Core Components

- **ReviewQueue**: Loads, saves, filters, and iterates over review items. Provides methods to add new items from pipeline output, retrieve the next pending item, and update item status after a decision.
- **QueueFilter**: Supports filtering by status, source_id, and date range. Filters are combined conjunctively (all conditions must match).
- **QueueStats**: Aggregates counts across the queue:
  - `total` -- all items regardless of status
  - `pending` -- awaiting review
  - `approved` -- matched to an existing store
  - `created` -- resulted in a new store
  - `discarded` -- rejected as bad data
  - `skipped` -- deferred for later review

Items are sorted by `created_at` in ascending order (oldest first), enforcing a FIFO processing discipline. This prevents items from languishing indefinitely at the bottom of the queue.

---

## ReviewItem Structure

Each ReviewItem captures a full snapshot of the match state at the time the pipeline produced the REVIEW verdict.

### Fields

| Field | Description |
|---|---|
| `id` | Unique identifier for the review item |
| `source_id` | Identifier of the data source (e.g., `shufersal`, `rami_levy`) |
| `input_name` | Raw store name from the scraped data |
| `match_verdict` | Full `MatchVerdict` snapshot: candidates, scores, explanation |
| `status` | Current status (see below) |
| `decision` | `ReviewDecision` recorded when status changes from PENDING |
| `created_at` | Timestamp when the item entered the queue |
| `reviewed_at` | Timestamp when the decision was made |

### Status Transitions

```
PENDING --> APPROVED
PENDING --> CREATED
PENDING --> DISCARDED
PENDING --> SKIPPED
```

All items start as `PENDING`. A review decision moves the item to exactly one of the four terminal states. `SKIPPED` is a soft terminal state -- the item retains its `SKIPPED` status but will reappear in future review sessions.

### ReviewDecision

When a reviewer acts on an item, a `ReviewDecision` is recorded:

| Field | Description |
|---|---|
| `action` | One of APPROVE, CREATE_NEW, DISCARD, SKIP |
| `store_id` | The canonical store ID (for APPROVE) or newly created store ID (for CREATE_NEW) |
| `new_store_name` | The name for a newly created store (CREATE_NEW only) |
| `note` | Optional free-text note from the reviewer |
| `reviewed_by` | Identifier of the person who made the decision |

---

## Review Actions (`actions.py`)

Each action produces different side effects in the system.

### APPROVE

Accept the best candidate match. The input name refers to an existing canonical store.

- Links the deal to the existing canonical store
- Creates a `StoreAlias` with `source=REVIEW` mapping the input name to the store
- Future scrapes with the same input name will auto-match at Stage 1 (exact alias lookup), bypassing fuzzy matching entirely

### CREATE_NEW

The input name represents a genuinely new store not yet in the canonical database.

- Creates a new `CanonicalStore` entry
- Creates a `StoreAlias` with `source=REVIEW` mapping the input name to the new store
- Creates a `Deal` linked to the new store
- The new store is immediately available for matching in subsequent pipeline runs

### DISCARD

The input data is bad, malformed, or does not represent a real store match.

- Marks the item as discarded in the queue
- No alias is created
- No deal is created
- Raw data is preserved in the review queue file for audit purposes

### SKIP

The reviewer is unsure and wants to revisit this item later.

- Sets the item status to `SKIPPED`
- The item remains in the queue and will appear again in future review sessions
- No changes to the store database or alias table

### SET MCC

Tag a canonical store with its MCC categories. Unlike the four actions above
this is **not a decision** -- it does not resolve the review item or change its
status, it edits the store behind it and returns you to the same item so you can
still approve, link, create, discard or skip.

- Writes `metadata.mcc_codes` on the store as a ranked list of canonical
  category names, plus `mcc_confidence: "HIGH"` and `mcc_source: "review:<user>"`
  so a human decision is never overwritten silently by the LLM enricher
- Targets the item's best candidate store; when the item has no candidates it
  asks you to search for the store to tag
- Also runs automatically right after CREATE_NEW (a brand-new store has no
  categories yet). Turn that off with `deals review --no-mcc-on-create`

#### The category vocabulary

`metadata.mcc_codes` holds **category names** (`GROCERIES`, `RESTAURANT`,
`CLOTHES_&_ACCESSORIES`, …), not the 4-digit ISO 18245 numbers. The closed set of
46 names lives in `enrichment/mcc_catalog.py`; the same module keeps the
numeric-MCC → category mapping so older rows that stored raw numbers still read
back as categories.

At the `MCC:` prompt you can enter:

| Input | Meaning |
|---|---|
| `GROCERIES, RESTAURANT` | Category names, any casing or spacing |
| `22, 39` | Catalog numbers as printed by `?` |
| `5411, 5812` | 4-digit MCCs, resolved through the saved mapping |
| `?` | Print the numbered catalog |
| `s` | Ask the LLM to classify the store, then `y` to accept |
| *(empty)* | Cancel, leaving the store's categories untouched |

Entries are de-duplicated, kept in the order you typed them (the list is ranked
most-specific first) and truncated to three. If nothing you typed resolves to a
canonical category the store is left alone and the prompt repeats.

---

## Alias Learning (`learner.py`)

The `AliasLearner` is the feedback mechanism that makes the system smarter over time. Every APPROVE and CREATE_NEW decision feeds back into the alias database, so the same input name will match instantly on subsequent pipeline runs.

### Behavior by Action

- **On APPROVE**: Creates an alias where `alias = input_name`, `store_id = approved candidate's store_id`, `source = REVIEW`.
- **On CREATE_NEW**: Creates an alias where `alias = input_name`, `store_id = newly created store's id`, `source = REVIEW`.
- **On DISCARD / SKIP**: No alias is created.

### NameForms Computation

When an alias is created, the learner automatically computes `NameForms` for the alias. This includes normalized variants of the name, enabling the Stage 1 matcher to find the alias even when the input has minor formatting differences.

### The Feedback Loop

```
Pipeline run
  --> REVIEW verdict (confidence 0.50-0.89)
    --> Human reviews and approves
      --> Alias created (source=REVIEW)
        --> Next pipeline run: same name matches at Stage 1
```

Each review decision permanently improves future matching. Over time, the proportion of items reaching the review queue decreases as the alias database grows.

---

## CLI Workflow (`cli/review_session.py`)

### Commands

```
deals review              Start an interactive review session
deals review-stats        Show queue statistics
```

### Interactive Review Session

The session presents one item at a time using Rich formatting. For each item, the display shows:

- The raw input name and its normalized form
- Top candidates ranked by confidence score, including the match stage that produced each candidate
- The explanation trace detailing why each candidate matched
- Available actions with keyboard shortcuts

Example session output:

```
Review Queue: 5 items pending

--- Item 1 of 5 ---

Input Name (raw):        רמי לוי - שיווק השקמה
Input Name (normalized): רמי לוי שיווק השקמה

Candidates:
+------+-----------+------------+-------+
| Rank | Store     | Confidence | Stage |
+------+-----------+------------+-------+
|    1 | רמי לוי   |       0.82 |     2 |
|    2 | שופרסל    |       0.41 |     3 |
+------+-----------+------------+-------+

Explanation:
  Stage 2 fuzzy match: "רמי לוי" substring found in input.
  Token overlap score: 0.82

Actions:
  [a] Approve best match (רמי לוי)
  [l] Link to an existing store
  [c] Create new store
  [m] Set MCC categories
  [d] Discard
  [s] Skip
  [q] Quit session

>
```

### Options

- **Batch mode**: Process a fixed number of items then stop.
  ```
  deals review --batch 10
  ```
- **Filter by source**: Review only items from a specific data source.
  ```
  deals review --source shufersal
  ```
- **Skip the MCC prompt after CREATE_NEW**: leave new stores untagged.
  ```
  deals review --no-mcc-on-create
  ```

### Statistics

```
$ deals review-stats

Review Queue Statistics
-----------------------
Total:     42
Pending:   12
Approved:  18
Created:    5
Discarded:  4
Skipped:    3
```

---

## Display (`display.py`)

The display module uses Rich to render review items in the terminal.

### Candidate Table

Candidates are shown in a ranked table with color-coded confidence scores:

- **Green** (confidence >= 0.80): Strong match, likely correct
- **Yellow** (confidence >= 0.60): Moderate match, needs attention
- **Red** (confidence < 0.60): Weak match, probably wrong

### Additional Display Features

- Full explanation trace showing the reasoning behind each candidate's score
- Progress bar for batch sessions showing items completed vs. total
- Clear visual separation between items

---

## Review Workflow Example

A complete walkthrough of the review cycle, from pipeline output to automatic matching.

### Step 1: Run the Pipeline

The matching pipeline processes scraped deal data. Five items produce REVIEW verdicts (confidence between 0.50 and 0.89) and enter the review queue.

```
$ deals match --source shufersal

Matching results:
  Automatic matches:  23
  Review required:     5
  No match:            2
```

### Step 2: Start a Review Session

```
$ deals review
```

### Step 3: Review the First Item

The first item is displayed:

```
--- Item 1 of 5 ---

Input Name (raw):        רמי לוי - שיווק השקמה
Input Name (normalized): רמי לוי שיווק השקמה

Candidates:
+------+-----------+------------+-------+
| Rank | Store     | Confidence | Stage |
+------+-----------+------------+-------+
|    1 | רמי לוי   |       0.82 |     2 |
+------+-----------+------------+-------+

Explanation:
  Stage 2 fuzzy match: "רמי לוי" substring found in input.
  Token overlap score: 0.82 

Actions:
  [a] Approve best match (רמי לוי)
  [l] Link to an existing store
  [c] Create new store
  [m] Set MCC categories
  [d] Discard
  [s] Skip
  [q] Quit session

>
```

### Step 4: Approve the Match

The reviewer presses `a` to approve. The system:

1. Links the deal to the canonical store "רמי לוי"
2. Creates a `StoreAlias`: "רמי לוי - שיווק השקמה" --> "רמי לוי" (source=REVIEW)
3. Moves the item status from PENDING to APPROVED

### Step 5: Automatic Matching on Next Run

On the next pipeline run, when the scraper encounters "רמי לוי - שיווק השקמה" again, Stage 1 finds the alias immediately. No fuzzy matching needed, no review required.

```
$ deals match --source shufersal

Matching results:
  Automatic matches:  28   # includes the previously reviewed name
  Review required:     2
  No match:            0
```

---

## Best Practices

- **Review regularly.** Keep the queue small. A large backlog means the system is not learning from its uncertain matches, and the same ambiguous names keep hitting the review queue on every pipeline run.

- **Approve liberally for known stores.** If you recognize the store, approve it. Each approval adds an alias that prevents the same name from requiring review again. The alias database is the primary mechanism for improving match quality over time.

- **Create new stores only for genuinely new entities.** Do not create a new store if the input name is a variant of an existing store. Approve and let the alias system handle the variant. Creating duplicates fragments the data.

- **Discard spam and test data.** If the input is clearly not a real store name (test entries, malformed data, garbage strings), discard it. The raw data remains in the review file for audit but produces no side effects in the store database.

- **Skip when unsure.** Do not guess. If you cannot confidently determine whether the input matches an existing store or represents a new one, skip it. The item will reappear in a future session, possibly with more context from additional scraped data.
