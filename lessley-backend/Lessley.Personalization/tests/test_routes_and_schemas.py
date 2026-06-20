"""Task 3 & 4 — route surface and broadcast schema."""

from routers.recommendation_controller import router
from routers.schemas import BroadcastDealRequest


def _paths():
    return {route.path for route in router.routes}


def test_deal_recommendation_route_removed():
    assert "/recommendations/calculate-deal-recommendation" not in _paths()


def test_recommendation_routes_present():
    paths = _paths()
    assert "/recommendations/matching-clubs" in paths
    assert "/recommendations/missed-savings" in paths


def test_broadcast_request_only_needs_deal_id_and_message():
    fields = set(BroadcastDealRequest.model_fields.keys())
    assert fields == {"deal_id", "message"}
    # deal_category must be gone — the category is resolved from the store.
    assert "deal_category" not in fields
