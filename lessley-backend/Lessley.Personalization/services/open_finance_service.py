import asyncio
import logging
from datetime import datetime, timedelta
from .clients.open_finance_client import OpenFinanceClient
from config.constants import LIMITS
from models.transaction import Transaction
from config.structured_logging import StructuredLogger, log_service_start, log_service_failure

logger = logging.getLogger(__name__)


class OpenFinanceService:
    def __init__(self, client: OpenFinanceClient):
        self.client = client

    async def get_access_token_async(self, user_id: str) -> str:
        """
        Retrieves an access token for the given user ID.
        """
        log_service_start(
            logger, service_name="OpenFinanceService", method_name="get_access_token_async", params={"user_id": user_id}
        )

        try:
            token = await self.client.get_access_token(user_id)

            StructuredLogger.log_with_context(
                logger,
                "debug",
                "Access token retrieved successfully",
                reason="User authentication with OpenFinance",
                extra_data={"user_id": user_id},
            )

            return token
        except Exception as e:
            log_service_failure(
                logger,
                service_name="OpenFinanceService",
                method_name="get_access_token_async",
                error=e,
                context={"user_id": user_id},
            )
            raise

    async def get_user_accounts_async(self, user_id: str) -> list[dict]:
        """
        Retrieves user accounts for the given user ID.
        """
        log_service_start(
            logger,
            service_name="OpenFinanceService",
            method_name="get_user_accounts_async",
            params={"user_id": user_id},
        )

        try:
            token = await self.client.get_access_token(user_id)
            accounts = await self.client.get_accounts(token)

            StructuredLogger.log_with_context(
                logger,
                "info",
                "User accounts retrieved successfully",
                reason="Data fetching from OpenFinance API",
                extra_data={"user_id": user_id, "account_count": len(accounts)},
            )

            return accounts
        except Exception as e:
            log_service_failure(
                logger,
                service_name="OpenFinanceService",
                method_name="get_user_accounts_async",
                error=e,
                context={"user_id": user_id},
            )
            raise

    async def get_user_transactions_by_account_async(
        self, user_id: str, account_id: str, is_time_filter: bool, days: int = LIMITS.DAYS
    ) -> list[Transaction]:
        """
        Retrieves banking data for the past {days} days.
        """
        log_service_start(
            logger,
            service_name="OpenFinanceService",
            method_name="get_user_transactions_by_account_async",
            params={"user_id": user_id, "account_id": account_id, "days": days},
        )

        try:
            # 1. Get Token
            token = await self.client.get_access_token(user_id)

            # 2. Get Transactions for account
            if is_time_filter:
                from_date = (datetime.utcnow() - timedelta(days=days)).date()
                params = {"dateFrom": from_date, "accountId": account_id}
            else:
                params = {"accountId": account_id}

            transactions = await self.client.get_transactions(token, params)

            StructuredLogger.log_with_context(
                logger,
                "info",
                "Transactions retrieved for account",
                reason="API data fetching",
                extra_data={
                    "user_id": user_id,
                    "account_id": account_id,
                    "transaction_count": len(transactions),
                    "time_filter_days": days if is_time_filter else None,
                },
            )

            return transactions
        except Exception as e:
            log_service_failure(
                logger,
                service_name="OpenFinanceService",
                method_name="get_user_transactions_by_account_async",
                error=e,
                context={"user_id": user_id, "account_id": account_id},
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

        log_service_start(
            logger,
            service_name="OpenFinanceService",
            method_name="get_user_transactions_async",
            params={"user_id": user_id, "days": days},
        )

        try:
            # 1. Get Token
            token = await self.client.get_access_token(user_id)

            # 2. Get Accounts
            accounts = await self.client.get_accounts(token)

            StructuredLogger.log_with_context(
                logger,
                "debug",
                "User accounts fetched",
                reason="Preparation for transaction retrieval",
                extra_data={"user_id": user_id, "account_count": len(accounts)},
            )

            # 3. Get Transactions for each account in parallel
            params = {}
            if is_time_filter:
                params = {"dateFrom": (datetime.utcnow() - timedelta(days=days)).date()}

            tasks = [
                self.client.get_transactions(token, {"accountId": account.get("id"), **params}) for account in accounts
            ]

            # Wait for ALL to complete simultaneously
            transaction_batches = await asyncio.gather(*tasks)
            all_transactions = [tx for batch in transaction_batches for tx in batch]

            elapsed_time_ms = (time.time() - start_time) * 1000

            StructuredLogger.log_with_context(
                logger,
                "info",
                "All user transactions retrieved successfully",
                reason="Data aggregation from all accounts complete",
                extra_data={
                    "user_id": user_id,
                    "account_count": len(accounts),
                    "total_transaction_count": len(all_transactions),
                    "elapsed_time_ms": elapsed_time_ms,
                    "time_filter_days": days if is_time_filter else None,
                },
            )

            return all_transactions
        except Exception as e:
            log_service_failure(
                logger,
                service_name="OpenFinanceService",
                method_name="get_user_transactions_async",
                error=e,
                context={"user_id": user_id, "account_count": len(accounts) if "accounts" in locals() else None},
            )
            raise
