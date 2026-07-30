from __future__ import annotations

import pytest
from lessley_deals.scraping.sources.mastercard import _TEASER_ID_RE, MastercardAdapter
from lessley_deals.scraping.base import SourceConfig


class TestTeaserIdRegex:
    def test_matches_current_teaser_wrapper_id(self) -> None:
        # Mastercard's current per-deal wrapper divs: <div id="teaser-<hex>">
        assert _TEASER_ID_RE.match("teaser-6008b2906c")

    def test_does_not_match_child_image_id(self) -> None:
        # Child elements like <div id="teaser-<hex>-image"> are not deal wrappers.
        assert _TEASER_ID_RE.match("teaser-dcaa103fe5-image") is None


class TestMastercardAdapter:
    def test_source_id(self) -> None:
        adapter = MastercardAdapter(SourceConfig(base_url="https://www.mastercard.co.il"))
        assert adapter.source_id == "mastercard"

    def test_extract_title_splits_on_period(self) -> None:
        adapter = MastercardAdapter(SourceConfig(base_url="https://www.mastercard.co.il"))
        assert adapter._extract_title("20% הנחה. תקף עד 31.3") == "20% הנחה"

    def test_extract_title_splits_on_hebrew_keywords(self) -> None:
        adapter = MastercardAdapter(SourceConfig(base_url="https://www.mastercard.co.il"))
        result = adapter._extract_title("50 ₪ הנחה תקף עד סוף החודש")
        assert result == "50 ₪ הנחה"

    def test_parse_discount_logic_percentage(self) -> None:
        adapter = MastercardAdapter(SourceConfig(base_url="https://www.mastercard.co.il"))
        logic = adapter._parse_discount_logic("20% הנחה על כל המוצרים", "20% הנחה")
        assert logic is not None
        assert logic["reward"]["type"] == "percentage_off"
        assert logic["reward"]["value"] == 0.2  # normalized to 0-1 range
        assert "constraints" not in logic

    def test_parse_discount_logic_spend_save(self) -> None:
        adapter = MastercardAdapter(SourceConfig(base_url="https://www.mastercard.co.il"))
        logic = adapter._parse_discount_logic("₪50 הנחה ברכישת מעל ₪250", "50 הנחה")
        assert logic is not None
        assert logic["condition"]["type"] == "min_spend"
        assert "constraints" not in logic

    def test_parse_discount_logic_none_when_no_pattern(self) -> None:
        adapter = MastercardAdapter(SourceConfig(base_url="https://www.mastercard.co.il"))
        logic = adapter._parse_discount_logic("מבצע מיוחד ללקוחות", "מבצע מיוחד")
        assert logic is None
