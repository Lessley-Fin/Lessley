import logging
from datetime import datetime, timezone
from typing import List

import aio_pika

from .rabbit_base import RabbitMQBase

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RabbitMQUserPublisher(RabbitMQBase):
    """Publishes user-scoped events: the tags derived from a category calculation."""

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
