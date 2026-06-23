import logging
from typing import Optional, Dict, Any, List
from pymongo import MongoClient
from config.settings import settings

logger = logging.getLogger(__name__)

_DB_NAME = "lessley"
_DEAL_COLLECTION = "deal_list"
_STORE_COLLECTION = "store_list"


class MongoRepository:
    def __init__(self):
        if not settings.ConnectionStrings_MongoDb:
            raise ConnectionError(
                "MongoDB connection string is not configured. Set ConnectionStrings_MongoDb in .env"
            )
        self._client = MongoClient(settings.ConnectionStrings_MongoDb)
        self._db = self._client[_DB_NAME]
        logger.info(
            "MongoRepository initialized",
            extra={"reason": "Database client created", "extra_data": {}},
        )

    def get_deal_by_id(self, deal_id: str) -> Optional[Dict[str, Any]]:
        return self._db[_DEAL_COLLECTION].find_one({"id": deal_id})

    def get_store_by_id(self, store_id: str) -> Optional[Dict[str, Any]]:
        return self._db[_STORE_COLLECTION].find_one({"id": store_id})

    def get_stores_page(self, page: int, page_size: int) -> List[Dict[str, Any]]:
        skip = (page - 1) * page_size
        return list(self._db[_STORE_COLLECTION].find().skip(skip).limit(page_size))

    def count_stores(self) -> int:
        return self._db[_STORE_COLLECTION].count_documents({})

    def get_first_deal_by_store_id(self, store_id: str) -> Optional[Dict[str, Any]]:
        return self._db[_DEAL_COLLECTION].find_one({"store_id": store_id})

    def update_store_mcc(self, store_id: str, mcc_codes: List[str], official_name: str, confidence: str):
        self._db[_STORE_COLLECTION].update_one(
            {"id": store_id},
            {"$set": {
                "metadata.mcc_codes": mcc_codes,
                "metadata.official_name": official_name,
                "metadata.mcc_confidence": confidence,
            }},
        )

    def close(self):
        if self._client:
            self._client.close()
