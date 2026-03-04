import httpx
from datetime import datetime, timedelta
from config import settings

from .insights_service import get_insights_service
from .files_service import get_files_utils_service


class OpenFinanceService:
    def __init__(self):
        self.base_url = settings.OpenFinanceConfig_BaseUrl
        self.client_id = settings.OpenFinanceConfig_ClientId
        self.client_secret = settings.OpenFinanceConfig_ClientSecret

        self.insights_service = get_insights_service()

    async def http_get_access_token(self, user_id: str) -> str:
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

    async def http_get_accounts(self, token: str):
        """
        Retrieves accounts for the given user ID.
        """
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.get("/v2/data/accounts", headers=headers)
            response.raise_for_status()
            return response.json().get("items", [])

    async def http_get_transactions(self, token: str, params: any):
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

    async def get_user_accounts(self, user_id: str):
        """
        Retrieves user accounts for the given user ID.
        """
        token = await self.http_get_access_token(user_id)
        accounts = await self.http_get_accounts(token)
        return accounts

    async def get_user_transactions_last_3_months(self, user_id: str):
        """
        Retrieves banking data for the past 90 days.
        """
        # Calculate the date 90 days ago
        from_date = (datetime.utcnow() - timedelta(days=90)).date()

        # 1. Get Token [cite: 388]
        token = await self.http_get_access_token(user_id)

        # 2. Get Accounts [cite: 389]
        accounts = await self.http_get_accounts(token)

        # 3. Get Transactions for each account [cite: 390]
        all_transactions = []
        for account in accounts:
            account_id = account.get("id")
            transactions = await self.http_get_transactions(
                token, {"dateFrom": from_date, "accountId": account_id}
            )
            all_transactions.extend(transactions)

        return all_transactions

    async def calc_user_categories(self, user_id: str):
        """
        Calculates user categories based on transactions.
        """
        # transactions = await self.get_user_transactions_last_3_months(user_id)

        file = get_files_utils_service()
        transactions = file.read_json("transactions.json")  # For testing purposes
        categories = self.insights_service.get_top_spending_categories(transactions)
        return categories


# Dependency Injection provider function
def get_open_finance_service():
    return OpenFinanceService()
