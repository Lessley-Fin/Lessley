import logging
from typing import List, Optional

from fastapi import HTTPException

import database.db_client as db_module

logger = logging.getLogger(__name__)

_COLLECTION = "users"


class UserRepository:
    """
    Read-only access to Gateway-managed user profiles stored in MongoDB.

    The Gateway (ASP.NET Identity) persists users in the shared 'lessley' database,
    collection 'users'. Personalization reads Tags and MatchingScore from there;
    writes always go through the Gateway via PublisherService.
    """

    def _collection(self):
        return db_module.client["lessley"][_COLLECTION]

    async def get_user(self, user_id: str) -> dict:
        """
        Fetch user document by email (NormalizedEmail — same identifier the insights
        service and OpenFinance client use as user_id).
        Raises HTTP 404 if the user is not registered in Lessley (task 14).
        """
        user = await self._collection().find_one({"NormalizedEmail": user_id.strip().upper()})
        if user is None:
            logger.warning(
                "User not found in Lessley",
                extra={"extra_data": {"user_id": user_id}},
            )
            raise HTTPException(status_code=404, detail=f"User '{user_id}' is not registered in Lessley")
        return user

    async def get_user_tags(self, user_id: str) -> List[str]:
        """Return the pre-computed category tags assigned by Personalization via the Gateway."""
        user = await self.get_user(user_id)
        return user.get("Tags") or []

    async def get_user_matching_score(self, user_id: str) -> Optional[float]:
        """Return the user's overall club-matching score."""
        user = await self.get_user(user_id)
        return user.get("MatchingScore")
