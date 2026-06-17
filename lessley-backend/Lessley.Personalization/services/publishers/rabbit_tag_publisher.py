import logging
from datetime import datetime, timezone
from typing import List

import aio_pika

from .rabbit_base import RabbitMQBase

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RabbitMQTagPublisher(RabbitMQBase):
    """Publishes group/deal broadcast events and calc-result notifications."""

    def __init__(self, connection: aio_pika.abc.AbstractRobustConnection) -> None:
        super().__init__(connection)

    async def publish_group_notification(self, group_tag: str, message: str, deal_id: str) -> None:
        """Legacy single-group notification — kept for backward compatibility."""
        await self._publish_with_retry(
            routing_key="Personalize.deal_group_notification",
            payload={"groupTag": group_tag, "message": message, "dealId": deal_id},
        )
        logger.info(
            "Published DealGroupNotification",
            extra={"extra_data": {"group_tag": group_tag, "deal_id": deal_id}},
        )

    async def publish_deal_notification(self, deal_id: str, message: str, categories: List[str]) -> None:
        """
        Consolidated deal broadcast: one message per deal with all matching categories.
        Gateway deduplicates recipients so each user receives exactly one notification.
        """
        await self._publish_with_retry(
            routing_key="Personalize.deal_notification",
            payload={"dealId": deal_id, "message": message, "categories": categories},
        )
        logger.info(
            "Published DealNotification",
            extra={"extra_data": {"deal_id": deal_id, "categories": categories}},
        )

    async def publish_top_accounts_calculated(self, user_id: str) -> None:
        await self._publish_with_retry(
            routing_key="Personalize.top_accounts_calculated",
            payload={"userId": user_id, "calculatedAt": _now()},
        )

    async def publish_top_stores_calculated(self, user_id: str) -> None:
        await self._publish_with_retry(
            routing_key="Personalize.top_stores_calculated",
            payload={"userId": user_id, "calculatedAt": _now()},
        )

    async def publish_missed_savings_calculated(self, user_id: str) -> None:
        await self._publish_with_retry(
            routing_key="Personalize.missed_savings_calculated",
            payload={"userId": user_id, "calculatedAt": _now()},
        )

    async def publish_matching_clubs_calculated(self, user_id: str) -> None:
        await self._publish_with_retry(
            routing_key="Personalize.matching_clubs_calculated",
            payload={"userId": user_id, "calculatedAt": _now()},
        )
