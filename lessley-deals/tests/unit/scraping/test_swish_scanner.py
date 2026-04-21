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
