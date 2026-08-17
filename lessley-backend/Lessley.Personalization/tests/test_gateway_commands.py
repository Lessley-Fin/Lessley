"""The Gateway's category-recalculation command reaches the calculation.

This is the trigger for the whole write path: the Gateway publishes the command, this service
computes, and the derived tags travel back as a UserTagAssignedEvent for the Gateway to
persist. Personalization never writes them itself.

The contract crosses a language boundary over raw JSON, so the field names are worth pinning.
A rename or a serializer change on the .NET side would not fail here — it would fall through
to a default and calculate a window nobody asked for, which is exactly the kind of fault that
shows up months later as "the categories look off".
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

import main
from config.constants import LIMITS


@pytest.fixture
def insights(monkeypatch):
    from services.insights_service import InsightsService

    service = MagicMock()
    service.calculate_user_categories_async = AsyncMock(return_value=[])
    # The real extraction, so a change to the tag format is caught here rather than mocked over.
    service.extract_mcc_tags = InsightsService.extract_mcc_tags
    monkeypatch.setattr(main.DIContainer, "get_insights_service", lambda: service)
    return service


@pytest.fixture
def publisher(monkeypatch):
    service = MagicMock()
    service.publish_user_tag_assigned = AsyncMock()
    monkeypatch.setattr(main.DIContainer, "get_publisher_service", lambda: service)
    return service


@pytest.fixture
def users(monkeypatch):
    """The stored profile, consulted only to decide whether an empty result is worth acting on."""
    repository = MagicMock()
    repository.get_user_tags = AsyncMock(return_value=[])
    monkeypatch.setattr(main.DIContainer, "get_user_repository", lambda: repository)
    return repository


async def test_the_command_recalculates_for_the_named_user(insights, publisher, users):
    await main._handle_gateway_command(
        "Gateway.calculate_user_categories",
        {"UserId": "user@test.com", "Days": 90},
    )

    insights.calculate_user_categories_async.assert_awaited_once_with(
        "user@test.com", time_filter=True, days=90
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"userId": "user@test.com", "days": 30},
        {"user_id": "user@test.com", "Days": 30},
    ],
    ids=["camelCase", "snake_case-id"],
)
async def test_field_names_are_read_in_any_casing(insights, publisher, users, payload):
    # Whichever spelling the publisher's serializer chooses, the window must survive the trip.
    await main._handle_gateway_command("Gateway.calculate_user_categories", payload)

    insights.calculate_user_categories_async.assert_awaited_once_with(
        "user@test.com", time_filter=True, days=30
    )


async def test_a_command_without_a_window_uses_the_standard_one(insights, publisher, users):
    await main._handle_gateway_command(
        "Gateway.calculate_user_categories", {"UserId": "user@test.com"}
    )

    insights.calculate_user_categories_async.assert_awaited_once_with(
        "user@test.com", time_filter=True, days=LIMITS.DAYS
    )


# ── the handler, not the calculation, is what writes ──────────────────────────

async def test_the_derived_tags_are_published_for_the_gateway_to_persist(insights, publisher):
    insights.calculate_user_categories_async = AsyncMock(
        return_value=[
            {"category": "GROCERIES", "mcc_codes": ["GROCERIES"]},
            {"category": "RESTAURANTS", "mcc_codes": ["RESTAURANT", "GROCERIES"]},
        ]
    )

    await main._handle_gateway_command(
        "Gateway.calculate_user_categories", {"UserId": "user@test.com"}
    )

    publisher.publish_user_tag_assigned.assert_awaited_once_with(
        "user@test.com", ["GROCERIES", "RESTAURANT"]
    )


async def test_an_empty_result_does_not_clear_existing_tags(insights, publisher, users):
    # Open Finance answers [] both for a user with no bank linked and for one whose data it
    # cannot produce right now. The weekly sweep asks for every user at once, so treating that
    # as "they have no categories" would let one bad Monday unsubscribe the whole user base.
    insights.calculate_user_categories_async = AsyncMock(return_value=[])
    users.get_user_tags = AsyncMock(return_value=["GROCERIES"])

    await main._handle_gateway_command(
        "Gateway.calculate_user_categories", {"UserId": "user@test.com"}
    )

    publisher.publish_user_tag_assigned.assert_not_awaited()


async def test_an_empty_result_for_an_untagged_user_publishes_nothing(insights, publisher, users):
    # Nothing to preserve and nothing to say — the common case for an account with no bank
    # linked, which must not generate a write on every sweep.
    insights.calculate_user_categories_async = AsyncMock(return_value=[])
    users.get_user_tags = AsyncMock(return_value=[])

    await main._handle_gateway_command(
        "Gateway.calculate_user_categories", {"UserId": "user@test.com"}
    )

    publisher.publish_user_tag_assigned.assert_not_awaited()


async def test_a_failed_calculation_publishes_nothing(insights, publisher, users):
    # Better to leave yesterday's tags in place than to wipe them because Open Finance blinked.
    insights.calculate_user_categories_async = AsyncMock(side_effect=RuntimeError("upstream down"))

    with pytest.raises(RuntimeError):
        await main._handle_gateway_command(
            "Gateway.calculate_user_categories", {"UserId": "user@test.com"}
        )

    publisher.publish_user_tag_assigned.assert_not_awaited()


async def test_an_unknown_routing_key_is_ignored_rather_than_raised(insights, publisher, users):
    # Unrecognised keys are logged and dropped: the queue binds Gateway.* wholesale, so a
    # command meant for a future handler must not nack every message behind it.
    await main._handle_gateway_command("Gateway.something_else", {"UserId": "user@test.com"})

    insights.calculate_user_categories_async.assert_not_awaited()
    publisher.publish_user_tag_assigned.assert_not_awaited()
