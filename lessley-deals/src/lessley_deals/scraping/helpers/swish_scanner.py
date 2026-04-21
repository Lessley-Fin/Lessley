from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import tempfile
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
        self._pw: Any = None
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
