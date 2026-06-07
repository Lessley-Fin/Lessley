import logging
from typing import List

logger = logging.getLogger(__name__)


class PublisherService:
    """
    Protocol-agnostic publisher selected at startup via Publisher_Mode env var.

    Holds one user_publisher (user-scoped events) and one tag_publisher (group broadcasts).
    For RabbitMQ mode these are separate classes sharing the same connection.
    For HTTP mode the same HttpPublisher instance satisfies both roles.

    Inject this service (via DIContainer) into InsightsService and RecommendationService
    instead of accessing publishers directly.
    """

    def __init__(self, user_publisher, tag_publisher) -> None:
        self._user_publisher = user_publisher
        self._tag_publisher = tag_publisher

    async def publish_user_tag_assigned(self, user_id: str, tags: List[str]) -> None:
        await self._user_publisher.publish_user_tag_assigned(user_id, tags)

    async def publish_user_notification(self, user_id: str, message: str, deal_id: str) -> None:
        await self._user_publisher.publish_user_notification(user_id, message, deal_id)

    async def publish_group_notification(self, group_tag: str, message: str, deal_id: str) -> None:
        await self._tag_publisher.publish_group_notification(group_tag, message, deal_id)

    async def close(self) -> None:
        await self._user_publisher.close()
        if self._tag_publisher is not self._user_publisher:
            await self._tag_publisher.close()
