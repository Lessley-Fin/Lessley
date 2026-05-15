import logging
from services.transaction_stash_service import TransactionStashService
from services.open_finance_service import OpenFinanceService
from services.processing_core_service import ProcessingCoreService
from config.constants import LIMITS


logger = logging.getLogger(__name__)


class InsightsService:
    def __init__(
        self,
        open_finance_service: OpenFinanceService,
        files_service: TransactionStashService,
        processing_core_service: ProcessingCoreService,
    ):
        self.open_finance_service = open_finance_service
        self.files_service = files_service
        self.processing_core_service = processing_core_service

    async def calculate_user_categories_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> list[dict]:
        """
        Calculates user categories based on transactions.
        """
        logger.info(
            "Service method called",
            extra={
                "reason": "Method invocation",
                "extra_data": {"user_id": user_id, "time_filter": time_filter, "days": days, "use_mock": use_mock},
            },
        )

        try:
            if use_mock:
                transactions = self.files_service.read_json("transactions_roee_all.json")
            else:
                transactions = await self.open_finance_service.get_user_transactions_async(user_id, time_filter, days)

            categories = self.processing_core_service.get_top_spending_categories(transactions)

            logger.info(
                "User categories calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {"user_id": user_id, "category_count": len(categories)},
                },
            )
            return categories
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise

    async def calculate_top_accounts_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> list[dict]:
        """
        Calculates top accounts based on transactions.
        """
        logger.info(
            "Service method called",
            extra={
                "reason": "Method invocation",
                "extra_data": {"user_id": user_id, "time_filter": time_filter, "days": days, "use_mock": use_mock},
            },
        )

        try:
            if use_mock:
                transactions = self.files_service.read_json("transactions_roee_all.json")
            else:
                transactions = await self.open_finance_service.get_user_transactions_async(user_id, time_filter, days)

            accounts = self.processing_core_service.get_top_spending_accounts(
                transactions,
                flat_columns=[
                    "accountId",
                    "accountNumber",
                    "providerId",
                    "type",
                    "amount.chargedAmount.amount",
                    "amount.originalAmount.amount",
                ],
                group_by_column="accountId",
                ascending=False,
            )

            logger.info(
                "Top accounts calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {"user_id": user_id, "account_count": len(accounts)},
                },
            )
            return accounts
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise

    async def calculate_top_stores_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> list[dict]:
        """
        Calculates top stores based on transactions.
        """
        logger.info(
            "Service method called",
            extra={
                "reason": "Method invocation",
                "extra_data": {"user_id": user_id, "time_filter": time_filter, "days": days, "use_mock": use_mock},
            },
        )

        try:
            if use_mock:
                transactions = self.files_service.read_json("transactions_roee_all.json")
            else:
                transactions = await self.open_finance_service.get_user_transactions_async(user_id, time_filter, days)

            stores = self.processing_core_service.get_top_spending_stores(transactions)

            logger.info(
                "Top stores calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {"user_id": user_id, "store_count": len(stores)},
                },
            )
            return stores
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise
