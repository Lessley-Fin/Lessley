"""
The trust boundary that makes exposing this service at the edge safe.

Personalization has no user-level authorization of its own: it acts on whatever identity it
is handed. These tests pin the two rules that make that acceptable — only the edge may
reach the service, and identity comes solely from the header the edge injects.
"""

import httpx
import pytest
from fastapi import Depends, FastAPI

from config.settings import settings
from dependencies.auth import authenticated_email
from middleware.edge_auth_middleware import EdgeAuthMiddleware


def build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(EdgeAuthMiddleware)

    @app.get("/whoami")
    async def whoami(email: str = Depends(authenticated_email)):
        return {"email": email}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


def client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://svc")


@pytest.fixture
def edge_enforced(monkeypatch):
    monkeypatch.setattr(settings, "Edge_ApiKey", "test-edge-key")
    monkeypatch.setattr(settings, "Environment", "Production")
    monkeypatch.setattr(settings, "Edge_AllowUnverified", False)


@pytest.mark.asyncio
async def test_request_without_edge_key_is_rejected(edge_enforced):
    async with client(build_app()) as c:
        resp = await c.get("/whoami", headers={"X-Auth-Email": "attacker@example.com"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_request_with_wrong_edge_key_is_rejected(edge_enforced):
    async with client(build_app()) as c:
        resp = await c.get("/whoami", headers={"X-Edge-Key": "guess", "X-Auth-Email": "a@b.c"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_edge_key_alone_is_not_identity(edge_enforced):
    """Reaching the service is not the same as being someone — 403 and 401 are distinct."""
    async with client(build_app()) as c:
        resp = await c.get("/whoami", headers={"X-Edge-Key": "test-edge-key"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_identity_comes_from_the_edge_header(edge_enforced):
    async with client(build_app()) as c:
        resp = await c.get(
            "/whoami",
            headers={"X-Edge-Key": "test-edge-key", "X-Auth-Email": "user@example.com"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"email": "user@example.com"}


@pytest.mark.asyncio
async def test_query_parameter_can_never_supply_identity(edge_enforced):
    """The pre-migration contract: ?email= must not be honoured, or the IDOR returns."""
    async with client(build_app()) as c:
        resp = await c.get(
            "/whoami?email=victim@example.com",
            headers={"X-Edge-Key": "test-edge-key"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_is_reachable_without_the_edge_key(edge_enforced):
    async with client(build_app()) as c:
        resp = await c.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_dev_bypass_requires_both_conditions(monkeypatch):
    """A stray flag must not open a production deployment on its own."""
    monkeypatch.setattr(settings, "Edge_ApiKey", "test-edge-key")
    monkeypatch.setattr(settings, "Edge_AllowUnverified", True)
    monkeypatch.setattr(settings, "Environment", "Production")  # not Development
    monkeypatch.setattr(settings, "Dev_AuthEmail", "dev@local")

    async with client(build_app()) as c:
        resp = await c.get("/whoami")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_dev_bypass_supplies_identity_in_development(monkeypatch):
    monkeypatch.setattr(settings, "Edge_ApiKey", "test-edge-key")
    monkeypatch.setattr(settings, "Edge_AllowUnverified", True)
    monkeypatch.setattr(settings, "Environment", "Development")
    monkeypatch.setattr(settings, "Dev_AuthEmail", "dev@local")

    async with client(build_app()) as c:
        resp = await c.get("/whoami")
    assert resp.status_code == 200
    assert resp.json() == {"email": "dev@local"}
