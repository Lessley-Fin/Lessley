"""
PublisherService — verify RabbitMQ wiring and delegation.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.publisher_service import PublisherService


async def test_publish_before_initialize_raises():
    svc = PublisherService()
    with pytest.raises(RuntimeError):
        await svc.publish_user_tag_assigned("user@test.com", ["GROCERIES"])


async def test_initialize_is_idempotent():
    svc = PublisherService()
    with patch("services.publisher_service.RabbitMQBase.connect", new=AsyncMock(return_value=MagicMock())), \
         patch("services.publisher_service.RabbitMQUserPublisher", return_value=MagicMock()):
        await svc.initialize()
        first = svc._user_publisher
        await svc.initialize()
        assert svc._user_publisher is first


async def test_publish_delegates_to_underlying_publisher():
    svc = PublisherService()
    svc._initialized = True
    svc._user_publisher = AsyncMock()

    await svc.publish_user_tag_assigned("user@test.com", ["GROCERIES", "RESTAURANT"])
    svc._user_publisher.publish_user_tag_assigned.assert_awaited_once_with("user@test.com", ["GROCERIES", "RESTAURANT"])


def test_only_the_tag_assignment_is_published():
    """
    The deal-broadcast and recommendation-result publishers were removed along with the
    consumers waiting on them. Anything new added here means another service is being told
    something, which is worth noticing in review.
    """
    published = {name for name in dir(PublisherService) if name.startswith("publish")}
    assert published == {"publish_user_tag_assigned"}
