"""
TransactionAmountService — reading money off one row of the card feed.

Every case here fired on a real year of transactions (`data/shmer.json`, 355 rows). The amounts
are the real ones, kept verbatim so a failure points at the row it came from.

A row is one of four kinds and the kind decides what its money means. Three of the four are a
gap between the two amounts and only one of them is a discount, so most of what follows is
about telling those three apart.
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
    COUPON,
    FOREIGN,
    INFLOW,
    INSTALLMENT,
    ORDINARY,
    OUTFLOW,
    REFUND,
    REGULAR,
    STATEMENT,
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
    merchant: str | None = None,
) -> Transaction:
    return Transaction(
        status=status,
        merchantName=merchant,
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
def service():
    return TransactionAmountService()


# ── Which way the money moved ─────────────────────────────────────────────────


def test_a_purchase_is_an_outflow(service):
    assert service.direction(_tx(charged=-86.0)) == OUTFLOW


def test_a_credit_is_an_inflow(service):
    assert service.direction(_tx(charged=29.21)) == INFLOW


def test_a_row_with_no_amount_at_all_says_so(service):
    assert service.direction(_tx()) == UNKNOWN


def test_the_sign_beats_the_providers_own_label(service):
    """Two mirrored refunds arrived flagged VARIABLE_EXPENSE on real data. The sign was right."""
    assert service.direction(_tx(charged=29.21, classification="VARIABLE_EXPENSE")) == INFLOW


# ── What kind of row is this? ─────────────────────────────────────────────────


def test_an_ordinary_purchase(service):
    assert service.detailed_kind_of(_tx(charged=-86.0, original=-86.0)) == ORDINARY
    assert service.kind_of(_tx(charged=-86.0, original=-86.0)) == REGULAR


def test_a_credit_is_a_refund(service):
    assert service.detailed_kind_of(_tx(charged=29.21)) == REFUND


def test_a_settled_row_the_card_was_never_billed_for_is_a_coupon(service):
    """A loaded club card paid: the merchant recorded the sale, the bank billed nothing."""
    assert service.detailed_kind_of(_tx(charged=None, original=-176.15)) == COUPON


def test_a_zero_charge_is_read_the_same_as_a_blank_one(service):
    assert service.detailed_kind_of(_tx(charged=0, original=-176.15)) == COUPON


def test_a_charge_that_has_not_landed_yet_is_not_a_coupon(service):
    """Before settlement a blank charge means the billing is still coming."""
    assert service.detailed_kind_of(_tx(charged=None, original=-40, status="PENDING")) != COUPON


def test_two_currencies_make_it_foreign_not_a_discount(service):
    """41,328 koruna billed as 6,815 shekels is a conversion, not 34,512 saved."""
    assert service.detailed_kind_of(_tx(charged=-6815.43, original=-41328.0, original_currency="CZK")) == FOREIGN


def test_the_installment_flag_settles_it(service):
    """3,728 charged as four payments of 932 looks exactly like 75% off. The feed says otherwise."""
    assert service.detailed_kind_of(_tx(charged=-932, original=-3728, installment=True)) == INSTALLMENT


def test_a_plan_is_recognised_by_its_shape_when_the_flag_is_missing(service):
    """The fallback for a trimmed payload: the charge divides the price a whole number of times."""
    assert service.detailed_kind_of(_tx(charged=-216, original=-648)) == INSTALLMENT


def test_a_gap_that_divides_unevenly_is_a_real_discount(service):
    assert service.detailed_kind_of(_tx(charged=-47.81, original=-49.80)) == STATEMENT


def test_a_duplicate_is_not_a_second_purchase(service):
    assert service.detailed_kind_of(_tx(charged=-86, duplicate=True)) == "duplicate"


def test_a_refund_abroad_is_read_as_a_refund_first(service):
    """Four Prague credits are both. Being told money came back matters more than the currency."""
    assert service.detailed_kind_of(_tx(charged=120.0, original=700.0, original_currency="CZK")) == REFUND


# ── The four figures ──────────────────────────────────────────────────────────


def test_a_regular_purchase_was_paid_for(service):
    transaction = _tx(charged=-86.0, original=-86.0)

    assert service.paid(transaction) == 86.0
    assert service.returned(transaction) == 0.0
    assert service.saved(transaction) == 0.0
    assert service.value(transaction) == 86.0


def test_a_statement_was_paid_at_the_billed_figure_and_saved_the_gap(service):
    transaction = _tx(charged=-47.81, original=-49.80)

    assert service.paid(transaction) == 47.81
    assert service.saved(transaction) == pytest.approx(1.99)
    assert service.value(transaction) == 47.81


def test_a_coupon_cost_nothing_and_saved_the_whole_price(service):
    transaction = _tx(charged=None, original=-176.15)

    assert service.paid(transaction) == 0.0
    assert service.saved(transaction) == 176.15
    # Still worth its full price wherever the question is what the user bought, or a card used
    # only for coupons would report no activity at all.
    assert service.value(transaction) == 176.15


def test_a_refund_came_back_and_is_never_a_saving(service):
    """
    A returned pair of shoes and a topcash cashback arrive identically: a positive amount.

    The feed cannot tell them apart, so calling either a saving would call both one. Money
    coming back reduces what was spent instead.
    """
    transaction = _tx(charged=29.21)

    assert service.returned(transaction) == 29.21
    assert service.saved(transaction) == 0.0
    assert service.paid(transaction) == 0.0
    assert service.value(transaction) == -29.21


def test_a_pending_charge_falls_back_to_the_merchants_figure(service):
    assert service.paid(_tx(charged=None, original=-42.5, status="PENDING")) == 42.5


def test_a_pending_charge_abroad_is_left_out_rather_than_guessed_at(service):
    """The merchant's figure is koruna and would be summed as shekels."""
    assert service.paid(_tx(charged=None, original=-700.0, original_currency="CZK", status="PENDING")) == 0.0


def test_a_duplicate_is_worth_nothing(service):
    assert service.value(_tx(charged=-86, duplicate=True)) == 0.0


def test_the_conversion_fee_is_a_fee_not_a_saving(service):
    assert service.markup_fee(_tx(charged=-6815.43, markup=-235.69)) == 235.69


# ── Totals over a list ────────────────────────────────────────────────────────


def test_spend_is_what_the_bank_statement_shows(service):
    """86 billed, 176.15 on a coupon, 20 returned → 66 out of the account."""
    transactions = [_tx(charged=-86), _tx(charged=None, original=-176.15), _tx(charged=20.0)]

    assert service.spend(transactions) == pytest.approx(66.0)


def test_the_source_blind_total_counts_the_coupon_and_is_larger(service):
    """
    The two disagree by exactly the coupons, and that is the point rather than a bug.

    `spend` answers "what does my bank show"; `total_value` answers "what did I buy". A coupon
    purchase belongs in the second and not the first.
    """
    transactions = [_tx(charged=-86), _tx(charged=None, original=-176.15)]

    assert service.spend(transactions) == 86.0
    assert service.total_value(transactions) == pytest.approx(262.15)


def test_savings_are_coupons_and_statement_gaps_only(service):
    transactions = [
        _tx(charged=None, original=-176.15),   # coupon: the whole price
        _tx(charged=-47.81, original=-49.80),  # statement: the gap
        _tx(charged=20.0),                     # refund: not a saving
        _tx(charged=-86, original=-86),        # regular: nothing
    ]

    assert service.savings(transactions) == pytest.approx(178.14)


def test_the_spend_breakdown_adds_up_to_spend(service):
    transactions = [_tx(charged=-86), _tx(charged=-47.81, original=-49.80), _tx(charged=20.0)]

    rows = {row["source"]: row["amount"] for row in service.spend_breakdown(transactions)}

    assert rows[REGULAR] == 86.0
    assert rows[STATEMENT] == 47.81
    assert rows[REFUND] == 20.0
    assert rows[REGULAR] + rows[STATEMENT] - rows[REFUND] == pytest.approx(service.spend(transactions))


def test_the_savings_breakdown_adds_up_to_savings(service):
    transactions = [_tx(charged=None, original=-176.15), _tx(charged=-47.81, original=-49.80)]

    rows = {row["source"]: row["amount"] for row in service.savings_breakdown(transactions)}

    assert rows[COUPON] == 176.15
    assert rows[STATEMENT] == pytest.approx(1.99)
    assert sum(rows.values()) == pytest.approx(service.savings(transactions))


# ── The mix, and the sum it is meant to explain ───────────────────────────────


def test_the_mix_contributions_add_up_to_spend(service):
    """
    The whole reason `contributes` exists beside `amount`.

    `amount` is what the screen prints, always positive — a refund reads as what came back. It
    is the signed column that reconciles, so no client ever has to know which rows to subtract.
    """
    transactions = [
        _tx(charged=-86, original=-86),
        _tx(charged=-6815.43, original=-41328.0, original_currency="CZK", markup=-235.69),
        _tx(charged=-932, original=-3728, installment=True, installment_total=4, merchant="a"),
        _tx(charged=-47.81, original=-49.80),
        _tx(charged=None, original=-176.15),
        _tx(charged=20.0),
    ]

    mix = service.mix(transactions)

    assert sum(row["contributes"] for row in mix) == pytest.approx(service.spend(transactions))


def test_a_coupon_contributes_nothing_but_is_still_shown(service):
    transactions = [_tx(charged=-86), _tx(charged=None, original=-176.15)]

    coupon = next(row for row in service.mix(transactions) if row["kind"] == COUPON)

    assert coupon["amount"] == 176.15
    assert coupon["contributes"] == 0.0


def test_a_refund_is_shown_positive_and_counted_negative(service):
    refund = next(row for row in service.mix([_tx(charged=20.0)]) if row["kind"] == REFUND)

    assert (refund["amount"], refund["contributes"]) == (20.0, -20.0)


def test_the_mix_counts_every_row_exactly_once(service):
    transactions = [
        _tx(charged=-86),
        _tx(charged=-6815.43, original=-41328.0, original_currency="CZK"),
        _tx(charged=None, original=-176.15),
        _tx(charged=20.0),
    ]

    assert sum(row["count"] for row in service.mix(transactions)) == len(transactions)


def test_the_mix_names_what_the_conversions_cost(service):
    transactions = [_tx(charged=-6815.43, original=-41328.0, original_currency="CZK", markup=-235.69)]

    foreign = next(row for row in service.mix(transactions) if row["kind"] == FOREIGN)

    assert foreign["markup_fees"] == 235.69


def test_the_mix_counts_plans_rather_than_repeating_the_payment_count(service):
    """Seven payments across two plans reads very differently from seven plans."""
    transactions = [
        _tx(charged=-932, original=-3728, installment=True, installment_total=4, merchant="a"),
        _tx(charged=-932, original=-3728, installment=True, installment_total=4, merchant="a"),
        _tx(charged=-100, original=-300, installment=True, installment_total=3, merchant="b"),
    ]

    plan = next(row for row in service.mix(transactions) if row["kind"] == INSTALLMENT)

    assert (plan["count"], plan["plan_count"]) == (3, 2)


def test_the_kind_census_explains_a_total_that_looks_wrong(service):
    transactions = [
        _tx(charged=-47.81, original=-49.80),
        _tx(charged=-50, original=-50),
        _tx(charged=None, original=-40),
        _tx(charged=-6815.43, original=-41328.0, original_currency="CZK"),
        _tx(charged=29.21),
        _tx(charged=-86, duplicate=True),
    ]

    assert service.kind_census(transactions) == {
        STATEMENT: 1,
        ORDINARY: 1,
        COUPON: 1,
        FOREIGN: 1,
        REFUND: 1,
        "duplicate": 1,
    }


# ── Preparing a list for grouping ─────────────────────────────────────────────


def test_countable_drops_duplicates_and_keeps_refunds(service):
    transactions = [_tx(charged=-86), _tx(charged=20.0), _tx(charged=-86, duplicate=True)]

    assert len(service.countable(transactions)) == 2


def test_purchases_only_drops_refunds_too(service):
    transactions = [_tx(charged=-86), _tx(charged=20.0)]

    assert len(service.purchases_only(transactions)) == 1
    assert service.purchase_count(transactions) == 1
