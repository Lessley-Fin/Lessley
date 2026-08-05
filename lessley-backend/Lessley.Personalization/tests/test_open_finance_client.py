import asyncio
import time

import httpx
import pytest

from services.clients.open_finance_client import OpenFinanceClient


def _make_client(handler: httpx.MockTransport) -> OpenFinanceClient:
    client = OpenFinanceClient()
    client._client = httpx.AsyncClient(base_url="https://api.test.local", transport=handler)
    return client


def _token_response(request: httpx.Request, token: str, expires_in=86400) -> httpx.Response:
    return httpx.Response(200, json={"accessToken": token, "expiresIn": expires_in, "tokenType": "Bearer"})


@pytest.mark.asyncio
async def test_rejected_token_is_refreshed_and_request_retried():
    """A token the API rejects before its expiry must be replaced, not reused until it ages out."""
    issued = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/token":
            issued.append(f"token-{len(issued) + 1}")
            return _token_response(request, issued[-1])
        # Only the newest token is accepted; the first one is treated as revoked.
        if request.headers["Authorization"] == "Bearer token-2":
            return httpx.Response(200, json={"items": [{"id": "acc-1"}]})
        return httpx.Response(401, json={"error": "unauthorized"})

    client = _make_client(httpx.MockTransport(handler))

    # Prime the cache with the token that will be rejected.
    first = await client.get_access_token("user@test.local")
    assert first == "token-1"

    accounts = await client.get_accounts("user@test.local")

    assert accounts == [{"id": "acc-1"}]
    assert issued == ["token-1", "token-2"], "expected exactly one refresh after the 401"


@pytest.mark.asyncio
async def test_persistent_401_surfaces_as_http_status_error():
    """If a freshly issued token is also rejected, the error must propagate rather than loop."""
    calls = {"token": 0, "accounts": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/token":
            calls["token"] += 1
            return _token_response(request, f"token-{calls['token']}")
        calls["accounts"] += 1
        return httpx.Response(401, json={"error": "unauthorized"})

    client = _make_client(httpx.MockTransport(handler))

    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        await client.get_accounts("user@test.local")

    assert excinfo.value.response.status_code == 401
    assert calls["accounts"] == 2, "expected exactly one retry, not an infinite loop"


@pytest.mark.asyncio
async def test_cache_honours_api_expiry_not_the_fallback_constant():
    """A short-lived token must not be cached for the hardcoded 24h fallback."""

    def handler(request: httpx.Request) -> httpx.Response:
        return _token_response(request, "short-lived", expires_in=600)

    client = _make_client(httpx.MockTransport(handler))
    await client.get_access_token("user@test.local")

    _, expires_at = client._token_cache["user@test.local"]
    ttl = expires_at - time.time()

    assert ttl < 600, "cache TTL must be shorter than the API's own expiry"
    assert ttl > 0


@pytest.mark.asyncio
async def test_missing_access_token_raises_instead_of_caching_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"tokenType": "Bearer"})  # no accessToken

    client = _make_client(httpx.MockTransport(handler))

    with pytest.raises(ValueError, match="accessToken"):
        await client.get_access_token("user@test.local")
    assert "user@test.local" not in client._token_cache


@pytest.mark.asyncio
async def test_concurrent_requests_share_a_single_token_fetch():
    """Parallel per-account fetches must not stampede the token endpoint."""
    token_calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls
        if request.url.path == "/oauth/token":
            token_calls += 1
            await asyncio.sleep(0.01)  # widen the window for a race
            return _token_response(request, "token-1")
        return httpx.Response(200, json={"items": []})

    client = _make_client(httpx.MockTransport(handler))

    await asyncio.gather(*(client.get_accounts("user@test.local") for _ in range(10)))

    assert token_calls == 1, f"expected one token fetch, got {token_calls}"
