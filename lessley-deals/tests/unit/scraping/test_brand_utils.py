from __future__ import annotations

import pytest

from lessley_deals.scraping.helpers.brand_utils import (
    classify_group_deal,
    clean_brand,
    clean_store_name,
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


class TestCleanStoreName:
    def test_strips_suffix_tavim(self) -> None:
        assert clean_store_name("קבוצת גולף - תווים") == "קבוצת גולף"

    def test_strips_prefix_tavim(self) -> None:
        assert clean_store_name("תווים - פוד אפיל") == "פוד אפיל"

    def test_strips_leading_tav_kniya(self) -> None:
        assert clean_store_name("תו קניה sabon") == "sabon"

    def test_regular_name_unchanged(self) -> None:
        assert clean_store_name("sabon") == "sabon"

    def test_empty(self) -> None:
        assert clean_store_name("") == ""

    def test_strips_whitespace_variants(self) -> None:
        assert clean_store_name("תווים  -  פוד אפיל") == "פוד אפיל"
        assert clean_store_name("קבוצת בריל  -  תווים") == "קבוצת בריל"


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


# ---------------------------------------------------------------------------
# minimal inline groups fixture — avoids dependency on the real JSON file
# ---------------------------------------------------------------------------

_TEST_GROUPS: dict = {
    "קבוצת גולף - תווים": {
        "title_prefix": "תו קניה",
        "stores": ["kitan", "sabon", "golf&co", "golf", "polgat"],
    },
    "קבוצת פוקס - תווים": {
        "title_prefix": "תו קניה",
        "stores": ["fox", "fox home", "terminal x", "laline", "mango"],
    },
}


class TestClassifyGroupDeal:
    """Tests for classify_group_deal()."""

    # --- store-specific deals ---

    def test_store_specific_exact_match(self) -> None:
        name, is_wide, members = classify_group_deal(
            "קבוצת גולף - תווים", "תו קניה sabon", _TEST_GROUPS
        )
        assert name == "sabon"
        assert is_wide is False
        assert members == []

    def test_store_specific_case_insensitive(self) -> None:
        # The canonical name from the whitelist is returned (lowercase "sabon"),
        # regardless of how the store appears in the title.
        name, is_wide, members = classify_group_deal(
            "קבוצת גולף - תווים", "תו קניה SABON", _TEST_GROUPS
        )
        assert name == "sabon"
        assert is_wide is False
        assert members == []

    def test_store_specific_trailing_text_in_title(self) -> None:
        """Trailing content after the store name (e.g. amount) is stripped."""
        name, is_wide, members = classify_group_deal(
            "קבוצת גולף - תווים", "תו קניה sabon 200 ₪", _TEST_GROUPS
        )
        assert name == "sabon"
        assert is_wide is False
        assert members == []

    def test_store_specific_different_subgroup(self) -> None:
        name, is_wide, members = classify_group_deal(
            "קבוצת פוקס - תווים", "תו קניה fox", _TEST_GROUPS
        )
        assert name == "fox"
        assert is_wide is False
        assert members == []

    def test_unrecognised_substore_treated_as_specific(self) -> None:
        """A name extracted from the title that isn’t in the whitelist is still
        returned as a store-specific deal (conservative approach)."""
        name, is_wide, members = classify_group_deal(
            "קבוצת גולף - תווים", "תו קניה UNKNOWN STORE", _TEST_GROUPS
        )
        assert name == "UNKNOWN STORE"
        assert is_wide is False
        assert members == []

    # --- group-wide gift cards ---

    def test_group_wide_when_prefix_strips_to_group_name(self) -> None:
        name, is_wide, members = classify_group_deal(
            "קבוצת גולף - תווים",
            "תו קניה קבוצת גולף - תווים",
            _TEST_GROUPS,
        )
        assert is_wide is True
        assert "קבוצת גולף" in name
        assert "sabon" in members
        assert "kitan" in members

    def test_group_wide_when_title_has_no_prefix(self) -> None:
        """When the title doesn’t start with the prefix, treat as group-wide."""
        name, is_wide, members = classify_group_deal(
            "קבוצת גולף - תווים", "הנחה כללית לבנת הקבוצה", _TEST_GROUPS
        )
        assert is_wide is True
        assert len(members) > 0

    # --- non-group brands ---

    def test_non_group_brand_returned_unchanged(self) -> None:
        name, is_wide, members = classify_group_deal(
            "AHAVA", "הנחה 20% בAHAVA", _TEST_GROUPS
        )
        assert name == "AHAVA"
        assert is_wide is False
        assert members == []

    def test_group_lookup_case_insensitive(self) -> None:
        """קבוצת with different case still resolves."""
        name, is_wide, _members = classify_group_deal(
            "קבוצת גולף - תווים", "תו קניה sabon", _TEST_GROUPS
        )
        assert name == "sabon"
        assert is_wide is False


class TestResolveGroupStoreBackwardCompat:
    """Ensure resolve_group_store() still behaves as before (calls classify_group_deal)."""

    def test_known_substore(self) -> None:
        assert resolve_group_store("קבוצת פוקס - תווים", "תו קניה fox", _TEST_GROUPS) == "fox"

    def test_non_group_brand(self) -> None:
        assert resolve_group_store("AHAVA", "הנחה בAHAVA", _TEST_GROUPS) == "AHAVA"

    def test_group_wide_returns_group_name(self) -> None:
        """For group-wide deals, resolve_group_store returns the group brand itself."""
        result = resolve_group_store(
            "קבוצת גולף - תווים", "תו קניה קבוצת גולף - תווים", _TEST_GROUPS
        )
        assert "קבוצת גולף" in result
