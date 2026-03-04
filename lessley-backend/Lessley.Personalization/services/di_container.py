# services/di_container.py
from .clients.open_finance_client import OpenFinanceClient
from .open_finance_service import OpenFinanceService
from .insights_service import InsightsService
from .files_service import FilesUtilsService
from .mcc_service import MccService


class DIContainer:
    _instances = {}

    @staticmethod
    def get_files_service() -> FilesUtilsService:
        if "files_service" not in DIContainer._instances:
            DIContainer._instances["files_service"] = FilesUtilsService()
        return DIContainer._instances["files_service"]

    @staticmethod
    def get_mcc_service() -> MccService:
        if "mcc_service" not in DIContainer._instances:
            DIContainer._instances["mcc_service"] = MccService()
        return DIContainer._instances["mcc_service"]

    @staticmethod
    def get_insights_service() -> InsightsService:
        if "insights_service" not in DIContainer._instances:
            DIContainer._instances["insights_service"] = InsightsService(
                mcc_service=DIContainer.get_mcc_service()
            )
        return DIContainer._instances["insights_service"]

    @staticmethod
    def get_open_finance_service() -> OpenFinanceService:
        if "open_finance_service" not in DIContainer._instances:
            DIContainer._instances["open_finance_service"] = OpenFinanceService(
                client=DIContainer.get_open_finance_client(),
                insights_service=DIContainer.get_insights_service(),
                files_service=DIContainer.get_files_service(),
            )
        return DIContainer._instances["open_finance_service"]

    @staticmethod
    def get_open_finance_client() -> OpenFinanceClient:
        if "open_finance_client" not in DIContainer._instances:
            DIContainer._instances["open_finance_client"] = OpenFinanceClient()
        return DIContainer._instances["open_finance_client"]
