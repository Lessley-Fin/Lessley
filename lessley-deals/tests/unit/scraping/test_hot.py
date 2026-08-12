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
        assert record.items() <= deal.raw_payload.items()
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

    def test_to_raw_store_none_for_generic_hot_brand(self) -> None:
        adapter = HotAdapter(SourceConfig(base_url="https://www.hot.co.il"))
        record = _make_api_record(brand="מועדון הוט")
        now = datetime.now(timezone.utc)
        store = adapter._to_raw_store(record, now)

        assert store is None

    def test_clean_brand_strips_suffix(self) -> None:
        assert HotAdapter._clean_brand("ShareSpa - שר ספא הרצליה_2") == "ShareSpa - שר ספא הרצליה"

    def test_benefit_types_default(self) -> None:
        from lessley_deals.scraping.sources.hot import BENEFIT_TYPES
        adapter = HotAdapter(SourceConfig(base_url="https://www.hot.co.il"))
        assert adapter._benefit_types == BENEFIT_TYPES

    def test_benefit_types_custom(self) -> None:
        adapter = HotAdapter(
            SourceConfig(base_url="https://www.hot.co.il"),
            benefit_types=("100", "300"),
        )
        assert adapter._benefit_types == ("100", "300")

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


class TestHotAdapterDealType:
    """benefit_type -> deal-optimizer DealType mapping (confirmed against live data)."""

    @pytest.mark.parametrize(
        ("benefit_type", "expected"),
        [
            ("100", "payment_discount"),
            ("700", "coupon"),
            ("800", "coupon"),
            ("1300", "giftcard_discount"),
        ],
    )
    def test_mapped_benefit_types(self, benefit_type: str, expected: str) -> None:
        adapter = HotAdapter(SourceConfig(base_url="https://www.hot.co.il"))
        record = _make_api_record(benefit_type=benefit_type)
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)

        assert deal.raw_payload["deal_type"] == expected

    @pytest.mark.parametrize("benefit_type", ["300", "1100", "1200", "", "9999"])
    def test_unmapped_benefit_types_leave_deal_type_none(self, benefit_type: str) -> None:
        # deal-optimizer's own infer_deal_type() text-based fallback handles
        # these when deal_type is left unset.
        adapter = HotAdapter(SourceConfig(base_url="https://www.hot.co.il"))
        record = _make_api_record(benefit_type=benefit_type)
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)

        assert deal.raw_payload["deal_type"] is None

    def test_falls_back_to_type_field_when_benefit_type_absent(self) -> None:
        # The detail-merged shape carries the same code under "type" instead
        # of "benefit_type" (see deduce_hot_discount_mechanics's docstring).
        adapter = HotAdapter(SourceConfig(base_url="https://www.hot.co.il"))
        record = _make_api_record(type="1300")
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)

        assert deal.raw_payload["deal_type"] == "giftcard_discount"


# ---------------------------------------------------------------------------
# Inline groups fixture so tests are isolated from the real JSON file
# ---------------------------------------------------------------------------

_TEST_GROUPS: dict = {
    "קבוצת גולף": {
        "title_prefix": "תו קניה",
        "stores": ["kitan", "sabon", "golf&co", "golf", "polgat"],
    },
}


class TestHotAdapterGroupBrands:
    """Tests for group-brand classification in _to_raw_deal / _to_raw_store."""

    def _make_adapter(self) -> HotAdapter:
        adapter = HotAdapter(SourceConfig(base_url="https://www.hot.co.il"))
        adapter._store_groups = _TEST_GROUPS  # type: ignore[assignment]
        return adapter

    def test_to_raw_deal_store_specific_group(self) -> None:
        """Brand is a group but title encodes a specific sub-store."""
        adapter = self._make_adapter()
        record = _make_api_record(
            brand="קבוצת גולף",
            title="תו קניה sabon",
        )
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)

        assert deal.store_name == "sabon"
        assert "group_member_stores" not in deal.raw_payload

    def test_to_raw_deal_group_wide(self) -> None:
        """Brand is a group and title doesn’t resolve to a known sub-store."""
        adapter = self._make_adapter()
        record = _make_api_record(
            brand="קבוצת גולף",
            title="תו קניה קבוצת גולף - תווים",
        )
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(record, now)

        # store_name stays as the group so it gets its own CanonicalStore
        assert "קבוצת גולף" in deal.store_name
        # group_member_stores must be present in the payload
        assert "group_member_stores" in deal.raw_payload
        members = deal.raw_payload["group_member_stores"]
        assert isinstance(members, list)
        assert "sabon" in members
        assert "kitan" in members

    def test_to_raw_store_group_wide_keeps_group_name(self) -> None:
        """A group-wide deal produces a RawStore with the group name."""
        adapter = self._make_adapter()
        record = _make_api_record(
            brand="קבוצת גולף",
            title="תו קניה קבוצת גולף - תווים",
        )
        now = datetime.now(timezone.utc)
        store = adapter._to_raw_store(record, now)

        assert store is not None
        assert "קבוצת גולף" in store.name

    def test_to_raw_store_store_specific_uses_substore_name(self) -> None:
        """A store-specific group deal produces a RawStore with the sub-store name."""
        adapter = self._make_adapter()
        record = _make_api_record(
            brand="קבוצת גולף",
            title="תו קניה sabon",
        )
        now = datetime.now(timezone.utc)
        store = adapter._to_raw_store(record, now)

        assert store is not None
        assert store.name == "sabon"

    def test_to_raw_deal_original_record_not_mutated(self) -> None:
        """The original API record dict must not be modified."""
        adapter = self._make_adapter()
        record = _make_api_record(
            brand="קבוצת גולף",
            title="תו קניה קבוצת גולף - תווים",
        )
        import copy
        original = copy.deepcopy(record)
        now = datetime.now(timezone.utc)
        adapter._to_raw_deal(record, now)

        assert record == original, "Original record was mutated"
