import logging
import threading
from .categories_service import CategoriesService
from .clients.mongo_client import MongoRepository

logger = logging.getLogger(__name__)


class DIContainer:
    _instances = {}
    _lock = threading.RLock()

    @staticmethod
    def _get_mongo_repository():
        if "mongo_repository" not in DIContainer._instances:
            try:
                DIContainer._instances["mongo_repository"] = MongoRepository()
            except ConnectionError:
                logger.warning(
                    "MongoDB not configured — deal classification will be unavailable",
                    extra={"reason": "Optional dependency missing", "extra_data": {}},
                )
                DIContainer._instances["mongo_repository"] = None
        return DIContainer._instances["mongo_repository"]

    @staticmethod
    def get_categories_service() -> CategoriesService:
        with DIContainer._lock:
            if "categories_service" not in DIContainer._instances:
                mongo_repo = DIContainer._get_mongo_repository()
                DIContainer._instances["categories_service"] = CategoriesService(
                    mongo_repo=mongo_repo
                )
            return DIContainer._instances["categories_service"]
