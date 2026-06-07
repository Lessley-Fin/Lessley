import asyncio
import json
import logging

import aio_pika
from aio_pika import DeliveryMode, Message

logger = logging.getLogger(__name__)

_EXCHANGE_NAME = "lessley_events"
_MAX_RETRIES = 3


class RabbitMQBase:
    """
    Shared channel lifecycle and publish-with-retry for all RabbitMQ publishers.
    Both user and tag publishers hold the same AbstractRobustConnection injected via DI.
    """

    def __init__(self, connection: aio_pika.abc.AbstractRobustConnection) -> None:
        self._connection = connection
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    @staticmethod
    async def connect(url: str) -> aio_pika.abc.AbstractRobustConnection:
        connection = await aio_pika.connect_robust(url)
        logger.info("RabbitMQ connection established")
        return connection

    async def close(self) -> None:
        await self._connection.close()

    async def _ensure_channel(self) -> None:
        if self._exchange is None:
            self._channel = await self._connection.channel()
            self._exchange = await self._channel.declare_exchange(
                _EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
            )

    async def _publish_with_retry(self, routing_key: str, payload: dict) -> None:
        delay = 1.0
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                await self._ensure_channel()
                await self._exchange.publish(
                    Message(
                        body=json.dumps(payload).encode(),
                        content_type="application/json",
                        delivery_mode=DeliveryMode.PERSISTENT,
                    ),
                    routing_key=routing_key,
                )
                return
            except Exception as exc:
                if attempt == _MAX_RETRIES:
                    raise
                logger.warning(
                    "Publish attempt %d/%d failed, retrying in %.1fs: %s",
                    attempt,
                    _MAX_RETRIES,
                    delay,
                    exc,
                    extra={"extra_data": {"routing_key": routing_key}},
                )
                await asyncio.sleep(delay)
                self._channel = None
                self._exchange = None
                delay *= 2
