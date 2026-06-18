import logging
from typing import List

import aio_pika

from .rabbit_base import RabbitMQBase

logger = logging.getLogger(__name__)


class RabbitMQUserPublisher(RabbitMQBase):
    """Publishes user-scoped events: tag assignments and direct user notifications."""

    def __init__(self, connection: aio_pika.abc.AbstractRobustConnection) -> None:
        super().__init__(connection)

    async def publish_user_tag_assigned(self, user_id: str, tags: List[str]) -> None:
        """
        Notify the Gateway that user_id has been assigned the given tags.
        Gateway persists the tags and joins active SignalR connections to each tag group.
        Routing key matches: gateway.user_tag_assigned endpoint in ServiceCollectionExtensions.
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
        """
        Ask the Gateway to push message directly to user_id's SignalR connection(s).
        Routing key matches: gateway.deal_user_notification endpoint.
        """
        await self._publish_with_retry(
            routing_key="Personalize.deal_user_notification",
            payload={"userId": user_id, "message": message, "dealId": deal_id},
        )
        logger.info(
            "Published DealUserNotification",
            extra={"extra_data": {"user_id": user_id, "deal_id": deal_id}},
        )
