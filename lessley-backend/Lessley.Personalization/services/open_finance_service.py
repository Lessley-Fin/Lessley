import asyncio
from datetime import datetime, timedelta
from .clients.open_finance_client import OpenFinanceClient
from config.constants import LIMITS
from services.utils.normalise_data import Transaction


class OpenFinanceService:
    def __init__(self, client: OpenFinanceClient):

        self.client = client

    # TODO: manage token caching
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
        accounts = await self.client.get_accounts(token)
        return accounts

    # TODO: return List[Transaction]
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

        all_transactions = await self.client.get_transactions(token, params)

        return all_transactions

    # TODO: return List[Transaction]
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
        # all_transactions = []
        # for account in accounts:
        #     account_id = account.get("id")
        #     if is_time_filter:
        #         from_date = (datetime.utcnow() - timedelta(days=days)).date()
        #         params = {"dateFrom": from_date, "accountId": account_id}
        #     else:
        #         params = {"accountId": account_id}
        #     transactions = await self.client.get_transactions(token, params)
        #     all_transactions.extend(transactions)

        params = {}
        if is_time_filter:
            params = {"dateFrom": (datetime.utcnow() - timedelta(days=days)).date()}
        tasks = [
            self.client.get_transactions(token, {"accountId": account.get("id"), **params}) for account in accounts
        ]

        # Wait for ALL to complete simultaneously
        transaction_batches = await asyncio.gather(*tasks)
        return [tx for batch in transaction_batches for tx in batch]
