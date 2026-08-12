"""Edge-only access and verified identity — the two controls that make it safe to
expose this service at the edge alongside Personalization.

Both are enforced in front of the engine: EdgeAuthMiddleware proves the request came
through Caddy, and the authenticated_email dependency proves Caddy authenticated a
user before forwarding it.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from deal_optimizer import api, auth, edge_auth
from deal_optimizer.settings import settings

from conftest import mk_deal

EDGE_KEY = "test-edge-key"
CART = {"store_id": "store_1", "cart_total": 100, "cart_quantity": 1}


@pytest.fixture
def client():
    return TestClient(api.app)


@pytest.fixture(autouse=True)
def known_user(monkeypatch):
    """Eligibility resolution is not what these tests are about — see test_user_source.py.

    Without this the endpoint would try to read the users collection out of a database
    that isn't there, and every "the edge let this through" assertion would fail on the
    lookup rather than on the gate.
    """
    monkeypatch.setattr(api, "member_source_ids_for", lambda email: [])


@pytest.fixture(autouse=True)
def stocked_store(monkeypatch):
    """One deal at store_1 — enough that a permitted request has something to return."""
    deals = [
        mk_deal("a", "coupon", reward_type="percentage_off", reward_value=0.10,
                accepts_all=True, store_id="store_1", title="10% coupon"),
    ]
    monkeypatch.setattr(api, "load_store_deals", lambda store_id: deals)
    monkeypatch.setattr(api, "load_store", lambda store_id: None)
    return deals


@pytest.fixture
def edge_enforced(monkeypatch):
    """A configured edge key and no bypass — production's posture."""
    monkeypatch.setattr(settings, "Edge_ApiKey", EDGE_KEY)
    monkeypatch.setattr(settings, "Environment", "Production")
    monkeypatch.setattr(settings, "Edge_AllowUnverified", False)


# ── Edge key ──────────────────────────────────────────────────────────────────

def test_request_without_the_edge_key_is_refused(client, edge_enforced):
    response = client.post("/optimizer/optimize", json=CART, headers={"X-Auth-Email": "u@e.com"})

    assert response.status_code == 403
    assert "edge" in response.json()["detail"].lower()


def test_request_with_a_wrong_edge_key_is_refused(client, edge_enforced):
    response = client.post(
        "/optimizer/optimize",
        json=CART,
        headers={"X-Edge-Key": "not-the-key", "X-Auth-Email": "u@e.com"},
    )

    assert response.status_code == 403


def test_request_through_the_edge_is_served(client, edge_enforced):
    response = client.post(
        "/optimizer/optimize",
        json=CART,
        headers={"X-Edge-Key": EDGE_KEY, "X-Auth-Email": "u@e.com"},
    )

    assert response.status_code == 200
    assert response.json()["store_id"] == "store_1"


def test_health_is_exempt_from_the_edge_gate(client, edge_enforced, monkeypatch):
    # Docker's healthcheck calls this directly, with no edge in between, so it must
    # answer without a key — reaching the database check rather than a 403.
    class _Client:
        class admin:
            @staticmethod
            def command(_):
                return {"ok": 1}

    monkeypatch.setattr(api, "get_database", lambda: type("_Db", (), {"client": _Client})())

    assert client.get("/optimizer/health").status_code == 200


def test_no_configured_key_leaves_the_gate_open(client, monkeypatch):
    # Blank key = verification disabled (same convention as Personalization), which is
    # what keeps the pure-library test suite and the CLI usable with no environment.
    monkeypatch.setattr(settings, "Edge_ApiKey", None)

    response = client.post("/optimizer/optimize", json=CART, headers={"X-Auth-Email": "u@e.com"})

    assert response.status_code == 200


# ── Dev bypass ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("environment", "allow_unverified", "expected"),
    [
        ("Development", True, True),    # both conditions — the only open case
        ("Development", False, False),  # flag off
        ("Production", True, False),    # flag on, but not a dev environment
        ("Production", False, False),
    ],
)
def test_bypass_needs_both_conditions(monkeypatch, environment, allow_unverified, expected):
    monkeypatch.setattr(settings, "Environment", environment)
    monkeypatch.setattr(settings, "Edge_AllowUnverified", allow_unverified)

    assert edge_auth.dev_bypass_active() is expected


def test_bypass_is_case_insensitive_about_the_environment(monkeypatch):
    # The compose files write "Development"; a case-sensitive test here would silently
    # disable the bypass for everyone running Mode 1.
    monkeypatch.setattr(settings, "Environment", "development")
    monkeypatch.setattr(settings, "Edge_AllowUnverified", True)

    assert edge_auth.dev_bypass_active() is True


def test_active_bypass_drops_the_edge_key_requirement(client, monkeypatch):
    monkeypatch.setattr(settings, "Edge_ApiKey", EDGE_KEY)
    monkeypatch.setattr(settings, "Environment", "Development")
    monkeypatch.setattr(settings, "Edge_AllowUnverified", True)

    response = client.post("/optimizer/optimize", json=CART, headers={"X-Auth-Email": "u@e.com"})

    assert response.status_code == 200


# ── Verified identity ─────────────────────────────────────────────────────────

def test_optimize_without_a_verified_identity_is_unauthenticated(client, edge_enforced):
    response = client.post("/optimizer/optimize", json=CART, headers={"X-Edge-Key": EDGE_KEY})

    assert response.status_code == 401
    assert "Unauthenticated" in response.json()["detail"]


def test_identity_comes_from_the_header_not_the_body(client, edge_enforced):
    # A client cannot assert who it is: Caddy strips any inbound X-Auth-Email and sets
    # its own from the Gateway's verified claims. Nothing in the body is consulted.
    response = client.post(
        "/optimizer/optimize",
        json={**CART, "email": "attacker@example.com"},
        headers={"X-Edge-Key": EDGE_KEY},
    )

    assert response.status_code == 401


def test_dev_bypass_falls_back_to_the_access_token_cookie(client, monkeypatch):
    monkeypatch.setattr(settings, "Environment", "Development")
    monkeypatch.setattr(settings, "Edge_AllowUnverified", True)

    # Mode 1 has no Caddy to inject X-Auth-Email, so identity is decoded (never verified)
    # out of the Gateway's own cookie.
    client.cookies.set("access_token", _jwt_with_email("dev@example.com"))
    response = client.post("/optimizer/optimize", json=CART)

    assert response.status_code == 200


def test_dev_bypass_without_a_cookie_says_so(client, monkeypatch):
    monkeypatch.setattr(settings, "Environment", "Development")
    monkeypatch.setattr(settings, "Edge_AllowUnverified", True)

    response = client.post("/optimizer/optimize", json=CART)

    assert response.status_code == 401
    assert "Dev bypass" in response.json()["detail"]


@pytest.mark.parametrize("token", ["", "not-a-jwt", "a.b", "a.!!!.c"])
def test_malformed_access_tokens_are_not_identities(token):
    class _Request:
        cookies = {"access_token": token}

    assert auth.email_from_access_token(_Request()) is None


def _jwt_with_email(email: str) -> str:
    """An unsigned token shaped like the Gateway's — only the payload is ever read."""
    import base64
    import json

    payload = json.dumps({auth.JWT_EMAIL_CLAIM: email}).encode()
    body = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    return f"header.{body}.signature"
