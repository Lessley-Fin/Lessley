import logging
from typing import List

from config.settings import settings

from services.publishers.rabbit_base import RabbitMQBase
from services.publishers.rabbit_user_publisher import RabbitMQUserPublisher

logger = logging.getLogger(__name__)


class PublisherService:
    """
    Everything this service tells the Gateway about a user.

    Exactly one message goes out now: the tags derived from a category calculation, which the
    Gateway persists and turns into SignalR group membership. The deal-broadcast and
    recommendation-result publishers that used to live here were removed along with the
    consumers waiting on them — the answers they carried are returned directly over HTTP.
    """

    def __init__(self) -> None:
        self._user_publisher = None
        self._initialized = False

    async def initialize(self) -> None:
        """Wire up RabbitMQ publishers. Idempotent; safe to call once at startup."""
        if self._initialized:
            return

        connection = await RabbitMQBase.connect(settings.ConnectionStrings_Rabbit)
        self._user_publisher = RabbitMQUserPublisher(connection)
        logger.info("Publisher: RabbitMQ mode enabled")
        self._initialized = True

    def _ensure_initialized(self) -> None:
        if not self._initialized or self._user_publisher is None:
            raise RuntimeError("PublisherService.initialize() must be called before publishing")

    async def publish_user_tag_assigned(self, user_id: str, tags: List[str]) -> None:
        self._ensure_initialized()
        await self._user_publisher.publish_user_tag_assigned(user_id, tags)

    async def close(self) -> None:
        if self._user_publisher is not None:
            await self._user_publisher.close()
