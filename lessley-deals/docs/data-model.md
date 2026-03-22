# Lessley Deals -- Data Model

This document describes every model in the lessley-deals system: frozen
(immutable) dataclasses, mutable dataclasses, enums, JSON persistence files,
and the ID generation scheme.

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [ID Generation](#id-generation)
3. [Enums](#enums)
4. [Frozen (Immutable) Dataclasses](#frozen-immutable-dataclasses)
5. [Mutable Dataclasses](#mutable-dataclasses)
6. [JSON Persistence Files](#json-persistence-files)

---

## Design Principles

- **Immutable where possible.** Raw data, normalization outputs, and matching
  results are frozen dataclasses. This guarantees that pipeline stages never
  silently mutate upstream data.
- **Back-references everywhere.** Every derived record carries the `raw_id` or
  `record_id` of the record it was produced from, so any resolved deal can be
  traced back to the verbatim scraper output.
- **Fingerprints for dedup.** Computed `@property` fields produce a SHA-256
  digest over the fields that define identity, so duplicate detection is
  deterministic and auditable.
- **NameForms triple.** Hebrew store names need three representations
  (normalized, compact, tokens) to support exact match, fuzzy match, and
  token-overlap match in a single pass.
- **Structured explanations.** The matching pipeline emits an `Explanation`
  object, not a string, so downstream tooling (review UI, metrics) can inspect
  which stage fired and why.

---

## ID Generation

All entity IDs follow a single scheme:

```
{timestamp_ms_hex}_{random_hex}
```

| Component          | Description                                              |
|--------------------|----------------------------------------------------------|
| `timestamp_ms_hex` | Current time in milliseconds since epoch, hex-encoded.   |
| `random_hex`       | Random bytes (hex), providing collision resistance.       |

**Properties:**

- **Sortable by time** -- lexicographic sort on the hex prefix preserves
  chronological order.
- **Collision-resistant** -- the random suffix avoids conflicts even when
  multiple records are created in the same millisecond.

---

## Enums

All enums inherit from `StrEnum` so they serialize naturally to JSON strings.

### MatchDecision

Outcome of the store-matching pipeline for a single scraped name.

| Value        | Meaning                                                       |
|--------------|---------------------------------------------------------------|
| `AUTO_MATCH` | High-confidence match; record is linked automatically.        |
| `REVIEW`     | Ambiguous; sent to the review queue for human decision.       |
| `NO_MATCH`   | No plausible candidate found; record cannot be linked.        |

### ReviewStatus

Lifecycle state of an item in the review queue.

| Value       | Meaning                                                        |
|-------------|----------------------------------------------------------------|
| `PENDING`   | Awaiting human review.                                         |
| `APPROVED`  | Reviewer accepted a suggested match.                           |
| `CREATED`   | Reviewer created a new canonical store for this name.          |
| `DISCARDED` | Reviewer rejected the record (bad data, duplicate, etc.).      |
| `SKIPPED`   | Reviewer deferred; item stays in queue for later.              |

### ReviewAction

The action a reviewer selects when resolving a review item.

| Value        | Meaning                                                      |
|--------------|--------------------------------------------------------------|
| `APPROVE`    | Link the record to an existing canonical store.              |
| `CREATE_NEW` | Create a new canonical store from this record.               |
| `DISCARD`    | Drop the record permanently.                                 |
| `SKIP`       | Leave the item in the queue; come back later.                |

### AliasSource

How a store alias was introduced into the system.

| Value     | Meaning                                                         |
|-----------|-----------------------------------------------------------------|
| `SEED`    | Pre-loaded from a seed / bootstrap file.                        |
| `SCRAPER` | Discovered automatically from scraper output.                   |
| `REVIEW`  | Created during human review.                                    |
| `MANUAL`  | Added manually outside any automated flow.                      |

---

## Frozen (Immutable) Dataclasses

These are defined with `@dataclass(frozen=True)`. Fields cannot be reassigned
after construction.

---

### 1. RawScrapedRecord

The verbatim deal as returned by a scraper. Nothing is cleaned, parsed, or
normalized -- this is the audit-trail copy.

```python
@dataclass(frozen=True)
class RawScrapedRecord:
    id: str
    source_id: str
    store_name: str
    deal_description: str
    price_text: str
    url: str | None
    scraped_at: datetime
    raw_payload: dict[str, Any]

    @property
    def fingerprint(self) -> str: ...
```

| Field              | Type               | Description                                                                 |
|--------------------|--------------------|-----------------------------------------------------------------------------|
| `id`               | `str`              | Sorted timestamp ID (see [ID Generation](#id-generation)).                  |
| `source_id`        | `str`              | Identifier of the scraping source (e.g. `"shufersal"`, `"rami_levy"`).     |
| `store_name`       | `str`              | Store name exactly as scraped -- no trimming, no case folding.              |
| `deal_description` | `str`              | Raw deal text from the source page.                                         |
| `price_text`       | `str`              | Price string verbatim (e.g. `"29.90"`, `"2 for 15"`, `"9.90 ILS"`).        |
| `url`              | `str \| None`      | Source URL of the deal page, if available.                                   |
| `scraped_at`       | `datetime`         | Timestamp when the scraper captured this record.                            |
| `raw_payload`      | `dict[str, Any]`   | Full JSON payload from the source, preserved for audit and re-processing.   |
| `fingerprint`      | `@property -> str`  | SHA-256 of `(source_id, store_name, deal_description, price_text)`. Used for dedup: two records with the same fingerprint represent the same deal. |

**Rationale:** Keeping the raw record frozen and complete means no pipeline
bug can corrupt the original data. The `raw_payload` dict lets us re-extract
fields later without re-scraping. The fingerprint is a derived property (not
stored) so it is always consistent with the actual field values.

---

### 2. RawStore

A store entity as returned by a scraper, before any canonicalization.

```python
@dataclass(frozen=True)
class RawStore:
    id: str
    source_id: str
    name: str
    branch: str | None
    address: str | None
    url: str | None
    scraped_at: datetime
    raw_payload: dict[str, Any]

    @property
    def fingerprint(self) -> str: ...
```

| Field         | Type               | Description                                                              |
|---------------|--------------------|--------------------------------------------------------------------------|
| `id`          | `str`              | Sorted timestamp ID.                                                     |
| `source_id`   | `str`              | Scraping source identifier.                                              |
| `name`        | `str`              | Raw store name as scraped.                                               |
| `branch`      | `str \| None`      | Branch or location qualifier, if the source distinguishes branches.      |
| `address`     | `str \| None`      | Physical address, if provided by the source.                             |
| `url`         | `str \| None`      | URL of the store page on the source site.                                |
| `scraped_at`  | `datetime`         | When this store record was captured.                                     |
| `raw_payload` | `dict[str, Any]`   | Full source JSON for audit.                                              |
| `fingerprint` | `@property -> str`  | SHA-256 digest for dedup, computed over identifying fields.              |

**Rationale:** Stores arrive from multiple sources with inconsistent naming.
Freezing the raw version lets the normalization and matching pipelines work on
copies without risk of feedback loops.

---

### 3. NameForms

Three representations of a single name, optimized for different matching
strategies.

```python
@dataclass(frozen=True)
class NameForms:
    normalized: str
    compact: str
    tokens: tuple[str, ...]
```

| Field        | Type              | Description                                                                         |
|--------------|-------------------|-------------------------------------------------------------------------------------|
| `normalized` | `str`             | Display-ready form: lowercased, trimmed, Hebrew niqqud (vowel marks) stripped. Used for exact matching and human-facing display. |
| `compact`    | `str`             | Spaces, punctuation, and Hebrew final-form letters removed. Used for fuzzy / edit-distance matching where whitespace and punctuation differences should not count. |
| `tokens`     | `tuple[str, ...]` | Deduplicated significant words extracted from the normalized form. Used for token-overlap matching (e.g. Jaccard similarity). Stored as a tuple (not list) to maintain immutability. |

**Rationale:** Hebrew store names vary wildly across sources -- different
spacing, niqqud, punctuation, and final-letter forms. Pre-computing all three
representations at normalization time means matching stages can simply read
the form they need instead of re-deriving it.

---

### 4. NormalizedRecord

The output of the normalization pipeline. Links back to the raw record but
carries cleaned, structured data.

```python
@dataclass(frozen=True)
class NormalizedRecord:
    raw_id: str
    source_id: str
    store_name_forms: NameForms
    deal_description: str
    price: PriceInfo | None
    domain: str | None
    normalized_at: datetime
```

| Field               | Type               | Description                                                           |
|---------------------|--------------------|-----------------------------------------------------------------------|
| `raw_id`            | `str`              | Back-reference to the originating `RawScrapedRecord.id`.              |
| `source_id`         | `str`              | Carried forward from the raw record for convenience.                  |
| `store_name_forms`  | `NameForms`        | Triple representation of the cleaned store name.                      |
| `deal_description`  | `str`              | Deal text after cleanup (whitespace normalization, encoding fixes).   |
| `price`             | `PriceInfo \| None`| Structured price parsed from `price_text`, or `None` if unparseable.  |
| `domain`            | `str \| None`      | Domain extracted from the raw URL (e.g. `"shufersal.co.il"`).         |
| `normalized_at`     | `datetime`         | When normalization was performed.                                     |

**Rationale:** Normalization is a pure transformation: raw in, normalized out.
Keeping it frozen ensures the matching pipeline receives a stable snapshot.
The `raw_id` back-reference supports full-chain traceability.

---

### 5. PriceInfo

Structured representation of a price, parsed from free-text.

```python
@dataclass(frozen=True)
class PriceInfo:
    unit_price: Decimal | None
    expression: str
    quantity: int = 1
    total: Decimal | None = None
    currency: str = "ILS"
```

| Field        | Type              | Description                                                                |
|--------------|-------------------|----------------------------------------------------------------------------|
| `unit_price` | `Decimal \| None` | Price per single unit, if determinable.                                    |
| `expression` | `str`             | Original price text verbatim (e.g. `"2 for 15.00"`), preserved for display and debugging. |
| `quantity`   | `int`             | Number of units the price covers. Defaults to `1`.                         |
| `total`      | `Decimal \| None` | Total price for the quantity, if provided (e.g. `15.00` in "2 for 15").    |
| `currency`   | `str`             | ISO currency code. Defaults to `"ILS"` (Israeli New Shekel).              |

**Rationale:** Israeli deal sites express prices in many formats: per-unit,
multi-buy, percentage discounts. Capturing both the parsed values and the
original expression lets downstream consumers choose between structured data
and the human-readable original.

---

### 6. MatchCandidate

A single candidate store that the matching pipeline considers for a given
input name.

```python
@dataclass(frozen=True)
class MatchCandidate:
    store_id: str
    store_name: str
    confidence: float
    stage: str
    matched_alias: str | None
```

| Field           | Type           | Description                                                             |
|-----------------|----------------|-------------------------------------------------------------------------|
| `store_id`      | `str`          | ID of the `CanonicalStore` this candidate refers to.                    |
| `store_name`    | `str`          | Display name of the canonical store (for logging / review UI).          |
| `confidence`    | `float`        | Match confidence score in the range `[0.0, 1.0]`.                      |
| `stage`         | `str`          | Name of the pipeline stage that produced this candidate (e.g. `"exact"`, `"fuzzy"`, `"token"`). |
| `matched_alias` | `str \| None`  | If the match was via a `StoreAlias`, the alias string; otherwise `None`.|

**Rationale:** Carrying the stage name and optional alias makes match
decisions auditable -- reviewers can see *why* a candidate was proposed and
whether it matched the primary name or a known alias.

---

### 7. MatchVerdict

The complete matching decision for one scraped name.

```python
@dataclass(frozen=True)
class MatchVerdict:
    record_id: str
    input_name: str
    decision: MatchDecision
    candidates: list[MatchCandidate]
    best: MatchCandidate | None
    explanation: Explanation
```

| Field         | Type                    | Description                                                      |
|---------------|-------------------------|------------------------------------------------------------------|
| `record_id`   | `str`                   | ID of the normalized record being matched.                       |
| `input_name`  | `str`                   | The store name string that was fed into the matcher.             |
| `decision`    | `MatchDecision`         | Outcome: `AUTO_MATCH`, `REVIEW`, or `NO_MATCH`.                 |
| `candidates`  | `list[MatchCandidate]`  | All candidates considered, sorted by confidence descending.      |
| `best`        | `MatchCandidate \| None`| The top candidate if `decision` is `AUTO_MATCH` or `REVIEW`; `None` for `NO_MATCH`. |
| `explanation`  | `Explanation`           | Structured trace of the matching process.                        |

**Rationale:** Bundling the full candidate list with the verdict lets the
review UI show alternatives, not just the top pick. The `Explanation` object
provides machine-readable tracing for debugging and metrics.

---

### 8. Explanation

Structured trace of a matching pipeline run.

```python
@dataclass(frozen=True)
class Explanation:
    stages_run: list[str]
    stage_matched: str | None
    reason: str
    details: dict[str, Any]
```

| Field           | Type              | Description                                                          |
|-----------------|-------------------|----------------------------------------------------------------------|
| `stages_run`    | `list[str]`       | Ordered list of pipeline stages that were executed.                  |
| `stage_matched` | `str \| None`     | The stage that produced the winning match, or `None` if no match.    |
| `reason`        | `str`             | Human-readable summary of the decision (e.g. `"Exact alias match on 'shufersal deal'"`). |
| `details`       | `dict[str, Any]`  | Arbitrary key-value pairs for stage-specific data (scores, thresholds, intermediate values). |

**Rationale:** A plain-text reason is convenient for logs, but structured
`details` and `stages_run` allow tooling to compute metrics like "what
fraction of matches come from the fuzzy stage?" without parsing strings.

---

## Mutable Dataclasses

These are regular `@dataclass` instances. They represent entities that change
over their lifetime (stores gain aliases, review items get resolved, etc.).

---

### 9. CanonicalStore

The authoritative record for a store. All deals and aliases point here.

```python
@dataclass
class CanonicalStore:
    id: str
    name: str
    name_forms: NameForms
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]
```

| Field        | Type              | Description                                                              |
|--------------|-------------------|--------------------------------------------------------------------------|
| `id`         | `str`             | Sorted timestamp ID.                                                     |
| `name`       | `str`             | Primary display name for this store.                                     |
| `name_forms` | `NameForms`       | Pre-computed triple representation of `name` for matching.               |
| `created_at` | `datetime`        | When the store was first created.                                        |
| `updated_at` | `datetime`        | Last modification timestamp (name change, metadata update, etc.).        |
| `metadata`   | `dict[str, Any]`  | Open-ended metadata bag (e.g. chain, region, category).                  |

**Rationale:** This is the single source of truth. Every deal, alias, and
external reference ultimately resolves to a `CanonicalStore`. The `name_forms`
cache avoids recomputing name representations on every match run.

---

### 10. StoreAlias

Maps an alternative name to a canonical store. Aliases accumulate over time as
new scrapers, reviewers, and manual edits introduce name variants.

```python
@dataclass
class StoreAlias:
    id: str
    store_id: str
    alias: str
    alias_forms: NameForms
    source: AliasSource
    created_at: datetime
```

| Field         | Type           | Description                                                             |
|---------------|----------------|-------------------------------------------------------------------------|
| `id`          | `str`          | Sorted timestamp ID.                                                    |
| `store_id`    | `str`          | Foreign key to `CanonicalStore.id`.                                     |
| `alias`       | `str`          | The alternative name string.                                            |
| `alias_forms` | `NameForms`    | Pre-computed triple representation of the alias for matching.           |
| `source`      | `AliasSource`  | How this alias entered the system (`SEED`, `SCRAPER`, `REVIEW`, `MANUAL`). |
| `created_at`  | `datetime`     | When the alias was created.                                             |

**Rationale:** Aliases are the primary mechanism for absorbing name variation
across sources. Tracking `source` allows auditing and enables policies like
"auto-created aliases require review before they participate in AUTO_MATCH."

---

### 11. Deal

A resolved deal, linked to a canonical store. This is the downstream-ready
entity that consumers (API, UI, analytics) work with.

```python
@dataclass
class Deal:
    id: str
    store_id: str
    raw_id: str
    source_id: str
    description: str
    price: PriceInfo | None
    url: str | None
    scraped_at: datetime
    resolved_at: datetime

    @property
    def fingerprint(self) -> str: ...
```

| Field         | Type               | Description                                                            |
|---------------|--------------------|------------------------------------------------------------------------|
| `id`          | `str`              | Sorted timestamp ID.                                                   |
| `store_id`    | `str`              | Foreign key to `CanonicalStore.id`.                                    |
| `raw_id`      | `str`              | Back-reference to the originating `RawScrapedRecord.id`.               |
| `source_id`   | `str`              | Scraping source identifier.                                            |
| `description` | `str`              | Cleaned deal description.                                              |
| `price`       | `PriceInfo \| None`| Structured price, or `None` if unparseable.                            |
| `url`         | `str \| None`      | Source URL for the deal.                                                |
| `scraped_at`  | `datetime`         | When the raw record was scraped.                                       |
| `resolved_at` | `datetime`         | When the deal was linked to its canonical store.                       |
| `fingerprint` | `@property -> str`  | SHA-256 digest for dedup across resolved deals.                        |

**Rationale:** The `Deal` is the end product of the pipeline. Carrying both
`raw_id` (for traceability) and `store_id` (for downstream queries) means
consumers never need to traverse the full pipeline to answer "which store is
this deal for?" or "what was the original scraped text?"

---

### 12. ReviewItem

An entry in the human review queue. Created when the matcher returns
`REVIEW`; updated when a reviewer acts on it.

```python
@dataclass
class ReviewItem:
    id: str
    raw_id: str
    input_name: str
    input_name_forms: NameForms
    verdict: MatchVerdict
    status: ReviewStatus
    decision: ReviewDecision | None
    created_at: datetime
    reviewed_at: datetime | None
```

| Field              | Type                     | Description                                                    |
|--------------------|--------------------------|----------------------------------------------------------------|
| `id`               | `str`                    | Sorted timestamp ID.                                           |
| `raw_id`           | `str`                    | Back-reference to the raw record that triggered review.        |
| `input_name`       | `str`                    | The store name that could not be auto-matched.                 |
| `input_name_forms` | `NameForms`              | Pre-computed forms of the input name.                          |
| `verdict`          | `MatchVerdict`           | Snapshot of the match verdict at the time the item was queued. |
| `status`           | `ReviewStatus`           | Current lifecycle state (`PENDING`, `APPROVED`, etc.).         |
| `decision`         | `ReviewDecision \| None` | What the reviewer decided, or `None` if still pending.         |
| `created_at`       | `datetime`               | When the item entered the queue.                               |
| `reviewed_at`      | `datetime \| None`       | When the reviewer acted, or `None` if still pending.           |

**Rationale:** The `verdict` is stored as a snapshot (not a reference) so the
review UI shows exactly what the matcher saw, even if the store catalog has
changed since. This prevents confusing mismatches between what the reviewer
sees and what the system originally computed.

---

### 13. ReviewDecision

Captures the reviewer's action and any associated data.

```python
@dataclass
class ReviewDecision:
    action: ReviewAction
    store_id: str | None
    new_store_name: str | None
    note: str | None
    reviewed_by: str
```

| Field            | Type           | Description                                                           |
|------------------|----------------|-----------------------------------------------------------------------|
| `action`         | `ReviewAction` | The action taken (`APPROVE`, `CREATE_NEW`, `DISCARD`, `SKIP`).        |
| `store_id`       | `str \| None`  | For `APPROVE`: the canonical store ID to link to. `None` otherwise.   |
| `new_store_name` | `str \| None`  | For `CREATE_NEW`: the name for the new canonical store. `None` otherwise. |
| `note`           | `str \| None`  | Optional free-text note from the reviewer.                            |
| `reviewed_by`    | `str`          | Identifier of the reviewer (username, email, etc.).                   |

**Rationale:** Separating the decision from the review item keeps the item's
history clean: the item tracks *status*, the decision tracks *what was done
and by whom*.

---

### 14. ExternalReference

Links a canonical store to an identifier in an external system.

```python
@dataclass
class ExternalReference:
    id: str
    store_id: str
    system: str
    external_id: str
    metadata: dict[str, Any]
```

| Field         | Type              | Description                                                            |
|---------------|-------------------|------------------------------------------------------------------------|
| `id`          | `str`             | Sorted timestamp ID.                                                   |
| `store_id`    | `str`             | Foreign key to `CanonicalStore.id`.                                    |
| `system`      | `str`             | Name of the external system (e.g. `"open_finance"`, `"google_maps"`).  |
| `external_id` | `str`             | The store's identifier in that external system.                        |
| `metadata`    | `dict[str, Any]`  | System-specific metadata (e.g. coordinates, external URL, sync status).|

**Rationale:** Deals data becomes most valuable when linked to external
systems (finance platforms, maps, receipt parsers). This table provides that
linkage without polluting the `CanonicalStore` model with system-specific
fields.

---

### 15. NormalizationContext

Mutable state object threaded through the normalization pipeline steps. Each
step reads and mutates the relevant fields in place.

```python
@dataclass
class NormalizationContext:
    raw: RawScrapedRecord
    store_name: str
    deal_description: str
    price: PriceInfo | None
    domain: str | None
    tokens: tuple[str, ...] | None
    warnings: list[str]
```

| Field              | Type                     | Description                                                     |
|--------------------|--------------------------|-----------------------------------------------------------------|
| `raw`              | `RawScrapedRecord`       | The immutable raw record being normalized (read-only reference).|
| `store_name`       | `str`                    | Store name, mutated through successive pipeline steps.          |
| `deal_description` | `str`                    | Deal text, mutated through successive pipeline steps.           |
| `price`            | `PriceInfo \| None`      | Parsed price; set by the price-parsing step.                    |
| `domain`           | `str \| None`            | Extracted URL domain; set by the domain-extraction step.        |
| `tokens`           | `tuple[str, ...] \| None`| Name tokens; set by the tokenization step.                     |
| `warnings`         | `list[str]`              | Accumulates non-fatal warnings from any step (e.g. "unparseable price", "unusual characters in store name"). |

**Rationale:** The normalization pipeline is a sequence of small,
composable steps. A shared mutable context lets each step contribute its
output without requiring a new frozen dataclass per step. The `raw` field is
an immutable reference, so the original data is always accessible but never
modified. The `warnings` list provides observability without aborting the
pipeline on non-critical issues.

---

## JSON Persistence Files

All data is persisted as JSON files. Each file stores a JSON array of
serialized instances of the corresponding model.

| File                             | Contents                  | Model                |
|----------------------------------|---------------------------|----------------------|
| `raw_source_stores.json`         | Raw store records          | `list[RawStore]`     |
| `raw_source_deals.json`          | Raw deal records           | `list[RawScrapedRecord]` |
| `stores.json`                    | Canonical stores           | `list[CanonicalStore]` |
| `store_aliases.json`             | Store name aliases         | `list[StoreAlias]`   |
| `store_external_references.json` | External system links      | `list[ExternalReference]` |
| `store_match_review.json`        | Review queue               | `list[ReviewItem]`   |
| `deals.json`                     | Resolved deals             | `list[Deal]`         |

**Conventions:**

- Files are read and written atomically (write to temp, then rename).
- Datetime fields are serialized as ISO 8601 strings.
- `Decimal` fields are serialized as strings to avoid floating-point drift.
- `NameForms` and other nested frozen dataclasses are serialized inline as
  JSON objects.
- Enum values are serialized as their string value (enabled by `StrEnum`).
- `@property` fields (fingerprints) are not persisted; they are recomputed on
  access.
