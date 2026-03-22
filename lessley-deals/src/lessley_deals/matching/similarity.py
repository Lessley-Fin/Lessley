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
