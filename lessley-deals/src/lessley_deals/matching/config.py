from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchConfig:
    auto_match_threshold: float = 0.90
    review_threshold: float = 0.50
    compact_discount: float = 0.95
    normalized_jw_weight: float = 0.70
    normalized_token_weight: float = 0.30
    domain_fixed_confidence: float = 0.80
    token_confidence_cap: float = 0.70
