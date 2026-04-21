from __future__ import annotations

import json
from pathlib import Path

import pytest  # noqa: TCH002

from lessley_deals.scraping.helpers.swish_scanner import (
    ScanState,
    SwishPaths,
    SwishScanner,
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


class TestExtractProductIds:
    def test_extracts_ids_from_catalog_links(self) -> None:
        html = (
            '<a href="/home/all-gifts-giftcard/product-111">A</a><a href="/home/all-gifts-giftcard/product-222">B</a>'
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
        html = (
            r'self.__next_f.push([1, "{\"whatWillUGet\":\"Spa day\",'
            r"\"tagsChains\":[{\"chainsByWallet\":[{\"storeName\":\"Zeus Spa\"},"
            r'{\"storeName\":\"Hamei Gaash\"}]}]}"])'
        )
        result = SwishScanner._extract_product_data(html, "123")
        assert result is not None
        assert result["benefit_id"] == "123"
        assert result["benefit_name"] == "Spa day"
        assert result["stores"] == ["Zeus Spa", "Hamei Gaash"]

    def test_returns_none_when_no_store_names(self) -> None:
        result = SwishScanner._extract_product_data("<html>no stores here</html>", "999")
        assert result is None

    def test_fallback_to_h1_for_benefit_name(self) -> None:
        html = '<h1 class="title">My Benefit</h1>"storeName":"Store A"'
        result = SwishScanner._extract_product_data(html, "456")
        assert result is not None
        assert result["benefit_name"] == "My Benefit"
