"""UserContext eligibility prune (Part 3f)."""

from __future__ import annotations

from deal_optimizer.engine import UserContext, find_best_path

from conftest import mk_deal


def _ids(path):
    return [n.deal_id for n in path]


def test_membership_required_filters_non_member():
    deal = mk_deal("m", "member_discount", reward_type="percentage_off", reward_value=0.10,
                   accepts_all=True, membership_required="yes", source_id="hot")
    # User doesn't have this source → deal pruned → empty path.
    assert find_best_path(100, 1, [deal], UserContext(member_source_ids=[])) == []
    # User has this source → deal applies.
    assert _ids(find_best_path(100, 1, [deal], UserContext(member_source_ids=["hot"]))) == ["m"]


def test_membership_required_but_no_source_id_is_optimistic_keep():
    # Every real Deal always carries source_id, but the engine should still
    # degrade gracefully (rather than perma-prune) if it's ever missing —
    # mirrors the payment_method_required fallback below.
    deal = mk_deal("m", "member_discount", reward_type="percentage_off", reward_value=0.10,
                   accepts_all=True, membership_required="yes", source_id=None)
    assert _ids(find_best_path(100, 1, [deal], UserContext(member_source_ids=[]))) == ["m"]


def test_monthly_cap_exhausted_filters_deal():
    deal = mk_deal("c", "coupon", reward_type="percentage_off", reward_value=0.10,
                   accepts_all=True, max_uses_per_month=2)
    ctx = UserContext(uses_this_month={"c": 2})
    assert find_best_path(100, 1, [deal], ctx) == []


def test_store_type_all_excluded_filters_deal():
    deal = mk_deal("c", "coupon", reward_type="percentage_off", reward_value=0.10,
                   accepts_all=True, store_coverage={
                       "is_include_outlets_stores": "no",
                       "is_include_online_stores": "no",
                       "is_include_physical_stores": "no",
                   })
    ctx = UserContext(preferred_store_types=["online"])
    assert find_best_path(100, 1, [deal], ctx) == []


def test_store_type_unknown_is_optimistic():
    deal = mk_deal("c", "coupon", reward_type="percentage_off", reward_value=0.10,
                   accepts_all=True, store_coverage={"is_include_online_stores": "unknown"})
    ctx = UserContext(preferred_store_types=["online"])
    assert _ids(find_best_path(100, 1, [deal], ctx)) == ["c"]


def test_card_required_filters_wallet_without_matching_source():
    deal = mk_deal("pay", "payment_discount", reward_type="percentage_off", reward_value=0.20,
                   accepts_all=True, source_id="mastercard", payment_method_required="Mastercard credit card")
    assert find_best_path(100, 1, [deal], UserContext(member_source_ids=[])) == []


def test_card_required_passes_when_source_present_in_context():
    deal = mk_deal("pay", "payment_discount", reward_type="percentage_off", reward_value=0.20,
                   accepts_all=True, source_id="mastercard", payment_method_required="Mastercard credit card")
    assert _ids(find_best_path(100, 1, [deal], UserContext(member_source_ids=["mastercard"]))) == ["pay"]


def test_card_required_but_no_source_id_is_optimistic_keep():
    deal = mk_deal("pay", "payment_discount", reward_type="percentage_off", reward_value=0.15,
                   accepts_all=True, source_id=None, payment_method_required="Card X")
    assert _ids(find_best_path(100, 1, [deal], UserContext(member_source_ids=[]))) == ["pay"]


def test_membership_required_boolean_true_is_honored_like_string_yes():
    # Enriched real-world deals carry membership_required as a JSON boolean
    # (True/False) rather than the mock/legacy "yes"/"no"/"unknown" strings —
    # graph.py's combinability check already handles both; this must too.
    deal = mk_deal("m", "member_discount", reward_type="percentage_off", reward_value=0.10,
                   accepts_all=True, membership_required=True, source_id="hot")
    assert find_best_path(100, 1, [deal], UserContext(member_source_ids=[])) == []
    assert _ids(find_best_path(100, 1, [deal], UserContext(member_source_ids=["hot"]))) == ["m"]
