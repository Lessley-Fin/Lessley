# Swish Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate monthly Swish gift-card catalog scraping via Docker + cron, guarantee completeness via retry loops, feed unresolved member businesses into the review queue, and strip `SwishAdapter` to emit only `RawStore` (no fake deals).

**Architecture:** `SwishScanner` class in `scraping/helpers/swish_scanner.py` holds one Playwright context and drives four stages (catalog → scan → retry → verify). Four CLI commands wrap individual stages; `swish-all` runs them all in sequence sharing the browser. A Docker image (`Dockerfile.swish`) runs `swish-all` monthly via internal cron. `SwishAdapter` is changed to emit one `RawStore` per unique member business name (no `RawScrapedRecord`). `sync_swish_groups()` dedup is widened to exact-string match against all pending review names.

**Tech Stack:** Python 3.12, Playwright (sync API), playwright-stealth, Typer, Rich, Docker + crond, tini, pytest + unittest.mock

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| NEW | `src/lessley_deals/scraping/helpers/swish_scanner.py` | `SwishScanner` class, `SwishPaths`, `ScanState`, HTML parsers, file I/O |
| MOD | `src/lessley_deals/scraping/sources/swish.py` | Strip to `RawStore`-only output |
| MOD | `src/lessley_deals/scraping/helpers/swish_group_sync.py` | Widen dedup to all pending names |
| MOD | `src/lessley_deals/cli/main.py` | Add 4 commands, update `sync-swish-groups` default path |
| MOD | `pyproject.toml` | Add `playwright-stealth` to `browser` extra |
| NEW | `Dockerfile.swish` | Separate Docker image with Playwright + crond |
| NEW | `docker/swish-crontab` | Cron template (SWISH_CRON_PLACEHOLDER) |
| NEW | `docker/swish-entrypoint.sh` | Substitute cron schedule + tail log |
| MOD | `docker-compose.yml` | Add `swish-scanner` service |
| NEW | `tests/unit/scraping/test_swish_scanner.py` | Unit tests (mocked Playwright) |
| MOD | `tests/unit/scraping/test_swish_group_sync.py` | Add cross-benefit dedup tests |
| NEW | `tests/unit/scraping/test_swish_adapter.py` | RawStore-only assertion |
| DEL | `test_swish.py` | Replaced by `swish_scanner.py` |

---

## Task 1: Dependencies + SwishPaths + ScanState + file I/O helpers

**Files:**
- Modify: `pyproject.toml`
- Create: `src/lessley_deals/scraping/helpers/swish_scanner.py` (partial — dataclasses + I/O only)
- Create: `tests/unit/scraping/test_swish_scanner.py` (partial)

- [ ] **Step 1: Write failing tests for SwishPaths and ScanState I/O**

```python
# tests/unit/scraping/test_swish_scanner.py
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from lessley_deals.scraping.helpers.swish_scanner import (
    ScanState,
    SwishPaths,
    _load_database,
    _load_state,
    _save_database,
    _save_state,
)


def make_paths(tmp_path: Path) -> SwishPaths:
    return SwishPaths(
        data_dir=tmp_path,
        database=tmp_path / "swish_database.json",
        state=tmp_path / "scan_state.json",
        session=tmp_path / "session",
    )


class TestSwishPaths:
    def test_from_env_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SWISH_DATA_DIR", raising=False)
        paths = SwishPaths.from_env()
        assert paths.data_dir == Path("data/swish")
        assert paths.database == Path("data/swish/swish_database.json")
        assert paths.state == Path("data/swish/scan_state.json")
        assert paths.session == Path("data/swish/session")

    def test_from_env_custom(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("SWISH_DATA_DIR", str(tmp_path))
        paths = SwishPaths.from_env()
        assert paths.data_dir == tmp_path
        assert paths.database == tmp_path / "swish_database.json"


class TestScanStateIO:
    def test_load_missing_returns_empty(self, tmp_path: Path) -> None:
        state = _load_state(tmp_path / "no_state.json")
        assert state.processed == []
        assert state.queue == []
        assert state.blocked == []
        assert state.last_catalog_count is None

    def test_save_and_reload_roundtrip(self, tmp_path: Path) -> None:
        state = ScanState(
            processed=["1", "2"],
            blocked=["3"],
            queue=["4"],
            last_catalog_count=10,
        )
        path = tmp_path / "state.json"
        _save_state(path, state)
        loaded = _load_state(path)
        assert loaded.processed == ["1", "2"]
        assert loaded.blocked == ["3"]
        assert loaded.queue == ["4"]
        assert loaded.last_catalog_count == 10


class TestDatabaseIO:
    def test_load_missing_returns_empty(self, tmp_path: Path) -> None:
        records = _load_database(tmp_path / "no_db.json")
        assert records == []

    def test_save_and_reload_roundtrip(self, tmp_path: Path) -> None:
        records = [{"benefit_id": "111", "benefit_name": "A", "stores": ["Zeus"], "scraped_at": "2026-01-01"}]
        path = tmp_path / "db.json"
        _save_database(path, records)
        loaded = _load_database(path)
        assert loaded == records

    def test_save_is_atomic(self, tmp_path: Path) -> None:
        path = tmp_path / "db.json"
        _save_database(path, [{"benefit_id": "1"}])
        # Must be valid JSON (no partial writes)
        with path.open(encoding="utf-8") as f:
            assert json.load(f) == [{"benefit_id": "1"}]
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/unit/scraping/test_swish_scanner.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `swish_scanner` does not exist yet.

- [ ] **Step 3: Add playwright-stealth to pyproject.toml**

In `pyproject.toml`, change:
```toml
browser = ["playwright>=1.44,<2.0"]
```
to:
```toml
browser = ["playwright>=1.44,<2.0", "playwright-stealth>=1.0,<2.0"]
```

Install: `pip install -e ".[browser]"`

- [ ] **Step 4: Create swish_scanner.py with dataclasses and I/O helpers**

```python
# src/lessley_deals/scraping/helpers/swish_scanner.py
from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CATALOG_URL = "https://swish.co.il/home/all-gifts-giftcard"
PRODUCT_URL = "https://swish.co.il/home/all-gifts-giftcard/product-{pid}"
BLOCK_TEXT = "אוי, נראה שמשהו הפסיק לעבוד"


@dataclass
class SwishPaths:
    data_dir: Path
    database: Path
    state: Path
    session: Path

    @classmethod
    def from_env(cls) -> "SwishPaths":
        root = Path(os.getenv("SWISH_DATA_DIR", "data/swish"))
        return cls(
            data_dir=root,
            database=root / "swish_database.json",
            state=root / "scan_state.json",
            session=root / "session",
        )


@dataclass
class ScanState:
    processed: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    queue: list[str] = field(default_factory=list)
    last_catalog_count: int | None = None


@dataclass
class CatalogResult:
    ids_found: list[str]
    new_ids: list[str]
    stable: bool


@dataclass
class SwishRunSummary:
    catalog_stable: bool
    ids_total: int
    records_new: int
    records_retried: int
    still_missing: list[str]
    attempts: int


def _atomic_write_json(path: Path, payload: Any) -> None:
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


def _load_state(path: Path) -> ScanState:
    if not path.exists():
        return ScanState()
    with path.open(encoding="utf-8") as f:
        d = json.load(f)
    return ScanState(
        processed=d.get("processed", []),
        blocked=d.get("blocked", []),
        queue=d.get("queue", []),
        last_catalog_count=d.get("last_catalog_count"),
    )


def _save_state(path: Path, state: ScanState) -> None:
    _atomic_write_json(path, {
        "processed": state.processed,
        "blocked": state.blocked,
        "queue": state.queue,
        "last_catalog_count": state.last_catalog_count,
    })


def _load_database(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def _save_database(path: Path, records: list[dict[str, Any]]) -> None:
    _atomic_write_json(path, records)


def _reconcile_state(state: ScanState, pid: str) -> None:
    """Move pid from queue/blocked into processed."""
    if pid not in state.processed:
        state.processed.append(pid)
    state.queue = [q for q in state.queue if q != pid]
    state.blocked = [b for b in state.blocked if b != pid]
```

- [ ] **Step 5: Run tests — verify pass**

```bash
pytest tests/unit/scraping/test_swish_scanner.py -v -k "TestSwishPaths or TestScanStateIO or TestDatabaseIO"
```

Expected: all 7 tests pass.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/lessley_deals/scraping/helpers/swish_scanner.py tests/unit/scraping/test_swish_scanner.py
git commit -m "feat: add SwishPaths, ScanState, file I/O helpers for swish scanner"
```

---

## Task 2: Static HTML parsers on SwishScanner

**Files:**
- Modify: `src/lessley_deals/scraping/helpers/swish_scanner.py`
- Modify: `tests/unit/scraping/test_swish_scanner.py`

- [ ] **Step 1: Write failing tests for HTML parsers**

Add to `tests/unit/scraping/test_swish_scanner.py`:

```python
from lessley_deals.scraping.helpers.swish_scanner import SwishScanner


class TestExtractProductIds:
    def test_extracts_ids_from_catalog_links(self) -> None:
        html = (
            '<a href="/home/all-gifts-giftcard/product-111">A</a>'
            '<a href="/home/all-gifts-giftcard/product-222">B</a>'
        )
        ids = SwishScanner._extract_product_ids(html)
        assert ids == ["111", "222"]

    def test_deduplicates_ids_preserving_order(self) -> None:
        html = "/product-111 /product-222 /product-111"
        ids = SwishScanner._extract_product_ids(html)
        assert ids == ["111", "222"]

    def test_empty_html_returns_empty(self) -> None:
        assert SwishScanner._extract_product_ids("<html>no products</html>") == []


class TestExtractProductData:
    def test_extracts_store_names_and_benefit_name(self) -> None:
        # Simulate RSC payload with escaped quotes
        html = (
            r'self.__next_f.push([1, "{\"whatWillUGet\":\"Spa day\",'
            r'\"tagsChains\":[{\"chainsByWallet\":[{\"storeName\":\"Zeus Spa\"},'
            r'{\"storeName\":\"Hamei Gaash\"}]}]}"])'
        )
        result = SwishScanner._extract_product_data(html, "123")
        assert result is not None
        assert result["benefit_id"] == "123"
        assert result["benefit_name"] == "Spa day"
        assert result["stores"] == ["Zeus Spa", "Hamei Gaash"]

    def test_deduplicates_store_names(self) -> None:
        html = r'self.__next_f.push([1, "{\"storeName\":\"Zeus\",\"storeName\":\"Zeus\"}"])'
        # Both occurrences present in raw HTML
        html2 = (
            r'something \"storeName\":\"Zeus\" and again \"storeName\":\"Zeus\" end'
        )
        result = SwishScanner._extract_product_data(html2, "999")
        if result is not None:
            assert result["stores"].count("Zeus") == 1

    def test_returns_none_when_no_store_names(self) -> None:
        result = SwishScanner._extract_product_data("<html>no stores here</html>", "999")
        assert result is None

    def test_fallback_to_h1_for_benefit_name(self) -> None:
        html = '<h1 class="title">My Benefit</h1>\"storeName\":\"Store A\"'
        result = SwishScanner._extract_product_data(html, "456")
        assert result is not None
        assert result["benefit_name"] == "My Benefit"
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/unit/scraping/test_swish_scanner.py -v -k "TestExtract"
```

Expected: `AttributeError` — `SwishScanner` does not exist.

- [ ] **Step 3: Add SwishScanner class skeleton with static parsers**

Append to `src/lessley_deals/scraping/helpers/swish_scanner.py`:

```python
import random
import re
import time
from datetime import datetime, timezone


class SwishScanner:
    """Stateful Swish gift-card scraper.

    Holds one Playwright browser context for the duration of a run.
    Use as a context manager:

        with SwishScanner(paths=SwishPaths.from_env()) as scanner:
            scanner.catalog()
            scanner.scan()
    """

    def __init__(
        self,
        paths: SwishPaths,
        *,
        scan_limit: int | None = None,
    ) -> None:
        self._paths = paths
        self._scan_limit = scan_limit
        self._pw: Any = None
        self._context: Any = None
        self._page: Any = None

    # ------------------------------------------------------------------
    # Static HTML parsers (no browser dependency — easily unit-tested)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_product_ids(html: str) -> list[str]:
        hits = re.findall(r"/product-(\d+)", html)
        return list(dict.fromkeys(hits))

    @staticmethod
    def _extract_product_data(html: str, pid: str) -> dict[str, Any] | None:
        unescaped = html.replace('\\"', '"')
        store_names = re.findall(r'"storeName":"([^"]+)"', unescaped)
        if not store_names:
            return None
        benefit_names = re.findall(r'"whatWillUGet":"([^"]+)"', unescaped)
        benefit_name = benefit_names[0] if benefit_names else None
        if not benefit_name:
            h1 = re.search(r"<h1[^>]*>\s*([^<]+)\s*</h1>", html)
            benefit_name = h1.group(1).strip() if h1 else None
        return {
            "benefit_id": pid,
            "benefit_name": benefit_name,
            "stores": list(dict.fromkeys(store_names)),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }
```

- [ ] **Step 4: Run tests — verify pass**

```bash
pytest tests/unit/scraping/test_swish_scanner.py -v -k "TestExtract"
```

Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/lessley_deals/scraping/helpers/swish_scanner.py tests/unit/scraping/test_swish_scanner.py
git commit -m "feat: add SwishScanner skeleton with static HTML parsers"
```

---

## Task 3: SwishScanner browser context manager + block detection

**Files:**
- Modify: `src/lessley_deals/scraping/helpers/swish_scanner.py`
- Modify: `tests/unit/scraping/test_swish_scanner.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/scraping/test_swish_scanner.py`:

```python
from unittest.mock import MagicMock, patch


class TestIsBlocked:
    def test_not_blocked_when_locator_returns_zero(self, tmp_path: Path) -> None:
        paths = make_paths(tmp_path)
        scanner = SwishScanner(paths=paths)
        mock_page = MagicMock()
        mock_page.locator.return_value.count.return_value = 0
        assert scanner._is_blocked(mock_page) is False

    def test_blocked_when_locator_returns_nonzero(self, tmp_path: Path) -> None:
        paths = make_paths(tmp_path)
        scanner = SwishScanner(paths=paths)
        mock_page = MagicMock()
        mock_page.locator.return_value.count.return_value = 1
        assert scanner._is_blocked(mock_page) is True

    def test_blocked_returns_false_on_exception(self, tmp_path: Path) -> None:
        paths = make_paths(tmp_path)
        scanner = SwishScanner(paths=paths)
        mock_page = MagicMock()
        mock_page.locator.side_effect = RuntimeError("page closed")
        assert scanner._is_blocked(mock_page) is False
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/unit/scraping/test_swish_scanner.py -v -k "TestIsBlocked"
```

Expected: `AttributeError` — `_is_blocked` not defined.

- [ ] **Step 3: Add `_is_blocked` + context manager to SwishScanner**

Add to the `SwishScanner` class (inside the class body, after `_extract_product_data`):

```python
    def _is_blocked(self, page: Any) -> bool:
        try:
            return page.locator(f"text={BLOCK_TEXT}").count() > 0  # type: ignore[no-any-return]
        except Exception:
            return False

    def __enter__(self) -> "SwishScanner":
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth

        self._paths.session.mkdir(parents=True, exist_ok=True)
        self._pw = sync_playwright().__enter__()
        headless = os.getenv("SWISH_HEADLESS", "1") == "1"
        self._context = self._pw.chromium.launch_persistent_context(
            str(self._paths.session),
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        Stealth().apply_stealth_sync(self._context)
        self._page = self._context.new_page()
        return self

    def __exit__(self, *exc: Any) -> None:
        try:
            if self._context is not None:
                self._context.close()
        finally:
            if self._pw is not None:
                self._pw.__exit__(*exc)
```

- [ ] **Step 4: Run tests — verify pass**

```bash
pytest tests/unit/scraping/test_swish_scanner.py -v -k "TestIsBlocked"
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/lessley_deals/scraping/helpers/swish_scanner.py tests/unit/scraping/test_swish_scanner.py
git commit -m "feat: add SwishScanner browser context manager and block detection"
```

---

## Task 4: SwishScanner.catalog() — two-phase catalog scrape

**Files:**
- Modify: `src/lessley_deals/scraping/helpers/swish_scanner.py`
- Modify: `tests/unit/scraping/test_swish_scanner.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/scraping/test_swish_scanner.py`:

```python
class TestCatalog:
    def _make_scanner_with_page(self, tmp_path: Path, mock_page: MagicMock) -> SwishScanner:
        scanner = SwishScanner(paths=make_paths(tmp_path))
        scanner._page = mock_page
        return scanner

    def test_stable_catalog_same_ids_both_passes(self, tmp_path: Path) -> None:
        mock_page = MagicMock()
        mock_page.locator.return_value.count.return_value = 0
        html = "/product-111 /product-222 /product-333"
        mock_page.content.return_value = html
        scanner = self._make_scanner_with_page(tmp_path, mock_page)

        with patch("time.sleep"):
            result = scanner.catalog()

        assert result.stable is True
        assert sorted(result.ids_found) == ["111", "222", "333"]
        assert sorted(result.new_ids) == ["111", "222", "333"]
        state = _load_state(make_paths(tmp_path).state)
        assert sorted(state.queue) == ["111", "222", "333"]
        assert state.last_catalog_count == 3

    def test_unstable_catalog_uses_union(self, tmp_path: Path) -> None:
        mock_page = MagicMock()
        mock_page.locator.return_value.count.return_value = 0
        mock_page.content.side_effect = [
            "/product-111 /product-222",       # pass 1
            "/product-111 /product-333",       # pass 2 — different
        ]
        scanner = self._make_scanner_with_page(tmp_path, mock_page)

        with patch("time.sleep"):
            result = scanner.catalog()

        assert result.stable is False
        assert sorted(result.ids_found) == ["111", "222", "333"]

    def test_already_processed_ids_not_in_new_ids(self, tmp_path: Path) -> None:
        paths = make_paths(tmp_path)
        _save_state(paths.state, ScanState(processed=["111"], queue=[], blocked=[]))

        mock_page = MagicMock()
        mock_page.locator.return_value.count.return_value = 0
        mock_page.content.return_value = "/product-111 /product-222"
        scanner = self._make_scanner_with_page(tmp_path, mock_page)

        with patch("time.sleep"):
            result = scanner.catalog()

        assert "111" not in result.new_ids
        assert "222" in result.new_ids

    def test_blocked_on_catalog_raises(self, tmp_path: Path) -> None:
        mock_page = MagicMock()
        mock_page.locator.return_value.count.return_value = 1  # blocked
        scanner = self._make_scanner_with_page(tmp_path, mock_page)

        with patch("time.sleep"), pytest.raises(RuntimeError, match="Blocked on catalog"):
            scanner.catalog()
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/unit/scraping/test_swish_scanner.py -v -k "TestCatalog"
```

Expected: `AttributeError` — `catalog` method not defined.

- [ ] **Step 3: Implement catalog()**

Add to the `SwishScanner` class:

```python
    def catalog(self) -> CatalogResult:
        """Two-phase catalog scrape. Stable when both passes return identical IDs."""
        sleep_s = int(os.getenv("SWISH_CATALOG_SLEEP_S", "30"))

        self._page.goto(CATALOG_URL, wait_until="networkidle", timeout=60_000)
        if self._is_blocked(self._page):
            raise RuntimeError("Blocked on catalog page (pass 1)")
        html1 = self._page.content()
        ids1 = self._extract_product_ids(html1)

        time.sleep(sleep_s)

        self._page.goto(CATALOG_URL, wait_until="networkidle", timeout=60_000)
        if self._is_blocked(self._page):
            logger.warning("Blocked on catalog page (pass 2) — using pass 1 results")
            ids2 = ids1[:]
        else:
            html2 = self._page.content()
            ids2 = self._extract_product_ids(html2)

        stable = sorted(ids1) == sorted(ids2)
        if not stable:
            logger.warning(
                "Catalog unstable: %d vs %d IDs — using union", len(ids1), len(ids2)
            )

        all_ids = list(dict.fromkeys(ids1 + ids2))

        state = _load_state(self._paths.state)
        processed_set = set(state.processed)
        new_ids = [pid for pid in all_ids if pid not in processed_set]
        for pid in new_ids:
            if pid not in state.queue:
                state.queue.append(pid)
        state.last_catalog_count = len(all_ids)
        _save_state(self._paths.state, state)

        return CatalogResult(ids_found=all_ids, new_ids=new_ids, stable=stable)
```

- [ ] **Step 4: Run tests — verify pass**

```bash
pytest tests/unit/scraping/test_swish_scanner.py -v -k "TestCatalog"
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/lessley_deals/scraping/helpers/swish_scanner.py tests/unit/scraping/test_swish_scanner.py
git commit -m "feat: add SwishScanner.catalog() with two-phase stability check"
```

---

## Task 5: SwishScanner.scan() — scrape queue with block handling

**Files:**
- Modify: `src/lessley_deals/scraping/helpers/swish_scanner.py`
- Modify: `tests/unit/scraping/test_swish_scanner.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/scraping/test_swish_scanner.py`:

```python
class TestScan:
    _RSC_HTML = (
        'self.__next_f.push([1, "{\\"whatWillUGet\\":\\"Spa day\\",'
        '\\"tagsChains\\":[{\\"chainsByWallet\\":[{\\"storeName\\":\\"Zeus Spa\\"}]}]}"])'
    )

    def test_scan_saves_record_and_updates_state(self, tmp_path: Path) -> None:
        paths = make_paths(tmp_path)
        _save_state(paths.state, ScanState(queue=["111"]))

        mock_page = MagicMock()
        mock_page.locator.return_value.count.return_value = 0
        mock_page.content.return_value = self._RSC_HTML

        scanner = SwishScanner(paths=paths)
        scanner._page = mock_page

        with patch("time.sleep"):
            count = scanner.scan()

        assert count == 1
        records = _load_database(paths.database)
        assert len(records) == 1
        assert records[0]["benefit_id"] == "111"
        assert records[0]["benefit_name"] == "Spa day"

        state = _load_state(paths.state)
        assert "111" in state.processed
        assert "111" not in state.queue

    def test_block_moves_id_to_blocked(self, tmp_path: Path) -> None:
        paths = make_paths(tmp_path)
        _save_state(paths.state, ScanState(queue=["222"]))

        mock_page = MagicMock()
        mock_page.locator.return_value.count.return_value = 1  # blocked

        scanner = SwishScanner(paths=paths)
        scanner._page = mock_page

        with patch("time.sleep"):
            count = scanner.scan()

        assert count == 0
        state = _load_state(paths.state)
        assert "222" in state.blocked
        assert "222" not in state.queue

    def test_already_saved_id_is_reconciled_without_fetch(self, tmp_path: Path) -> None:
        paths = make_paths(tmp_path)
        _save_state(paths.state, ScanState(queue=["333"]))
        _save_database(paths.database, [
            {"benefit_id": "333", "benefit_name": "Existing", "stores": [], "scraped_at": ""}
        ])

        mock_page = MagicMock()
        scanner = SwishScanner(paths=paths)
        scanner._page = mock_page

        with patch("time.sleep"):
            scanner.scan()

        # page.goto should NOT have been called — ID already in database
        mock_page.goto.assert_not_called()
        state = _load_state(paths.state)
        assert "333" in state.processed

    def test_scan_limit_respected(self, tmp_path: Path) -> None:
        paths = make_paths(tmp_path)
        _save_state(paths.state, ScanState(queue=["1", "2", "3"]))

        mock_page = MagicMock()
        mock_page.locator.return_value.count.return_value = 0
        mock_page.content.return_value = self._RSC_HTML

        scanner = SwishScanner(paths=paths, scan_limit=1)
        scanner._page = mock_page

        with patch("time.sleep"):
            count = scanner.scan()

        assert count == 1
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/unit/scraping/test_swish_scanner.py -v -k "TestScan"
```

Expected: `AttributeError` — `scan` not defined.

- [ ] **Step 3: Implement scan()**

Add to the `SwishScanner` class:

```python
    def scan(self) -> int:
        """Scrape every pending ID in state.queue → append records to swish_database.json."""
        from playwright.sync_api import TimeoutError as PlaywrightTimeout

        state = _load_state(self._paths.state)
        records = _load_database(self._paths.database)
        saved_ids = {r["benefit_id"] for r in records}

        fresh = [pid for pid in state.queue if pid not in state.blocked]
        random.shuffle(fresh)
        ids_to_scan = state.blocked[:] + fresh

        if self._scan_limit is not None:
            ids_to_scan = ids_to_scan[: self._scan_limit]

        new_count = 0
        for pid in ids_to_scan:
            if pid in saved_ids:
                _reconcile_state(state, pid)
                _save_state(self._paths.state, state)
                continue

            url = PRODUCT_URL.format(pid=pid)
            logger.info("Scanning ID %s", pid)
            try:
                self._page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                self._page.wait_for_timeout(2000)

                if self._is_blocked(self._page):
                    if pid not in state.blocked:
                        state.blocked.append(pid)
                    state.queue = [q for q in state.queue if q != pid]
                    _save_state(self._paths.state, state)
                    cooldown = random.uniform(20, 60)
                    logger.warning("Blocked on %s — cooldown %.0fs", pid, cooldown)
                    time.sleep(cooldown)
                    continue

                html = self._page.content()
                record = self._extract_product_data(html, pid)
                if record is None:
                    logger.warning("No RSC data for ID %s — will retry later", pid)
                    continue

                records.append(record)
                saved_ids.add(pid)
                _save_database(self._paths.database, records)
                _reconcile_state(state, pid)
                _save_state(self._paths.state, state)
                new_count += 1
                logger.info(
                    "Saved: %s (%d stores)", record.get("benefit_name"), len(record.get("stores", []))
                )

            except PlaywrightTimeout:
                logger.warning("Timeout on ID %s — will retry", pid)
            except Exception as exc:
                logger.error("Error on ID %s: %s", pid, exc)

            time.sleep(random.uniform(5, 12))

        return new_count
```

- [ ] **Step 4: Run tests — verify pass**

```bash
pytest tests/unit/scraping/test_swish_scanner.py -v -k "TestScan"
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/lessley_deals/scraping/helpers/swish_scanner.py tests/unit/scraping/test_swish_scanner.py
git commit -m "feat: add SwishScanner.scan() with block detection and state reconciliation"
```

---

## Task 6: SwishScanner.retry() + verify_complete() + run_all()

**Files:**
- Modify: `src/lessley_deals/scraping/helpers/swish_scanner.py`
- Modify: `tests/unit/scraping/test_swish_scanner.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/scraping/test_swish_scanner.py`:

```python
class TestVerifyComplete:
    def test_complete_when_all_ids_have_records(self, tmp_path: Path) -> None:
        paths = make_paths(tmp_path)
        _save_state(paths.state, ScanState(processed=["111", "222"]))
        _save_database(paths.database, [
            {"benefit_id": "111", "benefit_name": "A", "stores": [], "scraped_at": ""},
            {"benefit_id": "222", "benefit_name": "B", "stores": [], "scraped_at": ""},
        ])
        scanner = SwishScanner(paths=paths)
        ok, missing = scanner.verify_complete()
        assert ok is True
        assert missing == []

    def test_incomplete_returns_missing_ids(self, tmp_path: Path) -> None:
        paths = make_paths(tmp_path)
        _save_state(paths.state, ScanState(processed=["111", "222", "333"]))
        _save_database(paths.database, [
            {"benefit_id": "111", "benefit_name": "A", "stores": [], "scraped_at": ""},
        ])
        scanner = SwishScanner(paths=paths)
        ok, missing = scanner.verify_complete()
        assert ok is False
        assert sorted(missing) == ["222", "333"]

    def test_queued_and_blocked_ids_included_in_check(self, tmp_path: Path) -> None:
        paths = make_paths(tmp_path)
        _save_state(paths.state, ScanState(
            processed=["111"],
            queue=["222"],
            blocked=["333"],
        ))
        _save_database(paths.database, [
            {"benefit_id": "111", "benefit_name": "A", "stores": [], "scraped_at": ""},
        ])
        scanner = SwishScanner(paths=paths)
        ok, missing = scanner.verify_complete()
        assert ok is False
        assert sorted(missing) == ["222", "333"]


class TestRetry:
    _RSC_HTML = (
        'self.__next_f.push([1, "{\\"whatWillUGet\\":\\"Spa day\\",'
        '\\"tagsChains\\":[{\\"chainsByWallet\\":[{\\"storeName\\":\\"Zeus Spa\\"}]}]}"])'
    )

    def test_retry_recovers_blocked_id(self, tmp_path: Path) -> None:
        paths = make_paths(tmp_path)
        _save_state(paths.state, ScanState(blocked=["444"], processed=["444"]))

        mock_page = MagicMock()
        mock_page.locator.return_value.count.return_value = 0
        mock_page.content.return_value = self._RSC_HTML

        scanner = SwishScanner(paths=paths)
        scanner._page = mock_page

        with patch("time.sleep"):
            count = scanner.retry()

        assert count == 1
        state = _load_state(paths.state)
        assert "444" not in state.blocked
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/unit/scraping/test_swish_scanner.py -v -k "TestVerify or TestRetry"
```

Expected: `AttributeError` — methods not defined.

- [ ] **Step 3: Implement verify_complete() + retry() + run_all()**

Add to the `SwishScanner` class:

```python
    def verify_complete(self) -> tuple[bool, list[str]]:
        """Check every known ID has an entry in swish_database.json."""
        state = _load_state(self._paths.state)
        records = _load_database(self._paths.database)
        saved_ids = {r["benefit_id"] for r in records}
        all_known = set(state.processed) | set(state.queue) | set(state.blocked)
        missing = [pid for pid in all_known if pid not in saved_ids]
        return len(missing) == 0, missing

    def retry(self) -> int:
        """Re-queue blocked IDs and IDs with no record, then run scan()."""
        state = _load_state(self._paths.state)
        records = _load_database(self._paths.database)
        saved_ids = {r["benefit_id"] for r in records}

        all_known = set(state.processed) | set(state.queue) | set(state.blocked)
        missing_no_record = [pid for pid in all_known if pid not in saved_ids]

        ids_to_retry = list(dict.fromkeys(state.blocked + missing_no_record))
        if not ids_to_retry:
            logger.info("Nothing to retry")
            return 0

        for pid in ids_to_retry:
            if pid not in state.queue:
                state.queue.append(pid)
        for pid in state.blocked[:]:
            state.blocked.remove(pid)
        _save_state(self._paths.state, state)

        return self.scan()

    def run_all(self, *, max_attempts: int = 3) -> SwishRunSummary:
        """Full run: catalog → (scan → retry → verify) loop → return summary.

        The caller (swish-all CLI) is responsible for running sync_swish_groups
        after this method returns.
        """
        catalog_result = self.catalog()
        records_new = 0
        records_retried = 0
        attempts = 0

        for attempt in range(max_attempts):
            attempts = attempt + 1
            records_new += self.scan()
            recovered = self.retry()
            records_retried += recovered
            ok, missing = self.verify_complete()
            if ok:
                break
            logger.warning("Attempt %d/%d: %d IDs still missing", attempts, max_attempts, len(missing))

        _, still_missing = self.verify_complete()
        return SwishRunSummary(
            catalog_stable=catalog_result.stable,
            ids_total=len(catalog_result.ids_found),
            records_new=records_new,
            records_retried=records_retried,
            still_missing=still_missing,
            attempts=attempts,
        )
```

- [ ] **Step 4: Run tests — verify pass**

```bash
pytest tests/unit/scraping/test_swish_scanner.py -v
```

Expected: all tests in this file pass.

- [ ] **Step 5: Commit**

```bash
git add src/lessley_deals/scraping/helpers/swish_scanner.py tests/unit/scraping/test_swish_scanner.py
git commit -m "feat: add SwishScanner.verify_complete(), retry(), run_all()"
```

---

## Task 7: SwishAdapter — emit RawStore only, no deals

**Files:**
- Modify: `src/lessley_deals/scraping/sources/swish.py`
- Create: `tests/unit/scraping/test_swish_adapter.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/scraping/test_swish_adapter.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lessley_deals.scraping.base import SourceConfig
from lessley_deals.scraping.sources.swish import SwishAdapter


@pytest.fixture
def swish_db(tmp_path: Path) -> Path:
    records = [
        {
            "benefit_id": "101",
            "benefit_name": "Spa Package",
            "stores": ["Zeus Spa", "Hamei Gaash", "Zeus Spa"],  # duplicate intentional
            "scraped_at": "2026-01-01T00:00:00",
        },
        {
            "benefit_id": "202",
            "benefit_name": "Shopping Card",
            "stores": ["Renuar", "Zeus Spa"],  # Zeus already seen in 101
            "scraped_at": "2026-01-01T00:00:00",
        },
    ]
    path = tmp_path / "swish_database.json"
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_swish_adapter_emits_raw_stores_not_deals(swish_db: Path, tmp_path: Path) -> None:
    adapter = SwishAdapter(SourceConfig(base_url="https://swish.co.il"), database_path=swish_db)
    stores, deals = await adapter.scrape()

    assert deals == [], "SwishAdapter must never emit deals"
    assert len(stores) > 0


@pytest.mark.asyncio
async def test_swish_adapter_deduplicates_member_names(swish_db: Path) -> None:
    adapter = SwishAdapter(SourceConfig(base_url="https://swish.co.il"), database_path=swish_db)
    stores, _ = await adapter.scrape()

    store_names = [s.name for s in stores]
    # "Zeus Spa" appears in benefit 101 (twice) and 202 — should be emitted once
    assert store_names.count("Zeus Spa") == 1


@pytest.mark.asyncio
async def test_swish_adapter_emits_one_store_per_unique_member(swish_db: Path) -> None:
    adapter = SwishAdapter(SourceConfig(base_url="https://swish.co.il"), database_path=swish_db)
    stores, _ = await adapter.scrape()

    # Unique members: "Zeus Spa", "Hamei Gaash", "Renuar" = 3
    assert len(stores) == 3


@pytest.mark.asyncio
async def test_swish_adapter_returns_empty_when_db_missing(tmp_path: Path) -> None:
    adapter = SwishAdapter(
        SourceConfig(base_url="https://swish.co.il"),
        database_path=tmp_path / "no_file.json",
    )
    stores, deals = await adapter.scrape()
    assert stores == []
    assert deals == []
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/unit/scraping/test_swish_adapter.py -v
```

Expected: tests fail — current adapter emits deals.

- [ ] **Step 3: Rewrite SwishAdapter.scrape()**

Replace the entire `scrape()` method in `src/lessley_deals/scraping/sources/swish.py`:

```python
    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        """Read swish_database.json and emit one RawStore per unique member business.

        No RawScrapedRecord is emitted — Swish is an enrichment source, not a
        deal source.  The emitted RawStore objects enter the normal pipeline
        (normalize → match → persist) to populate the canonical store catalog
        and feed the review queue for unresolved names.
        """
        if not self._database_path.exists():
            logger.warning(
                "Swish database not found at %s — skipping", self._database_path
            )
            return [], []

        with self._database_path.open(encoding="utf-8") as f:
            records = json.load(f)
        if not isinstance(records, list):
            logger.error(
                "Swish database has unexpected shape: %s", type(records).__name__
            )
            return [], []

        now = datetime.now(timezone.utc)
        seen_names: set[str] = set()
        stores: list[RawStore] = []

        for record in records:
            benefit_id = str(record.get("benefit_id") or "").strip()
            for raw_name in record.get("stores", []):
                name = str(raw_name).strip()
                if not name or name in seen_names:
                    continue
                seen_names.add(name)
                stores.append(
                    RawStore(
                        id=generate_id(),
                        source_id=self.source_id,
                        name=name,
                        scraped_at=now,
                        raw_payload={"benefit_id": benefit_id, "source": "swish"},
                    )
                )

        logger.info("Swish adapter emitted %d stores (0 deals)", len(stores))
        return stores, []
```

Also remove unused imports from `swish.py` that were used by the old deal-emitting code:
- Remove: `GroupMember`, `_normalize_member_entries`, `load_hot_store_groups` (if no longer referenced)

Check the import block at the top of `swish.py` and remove any imports only needed for the old `RawScrapedRecord`-emitting logic.

- [ ] **Step 4: Run tests — verify pass**

```bash
pytest tests/unit/scraping/test_swish_adapter.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Run full test suite to catch regressions**

```bash
pytest -m "not integration" -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/lessley_deals/scraping/sources/swish.py tests/unit/scraping/test_swish_adapter.py
git commit -m "feat: SwishAdapter emits RawStore-only, drops fake deal records"
```

---

## Task 8: sync_swish_groups — widen dedup to all pending names

**Files:**
- Modify: `src/lessley_deals/scraping/helpers/swish_group_sync.py`
- Modify: `tests/unit/scraping/test_swish_group_sync.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/scraping/test_swish_group_sync.py`:

```python
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lessley_deals.domain.enums import MatchDecision
from lessley_deals.domain.models import Explanation, MatchVerdict, ReviewItem
from lessley_deals.matching.index import AliasIndex
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.review.queue import ReviewQueue
from lessley_deals.scraping.helpers.swish_group_sync import (
    _build_name_forms,
    sync_swish_groups,
)


def _make_no_match_verdict(name: str, raw_id: str) -> MatchVerdict:
    return MatchVerdict(
        record_id=raw_id,
        input_name=name,
        decision=MatchDecision.NO_MATCH,
        candidates=(),
        explanation=Explanation(stages_run=(), reason="no match", stage_matched=None),
    )


def test_cross_benefit_dedup_creates_only_one_review_item(tmp_path: Path) -> None:
    """Same raw store name in two benefits → single review item."""
    db = [
        {"benefit_id": "101", "benefit_name": "A", "stores": ["רנואר"]},
        {"benefit_id": "202", "benefit_name": "B", "stores": ["רנואר"]},
    ]
    db_path = tmp_path / "swish_database.json"
    db_path.write_text(json.dumps(db, ensure_ascii=False), encoding="utf-8")

    alias_index = AliasIndex(aliases=[], stores=[])
    queue = ReviewQueue(ReviewJsonRepository(tmp_path / "review.json"))

    result = sync_swish_groups(db_path, alias_index, queue)

    pending = queue.get_pending()
    review_names = [item.raw_input_name for item in pending]
    assert review_names.count("רנואר") == 1
    assert result.pre_existing_review_skipped == 1


def test_name_already_pending_from_other_source_prevents_push(tmp_path: Path) -> None:
    """Name already in queue from non-Swish source → not pushed again."""
    review_repo = ReviewJsonRepository(tmp_path / "review.json")
    existing = ReviewItem(
        id="existing-id",
        raw_id="hot::רנואר",
        input_name="רנואר",
        input_name_forms=_build_name_forms("רנואר"),
        raw_input_name="רנואר",
        verdict=_make_no_match_verdict("רנואר", "hot::רנואר"),
        created_at=datetime.now(timezone.utc),
    )
    review_repo.save(existing)

    db = [{"benefit_id": "101", "benefit_name": "A", "stores": ["רנואר"]}]
    db_path = tmp_path / "swish_database.json"
    db_path.write_text(json.dumps(db, ensure_ascii=False), encoding="utf-8")

    queue = ReviewQueue(review_repo)
    alias_index = AliasIndex(aliases=[], stores=[])

    result = sync_swish_groups(db_path, alias_index, queue)

    assert result.review_items_created == 0
    assert result.pre_existing_review_skipped == 1
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/unit/scraping/test_swish_group_sync.py -v -k "cross_benefit or other_source"
```

Expected: `test_cross_benefit_dedup` fails (2 items created, not 1). `test_name_already_pending_from_other_source` fails (item pushed despite existing name).

- [ ] **Step 3: Replace `_existing_pending_review_keys` with `_existing_pending_names`**

In `src/lessley_deals/scraping/helpers/swish_group_sync.py`:

Replace:
```python
def _existing_pending_review_keys(queue: ReviewQueue) -> set[str]:
    """Return ``{group_key|raw_name}`` for every pending GROUP_MEMBER_MATCH item.

    Used to skip pushing duplicate review items when re-running the sync —
    otherwise every sync would multiply the queue.
    """
    keys: set[str] = set()
    for item in queue.get_pending():
        if not item.raw_id.startswith(SWISH_GROUP_PREFIX):
            continue
        # raw_id format: "swish:<benefit_id>::<raw_member_name>"
        keys.add(item.raw_id)
    return keys
```

With:
```python
def _existing_pending_names(queue: ReviewQueue) -> set[str]:
    """Return exact ``raw_input_name`` of every pending review item.

    Dedup is done on the raw name string, not on the raw_id prefix.
    This prevents the same store name being pushed multiple times when it
    appears in more than one Swish benefit, or when it is already pending
    from a different source.
    """
    return {item.raw_input_name for item in queue.get_pending() if item.raw_input_name}
```

In `sync_swish_groups()`, replace the three lines that use `pending_keys` with `pending_names`:

Line `pending_keys = _existing_pending_review_keys(review_queue)` → `pending_names = _existing_pending_names(review_queue)`

Line `if review_record_id in pending_keys:` → `if raw_name in pending_names:`

Line `pending_keys.add(review_record_id)` → `pending_names.add(raw_name)`

- [ ] **Step 4: Run tests — verify pass**

```bash
pytest tests/unit/scraping/test_swish_group_sync.py -v
```

Expected: all pass.

- [ ] **Step 5: Run full test suite**

```bash
pytest -m "not integration" -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/lessley_deals/scraping/helpers/swish_group_sync.py tests/unit/scraping/test_swish_group_sync.py
git commit -m "fix: widen swish_group_sync dedup to all pending review names"
```

---

## Task 9: CLI commands — swish-catalog, swish-scan, swish-retry, swish-all

**Files:**
- Modify: `src/lessley_deals/cli/main.py`

No new test file — CLI commands are thin wrappers; tested via existing unit tests and manual smoke-test.

- [ ] **Step 1: Add `_swish_paths` helper and four commands**

In `src/lessley_deals/cli/main.py`, add after the `sync_swish_groups_cmd` function (after line 376):

```python
# ---------------------------------------------------------------------------
# Swish CLI helpers
# ---------------------------------------------------------------------------

def _swish_paths(data_dir: str | None) -> "SwishPaths":
    from lessley_deals.scraping.helpers.swish_scanner import SwishPaths
    if data_dir is not None:
        os.environ["SWISH_DATA_DIR"] = data_dir
    return SwishPaths.from_env()


_SWISH_DATA_DIR_OPT: Optional[str] = typer.Option(
    None,
    "--data-dir",
    "-d",
    help="Swish data directory. Overrides $SWISH_DATA_DIR (default: data/swish).",
)


@app.command(name="swish-catalog")
def swish_catalog_cmd(
    data_dir: Optional[str] = _SWISH_DATA_DIR_OPT,
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Map all Swish gift-card IDs via two-phase catalog scrape."""
    _setup_logging(log_level)
    from lessley_deals.scraping.helpers.swish_scanner import SwishScanner

    with SwishScanner(paths=_swish_paths(data_dir)) as scanner:
        result = scanner.catalog()

    console.print(
        f"Catalog: {len(result.ids_found)} IDs found "
        f"({len(result.new_ids)} new, {len(result.ids_found) - len(result.new_ids)} already processed). "
        f"Stable: {result.stable}"
    )
    if not result.stable:
        raise typer.Exit(code=2)


@app.command(name="swish-scan")
def swish_scan_cmd(
    data_dir: Optional[str] = _SWISH_DATA_DIR_OPT,
    limit: int = typer.Option(0, "--limit", help="Max IDs to scrape this run (0=unlimited)."),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Scrape pending Swish gift-card IDs into swish_database.json."""
    _setup_logging(log_level)
    from lessley_deals.scraping.helpers.swish_scanner import SwishScanner

    with SwishScanner(paths=_swish_paths(data_dir), scan_limit=limit or None) as scanner:
        count = scanner.scan()

    console.print(f"Scan complete: {count} new records saved.")


@app.command(name="swish-retry")
def swish_retry_cmd(
    data_dir: Optional[str] = _SWISH_DATA_DIR_OPT,
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Retry blocked/failed Swish gift-card IDs."""
    _setup_logging(log_level)
    from lessley_deals.scraping.helpers.swish_scanner import SwishScanner

    with SwishScanner(paths=_swish_paths(data_dir)) as scanner:
        count = scanner.retry()

    console.print(f"Retry complete: {count} records recovered.")


@app.command(name="swish-all")
def swish_all_cmd(
    data_dir: Optional[str] = _SWISH_DATA_DIR_OPT,
    deals_data_dir: str = typer.Option(
        "data", "--deals-data-dir", help="Deals data directory (for review queue, stores, aliases)."
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Full Swish run: catalog → scan → retry loop → sync-swish-groups."""
    _setup_logging(log_level)
    from lessley_deals.matching.index import AliasIndex
    from lessley_deals.scraping.helpers.swish_group_sync import sync_swish_groups
    from lessley_deals.scraping.helpers.swish_scanner import SwishScanner

    paths = _swish_paths(data_dir)

    with SwishScanner(paths=paths) as scanner:
        summary = scanner.run_all()

    console.print(
        f"Swish run: {summary.ids_total} IDs, "
        f"{summary.records_new} new, {summary.records_retried} retried, "
        f"{len(summary.still_missing)} still missing, {summary.attempts} attempt(s). "
        f"Catalog stable: {summary.catalog_stable}"
    )
    if summary.still_missing:
        console.print(
            f"[yellow]Warning: {len(summary.still_missing)} IDs have no record after {summary.attempts} attempts[/yellow]"
        )

    repos = _make_repos(deals_data_dir)
    index = AliasIndex(
        aliases=repos.alias_repo.get_all(),
        stores=repos.store_repo.get_all(),
    )
    queue = ReviewQueue(repos.review_repo)
    sync_result = sync_swish_groups(
        swish_db_path=paths.database,
        alias_index=index,
        review_queue=queue,
    )
    console.print(
        f"Sync: {sync_result.benefits_processed} benefits, "
        f"[green]{sync_result.members_resolved} resolved[/green], "
        f"[yellow]{sync_result.members_to_review} to review[/yellow], "
        f"{sync_result.review_items_created} new review items."
    )

    if summary.still_missing:
        raise typer.Exit(code=2)
```

- [ ] **Step 2: Update sync-swish-groups default `--swish-db`**

In the existing `sync_swish_groups_cmd` function, change:
```python
    swish_db: str = typer.Option(
        "swish_database.json",
        "--swish-db",
        help="Path to swish_database.json (the Swish scraper output).",
    ),
```
to:
```python
    swish_db: Optional[str] = typer.Option(
        None,
        "--swish-db",
        help="Path to swish_database.json. Defaults to $SWISH_DATA_DIR/swish_database.json.",
    ),
```

And update the path resolution inside the function body (after `_setup_logging`):
```python
    from lessley_deals.scraping.helpers.swish_scanner import SwishPaths
    resolved_db = Path(swish_db) if swish_db else SwishPaths.from_env().database
    if not resolved_db.exists():
        console.print(f"[red]Swish database not found at {resolved_db}[/red]")
        raise typer.Exit(code=1)
    result = sync_swish_groups(
        swish_db_path=resolved_db,
        alias_index=index,
        review_queue=queue,
    )
```

Remove the `db_path` variable (now `resolved_db` replaces it).

- [ ] **Step 3: Smoke-test CLI registration**

```bash
python -m deals --help
```

Expected output includes: `swish-catalog`, `swish-scan`, `swish-retry`, `swish-all` in the commands list.

```bash
python -m deals swish-catalog --help
python -m deals swish-scan --help
python -m deals swish-retry --help
python -m deals swish-all --help
```

Expected: each prints usage without error.

- [ ] **Step 4: Run full test suite**

```bash
pytest -m "not integration" -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/lessley_deals/cli/main.py
git commit -m "feat: add swish-catalog, swish-scan, swish-retry, swish-all CLI commands"
```

---

## Task 10: Docker — Dockerfile.swish + entrypoint + crontab + compose

**Files:**
- Create: `Dockerfile.swish`
- Create: `docker/swish-crontab`
- Create: `docker/swish-entrypoint.sh`
- Modify: `docker-compose.yml` (create if absent)

- [ ] **Step 1: Create docker/ directory and crontab template**

```bash
mkdir -p docker
```

Create `docker/swish-crontab`:
```
SWISH_CRON_PLACEHOLDER  root  cd /app && python -m deals swish-all >> /var/log/swish.log 2>&1
# (newline required at end of crontab)
```

- [ ] **Step 2: Create docker/swish-entrypoint.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

# Substitute cron schedule env var into the crontab
sed -i "s|SWISH_CRON_PLACEHOLDER|${SWISH_CRON}|" /etc/cron.d/swish
crontab /etc/cron.d/swish

# Ensure data directories exist
mkdir -p "${SWISH_DATA_DIR}" "${DEALS_DATA_DIR}"

# Create log file and make it readable by tail
touch /var/log/swish.log

# Optional immediate run (set SWISH_RUN_ON_START=1 in compose or docker run)
if [ "${SWISH_RUN_ON_START:-0}" = "1" ]; then
    python -m deals swish-all >> /var/log/swish.log 2>&1 &
fi

# Start cron daemon in background
cron

# Tail the log to stdout so `docker logs swish-scanner` shows all output
exec tail -F /var/log/swish.log
```

Make executable:
```bash
chmod +x docker/swish-entrypoint.sh
```

- [ ] **Step 3: Create Dockerfile.swish**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# System deps: cron + tini (PID 1 signal handling) + Chromium system libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    tini \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python package + browser extra (playwright + playwright-stealth)
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e ".[browser]"
RUN playwright install --with-deps chromium

# Cron setup
COPY docker/swish-crontab /etc/cron.d/swish
RUN chmod 0644 /etc/cron.d/swish

# Entrypoint
COPY docker/swish-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Environment defaults (all overridable via docker-compose / docker run -e)
ENV SWISH_DATA_DIR=/app/data/swish
ENV DEALS_DATA_DIR=/app/data
ENV SWISH_CRON="0 3 1 * *"
ENV SWISH_RUN_ON_START=0
ENV SWISH_HEADLESS=1
ENV SWISH_CATALOG_SLEEP_S=30

# Mount point for all persistent state (swish + deals data + config)
VOLUME ["/app/data"]

# tini as PID 1 prevents Chromium zombie processes
ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
```

- [ ] **Step 4: Add swish-scanner service to docker-compose.yml**

If `docker-compose.yml` does not exist, create it. If it exists, add the service.

```yaml
services:
  swish-scanner:
    build:
      context: .
      dockerfile: Dockerfile.swish
    environment:
      SWISH_CRON: "0 3 1 * *"         # 03:00 on the 1st of each month
      SWISH_DATA_DIR: /app/data/swish
      DEALS_DATA_DIR: /app/data
      DEALS_STORAGE: json              # change to mongo + add MONGO_URI if needed
      SWISH_RUN_ON_START: "0"
      SWISH_HEADLESS: "1"
    volumes:
      - ./data:/app/data
      - ./src/lessley_deals/scraping/config:/app/src/lessley_deals/scraping/config
    restart: unless-stopped
```

The `./src/lessley_deals/scraping/config` volume allows `sync-swish-groups` inside the container to write `hot_store_groups.json` back to the host.

- [ ] **Step 5: Build and verify image builds**

```bash
docker build -f Dockerfile.swish -t swish-scanner:test .
```

Expected: build succeeds, Playwright + Chromium installed without error.

- [ ] **Step 6: Smoke-test container CLI**

```bash
docker run --rm swish-scanner:test python -m deals --help
```

Expected: CLI help printed including `swish-catalog`, `swish-all`, etc.

```bash
docker run --rm -e SWISH_HEADLESS=1 swish-scanner:test python -m deals swish-catalog --help
```

Expected: usage printed.

- [ ] **Step 7: Commit**

```bash
git add Dockerfile.swish docker/ docker-compose.yml
git commit -m "feat: add Dockerfile.swish with internal cron for monthly swish-all"
```

---

## Task 11: Delete test_swish.py + move session dir reference

**Files:**
- Delete: `test_swish.py`
- Delete: `scan_state.json` (repo root artifact — now lives in `data/swish/`)
- Delete: `swish_database.json` (repo root artifact — now lives in `data/swish/`)
- Delete: `get-all-benefits-swish.html` (debug artifact)
- Delete: `swish-product.html` (debug artifact)
- Modify: `.gitignore` — add `data/swish/` exclusion

- [ ] **Step 1: Remove root-level artifacts**

```bash
git rm test_swish.py scan_state.json swish_database.json get-all-benefits-swish.html swish-product.html
```

- [ ] **Step 2: Update .gitignore**

Open `.gitignore` (create if absent) and add:

```
# Swish scraper state and session
data/swish/
```

- [ ] **Step 3: Run full test suite to confirm nothing broken**

```bash
pytest -m "not integration" -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: remove test_swish.py and root-level scan artifacts, gitignore data/swish/"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task that implements it |
|---|---|
| Automated monthly Docker + cron scrape | Task 10 |
| Capture ALL gift cards — two-phase stability | Task 4 (catalog) |
| Retry loop until complete | Task 6 (retry + run_all) |
| SwishAdapter RawStore-only, no fake deals | Task 7 |
| Swish adds unresolved businesses to review queue | Task 8 (dedup fix + existing sync_swish_groups mechanism) |
| Cross-benefit dedup — exact string on pending names | Task 8 |
| swish-catalog / swish-scan / swish-retry / swish-all commands | Task 9 |
| sync-swish-groups updated default path | Task 9, Step 2 |
| Delete test_swish.py | Task 11 |
| playwright-stealth in dependencies | Task 1, Step 3 |
| SWISH_DATA_DIR / SWISH_CRON / SWISH_HEADLESS env vars | Tasks 1, 3, 10 |

All spec requirements covered. No gaps.
