from __future__ import annotations

import json

import pytest
from pathlib import Path

from lessley_deals.persistence.json_store import JsonStore


pytestmark = pytest.mark.integration


class TestJsonStore:
    def test_read_nonexistent_returns_empty(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "missing.json")
        assert store.read() == []

    def test_write_and_read_roundtrip(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "test.json")
        data = [{"id": "1", "name": "test"}]
        store.write(data)
        assert store.read() == data

    def test_append(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "test.json")
        store.write([{"id": "1"}])
        store.append({"id": "2"})
        result = store.read()
        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"

    def test_append_to_nonexistent_file(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "new.json")
        store.append({"id": "1"})
        assert store.read() == [{"id": "1"}]

    def test_append_many(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "test.json")
        store.write([{"id": "1"}])
        store.append_many([{"id": "2"}, {"id": "3"}])
        result = store.read()
        assert len(result) == 3
        assert [d["id"] for d in result] == ["1", "2", "3"]

    def test_append_many_empty_is_noop(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "test.json")
        store.write([{"id": "1"}])
        store.append_many([])
        assert len(store.read()) == 1

    def test_update_by_id(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "test.json")
        store.write([
            {"id": "1", "name": "old"},
            {"id": "2", "name": "keep"},
        ])
        updated = store.update_by_id("1", {"id": "1", "name": "new"})
        assert updated is True
        result = store.read()
        assert result[0]["name"] == "new"
        assert result[1]["name"] == "keep"

    def test_update_by_id_missing_returns_false(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "test.json")
        store.write([{"id": "1", "name": "old"}])
        updated = store.update_by_id("999", {"id": "999", "name": "ghost"})
        assert updated is False
        assert store.read() == [{"id": "1", "name": "old"}]

    def test_atomic_write_creates_valid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "atomic.json"
        store = JsonStore(path)
        data = [{"id": str(i), "value": f"item_{i}"} for i in range(100)]
        store.write(data)

        # Verify the file is valid JSON directly
        raw = path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert len(parsed) == 100
        assert parsed[0]["id"] == "0"
        assert parsed[99]["id"] == "99"

    def test_write_creates_parent_directories(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c" / "data.json"
        store = JsonStore(nested)
        store.write([{"id": "1"}])
        assert store.read() == [{"id": "1"}]

    def test_overwrite_replaces_content(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "test.json")
        store.write([{"id": "1"}, {"id": "2"}])
        store.write([{"id": "3"}])
        result = store.read()
        assert len(result) == 1
        assert result[0]["id"] == "3"
