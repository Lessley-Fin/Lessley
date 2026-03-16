import httpx
import time
from config.settings import settings
from models.transaction import PaginatedTransactionsResponse, Transaction


class OpenFinanceClient:
    TOKEN_EXPIRY_SECONDS = 86400  # 24 hours

    def __init__(self):
        self.base_url = settings.OpenFinanceConfig_BaseUrl
        self.client_id = settings.OpenFinanceConfig_ClientId
        self.client_secret = settings.OpenFinanceConfig_ClientSecret
        self._client: httpx.AsyncClient | None = None  # Lazy initialization of the HTTP client
        self._token_cache: dict[str, tuple[str, float]] = {}  # Cache for access tokens: {user_id: (token, timestamp)}

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

    def _is_token_expired(self, timestamp: float) -> bool:
        """Check if a cached token has expired"""
        return time.time() - timestamp > self.TOKEN_EXPIRY_SECONDS

    async def get_access_token(self, user_id: str) -> str:
        """
        Retrieves an access token for the given user ID.
        Returns cached token if available and not expired, otherwise fetches a new one.
        Token cache expires after 86400 seconds (24 hours).
        """
        # Check cache first
        if user_id in self._token_cache:
            token, timestamp = self._token_cache[user_id]
            if not self._is_token_expired(timestamp):
                print("Returning cached token")
                return token

        print("Fetching new token due to cache miss or expired")
        # Fetch new token if not cached or expired
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

        # Store in cache with current timestamp
        self._token_cache[user_id] = (access_token, time.time())
        return access_token

    def clear_token_cache(self) -> None:
        """Clear the access token cache"""
        self._token_cache.clear()

    def invalidate_token(self, user_id: str) -> None:
        """Remove a specific user's token from cache (e.g., on logout)"""
        self._token_cache.pop(user_id, None)

    async def get_accounts(self, token: str) -> list[dict]:
        """
        Retrieves accounts for the given user ID.
        """
        headers = {"Authorization": f"Bearer {token}"}

        client = await self._get_client()
        response = await client.get("/v2/data/accounts", headers=headers, timeout=10.0)
        response.raise_for_status()
        return response.json().get("items", [])

    async def get_transactions(self, token: str, params: dict[str, str]) -> list[Transaction]:
        """
        Retrieves transactions for the given user ID starting from the specified date.
        """
        headers = {"Authorization": f"Bearer {token}"}

        client = await self._get_client()
        response = await client.get(
            "/v2/data/transactions",
            params=params,
            headers=headers,
            timeout=10.0,  # Add timeout for transactions request
        )
        response.raise_for_status()
        return PaginatedTransactionsResponse.normalize_data(response)
