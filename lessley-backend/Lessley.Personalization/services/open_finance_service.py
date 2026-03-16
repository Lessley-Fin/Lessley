import asyncio
from datetime import datetime, timedelta
from .clients.open_finance_client import OpenFinanceClient
from config.constants import LIMITS
from models.transaction import Transaction


class OpenFinanceService:
    def __init__(self, client: OpenFinanceClient):

        self.client = client

    async def get_access_token_async(self, user_id: str) -> str:
        """
        Retrieves an access token for the given user ID.
        """
        return await self.client.get_access_token(user_id)

    async def get_user_accounts_async(self, user_id: str) -> list[dict]:
        """
        Retrieves user accounts for the given user ID.
        """
        token = await self.client.get_access_token(user_id)
        return await self.client.get_accounts(token)

    async def get_user_transactions_by_account_async(
        self, user_id: str, account_id: str, is_time_filter: bool, days: int = LIMITS.DAYS
    ) -> list[Transaction]:
        """
        Retrieves banking data for the past {days} days.
        """
        # 1. Get Token [cite: 388]
        token = await self.client.get_access_token(user_id)

        # 2. Get Transactions for each account [cite: 390]
        if is_time_filter:
            from_date = (datetime.utcnow() - timedelta(days=days)).date()
            params = {"dateFrom": from_date, "accountId": account_id}
        else:
            params = {"accountId": account_id}

        return await self.client.get_transactions(token, params)

    async def get_user_transactions_async(
        self, user_id: str, is_time_filter: bool, days: int = LIMITS.DAYS
    ) -> list[Transaction]:
        """
        Retrieves banking data for the past {days} days.
        """
        # 1. Get Token [cite: 388]
        token = await self.client.get_access_token(user_id)

        # 2. Get Accounts [cite: 389]
        accounts = await self.client.get_accounts(token)

        # 3. Get Transactions for each account [cite: 390]
        params = {}
        if is_time_filter:
            params = {"dateFrom": (datetime.utcnow() - timedelta(days=days)).date()}
        tasks = [
            self.client.get_transactions(token, {"accountId": account.get("id"), **params}) for account in accounts
        ]

        # Wait for ALL to complete simultaneously
        transaction_batches = await asyncio.gather(*tasks)
        return [tx for batch in transaction_batches for tx in batch]
