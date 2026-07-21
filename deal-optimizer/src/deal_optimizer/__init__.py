"""deal-optimizer — layered-DAG deal stacking engine.

Finds the cheapest legal combination of compatible deals for a cart, modeled as
a directed acyclic flow graph: START → deals → END.
"""

from .engine import UserContext, find_best_path, find_top_paths, get_optimal_deal_path, optimize
from .graph import ACCEPTS_KEY, LAYER_ORDER, DealNode
from .schema import (
    Combinability,
    DealConstraints,
    DealParseResult,
    DealType,
    Eligibility,
    Limits,
    StoreCoverage,
)
from .transform import apply_deal

__all__ = [
    "UserContext",
    "find_best_path",
    "find_top_paths",
    "get_optimal_deal_path",
    "optimize",
    "apply_deal",
    "DealNode",
    "LAYER_ORDER",
    "ACCEPTS_KEY",
    "DealType",
    "Combinability",
    "Limits",
    "StoreCoverage",
    "Eligibility",
    "DealConstraints",
    "DealParseResult",
]
