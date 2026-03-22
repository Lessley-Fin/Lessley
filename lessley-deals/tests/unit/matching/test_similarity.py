from __future__ import annotations

import pytest

from lessley_deals.matching.similarity import jaro_winkler, token_jaccard


class TestJaroWinkler:
    def test_identical_strings(self) -> None:
        assert jaro_winkler("hello", "hello") == 1.0

    def test_completely_different(self) -> None:
        score = jaro_winkler("abc", "xyz")
        assert score < 0.5

    def test_similar_strings(self) -> None:
        score = jaro_winkler("kitten", "sitting")
        assert 0.4 < score < 0.9

    def test_empty_strings(self) -> None:
        assert jaro_winkler("", "") == 1.0

    def test_one_empty(self) -> None:
        assert jaro_winkler("hello", "") == 0.0

    def test_returns_float(self) -> None:
        result = jaro_winkler("test", "tset")
        assert isinstance(result, float)

    def test_symmetric(self) -> None:
        """jaro_winkler(a, b) should equal jaro_winkler(b, a)."""
        s1, s2 = "hello", "hallo"
        assert jaro_winkler(s1, s2) == pytest.approx(jaro_winkler(s2, s1))


class TestTokenJaccard:
    def test_identical_sets(self) -> None:
        tokens = ("a", "b", "c")
        assert token_jaccard(tokens, tokens) == 1.0

    def test_disjoint_sets(self) -> None:
        assert token_jaccard(("a", "b"), ("c", "d")) == 0.0

    def test_partial_overlap(self) -> None:
        score = token_jaccard(("a", "b", "c"), ("b", "c", "d"))
        # intersection = {b, c}, union = {a, b, c, d} -> 2/4 = 0.5
        assert score == pytest.approx(0.5)

    def test_empty_sets(self) -> None:
        assert token_jaccard((), ()) == 0.0

    def test_one_empty(self) -> None:
        assert token_jaccard(("a",), ()) == 0.0

    def test_duplicate_tokens_in_tuple(self) -> None:
        """Duplicates in tuples are reduced to sets internally."""
        score = token_jaccard(("a", "a", "b"), ("a", "b"))
        assert score == 1.0
