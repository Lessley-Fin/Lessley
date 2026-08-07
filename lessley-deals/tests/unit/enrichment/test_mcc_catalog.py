from __future__ import annotations

import pytest

from lessley_deals.enrichment.mcc_catalog import (
    CATEGORY_SET,
    FALLBACK_CATEGORY,
    MCC_CATEGORIES,
    SPELLING_ALIASES,
    category_by_numeric_code,
    category_for_numeric_code,
    coerce_category,
    normalize_mcc_codes,
    unresolvable_codes,
)


class TestVocabulary:
    def test_has_the_full_canonical_set(self) -> None:
        assert len(MCC_CATEGORIES) == 46
        assert len(CATEGORY_SET) == 46
        assert FALLBACK_CATEGORY in CATEGORY_SET

    def test_every_category_is_reachable_from_a_numeric_code(self) -> None:
        assert set(category_by_numeric_code().values()) == CATEGORY_SET

    def test_numeric_map_only_yields_canonical_names(self) -> None:
        assert all(c in CATEGORY_SET for c in category_by_numeric_code().values())


class TestCategoryForNumericCode:
    @pytest.mark.parametrize(
        ("code", "expected"),
        [(5411, "GROCERIES"), ("5411", "GROCERIES"), ("0742", "PETS"), (742, "PETS")],
    )
    def test_resolves_padded_and_unpadded(self, code: int | str, expected: str) -> None:
        assert category_for_numeric_code(code) == expected

    def test_unknown_code_is_none(self) -> None:
        assert category_for_numeric_code(9999) is None

    def test_non_numeric_is_none(self) -> None:
        assert category_for_numeric_code("GROCERIES") is None


class TestCoerceCategory:
    @pytest.mark.parametrize(
        "value",
        ["GROCERIES", "groceries", "  Groceries  ", 5411, "5411"],
    )
    def test_accepts_names_and_numbers(self, value: object) -> None:
        assert coerce_category(value) == "GROCERIES"

    @pytest.mark.parametrize(
        "value",
        [
            "HOUSEHOLD_&_SERVICES_-_OTHER",
            "household & services - other",
            "Household & Services - Other",
        ],
    )
    def test_tolerates_punctuation_variants(self, value: str) -> None:
        assert coerce_category(value) == "HOUSEHOLD_&_SERVICES_-_OTHER"

    @pytest.mark.parametrize("value", [None, "", "   ", "NOT_A_CATEGORY", True, 9999])
    def test_rejects_unresolvable(self, value: object) -> None:
        assert coerce_category(value) is None


class TestNormalizeMccCodes:
    def test_maps_legacy_numeric_list(self) -> None:
        assert normalize_mcc_codes([5411, 5812]) == ["GROCERIES", "RESTAURANT"]

    def test_preserves_rank_order(self) -> None:
        assert normalize_mcc_codes(["RESTAURANT", "GROCERIES"]) == ["RESTAURANT", "GROCERIES"]

    def test_drops_duplicates_keeping_first_position(self) -> None:
        assert normalize_mcc_codes(["GROCERIES", 5411, "RESTAURANT"]) == [
            "GROCERIES",
            "RESTAURANT",
        ]

    def test_drops_unresolvable_entries(self) -> None:
        assert normalize_mcc_codes(["GROCERIES", "NOPE", 9999]) == ["GROCERIES"]

    def test_truncates_to_max_codes(self) -> None:
        codes = ["GROCERIES", "RESTAURANT", "BARS", "PHARMACY"]
        assert normalize_mcc_codes(codes) == ["GROCERIES", "RESTAURANT", "BARS"]
        assert normalize_mcc_codes(codes, max_codes=2) == ["GROCERIES", "RESTAURANT"]

    def test_accepts_a_bare_scalar(self) -> None:
        assert normalize_mcc_codes("GROCERIES") == ["GROCERIES"]
        assert normalize_mcc_codes(5411) == ["GROCERIES"]

    def test_empty_without_fallback_stays_empty(self) -> None:
        assert normalize_mcc_codes(None) == []
        assert normalize_mcc_codes([]) == []
        assert normalize_mcc_codes(["NOPE"]) == []

    def test_fallback_guarantees_a_value(self) -> None:
        assert normalize_mcc_codes(["NOPE"], fallback=FALLBACK_CATEGORY) == [FALLBACK_CATEGORY]


class TestUnresolvableCodes:
    def test_reports_only_the_bad_entries(self) -> None:
        assert unresolvable_codes(["GROCERIES", "NOPE", 5411, 9999]) == ["NOPE", 9999]

    def test_empty_for_clean_input(self) -> None:
        assert unresolvable_codes(["GROCERIES", 5411]) == []
        assert unresolvable_codes(None) == []


class TestSpellingAliases:
    def test_every_alias_targets_a_real_category(self) -> None:
        assert set(SPELLING_ALIASES.values()) <= CATEGORY_SET

    def test_no_alias_shadows_a_canonical_name(self) -> None:
        assert not set(SPELLING_ALIASES) & CATEGORY_SET

    @pytest.mark.parametrize("alias,expected", sorted(SPELLING_ALIASES.items()))
    def test_alias_resolves_to_its_canonical_name(self, alias: str, expected: str) -> None:
        assert coerce_category(alias) == expected
        assert coerce_category(alias.lower()) == expected

    def test_restuarant_typo_survives_normalization(self) -> None:
        """The classifier emits this spelling; it must not be dropped.

        Before the alias existed it was rejected as off-vocabulary, so a store
        the model had confidently called a restaurant fell back to OTHER.
        """
        assert normalize_mcc_codes(["RESTUARANT"]) == ["RESTAURANT"]
        assert unresolvable_codes(["RESTUARANT"]) == []
        assert normalize_mcc_codes(["RESTUARANT"], fallback=FALLBACK_CATEGORY) == ["RESTAURANT"]

    def test_alias_deduplicates_against_the_canonical_name(self) -> None:
        assert normalize_mcc_codes(["RESTAURANT", "RESTUARANT", "BARS"]) == ["RESTAURANT", "BARS"]
