import logging
from typing import List

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


class HttpPublisher:
    """
    HTTP fallback publisher.
    Calls Gateway REST endpoints when Publisher_Mode=http.
    Uses Gateway_ServiceToken (admin JWT) for all requests.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=settings.Gateway_BaseUrl or "",
                headers={"Authorization": f"Bearer {settings.Gateway_ServiceToken or ''}"},
                timeout=10.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def publish_user_tag_assigned(self, user_id: str, tags: List[str]) -> None:
        response = await self._get_client().put(f"/api/user/{user_id}/tags", json=tags)
        response.raise_for_status()
        logger.info(
            "HTTP: user tags updated",
            extra={"extra_data": {"user_id": user_id, "tags": tags}},
        )

    async def publish_user_notification(self, user_id: str, message: str, deal_id: str) -> None:
        response = await self._get_client().post(
            f"/api/notification/user/{user_id}",
            json={"message": message, "dealId": deal_id},
        )
        response.raise_for_status()
        logger.info(
            "HTTP: user notification sent",
            extra={"extra_data": {"user_id": user_id, "deal_id": deal_id}},
        )

    async def publish_group_notification(self, group_tag: str, message: str, deal_id: str) -> None:
        response = await self._get_client().post(
            f"/api/notification/group/{group_tag}",
            json={"message": message, "dealId": deal_id},
        )
        response.raise_for_status()
        logger.info(
            "HTTP: group notification sent",
            extra={"extra_data": {"group_tag": group_tag, "deal_id": deal_id}},
        )

    async def publish_deal_notification(self, deal_id: str, message: str, categories: List[str]) -> None:
        # HTTP fallback not implemented for consolidated deal notification; log warning.
        logger.warning(
            "HTTP: publish_deal_notification not supported in HTTP mode — use RabbitMQ mode",
            extra={"extra_data": {"deal_id": deal_id}},
        )

    async def publish_user_categories_calculated(self, user_id: str) -> None:
        logger.warning("HTTP: publish_user_categories_calculated not supported in HTTP mode")

    async def publish_top_accounts_calculated(self, user_id: str) -> None:
        logger.warning("HTTP: publish_top_accounts_calculated not supported in HTTP mode")

    async def publish_top_stores_calculated(self, user_id: str) -> None:
        logger.warning("HTTP: publish_top_stores_calculated not supported in HTTP mode")

    async def publish_missed_savings_calculated(self, user_id: str) -> None:
        logger.warning("HTTP: publish_missed_savings_calculated not supported in HTTP mode")

    async def publish_matching_clubs_calculated(self, user_id: str) -> None:
        logger.warning("HTTP: publish_matching_clubs_calculated not supported in HTTP mode")
