"""UserWallet: generic user info + clubs/cards, and cross-validating it against
the real Lee Cooper mock deals."""

from __future__ import annotations

import json
from pathlib import Path

from deal_optimizer.wallet import (
    UserWallet,
    WalletCard,
    get_eligible_deals,
    load_wallets,
    resolved_club_ids,
    wallet_to_user_context,
)

from conftest import mk_deal

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_resolved_club_ids_unions_member_clubs_and_card_club_ids():
    wallet = UserWallet(
        user_id="u1",
        member_clubs=["club_a"],
        credit_cards=[WalletCard(card_id="c1", club_id="club_b", brand="Visa")],
    )
    assert resolved_club_ids(wallet) == ["club_a", "club_b"]


def test_resolved_club_ids_dedupes_when_club_appears_in_both():
    wallet = UserWallet(
        user_id="u1",
        member_clubs=["club_a"],
        credit_cards=[WalletCard(card_id="c1", club_id="club_a", brand="Visa")],
    )
    assert resolved_club_ids(wallet) == ["club_a"]


def test_wallet_to_user_context_bridges_all_fields():
    wallet = UserWallet(
        user_id="u1",
        member_clubs=["club_a"],
        credit_cards=[WalletCard(card_id="c1", club_id="club_b", brand="Visa")],
        preferred_store_types=["online"],
        uses_this_month={"d1": 2},
    )
    ctx = wallet_to_user_context(wallet)
    assert ctx.member_club_ids == ["club_a", "club_b"]
    assert ctx.preferred_store_types == ["online"]
    assert ctx.uses_this_month == {"d1": 2}


def test_get_eligible_deals_keeps_open_deal_and_matching_club_deal():
    open_deal = mk_deal("open", "coupon", reward_type="percentage_off", reward_value=0.10, accepts_all=True)
    club_deal = mk_deal("club", "member_discount", reward_type="percentage_off", reward_value=0.10,
                         accepts_all=True, membership_required="yes", club_id="club_a")
    wallet = UserWallet(user_id="u1", member_clubs=["club_a"])
    kept = {d["id"] for d in get_eligible_deals([open_deal, club_deal], wallet)}
    assert kept == {"open", "club"}


def test_get_eligible_deals_prunes_card_gated_deal_with_no_matching_card():
    card_deal = mk_deal("pay", "payment_discount", reward_type="percentage_off", reward_value=0.20,
                         accepts_all=True, club_id="club_mastercard", payment_method_required="Mastercard credit card")
    wallet = UserWallet(user_id="u1")
    assert get_eligible_deals([card_deal], wallet) == []

    wallet_with_card = UserWallet(
        user_id="u1",
        credit_cards=[WalletCard(card_id="c1", club_id="club_mastercard", brand="Mastercard")],
    )
    kept = {d["id"] for d in get_eligible_deals([card_deal], wallet_with_card)}
    assert kept == {"pay"}


def test_load_wallets_keys_by_user_id(tmp_path):
    payload = [
        {
            "user_id": "u1",
            "display_name": "Test User",
            "member_clubs": ["club_a"],
            "credit_cards": [{"card_id": "c1", "club_id": "club_b", "brand": "Visa"}],
        },
        {"user_id": "u2"},
    ]
    p = tmp_path / "wallets.json"
    p.write_text(json.dumps(payload), encoding="utf-8")

    wallets = load_wallets(p)
    assert set(wallets) == {"u1", "u2"}
    assert wallets["u1"].display_name == "Test User"
    assert wallets["u1"].credit_cards == [WalletCard(card_id="c1", club_id="club_b", brand="Visa")]
    assert wallets["u2"].member_clubs == []
    assert wallets["u2"].credit_cards == []


def test_mock_wallets_unlock_expected_lc_deal_subsets():
    deals = json.loads((_DATA_DIR / "mock_deals.json").read_text(encoding="utf-8"))
    lc_deals = [d for d in deals if d["id"].startswith("LC")]
    wallets = load_wallets(_DATA_DIR / "mock_wallets.json")

    full = {d["id"] for d in get_eligible_deals(lc_deals, wallets["user_ido_full"])}
    assert full == {
        "LC01_hot_giftcard",
        "LC02_mastercard_20pct",
        "LC03_pais_voucher_200",
        "LC04_hever_giftcard_1000",
        "LC05_behatsdaa_giftcard_500",
    }

    card_only = {d["id"] for d in get_eligible_deals(lc_deals, wallets["user_dana_card_only"])}
    assert card_only == {"LC02_mastercard_20pct"}

    loyalty_only = {d["id"] for d in get_eligible_deals(lc_deals, wallets["user_yossi_loyalty_only"])}
    assert loyalty_only == {"LC03_pais_voucher_200", "LC04_hever_giftcard_1000"}
