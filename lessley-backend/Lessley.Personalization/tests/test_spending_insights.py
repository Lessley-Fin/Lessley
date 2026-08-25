"""
Tasks 1-4 (tasks.txt): plain-Python spending insight computations on InsightsService,
and task 5: sorting transactions before building missed-savings insights.
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.transaction import AmountDetail, Transaction, TransactionAmount, TransactionDates
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


# ── Task 3: spending saved (charged vs original amount) ────────────────────────
#
# A gap between the two amounts is only a discount once a conversion, a refund, an installment
# plan and a missing figure have been ruled out. Each of those produced a gap on real data, and
# together they reported a year's savings as 51,499 against a total spend of 51,668.

def test_spending_saved_counts_a_genuine_discount():
    service = _service()
    transactions = [_tx(charged=-47.81, original=-49.80)]

    assert service.spending_saved(transactions) == pytest.approx(1.99)


def test_spending_saved_equal_amounts_is_zero():
    service = _service()
    transactions = [_tx(charged=-50, original=-50)]

    assert service.spending_saved(transactions) == 0


def test_spending_saved_ignores_a_charge_larger_than_the_original():
    service = _service()
    transactions = [_tx(charged=-100, original=-90)]

    assert service.spending_saved(transactions) == 0


def test_spending_saved_counts_a_settled_purchase_that_was_never_billed():
    """Nothing was charged and the row has settled: the voucher paid, so the price was saved."""
    service = _service()
    transactions = [_tx(charged=None, original=-40)]

    assert service.spending_saved(transactions) == 40


def test_spending_saved_ignores_a_charge_that_has_not_landed_yet():
    """Before settlement the charge is still coming, so there is nothing saved to report."""
    service = _service()
    transactions = [_tx(charged=None, original=-40, status="PENDING")]

    assert service.spending_saved(transactions) == 0


def test_spending_saved_treats_a_settled_zero_charge_like_a_blank_one():
    """Billed exactly nothing and billed nothing at all say the same thing about what was paid."""
    service = _service()
    transactions = [_tx(charged=0.0, original=-40)]

    assert service.spending_saved(transactions) == 40


def test_spending_saved_ignores_a_currency_conversion():
    """USD 20 billed as ILS 60.26 is a conversion, not ILS 40.26 saved."""
    service = _service()
    transactions = [_tx(charged=-60.26, charged_currency="ILS", original=-20.0, original_currency="USD")]

    assert service.spending_saved(transactions) == 0


def test_spending_saved_ignores_an_installment_plan():
    """ILS 3,728 charged as four payments of 932 is the full price, paid in four."""
    service = _service()
    transactions = [_tx(charged=-932, original=-3728)]

    assert service.spending_saved(transactions) == 0


def test_spending_saved_ignores_a_plan_whose_payments_do_not_divide_evenly():
    """The issuer rounds the last payment, so a plan's ratio is near-integer, not exact."""
    service = _service()
    transactions = [_tx(charged=-333.34, original=-1000.0)]

    assert service.spending_saved(transactions) == 0


def test_spending_saved_ignores_a_refund():
    """A credit mirrors the purchase; subtracting one from the other counts it twice."""
    service = _service()
    transactions = [_tx(charged=29.21, original=-29.21)]

    assert service.spending_saved(transactions) == 0


def test_spending_saved_sums_across_transactions():
    service = _service()
    transactions = [
        _tx(charged=-90, original=-100),
        _tx(charged=-47.81, original=-49.80),
        _tx(charged=None, original=-40, status="PENDING"),
    ]

    assert service.spending_saved(transactions) == pytest.approx(11.99)


def test_savings_exclusions_names_why_each_purchase_was_dropped():
    service = _service()
    transactions = [
        _tx(charged=-90, original=-100),                                                    # counted
        _tx(charged=-50, original=-50),                                                     # no gap
        _tx(charged=None, original=-40, status="PENDING"),                                  # missing
        _tx(charged=-60.26, charged_currency="ILS", original=-20.0, original_currency="USD"),  # fx
        _tx(charged=-932, original=-3728),                                                  # installment
        _tx(charged=29.21, original=-29.21),                                                # refund
    ]

    assert service.savings_exclusions(transactions) == {
        "counted": 1,
        "no_gap": 1,
        "missing_amount": 1,
        "foreign_currency": 1,
        "installment_inferred": 1,
        "refund": 1,
    }


# ── Vouchers count as activity everywhere except the headline total ────────────

def test_an_account_used_only_for_vouchers_still_reports_its_activity():
    """A voucher card reporting 0 spent was the whole complaint: it is used, so it must show."""
    service = _service()
    transactions = [
        _tx(charged=-100, account_id="bank", account_number="****1"),
        _tx(charged=None, original=-176.15, account_id="voucher", account_number="****2"),
    ]

    by_account = {row["accountId"]: row for row in service.top_spending_accounts(transactions)}

    assert by_account["voucher"]["total_amount"] == pytest.approx(176.15)
    assert by_account["voucher"]["total_count"] == 1


def test_the_headline_total_leaves_the_voucher_out():
    """The same two purchases, under the question the total asks: only 100 left the bank."""
    service = _service()
    transactions = [
        _tx(charged=-100, account_id="bank"),
        _tx(charged=None, original=-176.15, account_id="voucher"),
    ]

    total = service.spending_total(transactions)

    assert total["total_amount"] == 100
    assert total["purchase_count"] == 2
    # ...while the composition beside it still describes the voucher as a thing that happened.
    assert {row["kind"]: row["count"] for row in total["composition"]} == {"ordinary": 1, "voucher": 1}


def test_the_headline_total_gives_back_what_was_reclaimed():
    service = _service()
    transactions = [_tx(charged=-100), _tx(charged=30.0)]

    assert service.spending_total(transactions)["total_amount"] == 70


def test_a_refund_cancels_the_purchase_it_reverses_in_a_category():
    """Four NUMASTAYS credits against one hotel charge: VACATION nets down, it does not ignore."""
    service = _service()
    transactions = [_tx(charged=-1000), _tx(charged=250.0)]

    assert service.top_spending_categories(transactions)[0]["total_amount"] == 750


def test_a_refund_does_not_count_as_a_visit():
    service = _service()
    transactions = [_tx(charged=-1000), _tx(charged=250.0)]

    assert service.top_spending_categories(transactions)[0]["total_count"] == 1


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


# ── missed-savings sorts transactions before matching shops ───────────────────

def _missed_savings_service(open_finance) -> InsightsService:
    service = _service(
        open_finance_service=open_finance,
        publisher_service=MagicMock(),
        user_repository=MagicMock(get_user_clubs=AsyncMock(return_value=["c1"])),
    )
    # The matching itself is covered by its own tests; here we only care that the
    # orchestration hands it correctly-sorted transactions.
    service.missed_savings_by_store = MagicMock(return_value=[])
    return service


async def test_missed_savings_sorts_real_transactions_before_matching():
    fetched = [_tx(charged=1)]
    sorted_transactions = [_tx(charged=2)]

    open_finance = MagicMock()
    open_finance.get_user_transactions_async = AsyncMock(return_value=fetched)
    open_finance.sort_transactions = MagicMock(return_value=sorted_transactions)
    open_finance.get_user_accounts_async = AsyncMock(
        return_value=[{"id": "acc-hever", "product": "חבר נטען"}]
    )

    service = _missed_savings_service(open_finance)

    await service.calculate_missed_savings_by_store_async("user@test.com", time_filter=True, days=7)

    open_finance.sort_transactions.assert_called_once_with(fetched)
    # The accounts feed travels with the transactions: without it the matching cannot tell a
    # club's own benefit card from an ordinary one, and reports a saving already made as missed.
    service.missed_savings_by_store.assert_called_once_with(
        sorted_transactions,
        user_club_ids=["c1"],
        account_products={"acc-hever": "חבר נטען"},
    )


async def test_missed_savings_does_not_sort_mock_data():
    open_finance = MagicMock()
    open_finance.sort_transactions = MagicMock()
    service = _missed_savings_service(open_finance)
    service.files_service.read_json = MagicMock(return_value=[{"fake": "tx"}])

    await service.calculate_missed_savings_by_store_async(
        "user@test.com", time_filter=True, days=7, use_mock=True
    )

    open_finance.sort_transactions.assert_not_called()
