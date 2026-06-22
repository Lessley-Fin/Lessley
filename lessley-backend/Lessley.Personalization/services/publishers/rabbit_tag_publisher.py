import logging

import aio_pika

from .rabbit_base import RabbitMQBase

logger = logging.getLogger(__name__)


class RabbitMQTagPublisher(RabbitMQBase):
    """Publishes tag/group broadcast events."""

    def __init__(self, connection: aio_pika.abc.AbstractRobustConnection) -> None:
        super().__init__(connection)

    async def publish_group_notification(self, group_tag: str, message: str, deal_id: str) -> None:
        """
        Ask the Gateway to broadcast message to all SignalR clients in group_tag.
        Routing key matches: gateway.deal_group_notification endpoint in ServiceCollectionExtensions.
        """
        await self._publish_with_retry(
            routing_key="Personalize.deal_group_notification",
            payload={"groupTag": group_tag, "message": message, "dealId": deal_id},
        )
        logger.info(
            "Published DealGroupNotification",
            extra={"extra_data": {"group_tag": group_tag, "deal_id": deal_id}},
        )
