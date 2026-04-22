from __future__ import annotations

import contextlib
import json
import logging
import os
import random
import re
import tempfile
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
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
    def from_env(cls) -> SwishPaths:
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
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
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
    _atomic_write_json(
        path,
        {
            "processed": state.processed,
            "blocked": state.blocked,
            "queue": state.queue,
            "last_catalog_count": state.last_catalog_count,
        },
    )


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
        self._pw_cm: Any = None  # SyncPlaywrightContextManager
        self._pw: Any = None     # Playwright object (result of __enter__)
        self._context: Any = None
        self._page: Any = None

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
            "scraped_at": datetime.now(UTC).isoformat(),
        }

    def _is_blocked(self, page: Any) -> bool:
        try:
            return page.locator(f"text={BLOCK_TEXT}").count() > 0  # type: ignore[no-any-return]
        except Exception:
            return False

    def __enter__(self) -> SwishScanner:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth

        self._paths.session.mkdir(parents=True, exist_ok=True)
        self._pw_cm = sync_playwright()
        self._pw = self._pw_cm.__enter__()
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
            if self._pw_cm is not None:
                self._pw_cm.__exit__(*exc)

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
                    "Saved: %s (%d stores)",
                    record.get("benefit_name"),
                    len(record.get("stores", [])),
                )

            except PlaywrightTimeout:
                logger.warning("Timeout on ID %s — will retry", pid)
            except Exception as exc:
                logger.error("Error on ID %s: %s", pid, exc)

            time.sleep(random.uniform(5, 12))

        return new_count

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
            logger.warning(
                "Attempt %d/%d: %d IDs still missing", attempts, max_attempts, len(missing)
            )

        _, still_missing = self.verify_complete()
        return SwishRunSummary(
            catalog_stable=catalog_result.stable,
            ids_total=len(catalog_result.ids_found),
            records_new=records_new,
            records_retried=records_retried,
            still_missing=still_missing,
            attempts=attempts,
        )
