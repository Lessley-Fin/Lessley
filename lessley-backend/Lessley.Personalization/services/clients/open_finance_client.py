import asyncio
import httpx
import time
import logging
from config.settings import settings
from models.transaction import PaginatedTransactionsResponse, Transaction

logger = logging.getLogger(__name__)


class OpenFinanceClient:
    TOKEN_EXPIRY_SECONDS = 86400  # Fallback lifetime, used only if the API omits "expiresIn"
    # Refresh slightly before the API's own expiry, so a token can never be rejected
    # mid-request because of clock skew or latency between issue and use.
    TOKEN_EXPIRY_SKEW_SECONDS = 300

    def __init__(self):
        self.base_url = settings.OpenFinanceConfig_BaseUrl
        self.client_id = settings.OpenFinanceConfig_ClientId
        self.client_secret = settings.OpenFinanceConfig_ClientSecret
        self._client: httpx.AsyncClient | None = None  # Lazy initialization of the HTTP client
        self._token_cache: dict[str, tuple[str, float]] = {}  # Access tokens: {user_id: (token, expires_at)}
        self._token_lock = asyncio.Lock()  # Collapses concurrent refreshes into one token request

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create a reusable HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,  # Add timeout
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return self._client

    async def close_client(self):
        """Close the HTTP client if it exists"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self.clear_token_cache()

    def _is_usable(self, cached: tuple[str, float] | None, stale_token: str | None) -> bool:
        """A cached entry is usable if it exists, has not expired, and is not one the API just rejected"""
        if cached is None:
            return False
        token, expires_at = cached
        return time.time() < expires_at and token != stale_token

    async def get_access_token(self, user_id: str, stale_token: str | None = None) -> str:
        """
        Retrieves an access token for the given user ID.
        Returns the cached token if it is still valid, otherwise fetches a new one.
        Passing `stale_token` forces a refresh of that specific token — used when the API
        rejected it before its nominal expiry.
        """
        cached = self._token_cache.get(user_id)
        if self._is_usable(cached, stale_token):
            logger.info("Returning cached token")
            return cached[0]

        async with self._token_lock:
            # Re-check: another coroutine may have refreshed while we waited for the lock.
            cached = self._token_cache.get(user_id)
            if self._is_usable(cached, stale_token):
                logger.info("Returning cached token refreshed by a concurrent request")
                return cached[0]

            logger.info("Fetching new token due to cache miss, expiry, or rejection")
            client = await self._get_client()
            response = await client.post(
                "/oauth/token",
                json={
                    "userId": user_id,
                    "clientId": self.client_id,
                    "clientSecret": self.client_secret,
                },
                timeout=10.0,  # Add timeout for token request
            )
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data.get("accessToken")
            if not access_token:
                # Caching a null token here would 401 every downstream call until it aged out.
                raise ValueError("Open Finance token response did not contain 'accessToken'")

            # Trust the API's own lifetime when it sends one; the constant is only a fallback.
            expires_in = float(token_data.get("expiresIn") or self.TOKEN_EXPIRY_SECONDS)
            expires_at = time.time() + max(expires_in - self.TOKEN_EXPIRY_SKEW_SECONDS, 1.0)

            self._token_cache[user_id] = (access_token, expires_at)
            return access_token

    def clear_token_cache(self) -> None:
        """Clear the access token cache"""
        self._token_cache.clear()

    def invalidate_token(self, user_id: str) -> None:
        """Remove a specific user's token from cache (e.g., on logout)"""
        self._token_cache.pop(user_id, None)

    async def _authed_request(self, user_id: str, url: str, **kwargs) -> httpx.Response:
        """
        Performs a GET with the user's bearer token, refreshing it once if the API rejects it.

        The API can revoke a token before its stated expiry, and the client is a process-wide
        singleton — so without this retry a single rejected token stays cached and fails every
        subsequent request for that user until it ages out.
        """
        client = await self._get_client()
        token = await self.get_access_token(user_id)
        response = await client.get(url, headers={"Authorization": f"Bearer {token}"}, **kwargs)

        if response.status_code in (401, 403):
            logger.warning(
                "Open Finance rejected the cached token; refreshing and retrying once",
                extra={
                    "reason": "Token rejected before its nominal expiry",
                    "extra_data": {"user_id": user_id, "endpoint": url, "status_code": response.status_code},
                },
            )
            token = await self.get_access_token(user_id, stale_token=token)
            response = await client.get(url, headers={"Authorization": f"Bearer {token}"}, **kwargs)

        response.raise_for_status()
        return response

    async def get_accounts(self, user_id: str) -> list[dict]:
        """
        Retrieves accounts for the given user ID.
        """
        response = await self._authed_request(user_id, "/v2/data/accounts", timeout=10.0)
        return response.json().get("items", [])

    async def get_transactions(self, user_id: str, params: dict[str, str]) -> list[Transaction]:
        """
        Retrieves transactions for the given user ID starting from the specified date.
        """
        response = await self._authed_request(
            user_id,
            "/v2/data/transactions",
            params=params,
            timeout=10.0,  # Add timeout for transactions request
        )
        return PaginatedTransactionsResponse.normalize_data(response)
