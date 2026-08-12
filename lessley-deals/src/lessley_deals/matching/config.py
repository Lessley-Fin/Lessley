from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchConfig:
    auto_match_threshold: float = 0.90
    review_threshold: float = 0.50
    compact_discount: float = 0.95
    normalized_jw_weight: float = 0.55
    normalized_token_weight: float = 0.20
    normalized_containment_weight: float = 0.25
    domain_fixed_confidence: float = 0.95
    token_confidence_cap: float = 0.70
    containment_min_token_ratio: float = 0.35
    containment_base_score: float = 0.88
