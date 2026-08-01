"""Mock user wallets — generic user info plus the clubs/cards that gate deal
eligibility, and the bridge into ``UserContext``.

A wallet holds two things: loyalty programs joined directly
(``member_source_ids``) and credit cards held (``credit_cards``), each linked
to the ``source_id`` the deal-side eligibility checks (``deal_eligibility``
in ``engine.py``) already key on. ``source_id`` — which scraper/API a deal
came from (``hot``, ``mastercard``, ``hever_gift_card_company``, ...) — is a
required field on every real ``Deal``, unlike ``club_id`` (which needs a
separate Club-registry lookup and is frequently unset). Both wallet fields
resolve into the same flat set of source ids the engine consumes — "joined
the hot loyalty program" and "holds a Mastercard" are, for eligibility
purposes, the same kind of fact.

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
    source_id: str  # the deal-side source_id this card grants access to
    brand: str  # issuer/network display name, e.g. "Mastercard"
    nickname: str | None = None


@dataclass
class UserWallet:
    """Mock struct: generic user info + the clubs/cards that gate deal eligibility."""

    user_id: str
    display_name: str = ""
    email: str | None = None

    member_source_ids: list[str] = field(default_factory=list)
    credit_cards: list[WalletCard] = field(default_factory=list)

    # Optional — mirrors UserContext 1:1 so wallet_to_user_context is a
    # complete field mapping; empty unless a wallet models usage/store-type data.
    preferred_store_types: list[str] = field(default_factory=list)
    uses_this_month: dict[str, int] = field(default_factory=dict)


def resolved_source_ids(wallet: UserWallet) -> list[str]:
    """Union of joined-program source ids and card-linked source ids, de-duped,
    order-preserved — the full set of source_ids this wallet grants access to
    for eligibility checks."""
    ids = list(wallet.member_source_ids) + [c.source_id for c in wallet.credit_cards if c.source_id]
    seen: set[str] = set()
    out: list[str] = []
    for sid in ids:
        if sid not in seen:
            seen.add(sid)
            out.append(sid)
    return out


def wallet_to_user_context(wallet: UserWallet) -> UserContext:
    """Convert a UserWallet into the UserContext the engine consumes."""
    return UserContext(
        member_source_ids=resolved_source_ids(wallet),
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
            member_source_ids=w.get("member_source_ids", []),
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
