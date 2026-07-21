"""deal-optimizer — layered-DAG deal stacking engine.

Finds the cheapest legal combination of compatible deals for a cart, modeled as
a directed acyclic flow graph: START → deals → END.
"""

from .engine import UserContext, deal_eligibility, find_best_path, find_top_paths, get_optimal_deal_path, optimize
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
from .wallet import (
    UserWallet,
    WalletCard,
    get_eligible_deals,
    load_wallets,
    resolved_club_ids,
    wallet_to_user_context,
)

__all__ = [
    "UserContext",
    "deal_eligibility",
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
    "RedemptionChannels",
    "Eligibility",
    "DealConstraints",
    "DealParseResult",
    "UserWallet",
    "WalletCard",
    "get_eligible_deals",
    "load_wallets",
    "resolved_club_ids",
    "wallet_to_user_context",
]
