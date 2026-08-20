"""
TransactionAmountService — reading money off one row of the card feed.

Every case here fired on a real year of transactions (`data/shmer.json`, 355 rows). The amounts
are the real ones, kept verbatim so a failure points at the row it came from.
"""

import pytest

from models.transaction import (
    AmountDetail,
    InstallmentPlan,
    Transaction,
    TransactionAmount,
    TransactionClassification,
)
from services.transaction_amount_service import (
    INFLOW,
    OUTFLOW,
    UNKNOWN,
    TransactionAmountService,
)


def _tx(
    charged: float | None = None,
    original: float | None = None,
    charged_currency: str = "ILS",
    original_currency: str = "ILS",
    installment: bool = False,
    installment_number: int | None = None,
    installment_total: int | None = None,
    duplicate: bool = False,
    markup: float | None = None,
    classification: str | None = None,
    status: str = "BOOKED",
) -> Transaction:
    return Transaction(
        status=status,
        amount=TransactionAmount(
            # The charged node is always present on a real row, carrying its currency even when
            # the amount itself arrives blank — so a blank charge is `amount=None`, not a
            # missing node.
            chargedAmount=AmountDetail(amount=charged, currency=charged_currency),
            originalAmount=(
                AmountDetail(amount=original, currency=original_currency) if original is not None else None
            ),
        ),
        isCreditCardInstallment=installment,
        installments=(
            InstallmentPlan(number=installment_number, total=installment_total)
            if installment_total is not None
            else None
        ),
        isDuplicate=duplicate,
        markupFee=AmountDetail(amount=markup, currency="ILS") if markup is not None else None,
        classification=TransactionClassification(type=classification) if classification else None,
    )


@pytest.fixture
def service() -> TransactionAmountService:
    return TransactionAmountService()


# ── The model keeps what the provider sends ───────────────────────────────────
# These fields arrive on every row and were being dropped on the floor, which is why the
# calculations were guessing at what the feed states outright.

def test_the_model_keeps_the_installment_flag_and_plan():
    transaction = Transaction.model_validate(
        {
            "amount": {
                "originalAmount": {"amount": -3728, "currency": "ILS"},
                "chargedAmount": {"amount": -932, "currency": "ILS"},
            },
            "isCreditCardInstallment": True,
            "installments": {"number": 2, "total": 4},
            "isDuplicate": False,
            "markupFee": {"amount": 0, "currency": "ILS"},
            "classification": {"type": "VARIABLE_EXPENSE", "classifiedBy": "SYSTEM"},
        }
    )

    assert transaction.isCreditCardInstallment is True
    assert transaction.installments.number == 2
    assert transaction.installments.total == 4
    assert transaction.classification.type == "VARIABLE_EXPENSE"


def test_a_blank_amount_string_becomes_none():
    """The feed sends `"amount": ""` on real rows, not null."""
    transaction = Transaction.model_validate(
        {"amount": {"chargedAmount": {"amount": "", "currency": "ILS"},
                    "originalAmount": {"amount": -176.15, "currency": "ILS"}}}
    )

    assert transaction.amount.chargedAmount.amount is None


# ── Which way did the money move? ─────────────────────────────────────────────

def test_a_negative_charge_is_money_leaving(service):
    assert service.direction(_tx(charged=-86)) == OUTFLOW


def test_a_positive_charge_is_money_coming_back(service):
    assert service.direction(_tx(charged=141.86)) == INFLOW


def test_nothing_billed_takes_its_direction_from_the_merchants_figure(service):
    assert service.direction(_tx(charged=0.0, original=-40)) == OUTFLOW


def test_direction_falls_back_to_the_merchants_figure_when_nothing_is_billed(service):
    assert service.direction(_tx(charged=None, original=-176.15)) == OUTFLOW


# ── How much left the account ─────────────────────────────────────────────────

def test_amount_spent_is_the_billed_figure_as_a_positive_number(service):
    assert service.amount_spent(_tx(charged=-86)) == 86


def test_a_refund_is_not_spending(service):
    """Four refunded hotel nights were counted as ILS 567 of holiday spending."""
    refund = _tx(charged=141.86, original=942, original_currency="CZK", classification="VARIABLE_INCOME")

    assert service.amount_spent(refund) == 0.0
    assert service.amount_received(refund) == pytest.approx(141.86)


def test_a_refund_the_provider_mislabelled_as_an_expense_is_still_a_refund(service):
    """The sign is the reliable signal; `classification` called this one VARIABLE_EXPENSE."""
    assert service.amount_spent(_tx(charged=29.21, original=-29.21, classification="VARIABLE_EXPENSE")) == 0.0


def test_a_duplicate_is_not_a_second_purchase(service):
    assert service.amount_spent(_tx(charged=-86, duplicate=True)) == 0.0


def test_each_installment_row_bills_one_payment(service):
    """Four rows of 932 add up to the 3,728 purchase exactly once."""
    plan_row = _tx(charged=-932, original=-3728, installment=True, installment_number=2, installment_total=4)

    assert service.amount_spent(plan_row) == 932


def test_a_settled_purchase_that_was_never_billed_cost_nothing(service):
    """TERMINAL X, BOOKED and invoiced, ILS 176.15 asked and nothing charged: a voucher paid."""
    assert service.amount_spent(_tx(charged=None, original=-176.15)) == 0.0


def test_a_charge_still_to_come_falls_back_to_the_merchants_figure(service):
    """Before settlement a blank charge is billing that has not happened yet, not a voucher."""
    assert service.amount_spent(
        _tx(charged=None, original=-176.15, status="PENDING")
    ) == pytest.approx(176.15)


def test_the_fallback_refuses_to_sum_a_foreign_figure_as_shekels(service):
    """`originalAmount` here is koruna; summing it as ILS is how 41,328 got into a total."""
    assert service.amount_spent(
        _tx(charged=None, charged_currency="ILS", original=-41328, original_currency="CZK",
            status="PENDING")
    ) == 0.0


def test_the_fallback_refuses_to_use_a_plans_full_price_as_one_payment(service):
    assert service.amount_spent(
        _tx(charged=None, original=-3728, installment=True, installment_total=4, status="PENDING")
    ) == 0.0


# ── The signed view, and what the conversion cost ─────────────────────────────

def test_net_amount_is_negative_for_a_purchase_and_positive_for_a_refund(service):
    assert service.net_amount(_tx(charged=-86)) == -86
    assert service.net_amount(_tx(charged=141.86)) == pytest.approx(141.86)


def test_markup_fee_is_the_real_cost_of_a_foreign_purchase(service):
    """The row that read as ILS 34,512 saved in fact cost ILS 198.51 in issuer markup."""
    abroad = _tx(charged=-6815.43, original=-41328, original_currency="CZK", markup=198.51)

    assert service.markup_fee(abroad) == pytest.approx(198.51)
    assert service.amount_saved(abroad) == 0.0


# ── How much of the gap was a discount ────────────────────────────────────────

def test_a_genuine_discount_is_counted(service):
    assert service.amount_saved(_tx(charged=-47.81, original=-49.80)) == pytest.approx(1.99)


def test_equal_amounts_save_nothing(service):
    assert service.amount_saved(_tx(charged=-50, original=-50)) == 0.0


def test_a_conversion_is_not_a_discount(service):
    assert service.amount_saved(
        _tx(charged=-6815.43, charged_currency="ILS", original=-41328, original_currency="CZK")
    ) == 0.0


def test_a_settled_purchase_that_was_never_billed_is_the_whole_price_saved(service):
    """The one gap in this feed that is a real saving: the user was asked 176.15 and paid none."""
    amount, reason = service.saving_of(_tx(charged=None, original=-176.15))

    assert (amount, reason) == (pytest.approx(176.15), "not_charged")


def test_a_charge_still_to_come_is_not_a_saving(service):
    """It would reverse itself the moment the charge lands."""
    assert service.amount_saved(_tx(charged=None, original=-176.15, status="PENDING")) == 0.0


def test_a_settled_zero_charge_counts_the_same_as_a_blank_one(service):
    assert service.saving_of(_tx(charged=0.0, original=-49.80))[1] == "not_charged"


def test_a_credit_that_has_not_been_paid_out_is_not_a_saving(service):
    """A blank charge against a positive merchant figure is a refund pending, not a voucher."""
    assert service.amount_saved(_tx(charged=None, original=42.5)) == 0.0


def test_a_refund_is_not_a_discount(service):
    assert service.amount_saved(_tx(charged=29.21, original=-29.21)) == 0.0


def test_the_installment_flag_settles_it(service):
    """With the flag present nothing has to be inferred from the numbers."""
    amount, reason = service.saving_of(
        _tx(charged=-932, original=-3728, installment=True, installment_number=1, installment_total=4)
    )

    assert (amount, reason) == (0.0, "installment")


def test_a_plan_is_still_caught_when_the_feed_omits_the_flag(service):
    """A trimmed payload drops `isCreditCardInstallment`; the ratio is the backstop."""
    amount, reason = service.saving_of(_tx(charged=-932, original=-3728))

    assert (amount, reason) == (0.0, "installment_inferred")


def test_a_plan_whose_payments_do_not_divide_evenly_is_still_a_plan(service):
    """The issuer rounds the last payment, so the ratio is near-integer, not exact."""
    assert service.amount_saved(_tx(charged=-333.34, original=-1000.0)) == 0.0


def test_a_gap_too_uneven_to_be_a_plan_is_counted(service):
    assert service.amount_saved(_tx(charged=-160, original=-200)) == 40


def test_a_duplicate_saves_nothing(service):
    assert service.saving_of(_tx(charged=-47.81, original=-49.80, duplicate=True)) == (0.0, "duplicate")


# ── Explaining a total ────────────────────────────────────────────────────────

def test_savings_exclusions_names_why_each_purchase_was_dropped(service):
    transactions = [
        _tx(charged=-47.81, original=-49.80),                                              # counted
        _tx(charged=-50, original=-50),                                                    # no gap
        _tx(charged=None, original=-40),                                                   # voucher
        _tx(charged=None, original=-40, status="PENDING"),                                 # missing
        _tx(charged=-60.26, original=-20.0, original_currency="USD"),                      # fx
        _tx(charged=-932, original=-3728, installment=True, installment_total=4),          # flagged
        _tx(charged=-216, original=-648),                                                  # inferred
        _tx(charged=29.21, original=-29.21),                                               # refund
        _tx(charged=-86, original=-86, duplicate=True),                                    # duplicate
    ]

    assert service.savings_exclusions(transactions) == {
        "counted": 1,
        "not_charged": 1,
        "no_gap": 1,
        "missing_amount": 1,
        "foreign_currency": 1,
        "installment": 1,
        "installment_inferred": 1,
        "refund": 1,
        "duplicate": 1,
    }


# ── Preparing a list for grouping ─────────────────────────────────────────────

def test_countable_drops_duplicates_but_keeps_refunds(service):
    """A refund has to reach its category to cancel the purchase it reverses."""
    purchase, refund = _tx(charged=-86), _tx(charged=141.86)

    assert service.countable([purchase, refund, _tx(charged=-86, duplicate=True)]) == [purchase, refund]


def test_purchases_only_drops_refunds_too(service):
    """For questions about shopping habits, a credit is not a visit."""
    purchase = _tx(charged=-86)

    assert service.purchases_only([purchase, _tx(charged=141.86), _tx(charged=-86, duplicate=True)]) == [purchase]


def test_purchase_count_ignores_refunds_and_duplicates(service):
    assert service.purchase_count([_tx(charged=-86), _tx(charged=141.86), _tx(charged=-86, duplicate=True)]) == 1


# ── The two amount questions, which have two different answers ────────────────

def test_a_voucher_purchase_is_worth_its_price_but_costs_nothing(service):
    """The whole point of the split: the voucher account must not report zero activity."""
    voucher = _tx(charged=None, original=-176.15)

    assert service.amount_spent(voucher) == 0.0
    assert service.purchase_value(voucher) == pytest.approx(176.15)


def test_an_ordinary_purchase_is_the_same_under_both(service):
    ordinary = _tx(charged=-86)

    assert service.amount_spent(ordinary) == 86
    assert service.purchase_value(ordinary) == 86


def test_an_installment_row_is_worth_one_payment_under_both(service):
    plan_row = _tx(charged=-932, original=-3728, installment=True, installment_total=4)

    assert service.amount_spent(plan_row) == 932
    assert service.purchase_value(plan_row) == 932


def test_net_purchase_value_lets_a_refund_cancel_what_it_reverses(service):
    assert service.net_purchase_value(_tx(charged=-86)) == 86
    assert service.net_purchase_value(_tx(charged=141.86)) == pytest.approx(-141.86)


def test_total_spent_excludes_vouchers_and_nets_out_refunds(service):
    """ILS 86 spent, ILS 176.15 on a voucher, ILS 20 refunded → 66 out of the account."""
    transactions = [_tx(charged=-86), _tx(charged=None, original=-176.15), _tx(charged=20.0)]

    assert service.total_spent(transactions) == pytest.approx(66.0)


def test_total_spent_disagrees_with_the_breakdowns_on_purpose(service):
    """The breakdowns count the voucher at full worth; the headline total does not count it."""
    transactions = [_tx(charged=-86), _tx(charged=None, original=-176.15)]

    assert service.total_spent(transactions) == 86
    assert sum(service.net_purchase_value(t) for t in transactions) == pytest.approx(262.15)
