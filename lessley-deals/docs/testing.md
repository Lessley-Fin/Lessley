# Testing Strategy

## Overview

The project has approximately 200 tests in total. **pytest** is the test runner.

Tests are split into two categories:

- **Unit tests (~147)** -- no file I/O, no network calls. Pure logic validation.
- **Integration tests (~53)** -- exercise real JSON file persistence, end-to-end pipelines, and review loops.

Static analysis tools complement the test suite:

- **mypy** for static type checking.
- **ruff** for linting and style enforcement.

---

## Test Structure

```
tests/
├── conftest.py           # Root fixtures (tmp_path factories, sample data)
├── factories.py          # make_raw_deal(), make_store(), make_alias(), etc.
├── unit/
│   ├── normalization/
│   │   ├── test_hebrew_utils.py      # niqqud stripping, final forms, presentation forms
│   │   ├── test_text.py              # whitespace, punctuation, casing
│   │   ├── test_store_name.py        # legal suffixes, branch extraction
│   │   ├── test_deal_text.py         # deal description cleaning
│   │   ├── test_price.py             # Israeli price patterns
│   │   └── test_date.py              # DD/MM/YYYY, Hebrew dates
│   ├── matching/
│   │   ├── test_similarity.py        # jaro_winkler, token_jaccard
│   │   ├── test_exact_alias.py       # Stage 1
│   │   ├── test_compact.py           # Stage 2
│   │   ├── test_normalized.py        # Stage 3
│   │   ├── test_domain.py            # Stage 4
│   │   ├── test_token.py             # Stage 5
│   │   ├── test_pipeline.py          # Full pipeline flow
│   │   └── test_index.py             # AliasIndex building
│   ├── domain/
│   │   ├── test_models.py            # Dataclass creation, fingerprints
│   │   ├── test_enums.py             # StrEnum values
│   │   └── test_name_forms.py        # NameForms generation
│   ├── review/
│   │   ├── test_queue.py             # Queue operations, filtering
│   │   ├── test_actions.py           # approve/create/discard effects
│   │   └── test_learner.py           # Alias creation from decisions
│   └── persistence/
│       ├── test_id_gen.py            # ID format, sortability, uniqueness
│       └── test_serialization.py     # Dataclass <-> dict <-> JSON
├── integration/
│   ├── test_json_store.py            # Atomic writes, concurrent access
│   ├── test_repositories.py          # All 7 repositories CRUD
│   ├── test_pipeline.py              # Full pipeline end-to-end
│   └── test_review_loop.py           # Review -> alias -> re-match
└── fixtures/
    ├── sample_shufersal.html
    ├── sample_rami_levy.json
    ├── stores_seed.json
    └── aliases_seed.json
```

---

## Test Factories

All factories live in `tests/factories.py`. They provide sensible defaults for every field and accept `**overrides` so tests only specify the fields they care about. This avoids brittle tests tied to specific field values.

| Factory                              | Purpose                                  |
| ------------------------------------ | ---------------------------------------- |
| `make_raw_deal(**overrides)`         | Create a `RawScrapedRecord` with defaults |
| `make_raw_store(**overrides)`        | Create a raw store record                |
| `make_store(**overrides)`            | Create a canonical `Store`               |
| `make_alias(store_id, alias, **overrides)` | Create a `StoreAlias`              |
| `make_review_item(raw_id, **overrides)`    | Create a `ReviewItem`              |
| `make_match_verdict(**overrides)`    | Create a `MatchVerdict`                  |

Usage example:

```python
deal = make_raw_deal(store_name="רמי לוי", price="29.90")
```

Only the fields relevant to the test are specified; everything else gets a reasonable default.

---

## Unit Tests (~147)

### Normalization

- **Hebrew-specific**: niqqud (vowel mark) stripping, final-form normalization (e.g. mem-sofit to mem), presentation form conversion, geresh and gershayim handling.
- **Text cleaning**: whitespace collapse, punctuation normalization, casing.
- **Store names**: legal suffix removal (e.g. removing trailing `"בע"מ"`), branch extraction (e.g. extracting the branch from strings like `"סניף תל אביב"`).
- **Price parsing**: Israeli price patterns such as `"2 ב-30"` parsed into `PriceInfo(quantity=2, total=30)`.
- **Date parsing**: DD/MM/YYYY format and Hebrew month names.

### Matching

Each of the five matching stages is tested independently with known inputs and expected outputs:

1. **Exact alias** (Stage 1)
2. **Compact** (Stage 2)
3. **Normalized** (Stage 3)
4. **Domain** (Stage 4)
5. **Token** (Stage 5)

Additional matching tests cover:

- Similarity functions (jaro_winkler, token_jaccard) with edge cases.
- Pipeline short-circuit behavior (stops at first confident match).
- Confidence cap verification per stage.

### Domain

- Frozen dataclass immutability enforcement.
- Fingerprint determinism (same input always produces the same fingerprint).
- NameForms computation from raw store names.

### Review

- Queue operations: add items, filter by status, compute stats.
- Action effects: approve creates an alias, create makes a new store, discard removes the item.
- Learner: verifies correct alias source attribution and form generation.

---

## Integration Tests (~53)

### JSON Store

- Atomic write safety: simulates a crash mid-write and verifies data integrity.
- Concurrent read/write behavior.
- File locking correctness.

### Repositories

- Full CRUD operations for all 7 repositories.
- Uses `tmp_path` for isolated file system access.
- Verifies the JSON structure written to disk matches expectations.

### Pipeline

- End-to-end flow: feed raw scraped records into the pipeline, receive deals and review items.
- Verifies output counts and linkage between deals and their source records.

### Review Loop

- Creates a review item.
- Approves it and verifies the corresponding alias is created.
- Re-runs matching and verifies the previously unmatched record now auto-matches.

---

## Key Testing Patterns

- **`tmp_path` for all file I/O.** This is a built-in pytest fixture that provides a unique temporary directory per test and cleans up automatically.
- **Factories for test data.** Never hardcode full objects in tests. Always use the factory functions from `tests/factories.py`.
- **`@pytest.mark.parametrize` for Hebrew edge cases.** Many normalization tests use parametrize to cover a matrix of inputs (niqqud variants, final forms, mixed scripts).
- **No mocking of JSON persistence.** Integration tests exercise the real JSON read/write path. This catches serialization bugs that mocks would hide.
- **Mock only external HTTP calls.** The only mocked boundary is outbound HTTP (httpx responses). Everything else runs against real implementations.

---

## Running Tests

```bash
# All tests
pytest

# Unit only
pytest tests/unit/

# Integration only
pytest tests/integration/

# Specific subsystem
pytest tests/unit/normalization/
pytest tests/unit/matching/

# With coverage
pytest --cov=lessley_deals --cov-report=term-missing

# Type checking
mypy src/

# Linting
ruff check src/ tests/
```

---

## CI Integration

Tests run inside Docker as part of the CI pipeline:

```bash
docker compose --profile test run --rm deals-test
```

The test stage in the Dockerfile executes three checks in order:

1. `ruff check` -- linting
2. `mypy` -- type checking
3. `pytest` -- test suite

An exit code of 0 means all checks passed.

---

## What to Test When Adding a New Scraper

When adding support for a new deal source, write the following tests:

1. **Unit test**: parse a sample HTML or JSON response and verify the resulting `RawScrapedRecord` fields are correct.
2. **Fixture file**: add the sample response (HTML or JSON) to `tests/fixtures/` so the test is reproducible without network access.
3. **Integration test**: mock the HTTP responses (using httpx mock) and verify the full scrape-to-output flow produces the expected records.
