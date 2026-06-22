"""
Tasks 2, 3, 4 — club matching works end-to-end, deal-recommendation is gone,
and deal-broadcast resolves the category from the store.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from services.mcc_service import MccService
from services.recommendation_core_service import RecommendationCoreService
from services.recommendation_service import RecommendationService


def _mcc_service():
    svc = MccService()
    svc._mcc_map = {"5411": "GROCERY STORES", "5812": "RESTAURANTS"}
    return svc


def _store(mcc_codes):
    return SimpleNamespace(store_id="s", name="Store", metadata=SimpleNamespace(mcc_codes=mcc_codes))


# ── Task 2: calculate-club works ────────────────────────────────────────────────

async def test_calculate_matching_clubs_returns_recommendations():
    core = RecommendationCoreService()
    core._clubs_dict = {"c1": SimpleNamespace(club_id="c1", name="Grocery Club", stores=["s1", "s2"])}
    core._stores_dict = {
        "s1": SimpleNamespace(store_id="s1", name="A", metadata=SimpleNamespace(mcc_codes=[5411])),
        "s2": SimpleNamespace(store_id="s2", name="B", metadata=SimpleNamespace(mcc_codes=[5812])),
    }

    user_repo = MagicMock()
    user_repo.get_user_tags = AsyncMock(return_value=["5411"])  # category stored as MCC string label

    service = RecommendationService(core, user_repo, MagicMock(), _mcc_service())

    result = await service.calculate_matching_clubs("user@test.com")

    assert result["email"] == "user@test.com"
    assert len(result["recommendations"]) == 1
    rec = result["recommendations"][0]
    assert rec["club_id"] == "c1"
    assert rec["hit_count"] == 1           # only s1 matches MCC 5411
    assert rec["total_stores"] == 2
    assert rec["fit_score"] == 0.5
    assert rec["is_recommended"] is True


async def test_calculate_matching_clubs_no_matching_codes_gives_zero_hits():
    core = RecommendationCoreService()
    core._clubs_dict = {"c1": SimpleNamespace(club_id="c1", name="Club", stores=["s1"])}
    core._stores_dict = {"s1": SimpleNamespace(store_id="s1", name="A", metadata=SimpleNamespace(mcc_codes=[5411]))}

    user_repo = MagicMock()
    user_repo.get_user_tags = AsyncMock(return_value=["5812"])  # user has no grocery spending

    service = RecommendationService(core, user_repo, MagicMock(), _mcc_service())
    result = await service.calculate_matching_clubs("user@test.com")

    assert result["recommendations"][0]["hit_count"] == 0


# ── Task 3: deal-recommendation removed ─────────────────────────────────────────

def test_calculate_deal_recommendation_removed():
    assert not hasattr(RecommendationService, "calculate_deal_recommendation_for_user")
    assert not hasattr(RecommendationCoreService, "get_store_mcc_codes")


# ── Task 4: deal-broadcast resolves category from the store ─────────────────────

async def test_publish_broadcast_deal_uses_store_category():
    core = MagicMock()
    core.get_deal_categories = MagicMock(return_value=[5411, 5812])

    publisher = MagicMock()
    publisher.publish_group_notification = AsyncMock()

    service = RecommendationService(core, MagicMock(), publisher, _mcc_service())

    categories = await service.publish_broadcast_deal(deal_id="d1", message="50% off!")

    assert categories == ["5411", "5812"]
    core.get_deal_categories.assert_called_once_with("d1")
    assert publisher.publish_group_notification.await_count == 2
    publisher.publish_group_notification.assert_any_await(group_tag="5411", message="50% off!", deal_id="d1")
    publisher.publish_group_notification.assert_any_await(group_tag="5812", message="50% off!", deal_id="d1")


async def test_publish_broadcast_deal_unknown_deal_raises_404_and_does_not_publish():
    core = MagicMock()
    core.get_deal_categories = MagicMock(return_value=[])  # deal not found

    publisher = MagicMock()
    publisher.publish_group_notification = AsyncMock()

    service = RecommendationService(core, MagicMock(), publisher, _mcc_service())

    with pytest.raises(HTTPException) as exc:
        await service.publish_broadcast_deal(deal_id="ghost", message="x")

    assert exc.value.status_code == 404
    publisher.publish_group_notification.assert_not_awaited()


# ── Task 4 (core): resolve deal -> store -> mcc codes ───────────────────────────

def test_get_deal_categories_resolves_store_mcc():
    core = RecommendationCoreService()
    core._deals_dict = {"d1": SimpleNamespace(deal_id="d1", store_id="s1")}
    core._stores_dict = {"s1": _store([5411, 5812])}

    assert core.get_deal_categories("d1") == [5411, 5812]


def test_get_deal_categories_unknown_deal_returns_empty():
    core = RecommendationCoreService()
    core._deals_dict = {}
    core._stores_dict = {}
    assert core.get_deal_categories("nope") == []
