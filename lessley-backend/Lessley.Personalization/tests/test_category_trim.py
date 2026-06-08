"""
Unit tests for Process 2 category trimming by match level.

Spec examples: 16 categories at 25% -> keep 12, at 50% -> keep 8, at 75% -> keep 4.
"""

from services.insights_service import trim_categories_by_match_level


def _categories(n):
    return [{"category": f"cat_{i}"} for i in range(n)]


def test_trim_examples_from_spec():
    cats = _categories(16)
    assert len(trim_categories_by_match_level(cats, 0.25)) == 12
    assert len(trim_categories_by_match_level(cats, 0.50)) == 8
    assert len(trim_categories_by_match_level(cats, 0.75)) == 4


def test_trim_keeps_top_in_order():
    cats = _categories(16)
    kept = trim_categories_by_match_level(cats, 0.75)
    assert kept == cats[:4]  # highest-relevance categories retained, in order


def test_none_score_keeps_all():
    cats = _categories(10)
    assert trim_categories_by_match_level(cats, None) == cats


def test_empty_categories():
    assert trim_categories_by_match_level([], 0.5) == []


def test_keeps_at_least_one():
    cats = _categories(2)
    # 2 * (1 - 0.99) -> round(0.02) = 0, clamped up to 1
    assert len(trim_categories_by_match_level(cats, 0.99)) == 1


def test_score_clamped_to_valid_range():
    cats = _categories(8)
    assert trim_categories_by_match_level(cats, 1.5) == cats[:1]   # clamp to 1.0
    assert trim_categories_by_match_level(cats, -0.5) == cats      # clamp to 0.0


if __name__ == "__main__":
    test_trim_examples_from_spec()
    test_trim_keeps_top_in_order()
    test_none_score_keeps_all()
    test_empty_categories()
    test_keeps_at_least_one()
    test_score_clamped_to_valid_range()
    print("All category-trim tests passed.")
