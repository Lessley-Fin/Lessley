from __future__ import annotations

import pytest

from lessley_deals.scraping.helpers.brand_utils import (
    clean_brand,
    is_generic_behatsdaa_brand,
    is_generic_hot_brand,
    normalize_website,
    resolve_group_store,
    to_slug,
)


class TestCleanBrand:
    def test_strip_trailing_number(self) -> None:
        assert clean_brand("ShareSpa - שר ספא הרצליה_2") == "ShareSpa - שר ספא הרצליה"

    def test_strip_single_digit(self) -> None:
        assert clean_brand("קפה עלית_1") == "קפה עלית"

    def test_no_suffix(self) -> None:
        assert clean_brand("רמי לוי") == "רמי לוי"

    def test_empty_string(self) -> None:
        assert clean_brand("") == ""

    def test_none_value(self) -> None:
        assert clean_brand(None) == ""  # type: ignore[arg-type]

    def test_whitespace_collapse(self) -> None:
        assert clean_brand("  קפה   עלית  _3") == "קפה עלית"

    def test_strip_leading_trailing_dashes(self) -> None:
        assert clean_brand("-brand-_2") == "brand"


class TestGenericBrands:
    def test_hot_generic_club_name(self) -> None:
        assert is_generic_hot_brand("מועדון הוט") is True

    def test_hot_generic_club_name_variant(self) -> None:
        assert is_generic_hot_brand("הוט מועדון צרכנות") is True

    def test_hot_generic_english(self) -> None:
        assert is_generic_hot_brand("HOT") is True
        assert is_generic_hot_brand("hot club") is True

    def test_hot_real_brand(self) -> None:
        assert is_generic_hot_brand("קפה עלית") is False

    def test_hot_empty(self) -> None:
        assert is_generic_hot_brand("") is True

    def test_behatsdaa_generic(self) -> None:
        assert is_generic_behatsdaa_brand("בהצדעה") is True
        assert is_generic_behatsdaa_brand("behatsdaa") is True

    def test_behatsdaa_real_brand(self) -> None:
        assert is_generic_behatsdaa_brand("שופרסל") is False


class TestNormalizeWebsite:
    def test_bare_domain(self) -> None:
        assert normalize_website("www.sharespa.co.il") == "sharespa.co.il"

    def test_with_https(self) -> None:
        assert normalize_website("https://shop.co.il/foo") == "shop.co.il"

    def test_empty(self) -> None:
        assert normalize_website("") is None
        assert normalize_website(None) is None

    def test_with_spaces(self) -> None:
        assert normalize_website("www. sharespa .co.il") == "sharespa.co.il"


class TestToSlug:
    def test_hebrew(self) -> None:
        assert to_slug("קפה עלית") == "קפה-עלית"

    def test_strip_suffix(self) -> None:
        assert to_slug("brand_2") == "brand"

    def test_english(self) -> None:
        assert to_slug("ShareSpa") == "sharespa"
