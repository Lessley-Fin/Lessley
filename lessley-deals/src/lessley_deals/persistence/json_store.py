from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any


def _atomic_replace(src: str, dst: str, *, retries: int = 5, delay: float = 0.1) -> None:
    """Replace ``dst`` with ``src`` atomically.

    On Windows, ``os.replace()`` can fail with ``PermissionError`` (WinError 5)
    when the destination file is momentarily locked by another process (e.g. an
    editor or antivirus).  We retry a few times with a short back-off before
    giving up.
    """
    for attempt in range(retries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if not sys.platform.startswith("win") or attempt == retries - 1:
                raise
            time.sleep(delay * (attempt + 1))


class JsonStore:
    """Atomic JSON file read/write with thread-level locking.

    Uses tempfile + os.replace() for atomic writes (safe on NTFS and ext4/xfs).
    Always resolves the path to absolute so that os.replace() works correctly
    regardless of the process working directory.
    """

    def __init__(self, path: Path) -> None:
        # Resolve to absolute path immediately so relative paths never cause
        # os.replace() failures on Windows when CWD changes.
        self._path = path.resolve()
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def read(self) -> list[dict[str, Any]]:
        with self._lock:
            if not self._path.exists():
                return []
            text = self._path.read_text(encoding="utf-8")
            if not text.strip():
                return []
            data = json.loads(text)
            if not isinstance(data, list):
                raise ValueError(f"Expected JSON array in {self._path}, got {type(data).__name__}")
            return data

    def write(self, data: list[dict[str, Any]]) -> None:
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self._path.parent),
                suffix=".tmp",
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                    f.flush()
                    os.fsync(f.fileno())
                _atomic_replace(tmp_path, str(self._path))
            except BaseException:
                # Clean up temp file on failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

    def append(self, item: dict[str, Any]) -> None:
        data = self.read()
        data.append(item)
        self.write(data)

    def append_many(self, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        data = self.read()
        data.extend(items)
        self.write(data)

    def update_by_id(self, item_id: str, updated: dict[str, Any]) -> bool:
        data = self.read()
        for i, item in enumerate(data):
            if item.get("id") == item_id:
                data[i] = updated
                self.write(data)
                return True
        return False
