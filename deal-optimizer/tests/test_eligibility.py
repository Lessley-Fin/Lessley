"""UserContext eligibility prune (Part 3f)."""

from __future__ import annotations

from deal_optimizer.engine import UserContext, find_best_path

from conftest import mk_deal


def _ids(path):
    return [n.deal_id for n in path]


def test_membership_required_filters_non_member():
    deal = mk_deal("m", "member_discount", reward_type="percentage_off", reward_value=0.10,
                   accepts_all=True, membership_required="yes", club_id="club_hot")
    # User not in club → deal pruned → empty path.
    assert find_best_path(100, 1, [deal], UserContext(member_club_ids=[])) == []
    # User in club → deal applies.
    assert _ids(find_best_path(100, 1, [deal], UserContext(member_club_ids=["club_hot"]))) == ["m"]


def test_monthly_cap_exhausted_filters_deal():
    deal = mk_deal("c", "coupon", reward_type="percentage_off", reward_value=0.10,
                   accepts_all=True, max_uses_per_month=2)
    ctx = UserContext(uses_this_month={"c": 2})
    assert find_best_path(100, 1, [deal], ctx) == []


def test_channel_all_no_filters_deal():
    deal = mk_deal("c", "coupon", reward_type="percentage_off", reward_value=0.10,
                   accepts_all=True, channels={"website": "no", "mobile_app": "no", "physical_store": "no"})
    ctx = UserContext(preferred_channels=["website"])
    assert find_best_path(100, 1, [deal], ctx) == []


def test_channel_unknown_is_optimistic():
    deal = mk_deal("c", "coupon", reward_type="percentage_off", reward_value=0.10,
                   accepts_all=True, channels={"website": "unknown"})
    ctx = UserContext(preferred_channels=["website"])
    assert _ids(find_best_path(100, 1, [deal], ctx)) == ["c"]
