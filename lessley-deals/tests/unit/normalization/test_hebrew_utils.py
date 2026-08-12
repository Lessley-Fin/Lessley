from __future__ import annotations

import pytest

from lessley_deals.normalization.hebrew_utils import (
    normalize_final_forms,
    normalize_geresh,
    normalize_hebrew,
    normalize_presentation_forms,
    strip_niqqud,
    strip_zero_width,
)


class TestStripNiqqud:
    def test_removes_vowel_points(self) -> None:
        assert strip_niqqud("\u05e9\u05c1\u05b8\u05dc\u05d5\u05b9\u05dd") == "\u05e9\u05dc\u05d5\u05dd"

    def test_no_change_on_plain_text(self) -> None:
        assert strip_niqqud("\u05e9\u05dc\u05d5\u05dd") == "\u05e9\u05dc\u05d5\u05dd"

    def test_empty_string(self) -> None:
        assert strip_niqqud("") == ""

    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("\u05d0\u05b2\u05e0\u05b4\u05d9", "\u05d0\u05e0\u05d9"),  # אֲנִי -> אני
            ("\u05d9\u05b0\u05e8\u05d5\u05bc\u05e9\u05b8\u05c1\u05dc\u05b7\u05d9\u05b4\u05dd",
             "\u05d9\u05e8\u05d5\u05e9\u05dc\u05d9\u05dd"),  # ירושלים with niqqud
        ],
    )
    def test_parametrized_niqqud_cases(self, input_text: str, expected: str) -> None:
        assert strip_niqqud(input_text) == expected


class TestNormalizeFinalForms:
    def test_all_final_forms(self) -> None:
        assert normalize_final_forms("\u05dd\u05df\u05e5\u05e3\u05da") == "\u05de\u05e0\u05e6\u05e4\u05db"

    def test_mixed_text(self) -> None:
        # "שלום" with final mem -> "שלומ" with regular mem
        assert normalize_final_forms("\u05e9\u05dc\u05d5\u05dd") == "\u05e9\u05dc\u05d5\u05de"

    def test_no_final_forms(self) -> None:
        text = "\u05d0\u05d1\u05d2"
        assert normalize_final_forms(text) == text

    def test_empty_string(self) -> None:
        assert normalize_final_forms("") == ""


class TestNormalizeGeresh:
    def test_geresh_to_apostrophe(self) -> None:
        # ג׳ינס -> ג'ינס
        assert normalize_geresh("\u05d2\u05f3\u05d9\u05e0\u05e1") == "\u05d2'\u05d9\u05e0\u05e1"

    def test_gershayim_to_double_quote(self) -> None:
        assert normalize_geresh("\u05f4") == '"'

    def test_no_geresh(self) -> None:
        text = "hello"
        assert normalize_geresh(text) == text


class TestStripZeroWidth:
    def test_removes_zero_width_space(self) -> None:
        assert strip_zero_width("hello\u200bworld") == "helloworld"

    def test_removes_bidi_controls(self) -> None:
        assert strip_zero_width("\u202ahello\u202e") == "hello"

    def test_removes_feff(self) -> None:
        assert strip_zero_width("\ufefftest") == "test"

    def test_preserves_normal_text(self) -> None:
        assert strip_zero_width("normal text") == "normal text"

    def test_empty_string(self) -> None:
        assert strip_zero_width("") == ""


class TestNormalizePresentationForms:
    def test_decomposes_presentation_form(self) -> None:
        # FB2A is shin with shin dot -> should decompose to shin
        result = normalize_presentation_forms("\ufb2a")
        assert "\u05e9" in result  # contains base shin

    def test_no_change_on_regular_text(self) -> None:
        text = "\u05e9\u05dc\u05d5\u05dd"
        assert normalize_presentation_forms(text) == text


class TestNormalizeHebrew:
    """Combined test ensuring all normalizations are applied in order."""

    def test_combined_normalization(self) -> None:
        # Text with niqqud, final forms, geresh, and zero-width chars
        text = "\u05e9\u05c1\u05b8\u05dc\u05d5\u05b9\u05dd\u200b"  # שָׁלוֹם + zero-width
        result = normalize_hebrew(text)
        # niqqud stripped, final mem -> regular mem, zero-width removed
        assert result == "\u05e9\u05dc\u05d5\u05de"

    def test_geresh_in_combined(self) -> None:
        text = "\u05d2\u05f3\u05d9\u05e0\u05e1"  # ג׳ינס
        result = normalize_hebrew(text)
        assert "'" in result
        assert "\u05f3" not in result

    @pytest.mark.parametrize(
        "input_text",
        [
            "",
            "plain ascii",
            "123",
        ],
    )
    def test_safe_on_non_hebrew(self, input_text: str) -> None:
        """normalize_hebrew must not crash or corrupt non-Hebrew text."""
        result = normalize_hebrew(input_text)
        assert isinstance(result, str)
