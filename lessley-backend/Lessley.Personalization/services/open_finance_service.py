import asyncio
import logging
from datetime import date, datetime, timedelta
from .clients.open_finance_client import OpenFinanceClient
from config.constants import LIMITS
from models.transaction import Transaction

logger = logging.getLogger(__name__)


class OpenFinanceService:
    def __init__(self, client: OpenFinanceClient):
        self.client = client

    async def get_access_token_async(self, user_id: str) -> str:
        """
        Retrieves an access token for the given user ID.
        """
        logger.info(
            "Service method called",
            extra={"reason": "Method invocation", "extra_data": {"user_id": user_id}},
        )

        try:
            token = await self.client.get_access_token(user_id)

            logger.debug(
                "Access token retrieved successfully",
                extra={
                    "reason": "User authentication with OpenFinance",
                    "extra_data": {"user_id": user_id},
                },
            )

            return token
        except Exception as e:
            logger.error(
                f"Error in get_access_token_async: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Service execution failure",
                    "extra_data": {"user_id": user_id},
                },
            )
            raise

    async def get_user_accounts_async(self, user_id: str) -> list[dict]:
        """
        Retrieves user accounts for the given user ID.
        """
        logger.info(
            "Service method called",
            extra={"reason": "Method invocation", "extra_data": {"user_id": user_id}},
        )

        try:
            accounts = await self.client.get_accounts(user_id)

            logger.info(
                "User accounts retrieved successfully",
                extra={
                    "reason": "Data fetching from OpenFinance API",
                    "extra_data": {"user_id": user_id, "account_count": len(accounts)},
                },
            )

            return accounts
        except Exception as e:
            logger.error(
                f"Error in get_user_accounts_async: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Service execution failure",
                    "extra_data": {"user_id": user_id},
                },
            )
            raise

    async def get_user_transactions_by_account_async(
        self, user_id: str, account_id: str, is_time_filter: bool, days: int = LIMITS.DAYS
    ) -> list[Transaction]:
        """
        Retrieves banking data for the past {days} days.
        """
        logger.info(
            "Service method called",
            extra={
                "reason": "Method invocation",
                "extra_data": {
                    "user_id": user_id,
                    "account_id": account_id,
                    "days": days,
                    "is_time_filter": is_time_filter,
                },
            },
        )

        try:
            # 1. Get Transactions for account (the client acquires/refreshes the token itself)
            if is_time_filter:
                from_date = (datetime.utcnow() - timedelta(days=days)).date()
                params = {"dateFrom": from_date, "accountId": account_id}
            else:
                params = {"accountId": account_id}

            transactions = await self.client.get_transactions(user_id, params)

            logger.info(
                "Transactions retrieved for account",
                extra={
                    "reason": "API data fetching",
                    "extra_data": {
                        "user_id": user_id,
                        "account_id": account_id,
                        "transaction_count": len(transactions),
                        "time_filter_days": days if is_time_filter else None,
                    },
                },
            )

            return transactions
        except Exception as e:
            logger.error(
                f"Error in get_user_transactions_by_account_async: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Service execution failure",
                    "extra_data": {"user_id": user_id, "account_id": account_id},
                },
            )
            raise

    async def get_user_transactions_async(
        self, user_id: str, is_time_filter: bool, days: int = LIMITS.DAYS
    ) -> list[Transaction]:
        """
        Retrieves banking data for the past {days} days for all user accounts.
        """
        import time

        start_time = time.time()
        logger.info(
            "Service method called",
            extra={
                "reason": "Method invocation",
                "extra_data": {"user_id": user_id, "days": days, "is_time_filter": is_time_filter},
            },
        )

        try:
            # 1. Get Accounts (the client acquires/refreshes the token itself)
            accounts = await self.client.get_accounts(user_id)

            logger.info(
                "User accounts fetched",
                extra={
                    "reason": "Preparation for transaction retrieval",
                    "extra_data": {"user_id": user_id, "account_count": len(accounts)},
                },
            )

            # 2. Get Transactions for each account in parallel
            params = {}
            if is_time_filter:
                params = {"dateFrom": (datetime.utcnow() - timedelta(days=days)).date()}

            tasks = [
                self.client.get_transactions(user_id, {"accountId": account.get("id"), **params})
                for account in accounts
            ]

            # Wait for ALL to complete simultaneously
            transaction_batches = await asyncio.gather(*tasks)
            all_transactions = [tx for batch in transaction_batches for tx in batch]

            elapsed_time_ms = (time.time() - start_time) * 1000

            logger.info(
                "All user transactions retrieved successfully",
                extra={
                    "reason": "Data aggregation from all accounts complete",
                    "extra_data": {
                        "user_id": user_id,
                        "account_count": len(accounts),
                        "total_transaction_count": len(all_transactions),
                        "elapsed_time_ms": elapsed_time_ms,
                        "time_filter_days": days if is_time_filter else None,
                    },
                },
            )

            return all_transactions
        except Exception as e:
            logger.error(
                f"Error in get_user_transactions_async: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Service execution failure",
                    "extra_data": {
                        "user_id": user_id,
                        "account_count": len(accounts) if "accounts" in locals() else None,
                    },
                },
            )
            raise

    def sort_transactions(self, transactions: list[Transaction]) -> list[Transaction]:
        """
        Sorts transactions by date in descending order.
        """
        return sorted(
            transactions,
            key=lambda tx: (
                tx.date.transactionDate or tx.date.bookingDate or tx.date.valueDate or date.min
                if tx.date else date.min
            ),
            reverse=True,
        )