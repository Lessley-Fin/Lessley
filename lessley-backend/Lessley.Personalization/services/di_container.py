import threading
from .clients.open_finance_client import OpenFinanceClient
from .open_finance_service import OpenFinanceService
from .insights_service import InsightsService
from .transaction_stash_service import TransactionStashService
from .processing_core_service import ProcessingCoreService
from .mcc_service import MccService
from .recommendation_service import RecommendationService
from .recommendation_core_service import RecommendationCoreService
from .user_repository import UserRepository
from .publisher_service import PublisherService


class DIContainer:
    _instances = {}
    _lock = threading.RLock()

    @staticmethod
    def set_publisher_service(service: PublisherService | None) -> None:
        """Called from main.py lifespan after async publisher setup completes."""
        DIContainer._instances["publisher_service"] = service

    @staticmethod
    def get_publisher_service() -> PublisherService | None:
        return DIContainer._instances.get("publisher_service")

    @staticmethod
    def get_transaction_stash_service() -> TransactionStashService:
        with DIContainer._lock:
            if "transaction_stash_service" not in DIContainer._instances:
                DIContainer._instances["transaction_stash_service"] = TransactionStashService()
            return DIContainer._instances["transaction_stash_service"]

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
                    files_service=DIContainer.get_transaction_stash_service(),
                    processing_core_service=DIContainer.get_processing_service(),
                    publisher_service=DIContainer.get_publisher_service(),
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
    def get_user_repository() -> UserRepository:
        with DIContainer._lock:
            if "user_repository" not in DIContainer._instances:
                DIContainer._instances["user_repository"] = UserRepository()
            return DIContainer._instances["user_repository"]

    @staticmethod
    def get_recommendation_service() -> RecommendationService:
        with DIContainer._lock:
            if "recommendation_service" not in DIContainer._instances:
                DIContainer._instances["recommendation_service"] = RecommendationService(
                    recommendation_core_service=DIContainer.get_recommendation_core_service(),
                    user_repository=DIContainer.get_user_repository(),
                    publisher_service=DIContainer.get_publisher_service(),
                    mcc_service=DIContainer.get_mcc_service(),
                )
            return DIContainer._instances["recommendation_service"]

    @staticmethod
    def get_recommendation_core_service() -> RecommendationCoreService:
        with DIContainer._lock:
            if "recommendation_core_service" not in DIContainer._instances:
                DIContainer._instances["recommendation_core_service"] = RecommendationCoreService()
            return DIContainer._instances["recommendation_core_service"]
