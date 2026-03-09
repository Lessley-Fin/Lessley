# services/di_container.py
from .clients.open_finance_client import OpenFinanceClient
from .open_finance_service import OpenFinanceService
from .insights_service import InsightsService
from .transaction_stash_service import TransactionStashService
from .processing_core_service import ProcessingCoreService
from .mcc_service import MccService


class DIContainer:
    _instances = {}

    @staticmethod
    def get_transaction_stash_service() -> TransactionStashService:
        if "transaction_stash_service" not in DIContainer._instances:
            DIContainer._instances["transaction_stash_service"] = TransactionStashService()
        return DIContainer._instances["transaction_stash_service"]

    @staticmethod
    def get_processing_service() -> ProcessingCoreService:
        if "processing_service" not in DIContainer._instances:
            DIContainer._instances["processing_service"] = ProcessingCoreService(
                mcc_service=DIContainer.get_mcc_service()
            )
        return DIContainer._instances["processing_service"]

    @staticmethod
    def get_mcc_service() -> MccService:
        if "mcc_service" not in DIContainer._instances:
            DIContainer._instances["mcc_service"] = MccService()
        return DIContainer._instances["mcc_service"]

    @staticmethod
    def get_insights_service() -> InsightsService:
        if "insights_service" not in DIContainer._instances:
            DIContainer._instances["insights_service"] = InsightsService(
                open_finance_service=DIContainer.get_open_finance_service(),
                files_service=DIContainer.get_transaction_stash_service(),
                processing_core_service=DIContainer.get_processing_service(),
            )
        return DIContainer._instances["insights_service"]

    @staticmethod
    def get_open_finance_client() -> OpenFinanceClient:
        if "open_finance_client" not in DIContainer._instances:
            DIContainer._instances["open_finance_client"] = OpenFinanceClient()
        return DIContainer._instances["open_finance_client"]

    @staticmethod
    def get_open_finance_service() -> OpenFinanceService:
        if "open_finance_service" not in DIContainer._instances:
            DIContainer._instances["open_finance_service"] = OpenFinanceService(
                client=DIContainer.get_open_finance_client()
            )
        return DIContainer._instances["open_finance_service"]
