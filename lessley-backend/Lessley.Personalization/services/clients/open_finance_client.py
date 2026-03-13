import httpx
from config.settings import settings


class OpenFinanceClient:
    def __init__(self):
        self.base_url = settings.OpenFinanceConfig_BaseUrl
        self.client_id = settings.OpenFinanceConfig_ClientId
        self.client_secret = settings.OpenFinanceConfig_ClientSecret
        self._client: httpx.AsyncClient | None = None  # Lazy initialization of the HTTP client

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create a reusable HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,  # Add timeout
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return self._client

    async def get_access_token(self, user_id: str) -> str:
        """
        Retrieves an access token for the given user ID.
        """
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
        return token_data.get("accessToken")

    async def get_accounts(self, token: str) -> list[dict]:
        """
        Retrieves accounts for the given user ID.
        """
        headers = {"Authorization": f"Bearer {token}"}

        client = await self._get_client()
        response = await client.get("/v2/data/accounts", headers=headers, timeout=10.0)
        response.raise_for_status()
        return response.json().get("items", [])

    async def get_transactions(self, token: str, params: dict[str, str]) -> list[dict]:
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
        return response.json().get("items", [])
