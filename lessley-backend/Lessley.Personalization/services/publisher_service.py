import logging
from typing import List

from config.settings import settings

from services.publishers.rabbit_base import RabbitMQBase
from services.publishers.rabbit_user_publisher import RabbitMQUserPublisher
from services.publishers.rabbit_tag_publisher import RabbitMQTagPublisher

logger = logging.getLogger(__name__)


class PublisherService:
    def __init__(self) -> None:
        self._user_publisher = None
        self._tag_publisher = None
        self._initialized = False

    async def initialize(self) -> None:
        """Wire up RabbitMQ publishers. Idempotent; safe to call once at startup."""
        if self._initialized:
            return

        connection = await RabbitMQBase.connect(settings.ConnectionStrings_Rabbit)
        self._user_publisher = RabbitMQUserPublisher(connection)
        self._tag_publisher = RabbitMQTagPublisher(connection)
        logger.info("Publisher: RabbitMQ mode enabled")
        self._initialized = True

    def _ensure_initialized(self) -> None:
        if not self._initialized or self._user_publisher is None:
            raise RuntimeError("PublisherService.initialize() must be called before publishing")

    # ── User tag assignment ──────────────────────────────────────────────────────

    async def publish_user_tag_assigned(self, user_id: str, tags: List[str]) -> None:
        self._ensure_initialized()
        await self._user_publisher.publish_user_tag_assigned(user_id, tags)

    async def publish_user_notification(self, user_id: str, message: str, deal_id: str) -> None:
        self._ensure_initialized()
        await self._user_publisher.publish_user_notification(user_id, message, deal_id)

    # ── Calc result events ───────────────────────────────────────────────────────

    async def publish_user_categories_calculated(self, user_id: str) -> None:
        self._ensure_initialized()
        await self._user_publisher.publish_user_categories_calculated(user_id)

    async def publish_top_accounts_calculated(self, user_id: str) -> None:
        self._ensure_initialized()
        await self._tag_publisher.publish_top_accounts_calculated(user_id)

    async def publish_top_stores_calculated(self, user_id: str) -> None:
        self._ensure_initialized()
        await self._tag_publisher.publish_top_stores_calculated(user_id)

    async def publish_missed_savings_calculated(self, user_id: str) -> None:
        self._ensure_initialized()
        await self._tag_publisher.publish_missed_savings_calculated(user_id)

    async def publish_matching_clubs_calculated(self, user_id: str) -> None:
        self._ensure_initialized()
        await self._tag_publisher.publish_matching_clubs_calculated(user_id)

    # ── Deal broadcast ───────────────────────────────────────────────────────────

    async def publish_group_notification(self, group_tag: str, message: str, deal_id: str) -> None:
        """Legacy single-group broadcast — kept for backward compatibility."""
        self._ensure_initialized()
        await self._tag_publisher.publish_group_notification(group_tag, message, deal_id)

    async def publish_deal_notification(self, deal_id: str, message: str, categories: List[str]) -> None:
        """Consolidated deal broadcast: one message listing all categories."""
        self._ensure_initialized()
        await self._tag_publisher.publish_deal_notification(deal_id, message, categories)

    async def close(self) -> None:
        if self._user_publisher is not None:
            await self._user_publisher.close()
        if self._tag_publisher is not None and self._tag_publisher is not self._user_publisher:
            await self._tag_publisher.close()
