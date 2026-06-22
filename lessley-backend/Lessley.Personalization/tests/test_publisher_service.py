"""
Publisher injection — HTTP mode must wire both roles to an HttpPublisher and actually
delegate publish calls (this is what reaches the Gateway over HTTP).
"""

from unittest.mock import AsyncMock

import pytest

import services.publisher_service as ps_module
from services.publisher_service import PublisherService
from services.publishers.http_publisher import HttpPublisher


@pytest.fixture
def http_settings(monkeypatch):
    monkeypatch.setattr(ps_module.settings, "RabbitMQ_Enabled", False, raising=False)
    monkeypatch.setattr(ps_module.settings, "Publisher_Mode", "http", raising=False)
    monkeypatch.setattr(ps_module.settings, "Gateway_BaseUrl", "http://localhost:5001", raising=False)
    monkeypatch.setattr(ps_module.settings, "Gateway_ServiceToken", "test-token", raising=False)


async def test_initialize_http_wires_both_roles(http_settings):
    svc = PublisherService()
    await svc.initialize()

    assert isinstance(svc._user_publisher, HttpPublisher)
    assert svc._tag_publisher is svc._user_publisher  # one instance satisfies both roles


async def test_initialize_is_idempotent(http_settings):
    svc = PublisherService()
    await svc.initialize()
    first = svc._user_publisher
    await svc.initialize()
    assert svc._user_publisher is first


async def test_publish_delegates_to_underlying_publisher(http_settings):
    svc = PublisherService()
    await svc.initialize()

    # Swap the concrete HttpPublisher for a spy so we don't make a real network call.
    svc._user_publisher = AsyncMock()
    svc._tag_publisher = svc._user_publisher

    await svc.publish_user_tag_assigned("user@test.com", ["5411", "5812"])
    svc._user_publisher.publish_user_tag_assigned.assert_awaited_once_with("user@test.com", ["5411", "5812"])

    await svc.publish_group_notification("5411", "Deal!", "deal-1")
    svc._tag_publisher.publish_group_notification.assert_awaited_once_with("5411", "Deal!", "deal-1")


async def test_publish_before_initialize_raises():
    svc = PublisherService()
    with pytest.raises(RuntimeError):
        await svc.publish_user_tag_assigned("user@test.com", ["5411"])
