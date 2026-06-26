import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ScriptsService:
    """
    Service for one-off maintenance scripts run against the database.
    """

    def __init__(self, mongo_repo=None):
        self._mongo_repo = mongo_repo

    def delete_invalid_stores(self) -> Dict:
        """
        Deletes every store that is missing a store url or has no deals.

        A store is considered valid only when it has BOTH:
          - a non-empty metadata.store_url, AND
          - at least one deal referencing it (store_id in deal_list).

        Returns a summary of how many stores were scanned and deleted.
        """
        if self._mongo_repo is None:
            raise ConnectionError("MongoDB is not configured for this service")

        stores = self._mongo_repo.get_all_stores()
        store_ids_with_deals = set(self._mongo_repo.get_store_ids_with_deals())

        invalid_store_ids = []
        for store in stores:
            store_id = store.get("id")
            if not store_id:
                continue

            store_url = (store.get("metadata") or {}).get("store_url")
            has_url = bool(store_url and store_url.strip())
            has_deals = store_id in store_ids_with_deals

            if not has_url or not has_deals:
                invalid_store_ids.append(store_id)

        deleted_count = self._mongo_repo.delete_stores_by_ids(invalid_store_ids)

        logger.info(
            "Invalid stores cleanup completed",
            extra={
                "reason": "Removed stores without a url or without deals",
                "extra_data": {
                    "scanned": len(stores),
                    "invalid": len(invalid_store_ids),
                    "deleted": deleted_count,
                },
            },
        )

        return {
            "scanned": len(stores),
            "invalid": len(invalid_store_ids),
            "deleted": deleted_count,
        }
