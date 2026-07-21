"""Mock user wallets — generic user info plus the clubs/cards that gate deal
eligibility, and the bridge into ``UserContext``.

A wallet holds two things: loyalty clubs joined directly (``member_clubs``)
and credit cards held (``credit_cards``), each linked to the ``club_id`` the
deal-side eligibility checks (``deal_eligibility`` in ``engine.py``) already
key on. Both resolve into the same flat set of club ids the engine consumes —
"member of club_hot" and "holds a Mastercard tied to club_mastercard" are, for
eligibility purposes, the same kind of fact.

``get_eligible_deals`` exposes the exact same prune ``find_top_paths`` applies
internally as a standalone step, so a caller can see "wallet X unlocks these
N of M deals" before ever running the optimizer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .adapter import normalize_deals
from .engine import UserContext, deal_eligibility


@dataclass
class WalletCard:
    card_id: str
    club_id: str  # the deal-side club_id this card grants access to
    brand: str  # issuer/network display name, e.g. "Mastercard"
    nickname: str | None = None


@dataclass
class UserWallet:
    """Mock struct: generic user info + the clubs/cards that gate deal eligibility."""

    user_id: str
    display_name: str = ""
    email: str | None = None

    member_clubs: list[str] = field(default_factory=list)
    credit_cards: list[WalletCard] = field(default_factory=list)

    # Optional — mirrors UserContext 1:1 so wallet_to_user_context is a
    # complete field mapping; empty unless a wallet models usage/store-type data.
    preferred_store_types: list[str] = field(default_factory=list)
    uses_this_month: dict[str, int] = field(default_factory=dict)


def resolved_club_ids(wallet: UserWallet) -> list[str]:
    """Union of joined-club ids and card-linked club ids, de-duped, order-preserved —
    the full set of club_ids this wallet grants access to for eligibility checks."""
    ids = list(wallet.member_clubs) + [c.club_id for c in wallet.credit_cards if c.club_id]
    seen: set[str] = set()
    out: list[str] = []
    for cid in ids:
        if cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def wallet_to_user_context(wallet: UserWallet) -> UserContext:
    """Convert a UserWallet into the UserContext the engine consumes."""
    return UserContext(
        member_club_ids=resolved_club_ids(wallet),
        preferred_store_types=list(wallet.preferred_store_types),
        uses_this_month=dict(wallet.uses_this_month),
    )


def load_wallets(file_path: str | Path) -> dict[str, UserWallet]:
    """Load a mock wallets JSON file into a dict keyed by user_id."""
    with open(file_path, encoding="utf-8") as f:
        raw = json.load(f)

    wallets: dict[str, UserWallet] = {}
    for w in raw:
        cards = [WalletCard(**c) for c in w.get("credit_cards", [])]
        wallets[w["user_id"]] = UserWallet(
            user_id=w["user_id"],
            display_name=w.get("display_name", ""),
            email=w.get("email"),
            member_clubs=w.get("member_clubs", []),
            credit_cards=cards,
            preferred_store_types=w.get("preferred_store_types", []),
            uses_this_month=w.get("uses_this_month", {}),
        )
    return wallets


def get_eligible_deals(
    deal_dicts: list[dict[str, Any]],
    wallet: UserWallet,
    *,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """Pre-filter ``deal_dicts`` to only those this wallet is eligible for — the
    exact same rule ``find_top_paths`` applies internally, exposed standalone so
    a caller can show "wallet X unlocks these N of M deals" before running the
    optimizer.

    Normalizes deals first (same as ``find_top_paths``), so legacy- and
    new-shape deals both work here exactly as they do inside the optimizer.
    """
    ctx = wallet_to_user_context(wallet)
    kept = []
    for d in normalize_deals(deal_dicts):
        keep, reason = deal_eligibility(d, ctx)
        if verbose:
            print(f"  [{'KEEP ' if keep else 'PRUNE'}] {d['id']:<28} {reason}")
        if keep:
            kept.append(d)
    return kept
