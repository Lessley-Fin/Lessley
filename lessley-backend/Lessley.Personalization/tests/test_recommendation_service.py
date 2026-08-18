"""
Club matching works end-to-end with category name strings, and publishes nothing.

The service used to fire a Personalize.matching_clubs_calculated event so the Gateway could
store the answer as a notification the client fetched separately. It is now answered
synchronously over HTTP, so the result is simply returned.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from services.mcc_service import MccService
from services.recommendation_service import RecommendationService
from services.reference_data_repository import ReferenceDataRepository


def _mcc_service():
    svc = MccService()
    svc._mcc_map = {"5411": "GROCERIES", "5812": "RESTAURANT"}
    return svc


def _store(mcc_codes):
    return SimpleNamespace(store_id="s", name="Store", metadata=SimpleNamespace(mcc_codes=mcc_codes))


def _reference_data(clubs=None, stores=None, deals=None) -> ReferenceDataRepository:
    """A pre-loaded repository — bypasses Mongo by filling the in-memory indexes directly."""
    repo = ReferenceDataRepository()
    repo._clubs = clubs or {}
    repo._stores = stores or {}
    repo._deals_by_id = deals or {}
    repo._loaded = True
    return repo


# ── Club matching with category name strings ───────────────────────────────────

async def test_calculate_matching_clubs_returns_recommendations():
    repo = _reference_data(
        clubs={"c1": SimpleNamespace(club_id="c1", name="Grocery Club", stores=["s1", "s2"])},
        stores={
            "s1": SimpleNamespace(store_id="s1", name="A", metadata=SimpleNamespace(mcc_codes=["GROCERIES"])),
            "s2": SimpleNamespace(store_id="s2", name="B", metadata=SimpleNamespace(mcc_codes=["RESTAURANT"])),
        },
    )

    user_repo = MagicMock()
    user_repo.get_user_tags = AsyncMock(return_value=["GROCERIES"])
    user_repo.get_user_clubs = AsyncMock(return_value=["c1"])

    service = RecommendationService(repo, user_repo, _mcc_service())

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
    repo = _reference_data(
        clubs={"c1": SimpleNamespace(club_id="c1", name="Club", stores=["s1"])},
        stores={"s1": SimpleNamespace(store_id="s1", name="A", metadata=SimpleNamespace(mcc_codes=["GROCERIES"]))},
    )

    user_repo = MagicMock()
    user_repo.get_user_tags = AsyncMock(return_value=["RESTAURANT"])
    user_repo.get_user_clubs = AsyncMock(return_value=[])

    service = RecommendationService(repo, user_repo, _mcc_service())
    result = await service.calculate_matching_clubs("user@test.com")

    assert result["recommendations"][0]["hit_count"] == 0


# ── deal-recommendation removed ────────────────────────────────────────────────

def test_calculate_deal_recommendation_removed():
    assert not hasattr(RecommendationService, "calculate_deal_recommendation_for_user")


# ── nothing leaves this service ────────────────────────────────────────────────

def test_the_service_has_no_publisher():
    """
    Club matching returns its answer to the caller. A publisher reappearing here would mean
    the result is travelling somewhere else as well, which is the arrangement this replaced.
    """
    assert not hasattr(RecommendationService(_reference_data(), MagicMock(), _mcc_service()), "publisher_service")


def test_the_deal_broadcast_path_is_gone():
    # publish_broadcast_deal had no caller, and the Gateway consumer for its routing key was
    # never reachable — machinery whose only exercise was its own tests.
    assert not hasattr(RecommendationService, "publish_broadcast_deal")
    assert not hasattr(RecommendationService, "get_deal_categories")
