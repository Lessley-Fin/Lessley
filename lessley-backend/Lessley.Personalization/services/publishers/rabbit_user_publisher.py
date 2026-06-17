import logging
from datetime import datetime, timezone
from typing import List

import aio_pika

from .rabbit_base import RabbitMQBase

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RabbitMQUserPublisher(RabbitMQBase):
    """Publishes user-scoped events: tag assignments, direct notifications, and calc results."""

    def __init__(self, connection: aio_pika.abc.AbstractRobustConnection) -> None:
        super().__init__(connection)

    async def publish_user_tag_assigned(self, user_id: str, tags: List[str]) -> None:
        """
        Notify the Gateway that user_id has been assigned the given tags.
        Gateway persists the tags and joins active SignalR connections to each tag group.
        """
        await self._publish_with_retry(
            routing_key="Personalize.user_tag_assigned",
            payload={"userId": user_id, "tags": tags},
        )
        logger.info(
            "Published UserTagAssignedEvent",
            extra={"extra_data": {"user_id": user_id, "tags": tags}},
        )

    async def publish_user_notification(self, user_id: str, message: str, deal_id: str) -> None:
        """Ask the Gateway to push message directly to user_id's SignalR connection(s)."""
        await self._publish_with_retry(
            routing_key="Personalize.deal_user_notification",
            payload={"userId": user_id, "message": message, "dealId": deal_id},
        )
        logger.info(
            "Published DealUserNotification",
            extra={"extra_data": {"user_id": user_id, "deal_id": deal_id}},
        )

    async def publish_user_categories_calculated(self, user_id: str) -> None:
        """Signal that category calculation finished — Gateway creates a notification row."""
        await self._publish_with_retry(
            routing_key="Personalize.user_categories_calculated",
            payload={"userId": user_id, "calculatedAt": _now()},
        )
        logger.info(
            "Published UserCategoriesCalculatedEvent",
            extra={"extra_data": {"user_id": user_id}},
        )
