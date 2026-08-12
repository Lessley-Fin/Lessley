from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

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
            "/product-111 /product-222",
            "/product-111 /product-333",
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
