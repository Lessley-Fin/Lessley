"""
Club matching works end-to-end with category name strings,
deal-recommendation is gone, and deal-broadcast resolves the category from the store.
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
    svc._mcc_map = {"5411": "GROCERIES", "5812": "RESTAURANT"}
    return svc


def _store(mcc_codes):
    return SimpleNamespace(store_id="s", name="Store", metadata=SimpleNamespace(mcc_codes=mcc_codes))


# ── Club matching with category name strings ───────────────────────────────────

async def test_calculate_matching_clubs_returns_recommendations():
    core = RecommendationCoreService()
    core._clubs_dict = {"c1": SimpleNamespace(club_id="c1", name="Grocery Club", stores=["s1", "s2"])}
    core._stores_dict = {
        "s1": SimpleNamespace(store_id="s1", name="A", metadata=SimpleNamespace(mcc_codes=["GROCERIES"])),
        "s2": SimpleNamespace(store_id="s2", name="B", metadata=SimpleNamespace(mcc_codes=["RESTAURANT"])),
    }

    user_repo = MagicMock()
    user_repo.get_user_tags = AsyncMock(return_value=["GROCERIES"])
    user_repo.get_user_clubs = AsyncMock(return_value=["c1"])

    publisher = MagicMock()
    publisher.publish_matching_clubs_calculated = AsyncMock()

    service = RecommendationService(core, user_repo, publisher, _mcc_service())

    result = await service.calculate_matching_clubs("user@test.com")

    assert result["email"] == "user@test.com"
    assert len(result["recommendations"]) == 1
    rec = result["recommendations"][0]
    assert rec["club_id"] == "c1"
    assert rec["hit_count"] == 1           # only s1 matches "GROCERIES"
    assert rec["total_stores"] == 2
    assert rec["fit_score"] == 0.5
    assert rec["is_recommended"] is True
    assert rec["is_member"] is True        # user_repo reports "c1" as an owned club


async def test_calculate_matching_clubs_no_matching_codes_gives_zero_hits():
    core = RecommendationCoreService()
    core._clubs_dict = {"c1": SimpleNamespace(club_id="c1", name="Club", stores=["s1"])}
    core._stores_dict = {"s1": SimpleNamespace(store_id="s1", name="A", metadata=SimpleNamespace(mcc_codes=["GROCERIES"]))}

    user_repo = MagicMock()
    user_repo.get_user_tags = AsyncMock(return_value=["RESTAURANT"])
    user_repo.get_user_clubs = AsyncMock(return_value=[])

    publisher = MagicMock()
    publisher.publish_matching_clubs_calculated = AsyncMock()

    service = RecommendationService(core, user_repo, publisher, _mcc_service())
    result = await service.calculate_matching_clubs("user@test.com")

    assert result["recommendations"][0]["hit_count"] == 0


# ── deal-recommendation removed ────────────────────────────────────────────────

def test_calculate_deal_recommendation_removed():
    assert not hasattr(RecommendationService, "calculate_deal_recommendation_for_user")
    assert not hasattr(RecommendationCoreService, "get_store_mcc_codes")


# ── deal-broadcast resolves category from the store ────────────────────────────

async def test_publish_broadcast_deal_uses_store_category():
    core = MagicMock()
    core.get_deal_categories = MagicMock(return_value=["GROCERIES", "RESTAURANT"])

    publisher = MagicMock()
    publisher.publish_deal_notification = AsyncMock()

    service = RecommendationService(core, MagicMock(), publisher, _mcc_service())

    categories = await service.publish_broadcast_deal(deal_id="d1", message="50% off!")

    assert categories == ["GROCERIES", "RESTAURANT"]
    core.get_deal_categories.assert_called_once_with("d1")
    publisher.publish_deal_notification.assert_awaited_once_with(
        deal_id="d1", message="50% off!", categories=["GROCERIES", "RESTAURANT"]
    )


async def test_publish_broadcast_deal_unknown_deal_raises_404_and_does_not_publish():
    core = MagicMock()
    core.get_deal_categories = MagicMock(return_value=[])

    publisher = MagicMock()
    publisher.publish_deal_notification = AsyncMock()

    service = RecommendationService(core, MagicMock(), publisher, _mcc_service())

    with pytest.raises(HTTPException) as exc:
        await service.publish_broadcast_deal(deal_id="ghost", message="x")

    assert exc.value.status_code == 404
    publisher.publish_deal_notification.assert_not_awaited()


# ── resolve deal -> store -> category names ────────────────────────────────────

def test_get_deal_categories_resolves_store_categories():
    core = RecommendationCoreService()
    core._deals_dict = {"d1": SimpleNamespace(deal_id="d1", store_id="s1")}
    core._stores_dict = {"s1": _store(["GROCERIES", "RESTAURANT"])}

    assert core.get_deal_categories("d1") == ["GROCERIES", "RESTAURANT"]


def test_get_deal_categories_unknown_deal_returns_empty():
    core = RecommendationCoreService()
    core._deals_dict = {}
    core._stores_dict = {}
    assert core.get_deal_categories("nope") == []
