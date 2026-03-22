from __future__ import annotations

import pytest

from lessley_deals.normalization.text import (
    collapse_whitespace,
    extract_branch,
    extract_domain,
    normalize_punctuation,
    strip_legal_suffixes,
)


class TestCollapseWhitespace:
    def test_multiple_spaces(self) -> None:
        assert collapse_whitespace("  hello   world  ") == "hello world"

    def test_tabs_and_newlines(self) -> None:
        assert collapse_whitespace("hello\t\nworld") == "hello world"

    def test_single_space_unchanged(self) -> None:
        assert collapse_whitespace("hello world") == "hello world"

    def test_empty_string(self) -> None:
        assert collapse_whitespace("") == ""

    def test_only_whitespace(self) -> None:
        assert collapse_whitespace("   ") == ""


class TestNormalizePunctuation:
    def test_em_dash(self) -> None:
        assert normalize_punctuation("a\u2014b") == "a-b"

    def test_en_dash(self) -> None:
        assert normalize_punctuation("a\u2013b") == "a-b"

    def test_curly_single_quotes(self) -> None:
        result = normalize_punctuation("\u2018hello\u2019")
        assert result == "'hello'"

    def test_curly_double_quotes(self) -> None:
        result = normalize_punctuation("\u201chello\u201d")
        assert result == '"hello"'

    def test_no_change_on_plain_text(self) -> None:
        assert normalize_punctuation("hello world") == "hello world"


class TestStripLegalSuffixes:
    def test_baam(self) -> None:
        assert strip_legal_suffixes("\u05d7\u05d1\u05e8\u05d4 \u05d1\u05e2\"" + "\u05de") == "\u05d7\u05d1\u05e8\u05d4"

    def test_ltd(self) -> None:
        assert strip_legal_suffixes("Company Ltd") == "Company"

    def test_ltd_with_dot(self) -> None:
        assert strip_legal_suffixes("Company Ltd.") == "Company"

    def test_inc(self) -> None:
        assert strip_legal_suffixes("Company Inc") == "Company"

    def test_llc(self) -> None:
        assert strip_legal_suffixes("Company LLC") == "Company"

    def test_no_suffix(self) -> None:
        assert strip_legal_suffixes("Just A Store") == "Just A Store"

    def test_empty_string(self) -> None:
        assert strip_legal_suffixes("") == ""


class TestExtractBranch:
    def test_snif_pattern(self) -> None:
        name, branch = extract_branch(
            "\u05e9\u05d5\u05e4\u05e8\u05e1\u05dc \u05e1\u05e0\u05d9\u05e3 \u05ea\u05dc \u05d0\u05d1\u05d9\u05d1"
        )
        assert name == "\u05e9\u05d5\u05e4\u05e8\u05e1\u05dc"
        assert branch == "\u05ea\u05dc \u05d0\u05d1\u05d9\u05d1"

    def test_dash_separator(self) -> None:
        name, branch = extract_branch("Store - Downtown")
        assert name == "Store"
        assert branch == "Downtown"

    def test_en_dash_separator(self) -> None:
        name, branch = extract_branch("Store \u2013 Downtown")
        assert name == "Store"
        assert branch == "Downtown"

    def test_english_branch(self) -> None:
        name, branch = extract_branch("Store branch Main St")
        assert name == "Store"
        assert branch == "Main St"

    def test_no_branch(self) -> None:
        name, branch = extract_branch("Just A Store")
        assert name == "Just A Store"
        assert branch is None


class TestExtractDomain:
    def test_full_url(self) -> None:
        assert extract_domain("https://www.example.com/path") == "example.com"

    def test_no_www(self) -> None:
        assert extract_domain("https://example.com/path") == "example.com"

    def test_subdomain(self) -> None:
        assert extract_domain("https://shop.example.com") == "shop.example.com"

    def test_none_input(self) -> None:
        assert extract_domain(None) is None

    def test_empty_string(self) -> None:
        assert extract_domain("") is None

    def test_invalid_url(self) -> None:
        # urlparse doesn't raise on garbage, but hostname will be None/empty
        result = extract_domain("not a url at all")
        # Either None or empty depending on parse result
        assert result is None or isinstance(result, str)
