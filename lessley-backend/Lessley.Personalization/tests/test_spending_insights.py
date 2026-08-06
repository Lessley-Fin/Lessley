"""
Tasks 1-4 (tasks.txt): plain-Python spending insight computations on ProcessingCoreService,
and task 5: sorting transactions before building missed-savings insights.
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

from models.transaction import AmountDetail, Transaction, TransactionAmount, TransactionDates
from services.insights_service import InsightsService
from services.mcc_service import MccService
from services.processing_core_service import ProcessingCoreService


def _tx(
    tx_date: date | None = None,
    charged: float | None = None,
    original: float | None = None,
    account_id: str | None = None,
    account_number: str | None = None,
) -> Transaction:
    return Transaction(
        date=TransactionDates(transactionDate=tx_date) if tx_date else None,
        amount=TransactionAmount(
            chargedAmount=AmountDetail(amount=charged) if charged is not None else None,
            originalAmount=AmountDetail(amount=original) if original is not None else None,
        ),
        accountId=account_id,
        accountNumber=account_number,
    )


def _processing_service() -> ProcessingCoreService:
    return ProcessingCoreService(MagicMock(spec=MccService))


# ── Task 1: spending by day of week ────────────────────────────────────────────

def test_spending_by_day_of_week_groups_by_weekday_and_fills_all_days():
    service = _processing_service()
    transactions = [
        _tx(tx_date=date(2024, 1, 7), charged=1000),  # Sunday
        _tx(tx_date=date(2024, 1, 8), charged=700),  # Monday
        _tx(tx_date=date(2024, 1, 14), charged=250),  # next Sunday
    ]

    result = service.get_spending_by_day_of_week(transactions)

    by_day = {row["day"]: row["total_amount"] for row in result}
    assert set(by_day.keys()) == {
        "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
    }
    assert by_day["Sunday"] == 1250
    assert by_day["Monday"] == 700
    assert by_day["Tuesday"] == 0


def test_spending_by_day_of_week_skips_transactions_without_a_date():
    service = _processing_service()
    transactions = [_tx(tx_date=None, charged=100)]

    result = service.get_spending_by_day_of_week(transactions)

    assert all(row["total_amount"] == 0 for row in result)


# ── Task 2: spending difference between two periods ────────────────────────────

def test_spending_difference_splits_by_cutoff_date():
    service = _processing_service()
    today = date.today()
    transactions = [
        _tx(tx_date=today, charged=100),  # current period
        _tx(tx_date=today - timedelta(days=5), charged=40),  # previous period
    ]

    result = service.get_spending_difference_between_two_periods(transactions, days=1)

    assert result["current_period_total"] == 100
    assert result["previous_period_total"] == 40
    assert result["difference"] == 60


# ── Task 3: spending saved (charged vs original amount) ────────────────────────

def test_spending_saved_null_charged_falls_back_to_original():
    service = _processing_service()
    transactions = [_tx(charged=None, original=40)]

    assert service.get_spending_saved(transactions) == 40


def test_spending_saved_equal_amounts_is_zero():
    service = _processing_service()
    transactions = [_tx(charged=50, original=50)]

    assert service.get_spending_saved(transactions) == 0


def test_spending_saved_differing_amounts_is_the_absolute_difference():
    service = _processing_service()
    transactions = [_tx(charged=100, original=90)]

    assert service.get_spending_saved(transactions) == 10


def test_spending_saved_sums_across_transactions():
    service = _processing_service()
    transactions = [_tx(charged=100, original=90), _tx(charged=None, original=40)]

    assert service.get_spending_saved(transactions) == 50


# ── Task 4: spending saved by account ───────────────────────────────────────────

def test_spending_saved_by_account_groups_and_sorts_descending():
    service = _processing_service()
    transactions = [
        _tx(charged=100, original=90, account_id="acc1", account_number="****1"),
        _tx(charged=None, original=40, account_id="acc1", account_number="****1"),
        _tx(charged=100, original=70, account_id="acc2", account_number="****2"),
    ]

    result = service.get_spending_saved_by_account(transactions)

    assert result[0] == {"accountId": "acc1", "accountNumber": "****1", "total_saved": 50}
    assert result[1] == {"accountId": "acc2", "accountNumber": "****2", "total_saved": 30}


# ── Task 5: missed-savings sorts transactions before building insights ─────────

def _insights_service(open_finance) -> InsightsService:
    return InsightsService(
        open_finance_service=open_finance,
        files_service=MagicMock(),
        processing_core_service=MagicMock(calculate_missed_savings_async=AsyncMock(return_value=[])),
        publisher_service=MagicMock(publish_missed_savings_calculated=AsyncMock()),
        user_repository=MagicMock(get_user_clubs=AsyncMock(return_value=["c1"])),
    )


async def test_missed_savings_sorts_real_transactions_before_building_insights():
    fetched = [_tx(charged=1)]
    sorted_transactions = [_tx(charged=2)]

    open_finance = MagicMock()
    open_finance.get_user_transactions_async = AsyncMock(return_value=fetched)
    open_finance.sort_transactions = MagicMock(return_value=sorted_transactions)

    service = _insights_service(open_finance)

    await service.calculate_missed_savings_async("user@test.com", time_filter=True, days=7, use_mock=False)

    open_finance.sort_transactions.assert_called_once_with(fetched)
    service.processing_core_service.calculate_missed_savings_async.assert_awaited_once_with(
        sorted_transactions, user_club_ids=["c1"]
    )


async def test_missed_savings_does_not_sort_mock_data():
    open_finance = MagicMock()
    open_finance.sort_transactions = MagicMock()
    service = _insights_service(open_finance)
    service.files_service.read_json = MagicMock(return_value=[{"fake": "tx"}])

    await service.calculate_missed_savings_async("user@test.com", time_filter=True, days=7, use_mock=True)

    open_finance.sort_transactions.assert_not_called()
