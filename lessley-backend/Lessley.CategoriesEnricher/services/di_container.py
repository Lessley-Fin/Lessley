import threading
from .categories_service import CategoriesService


class DIContainer:
    _instances = {}
    _lock = threading.RLock()

    @staticmethod
    def get_categories_service() -> CategoriesService:
        with DIContainer._lock:
            if "categories_service" not in DIContainer._instances:
                DIContainer._instances["categories_service"] = CategoriesService()
            return DIContainer._instances["categories_service"]
