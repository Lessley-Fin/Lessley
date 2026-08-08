"""
Calc-categories stops if the user is unknown, and sends the recalculated
categories (category name strings) to the Gateway.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from services.insights_service import InsightsService


def _service(user_repo, publisher, categories):
    files = MagicMock()
    files.read_json = MagicMock(return_value=[{"fake": "tx"}])
    open_finance = MagicMock()
    open_finance.get_user_transactions_async = AsyncMock(return_value=[{"fake": "tx"}])
    service = InsightsService(
        open_finance_service=open_finance,
        files_service=files,
        publisher_service=publisher,
        user_repository=user_repo,
        reference_data_repository=MagicMock(),
        mcc_service=MagicMock(),
    )
    # These tests cover orchestration (stop on unknown user, trim, publish), not the
    # category calculation itself — that has its own tests and its own golden-output check.
    service.top_spending_categories = MagicMock(return_value=categories)
    return service


# ── unknown user → stop ───────────────────────────────────────────────────────

async def test_calc_categories_unknown_user_raises_and_stops():
    user_repo = MagicMock()
    user_repo.get_user = AsyncMock(side_effect=HTTPException(status_code=404, detail="not registered"))

    publisher = MagicMock()
    publisher.publish_user_tag_assigned = AsyncMock()

    service = _service(user_repo, publisher, categories=[{"category": "X", "mcc_codes": ["GROCERIES"]}])

    with pytest.raises(HTTPException) as exc:
        await service.calculate_user_categories_async("ghost@test.com", time_filter=True, use_mock=True)

    assert exc.value.status_code == 404
    publisher.publish_user_tag_assigned.assert_not_awaited()
    service.top_spending_categories.assert_not_called()


# ── publish category name tags to the Gateway ─────────────────────────────────

async def test_calc_categories_publishes_category_names_to_gateway():
    user_repo = MagicMock()
    user_repo.get_user = AsyncMock(return_value={"MatchingScore": None})

    publisher = MagicMock()
    publisher.publish_user_tag_assigned = AsyncMock()

    categories = [
        {"category": "GROCERIES", "total_count": 5, "total_amount": 100, "mcc_codes": ["GROCERIES"]},
        {"category": "RESTAURANTS", "total_count": 3, "total_amount": 50, "mcc_codes": ["RESTAURANT", "GROCERIES"]},
    ]
    service = _service(user_repo, publisher, categories)

    await service.calculate_user_categories_async("user@test.com", time_filter=True, use_mock=True)

    publisher.publish_user_tag_assigned.assert_awaited_once()
    args = publisher.publish_user_tag_assigned.await_args.args
    assert args[0] == "user@test.com"
    assert args[1] == ["GROCERIES", "RESTAURANT"]


async def test_calc_categories_trims_by_match_level_before_publishing():
    user_repo = MagicMock()
    user_repo.get_user = AsyncMock(return_value={"MatchingScore": 0.75})

    publisher = MagicMock()
    publisher.publish_user_tag_assigned = AsyncMock()

    categories = [
        {"category": "C1", "mcc_codes": ["CAT_1"]},
        {"category": "C2", "mcc_codes": ["CAT_2"]},
        {"category": "C3", "mcc_codes": ["CAT_3"]},
        {"category": "C4", "mcc_codes": ["CAT_4"]},
    ]
    service = _service(user_repo, publisher, categories)

    await service.calculate_user_categories_async("user@test.com", time_filter=True, use_mock=True)

    args = publisher.publish_user_tag_assigned.await_args.args
    assert args[1] == ["CAT_1"]
