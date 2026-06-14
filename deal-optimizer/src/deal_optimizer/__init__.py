"""deal-optimizer — layered-DAG deal stacking engine.

Finds the cheapest legal combination of compatible deals for a cart, modeled as
a directed acyclic flow graph: START → deals → END.
"""

from .engine import UserContext, find_best_path, get_optimal_deal_path, optimize
from .graph import ACCEPTS_KEY, LAYER_ORDER, DealNode
from .schema import (
    Combinability,
    DealConstraints,
    DealParseResult,
    DealType,
    Eligibility,
    Limits,
    RedemptionChannels,
)
from .transform import apply_deal

__all__ = [
    "UserContext",
    "find_best_path",
    "get_optimal_deal_path",
    "optimize",
    "apply_deal",
    "DealNode",
    "LAYER_ORDER",
    "ACCEPTS_KEY",
    "DealType",
    "Combinability",
    "Limits",
    "RedemptionChannels",
    "Eligibility",
    "DealConstraints",
    "DealParseResult",
]
