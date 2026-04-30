import threading
from .clients.open_finance_client import OpenFinanceClient
from .open_finance_service import OpenFinanceService
from .insights_service import InsightsService
from .processing_core_service import ProcessingCoreService
from .mcc_service import MccService
from .recommendation_service import RecommendationService
from .recommendation_core_service import RecommendationCoreService


class DIContainer:
    _instances = {}
    _lock = threading.RLock()

    @staticmethod
    def get_processing_service() -> ProcessingCoreService:
        with DIContainer._lock:
            if "processing_service" not in DIContainer._instances:
                DIContainer._instances["processing_service"] = ProcessingCoreService(
                    mcc_service=DIContainer.get_mcc_service()
                )
            return DIContainer._instances["processing_service"]

    @staticmethod
    def get_mcc_service() -> MccService:
        with DIContainer._lock:
            if "mcc_service" not in DIContainer._instances:
                DIContainer._instances["mcc_service"] = MccService()
            return DIContainer._instances["mcc_service"]

    @staticmethod
    def get_insights_service() -> InsightsService:
        with DIContainer._lock:
            if "insights_service" not in DIContainer._instances:
                DIContainer._instances["insights_service"] = InsightsService(
                    open_finance_service=DIContainer.get_open_finance_service(),
                    processing_core_service=DIContainer.get_processing_service(),
                )
            return DIContainer._instances["insights_service"]

    @staticmethod
    def get_open_finance_client() -> OpenFinanceClient:
        with DIContainer._lock:
            if "open_finance_client" not in DIContainer._instances:
                DIContainer._instances["open_finance_client"] = OpenFinanceClient()
            return DIContainer._instances["open_finance_client"]

    @staticmethod
    def get_open_finance_service() -> OpenFinanceService:
        with DIContainer._lock:
            if "open_finance_service" not in DIContainer._instances:
                DIContainer._instances["open_finance_service"] = OpenFinanceService(
                    client=DIContainer.get_open_finance_client()
                )
            return DIContainer._instances["open_finance_service"]

    @staticmethod
    def get_recommendation_service() -> RecommendationService:
        with DIContainer._lock:
            if "recommendation_service" not in DIContainer._instances:
                DIContainer._instances["recommendation_service"] = RecommendationService(
                    recommendation_core_service=DIContainer.get_recommendation_core_service(),
                    insights_service=DIContainer.get_insights_service(),
                )
            return DIContainer._instances["recommendation_service"]

    @staticmethod
    def get_recommendation_core_service() -> RecommendationCoreService:
        with DIContainer._lock:
            if "recommendation_core_service" not in DIContainer._instances:
                DIContainer._instances["recommendation_core_service"] = RecommendationCoreService()
            return DIContainer._instances["recommendation_core_service"]
