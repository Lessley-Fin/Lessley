# Lessley Deals -- Architecture

## 1. System Overview

Lessley Deals is a Python 3.12 system that scrapes deals from Israeli retail
sources, normalizes Hebrew and English text, resolves scraped store names to
canonical store entities, and queues uncertain matches for human review.

The core problem: retail data sources refer to the same store by dozens of
spelling variants (Hebrew with/without niqqud, transliterations, legal suffixes,
branch qualifiers). The system must collapse those variants into a single
canonical identity while never silently guessing wrong.

```
Israeli retail sources
        |
        v
   [ Scraping ]          -- fetch raw HTML / API responses
        |
        v
   [ Normalization ]     -- clean text, parse prices/dates, normalize Hebrew
        |
        v
   [ Matching ]          -- resolve store name -> canonical store
        |
      /   \
     v     v
  [auto]  [review]       -- high confidence vs uncertain
     |       |
     v       v
   [ Persistence ]       -- deals, stores, aliases, review queue
```


## 2. Design Principles

### Raw data is preserved verbatim

Every scraped payload is stored exactly as received. Normalization produces a
separate record; it never mutates the raw input. This allows full audit trails
and replay of the pipeline against updated normalization or matching logic.

### Frozen dataclasses for immutable records, mutable for canonical entities

Records that represent a point-in-time observation (scraped data, normalized
forms, match verdicts) are `@dataclass(frozen=True)`. Canonical entities that
accumulate state over time (stores, alias lists) are mutable dataclasses.

```python
@dataclass(frozen=True)
class RawScrapedRecord:
    source: str
    scraped_at: datetime
    payload: dict[str, Any]

@dataclass
class CanonicalStore:
    store_id: str
    name: str
    aliases: list[str]
```

### typing.Protocol for structural subtyping

Subsystem boundaries are defined by `typing.Protocol`, not by abstract base
classes. This eliminates inheritance coupling -- any object that satisfies the
protocol shape is accepted, enabling easy test doubles and future alternative
implementations.

```python
class StoreRepository(Protocol):
    def get(self, store_id: str) -> CanonicalStore | None: ...
    def save(self, store: CanonicalStore) -> None: ...
    def list_all(self) -> list[CanonicalStore]: ...
```

### Conservative matching

The system prefers sending an uncertain match to human review over recording a
false positive. Thresholds are tuned to minimize silent mismatches at the cost
of more review queue items.

### Atomic writes via os.replace()

All file-based persistence writes to a temporary file first, then calls
`os.replace()` to atomically swap it into place. A crash mid-write never
corrupts the existing data file.

```python
def atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
```

### Separation of concerns: scrapers never match, matchers never scrape

Each subsystem has a single responsibility. A scraper knows how to fetch data
from a source. A matcher knows how to compare names. They never call each other
directly; the pipeline orchestrator wires them together.


## 3. Subsystem Boundaries

### 3.1 Scraping

Responsible for fetching raw data from Israeli retail deal sources.

**Components:**

| Component        | Role                                           |
|------------------|------------------------------------------------|
| Source adapters   | One per retail source; knows URL patterns, auth, payload shape |
| HTTP client       | Shared `httpx` or `aiohttp` session with retries, rate limiting  |
| Browser client    | Playwright-based for JS-rendered sources        |
| Pagination handler| Iterates pages until exhaustion or staleness    |
| Auth handler      | Manages tokens, cookies, login flows per source |
| Scrape orchestrator| Invokes adapters, collects results, handles errors |

**Output types:**

```python
@dataclass(frozen=True)
class RawStore:
    name: str             # store name exactly as found in source
    source: str
    source_id: str | None

@dataclass(frozen=True)
class RawScrapedRecord:
    source: str
    scraped_at: datetime
    raw_store: RawStore
    raw_price: str | None
    raw_dates: dict[str, str]
    payload: dict[str, Any]   # full source-specific data
```

### 3.2 Normalization

A pipeline of deterministic, stateless transformation steps.

**Pipeline stages (in order):**

1. **Text cleaning** -- strip leading/trailing whitespace, collapse internal
   runs of whitespace, remove control characters.

2. **Hebrew normalization** -- remove niqqud (U+0591..U+05C7), map final-form
   letters to their standard forms (e.g. U+05DA -> U+05DB), decompose Hebrew
   presentation forms (FB1D..FB4F) to base characters.

3. **Store name normalization** -- strip common legal suffixes
   (e.g. `בע"מ`, `ltd`, `inc`), extract branch qualifiers
   (e.g. `- סניף תל אביב`), produce three name forms.

4. **Price parsing** -- extract numeric value and currency from free-text price
   strings (handles `₪`, `NIS`, `ILS`, comma/dot ambiguity).

5. **Date parsing** -- parse Hebrew date formats, relative dates, ISO strings
   into `datetime` objects.

**Output:**

```python
@dataclass(frozen=True)
class NameForms:
    normalized: str   # cleaned, niqqud-stripped, suffix-stripped
    compact: str      # normalized with spaces/punctuation removed,
                      #   final forms normalized
    tokens: tuple[str, ...]  # split on whitespace, sorted

@dataclass(frozen=True)
class NormalizedRecord:
    raw: RawScrapedRecord
    store_name: NameForms
    price: Decimal | None
    currency: str | None
    valid_from: datetime | None
    valid_until: datetime | None
```

### 3.3 Matching

A 5-stage pipeline that attempts to resolve a `NameForms` to a
`CanonicalStore`. Stages run in order; the first stage to produce a result
above threshold wins.

```
Stage 1: ExactAlias
    |  (no hit)
    v
Stage 2: Compact
    |  (no hit)
    v
Stage 3: Normalized (Jaro-Winkler + Token Jaccard)
    |  (no hit)
    v
Stage 4: Domain
    |  (no hit)
    v
Stage 5: Token
```

**Stage details:**

| #  | Stage            | Method                                | Auto threshold | Review threshold |
|----|------------------|---------------------------------------|----------------|------------------|
| 1  | ExactAlias       | Exact string match against alias list | 1.00           | --               |
| 2  | Compact          | Exact match on compact form           | 1.00           | --               |
| 3  | Normalized       | Jaro-Winkler + Token Jaccard blend    | >= 0.90        | >= 0.50          |
| 4  | Domain           | Domain-specific heuristics            | >= 0.90        | >= 0.50          |
| 5  | Token            | Token set overlap (Jaccard)           | capped at 0.70 | >= 0.50          |

**Why these thresholds:**

- **Auto >= 0.90**: high confidence required for unattended matching.
- **Review >= 0.50**: anything remotely plausible goes to a human.
- **Token Jaccard capped at 0.70**: token overlap alone can produce misleading
  scores for short names; it is never sufficient for auto-match.

**Output:**

```python
@dataclass(frozen=True)
class Explanation:
    stage: str
    score: float
    details: dict[str, Any]

@dataclass(frozen=True)
class MatchVerdict:
    status: Literal["auto", "review", "no_match"]
    candidate: CanonicalStore | None
    explanation: Explanation
```

### 3.4 Review

Handles uncertain matches that fall into the review band.

**Workflow:**

```
MatchVerdict(status="review")
        |
        v
    ReviewItem added to queue
        |
        v
    Human operator (CLI)
        |
    +---+---+---+---+
    |   |       |   |
    v   v       v   v
 approve create discard skip
    |      |       |
    v      v       v
  alias  new     drop
 learned store   record
```

**Actions:**

- **approve** -- confirm the suggested candidate. The scraped name is added as
  an alias to the canonical store (alias learning feedback loop).
- **create** -- the scraped name represents a genuinely new store. A new
  `CanonicalStore` is created with this name as its first alias.
- **discard** -- the record is junk or irrelevant. Dropped from further
  processing.
- **skip** -- defer decision. The item stays in the queue.

The alias learning feedback loop means that once a human approves
`"שופרסל דיל" -> Shufersal`, future records with that exact name will
auto-match in Stage 1 (ExactAlias).

### 3.5 Persistence

All data access goes through repository protocol abstractions.

**Repository protocols:**

```python
class DealRepository(Protocol):
    def save(self, deal: Deal) -> None: ...
    def get_by_store(self, store_id: str) -> list[Deal]: ...

class StoreRepository(Protocol):
    def get(self, store_id: str) -> CanonicalStore | None: ...
    def save(self, store: CanonicalStore) -> None: ...
    def list_all(self) -> list[CanonicalStore]: ...
    def find_by_alias(self, alias: str) -> CanonicalStore | None: ...

class ReviewQueueRepository(Protocol):
    def push(self, item: ReviewItem) -> None: ...
    def pop(self) -> ReviewItem | None: ...
    def list_pending(self) -> list[ReviewItem]: ...

class RawRecordRepository(Protocol):
    def save(self, record: RawScrapedRecord) -> None: ...
```

**JSON file implementation:**

- One JSON file per collection (e.g. `stores.json`, `deals.json`,
  `review_queue.json`, `raw_records.json`).
- All writes use `atomic_write()` (temp file + `os.replace()`).
- Record IDs are sorted-timestamp-based (e.g. `20260321T143000Z-a3f2`) for
  chronological ordering and uniqueness.
- Designed for later migration to MongoDB: repository protocol stays the same,
  only the implementation class changes.

### 3.6 Pipeline Orchestration

Wires the four processing stages together.

```
scrape --> normalize --> match --> persist
```

**PipelineContext** tracks each record through the pipeline:

```python
@dataclass
class PipelineContext:
    raw: RawScrapedRecord
    normalized: NormalizedRecord | None = None
    verdict: MatchVerdict | None = None
    outcome: Literal["persisted", "queued_for_review", "discarded"] | None = None
```

The orchestrator:

1. Invokes the scrape orchestrator to get `list[RawScrapedRecord]`.
2. Passes each through the normalization pipeline.
3. Passes each `NormalizedRecord` through the matching pipeline.
4. Routes based on verdict:
   - `auto` -- persist the deal immediately.
   - `review` -- push to the review queue.
   - `no_match` -- log and discard (or push to review if configured).
5. Reports summary statistics (auto-matched, queued, discarded).


## 4. Data Flow

```
                         +--------------------+
                         | Israeli retail site |
                         +--------+-----------+
                                  |
                            (HTTP / browser)
                                  |
                                  v
                       +----------+----------+
                       |  Source Adapter      |
                       +----------+----------+
                                  |
                                  v
                        RawScrapedRecord (frozen)
                        RawStore (frozen)
                                  |
                         (preserved verbatim)
                                  |
                                  v
                       +----------+----------+
                       |  Normalization      |
                       |  Pipeline           |
                       +----------+----------+
                                  |
                                  v
                        NormalizedRecord (frozen)
                        NameForms { normalized, compact, tokens }
                                  |
                                  v
                       +----------+----------+
                       |  Matching Pipeline  |
                       |  (5 stages)         |
                       +----------+----------+
                                  |
                                  v
                          MatchVerdict (frozen)
                         /        |         \
                        /         |          \
                  auto (>=0.90)  review     no_match
                      |       (0.50-0.89)      |
                      v           |            v
                  +---+---+       v        (log + discard)
                  | Deal  |   +---+------+
                  +---+---+   | ReviewItem|
                      |       +---+------+
                      v           |
                 DealRepository   v
                             Human (CLI)
                              /    |    \
                             v     v     v
                         approve create discard
                            |      |
                            v      v
                     alias added  new CanonicalStore
                     to store     created
                            \      /
                             v    v
                         StoreRepository
```


## 5. Key Architectural Decisions

### Python over C#

The existing Lessley system includes a .NET gateway (`Lessley.Gateway.Api`).
The deals subsystem is written in Python instead of C# because:

- Python has a stronger ecosystem for web scraping (httpx, Playwright,
  BeautifulSoup, Scrapy).
- The deals system is a separate bounded context with no shared domain model.
- Python enables faster iteration for data pipeline work.
- The gateway remains the system of record; the deals system is a feeder.

### JSON files before MongoDB

The initial persistence layer uses plain JSON files instead of MongoDB because:

- Zero infrastructure dependency -- run the system with nothing but Python.
- Files are human-inspectable with any text editor.
- Fast iteration during development -- no schema migrations, no connection
  strings.
- The repository protocol abstraction means switching to MongoDB later requires
  only a new implementation class, no changes to business logic.

### Jaro-Winkler over Levenshtein

Jaro-Winkler is preferred for store name matching because:

- It gives higher scores to strings that share a common prefix, which is
  typical of store name variants (e.g. "Shufersal" vs "Shufersal Deal").
- It handles short strings better than Levenshtein, which penalizes single-
  character differences too harshly on 5-8 character names.

### Token Jaccard capped at 0.70

Token-level Jaccard similarity is useful for catching reordered words
(e.g. "Mega Sport" vs "Sport Mega") but can produce misleadingly high scores
for short names where a single shared token dominates. The cap at 0.70 ensures
token overlap alone never triggers auto-match; it can only route to review.

### Compact form design

The compact form (`NameForms.compact`) strips all spaces and punctuation, and
normalizes Hebrew final forms. This catches variants that differ only in
spacing, hyphenation, or quotation style:

```
"שופר-סל"  -->  "שופרסל"
"שופר סל"  -->  "שופרסל"
"Shufer Sal" --> "shufersal"
```

Exact match on compact form (Stage 2) is cheap and catches a large class of
trivial variants before expensive fuzzy matching runs.

### Docker Compose profiles

The deals system uses Docker Compose profiles (`tools`, `test`) so that
development tooling (linters, test runners) does not interfere with the
existing gateway services. Running `docker compose --profile tools up` starts
only the deals-related containers.


## 6. Subsystem Interaction Diagram

```
+---------------------+
|  Pipeline           |
|  Orchestrator       |
+---------+-----------+
          |
          | calls
          |
    +-----+------+--------+--------+
    |            |        |        |
    v            v        v        v
+--------+  +--------+  +-----+  +-----------+
|Scraping|  |Normal- |  |Match|  |Persistence|
|        |  |ization |  |     |  |           |
+--------+  +--------+  +--+--+  +-----+-----+
                            |           ^
                            |           |
                            v           |
                        +---+---+       |
                        |Review |-------+
                        +-------+
```

**Dependency rules:**

- **Pipeline Orchestrator** depends on all four processing subsystems and
  persistence.
- **Scraping** depends on nothing else. It produces `RawScrapedRecord` and
  returns.
- **Normalization** depends on nothing else. It takes a `RawScrapedRecord` and
  returns a `NormalizedRecord`.
- **Matching** depends on **Persistence** (reads `StoreRepository` to look up
  candidates and aliases).
- **Review** depends on **Persistence** (reads/writes `ReviewQueueRepository`
  and `StoreRepository` to apply human decisions).
- **Persistence** depends on nothing else. It exposes repository protocols
  implemented by JSON files (or later MongoDB).

No subsystem imports from another subsystem's internals. All cross-boundary
communication uses the data types and protocols defined in a shared `types`
module.


## 7. Protected Boundary: Lessley.Gateway.Api

The .NET gateway (`Lessley.Gateway.Api`) is a **read-only dependency**. The
deals system must never:

- Write to the gateway's database directly.
- Call mutable endpoints on the gateway.
- Assume the gateway's schema or internal data model.

If integration with the gateway is needed (e.g. to push resolved deals into the
main system), the gateway must be treated as an external API:

- Communicate only through documented HTTP endpoints.
- Use a dedicated integration adapter behind a protocol abstraction.
- Handle gateway unavailability gracefully (retry, queue, degrade).

```
+------------------+          +------------------------+
| lessley-deals    |  ---->   | Lessley.Gateway.Api    |
| (Python)         | HTTP GET | (.NET)                 |
+------------------+  only    +------------------------+
```

The gateway owns its data. The deals system owns its data. Neither reaches into
the other's storage.
