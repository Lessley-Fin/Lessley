"""
RabbitMQ publisher for outbound events from Lessley.Personalization.

Publishes to the shared "lessley_events" TOPIC exchange used by all Lessley services.
The .NET Gateway listens on routing keys "Personalize.user_tag_assigned" and
"Personalize.send_notification".
"""

import json
import logging

import aio_pika
from aio_pika import DeliveryMode, Message

logger = logging.getLogger(__name__)

_EXCHANGE_NAME = "lessley_events"


class RabbitMQPublisher:
    def __init__(self, connection: aio_pika.abc.AbstractRobustConnection) -> None:
        self._connection = connection
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    async def create(cls, url: str) -> "RabbitMQPublisher":
        """Create and initialise a publisher connected to *url*."""
        connection = await aio_pika.connect_robust(url)
        publisher = cls(connection)
        await publisher._setup()
        logger.info("RabbitMQPublisher connected", extra={"extra_data": {"exchange": _EXCHANGE_NAME}})
        return publisher

    async def _setup(self) -> None:
        self._channel = await self._connection.channel()
        # Declare idempotently — matches the existing exchange topology in the Python consumers
        self._exchange = await self._channel.declare_exchange(
            _EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def publish_user_tag_assigned(self, user_id: str, tag: str) -> None:
        """
        Notify the Gateway that *user_id* has been assigned *tag*.
        The Gateway will persist the tag and join any active connections to the SignalR group.
        """
        await self._publish(
            routing_key="Personalize.user_tag_assigned",
            payload={"userId": user_id, "tag": tag},
        )
        logger.info(
            "Published UserTagAssignedEvent",
            extra={"extra_data": {"user_id": user_id, "tag": tag}},
        )

    async def publish_send_notification(self, group_tag: str, message: str) -> None:
        """
        Ask the Gateway to broadcast *message* to all SignalR clients in *group_tag*.
        """
        await self._publish(
            routing_key="Personalize.send_notification",
            payload={"groupTag": group_tag, "message": message},
        )
        logger.info(
            "Published SendNotificationCommand",
            extra={"extra_data": {"group_tag": group_tag}},
        )

    async def close(self) -> None:
        await self._connection.close()

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _publish(self, routing_key: str, payload: dict) -> None:
        if self._exchange is None:
            raise RuntimeError("RabbitMQPublisher is not initialised — call create() first")
        await self._exchange.publish(
            Message(
                body=json.dumps(payload).encode(),
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
            ),
            routing_key=routing_key,
        )
