from __future__ import annotations

from rapidfuzz.distance import JaroWinkler


def jaro_winkler(s1: str, s2: str) -> float:
    """Return Jaro-Winkler similarity in [0.0, 1.0]."""
    return JaroWinkler.similarity(s1, s2)


def token_jaccard(tokens_a: tuple[str, ...], tokens_b: tuple[str, ...]) -> float:
    """Return Jaccard similarity over two token tuples: |A ∩ B| / |A ∪ B|."""
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def token_containment(tokens_a: tuple[str, ...], tokens_b: tuple[str, ...]) -> float:
    """Return containment similarity: |A ∩ B| / min(|A|, |B|).

    Measures the fraction of the smaller token set found in the larger set.
    Returns 1.0 when the smaller set is entirely contained in the larger,
    regardless of how many extra tokens the larger set has.

    Unlike Jaccard, extra tokens in the longer string do not dilute the score.
    """
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    min_size = min(len(set_a), len(set_b))
    if min_size == 0:
        return 0.0
    return len(set_a & set_b) / min_size
