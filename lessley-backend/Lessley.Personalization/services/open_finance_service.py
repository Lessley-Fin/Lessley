from datetime import datetime, timedelta

from .clients.open_finance_client import OpenFinanceClient
from .insights_service import InsightsService
from .files_service import FilesUtilsService


class OpenFinanceService:
    def __init__(
        self,
        client: OpenFinanceClient,
        insights_service: InsightsService,
        files_service: FilesUtilsService,
    ):

        self.client = client
        self.insights_service = insights_service
        self.files_service = files_service

    async def get_access_token_async(self, user_id: str) -> str:
        """
        Retrieves an access token for the given user ID.
        """
        return await self.client.get_access_token(user_id)

    async def get_user_accounts_async(self, user_id: str):
        """
        Retrieves user accounts for the given user ID.
        """
        token = await self.client.get_access_token(user_id)
        accounts = await self.client.get_accounts(token)
        return accounts

    async def get_user_transactions_async(self, user_id: str, days: int = 90):
        """
        Retrieves banking data for the past {days} days.
        """
        # Calculate the date {days} days ago
        from_date = (datetime.utcnow() - timedelta(days=days)).date()

        # 1. Get Token [cite: 388]
        token = await self.client.get_access_token(user_id)

        # 2. Get Accounts [cite: 389]
        accounts = await self.client.get_accounts(token)

        # 3. Get Transactions for each account [cite: 390]
        all_transactions = []
        for account in accounts:
            account_id = account.get("id")
            transactions = await self.client.get_transactions(
                token, {"dateFrom": from_date, "accountId": account_id}
            )
            all_transactions.extend(transactions)

        return {"items": all_transactions}

    async def get_user_categories(self, user_id: str):
        """
        Calculates user categories based on transactions.
        """
        # transactions = await self.get_user_transactions_last_3_months(user_id)

        transactions = self.files_service.read_json("transactions_shmer.json")
        categories = self.insights_service.get_top_spending_categories(transactions)
        return categories

    async def calculate_user_categories_async(self, user_id: str, days: int = 90):
        """
        Calculates user categories based on transactions.
        """
        transactions = await self.get_user_transactions_async(user_id, days=days)
        print(
            f"Retrieved {len(transactions)} transactions for user {user_id}, {transactions.items}"
        )
        categories = self.insights_service.get_top_spending_categories(transactions)

        # then send to insights service for further processing, or return directly

        return categories


# Dependency Injection provider function
def get_open_finance_service():
    return OpenFinanceService()
