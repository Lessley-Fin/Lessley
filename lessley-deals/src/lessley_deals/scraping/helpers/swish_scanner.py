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
