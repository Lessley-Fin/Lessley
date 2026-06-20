"""
PublisherService — verify RabbitMQ wiring and delegation.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.publisher_service import PublisherService


async def test_publish_before_initialize_raises():
    svc = PublisherService()
    with pytest.raises(RuntimeError):
        await svc.publish_user_tag_assigned("user@test.com", ["5411"])


async def test_initialize_is_idempotent():
    svc = PublisherService()
    with patch("services.publisher_service.RabbitMQBase.connect", new=AsyncMock(return_value=MagicMock())), \
         patch("services.publisher_service.RabbitMQUserPublisher", return_value=MagicMock()), \
         patch("services.publisher_service.RabbitMQTagPublisher", return_value=MagicMock()):
        await svc.initialize()
        first = svc._user_publisher
        await svc.initialize()
        assert svc._user_publisher is first


async def test_publish_delegates_to_underlying_publisher():
    svc = PublisherService()
    svc._initialized = True
    svc._user_publisher = AsyncMock()
    svc._tag_publisher = AsyncMock()

    await svc.publish_user_tag_assigned("user@test.com", ["5411", "5812"])
    svc._user_publisher.publish_user_tag_assigned.assert_awaited_once_with("user@test.com", ["5411", "5812"])

    await svc.publish_group_notification("5411", "Deal!", "deal-1")
    svc._tag_publisher.publish_group_notification.assert_awaited_once_with("5411", "Deal!", "deal-1")
