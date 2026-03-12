from services.transaction_stash_service import TransactionStashService
from services.open_finance_service import OpenFinanceService
from services.processing_core_service import ProcessingCoreService


class InsightsService:
    def __init__(
        self,
        open_finance_service=OpenFinanceService,
        files_service=TransactionStashService,
        processing_core_service=ProcessingCoreService,
    ):
        self.open_finance_service = open_finance_service
        self.files_service = files_service
        self.processing_core_service = processing_core_service

    async def calculate_user_categories_async(
        self, user_id: str, time_filter: bool, days: int = 60, use_mock: bool = False
    ) -> list[dict]:
        """
        Calculates user categories based on transactions.
        """

        if use_mock:
            transactions = self.files_service.read_json("transactions_roee_all.json")
        else:
            transactions = await self.open_finance_service.get_user_transactions_async(user_id, time_filter, days)

        categories = self.processing_core_service.get_top_spending_categories(transactions, limit=10)
        return categories

    async def calculate_top_accounts_async(
        self, user_id: str, time_filter: bool, days: int = 60, use_mock: bool = False
    ) -> list[dict]:
        """
        Calculates top accounts based on transactions.
        """

        if use_mock:
            transactions = self.files_service.read_json("transactions_roee_all.json")
        else:
            transactions = await self.open_finance_service.get_user_transactions_async(user_id, time_filter, days)

        print(f"Retrieved {len(transactions)} transactions for user {user_id}")

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
            limit=5,
        )

        return accounts

    async def calculate_top_stores_async(
        self, user_id: str, time_filter: bool, days: int = 60, use_mock: bool = False
    ) -> list[dict]:
        """
        Calculates top stores based on transactions.
        """

        if use_mock:
            transactions = self.files_service.read_json("transactions_roee_all.json")
        else:
            transactions = await self.open_finance_service.get_user_transactions_async(user_id, time_filter, days)

        print(f"Retrieved {len(transactions)} transactions for user {user_id}")

        accounts = self.processing_core_service.get_top_spending_stores(transactions)

        return accounts
