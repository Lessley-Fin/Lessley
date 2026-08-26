"""
Tasks 1-4 (tasks.txt): plain-Python spending insight computations on InsightsService,
and task 5: sorting transactions before building missed-savings insights.
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.transaction import AmountDetail, Transaction, TransactionAmount, TransactionDates
from routers.responses import AppliedSavingsSchema, MissedSavingsSchema, SavingsAnswerSchema
from services.insights_service import InsightsService


def _tx(
    tx_date: date | None = None,
    charged: float | None = None,
    original: float | None = None,
    account_id: str | None = None,
    account_number: str | None = None,
    charged_currency: str = "ILS",
    original_currency: str = "ILS",
    status: str = "BOOKED",
) -> Transaction:
    return Transaction(
        status=status,
        date=TransactionDates(transactionDate=tx_date) if tx_date else None,
        amount=TransactionAmount(
            chargedAmount=(
                AmountDetail(amount=charged, currency=charged_currency) if charged is not None else None
            ),
            originalAmount=(
                AmountDetail(amount=original, currency=original_currency) if original is not None else None
            ),
        ),
        accountId=account_id,
        accountNumber=account_number,
    )


def _service(**overrides) -> InsightsService:
    """An InsightsService with every collaborator mocked — the calculations need none of them."""
    defaults = dict(
        open_finance_service=MagicMock(),
        files_service=MagicMock(),
        publisher_service=MagicMock(),
        user_repository=MagicMock(),
        reference_data_repository=MagicMock(),
        mcc_service=MagicMock(),
    )
    defaults.update(overrides)
    return InsightsService(**defaults)


# ── Task 1: spending by day of week ────────────────────────────────────────────

def test_spending_by_day_of_week_groups_by_weekday_and_fills_all_days():
    service = _service()
    transactions = [
        _tx(tx_date=date(2024, 1, 7), charged=-1000),  # Sunday
        _tx(tx_date=date(2024, 1, 8), charged=-700),  # Monday
        _tx(tx_date=date(2024, 1, 14), charged=-250),  # next Sunday
    ]

    result = service.spending_by_day_of_week(transactions)

    by_day = {row["day"]: row["total_amount"] for row in result}
    assert set(by_day.keys()) == {
        "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
    }
    assert by_day["Sunday"] == 1250
    assert by_day["Monday"] == 700
    assert by_day["Tuesday"] == 0


def test_spending_by_day_of_week_skips_transactions_without_a_date():
    service = _service()
    transactions = [_tx(tx_date=None, charged=100)]

    result = service.spending_by_day_of_week(transactions)

    assert all(row["total_amount"] == 0 for row in result)


# ── Task 2: spending difference between two periods ────────────────────────────

def test_spending_difference_splits_by_cutoff_date():
    service = _service()
    today = date.today()
    transactions = [
        _tx(tx_date=today, charged=-100),  # current period
        _tx(tx_date=today - timedelta(days=5), charged=-40),  # previous period
    ]

    result = service.spending_difference_between_two_periods(transactions, days=1)

    assert result["current_period_total"] == 100
    assert result["previous_period_total"] == 40
    assert result["difference"] == 60


def test_the_period_comparison_reads_the_bank_figure_not_what_was_bought():
    """
    The overview compares what the bank billed, so it lines up with the headline total.

    A coupon counts zero on both sides. Counting it at full price moved the bars for a period
    the user paid nothing extra in, and left the overview disagreeing with the total above it.
    """
    service = _service()
    recent = date.today() - timedelta(days=5)
    transactions = [
        _tx(tx_date=recent, charged=-100),
        _tx(tx_date=recent, charged=None, original=-176.15),
    ]

    comparison = service.spending_difference_between_two_periods(transactions, days=30)

    assert comparison["current_period_total"] == 100


# ── Task 1: what the user did not have to pay ─────────────────────────────
#
# Which gaps count as a discount is settled one row at a time in test_transaction_amounts.py.
# What matters here is that the total and the breakdown beside it describe the same money.


def test_spending_saved_splits_the_total_by_the_discount_that_did_it():
    service = _service()
    transactions = [
        _tx(charged=None, original=-176.15),   # coupon: the whole price
        _tx(charged=-47.81, original=-49.80),  # statement: the gap
        _tx(charged=-86, original=-86),        # regular: nothing
    ]

    saved = service.spending_saved(transactions)
    rows = {row["source"]: row["amount"] for row in saved["breakdown"]}

    assert saved["total_amount"] == pytest.approx(178.14)
    assert rows["coupon"] == 176.15
    assert rows["statement"] == pytest.approx(1.99)
    assert sum(rows.values()) == pytest.approx(saved["total_amount"])


def test_spending_saved_leaves_refunds_out():
    """
    A returned purchase and a cashback arrive identically, so neither is counted as a saving.

    Money coming back reduces what was spent instead — see the spending total below.
    """
    service = _service()

    assert service.spending_saved([_tx(charged=29.21, original=-29.21)])["total_amount"] == 0


# ── Tasks 2, 3 and 8: what the bank statement shows, and what it is made of ─────


def test_the_headline_total_is_what_the_bank_billed():
    """
    100 billed and 176.15 on a coupon → 100. No money left the account for the coupon.

    Deliberately smaller than the per-category and per-account breakdowns, which count the
    coupon at its full worth: they answer what the user buys, this answers what it cost them.
    """
    service = _service()
    transactions = [
        _tx(charged=-100, account_id="bank"),
        _tx(charged=None, original=-176.15, account_id="coupon"),
    ]

    total = service.spending_total(transactions)

    assert total["total_amount"] == 100
    assert total["purchase_count"] == 2


def test_the_spend_breakdown_adds_up_to_the_headline():
    service = _service()
    transactions = [
        _tx(charged=-100),
        _tx(charged=-47.81, original=-49.80),
        _tx(charged=20.0),
    ]

    total = service.spending_total(transactions)
    rows = {row["source"]: row["amount"] for row in total["breakdown"]}

    assert rows["regular"] + rows["statement"] - rows["refund"] == pytest.approx(total["total_amount"])


def test_the_mix_contributions_add_up_to_the_headline():
    """
    `contributes` is the column that reconciles; `amount` is the one the screen prints.

    A client that had to know which rows to negate would be doing arithmetic of its own, which
    is how the screen came to disagree with this service before.
    """
    service = _service()
    transactions = [
        _tx(charged=-100),
        _tx(charged=None, original=-176.15),
        _tx(charged=20.0),
    ]

    total = service.spending_total(transactions)

    assert sum(row["contributes"] for row in total["mix"]) == pytest.approx(total["total_amount"])


def test_the_mix_shows_the_coupon_without_counting_it():
    service = _service()
    transactions = [_tx(charged=-100), _tx(charged=None, original=-176.15)]

    coupon = next(row for row in service.spending_total(transactions)["mix"] if row["kind"] == "coupon")

    assert (coupon["amount"], coupon["contributes"]) == (176.15, 0.0)


_EMPTY_ANSWER = SavingsAnswerSchema(
    missed=MissedSavingsSchema(total_amount=0.0, purchase_count=0, bands=[]),
    applied=AppliedSavingsSchema(total_amount=0.0, purchase_count=0, merchants=[]),
)


# ── Task 4: spending saved by account ───────────────────────────────────────────

def test_spending_saved_by_account_groups_and_sorts_descending():
    service = _service()
    transactions = [
        _tx(charged=-90, original=-100, account_id="acc1", account_number="****1"),
        _tx(charged=-160, original=-200, account_id="acc1", account_number="****1"),
        _tx(charged=-70, original=-100, account_id="acc2", account_number="****2"),
    ]

    result = service.spending_saved_by_account(transactions)

    assert result[0] == {"accountId": "acc1", "accountNumber": "****1", "total_saved": 50}
    assert result[1] == {"accountId": "acc2", "accountNumber": "****2", "total_saved": 30}


def test_spending_saved_by_account_drops_the_same_gaps_as_the_total():
    service = _service()
    transactions = [
        _tx(charged=-90, original=-100, account_id="acc1", account_number="****1"),
        _tx(charged=-932, original=-3728, account_id="acc1", account_number="****1"),
    ]

    result = service.spending_saved_by_account(transactions)

    assert result == [{"accountId": "acc1", "accountNumber": "****1", "total_saved": 10}]


# ── savings opportunities: what the orchestration hands the matching ──────────

def _savings_service(open_finance) -> InsightsService:
    service = _service(
        open_finance_service=open_finance,
        publisher_service=MagicMock(),
        user_repository=MagicMock(get_user_clubs=AsyncMock(return_value=["c1"])),
    )
    # The matching itself is covered by its own tests; here we only care that the orchestration
    # hands it correctly-sorted transactions and the user's own clubs.
    service.savings_opportunities = MagicMock(return_value=_EMPTY_ANSWER)
    return service


async def test_savings_opportunities_sorts_real_transactions_before_matching():
    fetched = [_tx(charged=1)]
    sorted_transactions = [_tx(charged=2)]

    open_finance = MagicMock()
    open_finance.get_user_transactions_async = AsyncMock(return_value=fetched)
    open_finance.sort_transactions = MagicMock(return_value=sorted_transactions)

    service = _savings_service(open_finance)

    await service.calculate_savings_opportunities_async("user@test.com", time_filter=True, days=7)

    open_finance.sort_transactions.assert_called_once_with(fetched)
    service.savings_opportunities.assert_called_once_with(sorted_transactions, user_club_ids=["c1"])


async def test_savings_opportunities_does_not_sort_mock_data():
    open_finance = MagicMock()
    open_finance.sort_transactions = MagicMock()
    service = _savings_service(open_finance)
    service.files_service.read_json = MagicMock(return_value=[{"fake": "tx"}])

    await service.calculate_savings_opportunities_async(
        "user@test.com", time_filter=True, days=7, use_mock=True
    )

    open_finance.sort_transactions.assert_not_called()


async def test_savings_opportunities_never_reaches_for_the_accounts_feed():
    """
    The club card gives itself away in the transaction, so nothing here needs a second call.

    Pinned because that call used to exist: it fetched an account `product` string to spot a
    נטען card, against wording nobody had confirmed, and it could fail and take the whole
    answer with it.
    """
    open_finance = MagicMock()
    open_finance.get_user_transactions_async = AsyncMock(return_value=[_tx(charged=1)])
    open_finance.sort_transactions = MagicMock(return_value=[_tx(charged=1)])
    open_finance.get_user_accounts_async = AsyncMock()

    service = _savings_service(open_finance)

    await service.calculate_savings_opportunities_async("user@test.com", time_filter=True, days=7)

    open_finance.get_user_accounts_async.assert_not_called()
