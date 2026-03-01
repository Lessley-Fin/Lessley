from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient


class MongoRepository:
    def __init__(self, mongo_uri: str, database_name: str):
        self._client = AsyncIOMotorClient(mongo_uri)
        self._db = self._client[database_name]

    async def upsert_offer(self, collection: str, item: dict[str, Any]) -> None:
        external_id = item.get("external_id")
        source_club = item.get("source_club")

        if not external_id or not source_club:
            return

        await self._db[collection].update_one(
            {"source_club": source_club, "external_id": external_id},
            {"$set": item},
            upsert=True,
        )

    async def upsert_card(self, collection: str, item: dict[str, Any]) -> None:
        external_id = item.get("external_id")
        source_club = item.get("source_club")

        if not external_id or not source_club:
            return

        await self._db[collection].update_one(
            {"source_club": source_club, "external_id": external_id},
            {"$set": item},
            upsert=True,
        )

    async def close(self) -> None:
        self._client.close()