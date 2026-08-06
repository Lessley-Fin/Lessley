import logging
from services.transaction_stash_service import TransactionStashService
from services.open_finance_service import OpenFinanceService
from services.processing_core_service import ProcessingCoreService
from services.publisher_service import PublisherService
from services.user_repository import UserRepository
from config.constants import LIMITS
from models.transaction import Transaction
from routers.responses import TransactionInsightSchema


logger = logging.getLogger(__name__)


def trim_categories_by_match_level(categories: list, matching_score) -> list:
    """
    Keep only the most relevant categories based on the user's match level (Process 2).

    `categories` is expected sorted by relevance (highest spend first). `matching_score`
    is the fraction X of least-relevant categories to drop:
      keep = round(len * (1 - X))   →  16 @ 0.25 → 12, @ 0.50 → 8, @ 0.75 → 4.

    A null/None score means "no trim" (keep all). At least one category is always kept
    when any exist.
    """
    if not categories:
        return []
    if matching_score is None:
        return categories

    x = max(0.0, min(1.0, float(matching_score)))
    keep = max(1, round(len(categories) * (1 - x)))
    return categories[:keep]


class InsightsService:
    def __init__(
        self,
        open_finance_service: OpenFinanceService,
        files_service: TransactionStashService,
        processing_core_service: ProcessingCoreService,
        publisher_service: PublisherService,
        user_repository: UserRepository,
    ):
        self.open_finance_service = open_finance_service
        self.files_service = files_service
        self.processing_core_service = processing_core_service
        self.publisher_service = publisher_service
        self.user_repository = user_repository

    async def _require_user(self, email: str):
        """
        Ensure the user exists in the Lessley DB before doing any work.
        Returns the user document, or raises HTTP 404 (via UserRepository) if not registered.
        """
        if self.user_repository is None:
            return None
        return await self.user_repository.get_user(email)

    @staticmethod
    def _extract_mcc_tags(categories: list) -> list[str]:
        """
        Flatten the user's categories to a de-duplicated list of MCC codes (as strings).
        Categories are represented system-wide by their MCC code ("MCC string labels").
        """
        tags: list[str] = []
        for category in categories or []:
            for code in category.get("mcc_codes") or []:
                code_str = str(code).strip()
                if code_str and code_str != "N/A" and code_str not in tags:
                    tags.append(code_str)
        return tags

    async def calculate_user_categories_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> list[Transaction]:
        """
        Calculates user categories from spending transactions, then publishes the derived
        tags to the Gateway via publisher_service so they are stored on the user profile
        and become readable through UserRepository by other services (task 9).
        """
        logger.info(
            "Service method called",
            extra={
                "reason": "Method invocation",
                "extra_data": {"user_id": user_id, "time_filter": time_filter, "days": days, "use_mock": use_mock},
            },
        )

        try:
            # Task 1: stop early (HTTP 404) if the user is not registered in Lessley.
            user = await self._require_user(user_id)

            if use_mock:
                transactions = self.files_service.read_json("transactions_roee_all.json")
            else:
                transactions = await self.open_finance_service.get_user_transactions_async(user_id, time_filter, days)

            categories = self.processing_core_service.get_top_spending_categories(transactions)

            # Process 2: keep only the top (Len - X%) categories based on the user's match level.
            matching_score = user.get("MatchingScore") if user else None
            categories = trim_categories_by_match_level(categories, matching_score)

            # Task 5: send the recalculated categories (MCC codes) to the Gateway over HTTP so it
            # updates the user's profile (and SignalR groups). Other services read them back via
            # UserRepository instead of re-running this calculation.
            mcc_tags = self._extract_mcc_tags(categories)
            if self.publisher_service and mcc_tags:
                await self.publisher_service.publish_user_tag_assigned(user_id, mcc_tags)

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
    ) -> list[Transaction]:
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
    ) -> list[Transaction]:
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

    async def calculate_spending_by_day_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> list[dict]:
        """
        Calculates total spending per day of week (Sunday..Saturday) from transactions.
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

            spending_by_day = self.processing_core_service.get_spending_by_day_of_week(transactions)

            logger.info(
                "Spending by day of week calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {"user_id": user_id, "day_count": len(spending_by_day)},
                },
            )
            return spending_by_day
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise

    async def calculate_spending_difference_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> dict:
        """
        Calculates the spending difference between the current period (last `days` days) and the
        previous period of equal length, from a single fetch covering both periods.
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
                transactions = await self.open_finance_service.get_user_transactions_async(
                    user_id, time_filter, days * 2
                )

            difference = self.processing_core_service.get_spending_difference_between_two_periods(
                transactions, days
            )

            logger.info(
                "Spending difference between two periods calculated successfully",
                extra={"reason": "Business logic complete", "extra_data": {"user_id": user_id, **difference}},
            )
            return difference
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise

    async def calculate_spending_saved_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> float:
        """
        Calculates total spending saved (abs difference between charged and original amounts).
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

            total_saved = self.processing_core_service.get_spending_saved(transactions)

            logger.info(
                "Spending saved calculated successfully",
                extra={"reason": "Business logic complete", "extra_data": {"user_id": user_id, "total_saved": total_saved}},
            )
            return total_saved
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise

    async def calculate_spending_saved_by_account_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> list[dict]:
        """
        Calculates total spending saved (abs difference between charged and original amounts),
        grouped by account.
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

            saved_by_account = self.processing_core_service.get_spending_saved_by_account(transactions)

            logger.info(
                "Spending saved by account calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {"user_id": user_id, "account_count": len(saved_by_account)},
                },
            )
            return saved_by_account
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise

    async def calculate_missed_savings_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> list[TransactionInsightSchema]:
        """
        Analyzes user transactions to identify missed savings opportunities.
        For each transaction, identifies alternative stores with active deals for the same MCC category.

        Args:
            user_id: User ID for transaction retrieval
            time_filter: Whether to apply time-based filtering
            days: Number of past days to analyze
            use_mock: Whether to use mock data

        Returns:
            List of TransactionInsightSchema objects with missed savings analysis
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
                transactions = self.open_finance_service.sort_transactions(transactions)

            insights = await self.processing_core_service.calculate_missed_savings_async(transactions)

            if self.publisher_service:
                serialized = [i.dict() if hasattr(i, "dict") else i for i in insights]
                await self.publisher_service.publish_missed_savings_calculated(user_id, serialized)

            logger.info(
                "Missed savings calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {"user_id": user_id, "insight_count": len(insights)},
                },
            )
            return insights
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise
