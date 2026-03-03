import httpx
from datetime import datetime, timedelta
from config import settings


class OpenFinanceService:
    def __init__(self):
        self.base_url = settings.OpenFinanceConfig_BaseUrl
        self.client_id = settings.OpenFinanceConfig_ClientId
        self.client_secret = settings.OpenFinanceConfig_ClientSecret

    async def get_user_transactions_last_3_months(self, user_id: str):
        """
        Retrieves banking data for the past 90 days.
        """
        # Calculate the date 90 days ago
        from_date = (datetime.utcnow() - timedelta(days=90)).date()

        # We use httpx.AsyncClient exactly like HttpClient in C#
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            # 1. Get Token [cite: 388]
            token_response = await client.post(
                "/oauth/token",
                json={
                    "userId": user_id,
                    "clientId": self.client_id,
                    "clientSecret": self.client_secret,
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            token = token_data.get("accessToken")
            headers = {"Authorization": f"Bearer {token}"}

            # 2. Get Accounts [cite: 389]
            # accounts_response = await client.get(
            #     f"/data/accounts?userId={user_id}", headers=headers
            # )
            # accounts_response.raise_for_status()
            # accounts = accounts_response.json().get("accounts", [])

            # all_transactions = []

            # 3. Get Transactions for each account [cite: 390]
            # for account in accounts:
            #     account_id = account.get("id")
            #     trans_response = await client.get(
            #         f"/data/transactions?accountId={account_id}&from_date={from_date}",
            #         headers=headers,
            #     )
            #     trans_response.raise_for_status()
            #     all_transactions.extend(trans_response.json().get("transactions", []))

            # return all_transactions

            trans_response = await client.get(
                "/v2/data/transactions",
                params={"dateFrom": from_date},
                headers=headers,
            )
            trans_response.raise_for_status()
            transaction_data = trans_response.json()
            print(f"Obtained transactions for user {user_id}: {transaction_data}")
            all_transactions = transaction_data.get("items")

            return all_transactions


# Dependency Injection provider function
def get_open_finance_service():
    return OpenFinanceService()
