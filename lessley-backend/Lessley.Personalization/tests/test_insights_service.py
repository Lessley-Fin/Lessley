"""
Calc-categories stops if the user is unknown, trims by match level, and returns the
category-name tags — without writing anything anywhere.

The absence of a publish is the point of these tests, not an omission. This calculation is
shared by the client-facing GET and the Gateway's command handler; only the handler may turn
the result into a write. Publishing from in here made reading your own insights silently
update your stored profile, so a client could act on categories the database did not have yet.
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
    # These tests cover orchestration (stop on unknown user, trim, return), not the category
    # calculation itself — that has its own tests and its own golden-output check.
    service.top_spending_categories = MagicMock(return_value=categories)
    return service


def _publisher():
    publisher = MagicMock()
    publisher.publish_user_tag_assigned = AsyncMock()
    return publisher


# ── unknown user → stop ───────────────────────────────────────────────────────

async def test_calc_categories_unknown_user_raises_and_stops():
    user_repo = MagicMock()
    user_repo.get_user = AsyncMock(side_effect=HTTPException(status_code=404, detail="not registered"))

    service = _service(user_repo, _publisher(), categories=[{"category": "X", "mcc_codes": ["GROCERIES"]}])

    with pytest.raises(HTTPException) as exc:
        await service.calculate_user_categories_async("ghost@test.com", time_filter=True, use_mock=True)

    assert exc.value.status_code == 404
    service.top_spending_categories.assert_not_called()


# ── the calculation is free of side effects ───────────────────────────────────

async def test_calc_categories_never_publishes():
    user_repo = MagicMock()
    user_repo.get_user = AsyncMock(return_value={"MatchingScore": None})

    publisher = _publisher()
    service = _service(user_repo, publisher, [{"category": "GROCERIES", "mcc_codes": ["GROCERIES"]}])

    await service.calculate_user_categories_async("user@test.com", time_filter=True, use_mock=True)

    # A read must stay a read: the command handler owns the write, and it is the only caller
    # allowed to turn these categories into a change on the user's profile.
    publisher.publish_user_tag_assigned.assert_not_awaited()


# ── the tags derived from the result ──────────────────────────────────────────

async def test_calc_categories_returns_deduplicated_category_names():
    user_repo = MagicMock()
    user_repo.get_user = AsyncMock(return_value={"MatchingScore": None})

    categories = [
        {"category": "GROCERIES", "total_count": 5, "total_amount": 100, "mcc_codes": ["GROCERIES"]},
        {"category": "RESTAURANTS", "total_count": 3, "total_amount": 50, "mcc_codes": ["RESTAURANT", "GROCERIES"]},
    ]
    service = _service(user_repo, _publisher(), categories)

    result = await service.calculate_user_categories_async("user@test.com", time_filter=True, use_mock=True)

    assert InsightsService.extract_mcc_tags(result) == ["GROCERIES", "RESTAURANT"]


async def test_calc_categories_trims_by_match_level():
    user_repo = MagicMock()
    user_repo.get_user = AsyncMock(return_value={"MatchingScore": 0.75})

    categories = [
        {"category": "C1", "mcc_codes": ["CAT_1"]},
        {"category": "C2", "mcc_codes": ["CAT_2"]},
        {"category": "C3", "mcc_codes": ["CAT_3"]},
        {"category": "C4", "mcc_codes": ["CAT_4"]},
    ]
    service = _service(user_repo, _publisher(), categories)

    result = await service.calculate_user_categories_async("user@test.com", time_filter=True, use_mock=True)

    assert InsightsService.extract_mcc_tags(result) == ["CAT_1"]
