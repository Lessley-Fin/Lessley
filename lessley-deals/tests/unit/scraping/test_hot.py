from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from lessley_deals.scraping.sources.hot import HotAdapter
from lessley_deals.scraping.base import SourceConfig


def _make_api_record(
    record_id: int = 1001,
    brand: str = "קפה עלית",
    title: str = "הנחה 20% על קפה",
    value: str = "20%",
    small_text: str = "הנחה",
    **overrides: Any,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": record_id,
        "item_brand": brand,
        "title": title,
        "value": value,
        "small_text": small_text,
        "description": "מבצע מיוחד",
        "is_active": True,
    }
    record.update(overrides)
    return record


class TestHotAdapter:
    def test_source_id(self) -> None:
        adapter = HotAdapter(SourceConfig(base_url="https://www.hot.co.il"))
        assert adapter.source_id == "hot"

    def test_to_raw_deal_preserves_raw_payload(self) -> None:
        adapter = HotAdapter(SourceConfig(base_url="https://www.hot.co.il"))
        record = _make_api_record()
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)

        assert deal.source_id == "hot"
        assert deal.store_name == "קפה עלית"
        assert "הנחה 20% על קפה" in deal.deal_description
        assert deal.price_text == "20%"
        assert deal.raw_payload == record
        assert deal.url == "https://www.hot.co.il/benefit/1001"

    def test_to_raw_deal_fallback_title_as_store(self) -> None:
        adapter = HotAdapter(SourceConfig(base_url="https://www.hot.co.il"))
        record = _make_api_record(brand="", title="מבצע כללי")
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)

        assert deal.store_name == "מבצע כללי"

    def test_to_raw_store_creates_store(self) -> None:
        adapter = HotAdapter(SourceConfig(base_url="https://www.hot.co.il"))
        record = _make_api_record(brand="קפה עלית")
        now = datetime.now(timezone.utc)
        store = adapter._to_raw_store(record, now)

        assert store is not None
        assert store.name == "קפה עלית"
        assert store.source_id == "hot"

    def test_to_raw_store_none_when_no_brand(self) -> None:
        adapter = HotAdapter(SourceConfig(base_url="https://www.hot.co.il"))
        record = _make_api_record(brand="")
        now = datetime.now(timezone.utc)
        store = adapter._to_raw_store(record, now)

        assert store is None

    def test_to_raw_deal_price_fallback_to_small_text(self) -> None:
        adapter = HotAdapter(SourceConfig(base_url="https://www.hot.co.il"))
        record = _make_api_record(value="", small_text="1+1")
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)

        assert deal.price_text == "1+1"

    def test_to_raw_deal_no_url_when_no_id(self) -> None:
        adapter = HotAdapter(SourceConfig(base_url="https://www.hot.co.il"))
        record = _make_api_record()
        record.pop("id")
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)

        assert deal.url is None
