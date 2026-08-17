"""The public route surface.

Every client-facing route must sit under /insights or /open-finance. Those are the only two
prefixes the edge forwards to this service (lessley-cd/Caddyfile), and that file warns against
adding a third without forward_auth — so a route placed anywhere else is simply unreachable,
with nothing in this service's logs to say why.
"""

from routers.insights_controller import router as insights_router
from routers.schemas import InsightsCalcRequests


def _paths():
    return {route.path for route in insights_router.routes}


def test_matching_clubs_is_served_from_the_insights_prefix():
    # It answers a question about the user's own spending and returns the answer directly.
    # It used to be a POST under /recommendations whose result came back over RabbitMQ.
    assert "/insights/matching-clubs" in _paths()


def test_matching_clubs_is_a_get():
    route = next(r for r in insights_router.routes if r.path == "/insights/matching-clubs")
    assert route.methods == {"GET"}


def test_the_per_transaction_missed_savings_route_is_gone():
    # Superseded by /insights/missed-savings-by-store, which answers the same question one row
    # per shop instead of repeating a suggestion against every matching purchase.
    paths = _paths()
    assert "/insights/missed-savings-by-store" in paths
    assert not any("missed-savings" in path and "by-store" not in path for path in paths)


def test_the_recommendations_router_no_longer_exists():
    import importlib

    try:
        importlib.import_module("routers.recommendation_controller")
    except ModuleNotFoundError:
        return
    raise AssertionError("routers.recommendation_controller should have been deleted")


def test_insights_requests_never_accept_identity_or_a_data_source():
    # Identity comes from the edge, and use_mock let a caller swap their transactions for a
    # file on disk. Neither may return as a request field.
    fields = set(InsightsCalcRequests.model_fields.keys())
    assert fields == {"time_filter", "days"}
