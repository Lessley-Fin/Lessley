import httpx
from config import settings


class OpenFinanceClient:
    def __init__(self):
        self.base_url = settings.OpenFinanceConfig_BaseUrl
        self.client_id = settings.OpenFinanceConfig_ClientId
        self.client_secret = settings.OpenFinanceConfig_ClientSecret

    async def get_access_token(self, user_id: str) -> str:
        """
        Retrieves an access token for the given user ID.
        """
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.post(
                "/oauth/token",
                json={
                    "userId": user_id,
                    "clientId": self.client_id,
                    "clientSecret": self.client_secret,
                },
            )
            response.raise_for_status()
            token_data = response.json()
            return token_data.get("accessToken")

    async def get_accounts(self, token: str):
        """
        Retrieves accounts for the given user ID.
        """
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.get("/v2/data/accounts", headers=headers)
            response.raise_for_status()
            return response.json().get("items", [])

    async def get_transactions(self, token: str, params: any):
        """
        Retrieves transactions for the given user ID starting from the specified date.
        """
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.get(
                "/v2/data/transactions",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            return response.json().get("items", [])


# Dependency Injection provider function
def get_open_finance_client():
    return OpenFinanceClient()
