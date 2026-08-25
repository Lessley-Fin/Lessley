"""
The one place that reads money off a transaction.

A row of the Open Finance card feed carries two amounts, and neither means what its name
suggests:

    "amount": {
        "originalAmount": { "amount": -41328.00, "currency": "CZK" },
        "chargedAmount":  { "amount":  -6815.43, "currency": "ILS" }
    }

`originalAmount` is not the sticker price before a discount. It is the amount *before the issuer
touched it* — before converting the currency, before splitting it into payments. Read naively,
that hotel bill in Prague looks like ILS 34,512 saved. Measured against a real year of 355
transactions, the naive readings reported ILS 51,499.36 of savings against a genuine 1.99.

Every row is one of four kinds, and the kind decides what its money means:

    regular    the user paid what the merchant asked
    statement  the issuer billed less than the merchant asked — a real discount
    coupon     settled, and the card was never billed: a loaded club card paid
    refund     money came back

Three of those four are gaps between the two amounts, and only one of them is a discount. The
order in `detailed_kind_of` is what tells them apart, and each check is there because it fired
on real data. Please do not reorder it.
"""

import logging
from collections import Counter

from config.constants import SAVINGS
from models.transaction import Transaction

logger = logging.getLogger(__name__)


# What kind of thing happened. `detailed_kind_of` returns one of these six; `kind_of` folds the
# first three into REGULAR, because "the user simply paid" is one idea however it was billed.
ORDINARY = "ordinary"
FOREIGN = "foreign"
INSTALLMENT = "installment"
STATEMENT = "statement"
COUPON = "coupon"
REFUND = "refund"
DUPLICATE = "duplicate"

REGULAR = "regular"

REGULAR_SHAPES = (ORDINARY, FOREIGN, INSTALLMENT)

# The order the client reads them in: everyday first, then the exceptions by how much explaining
# they need. Fixed rather than sorted by count, so the legend does not reshuffle between one time
# range and the next.
MIX_ORDER = [ORDINARY, FOREIGN, INSTALLMENT, STATEMENT, REFUND, COUPON]

# Which way the money moved. The feed signs its amounts: a purchase is negative, a refund or a
# credit is positive. That sign is more reliable than `classification.type`, which labelled two
# plainly mirrored refunds (Google One, aliexpress) as VARIABLE_EXPENSE on real data.
OUTFLOW = "outflow"
INFLOW = "inflow"
UNKNOWN = "unknown"

# A settled row: the issuer is finished with it and the amount billed will not change. What a
# blank charge means turns on this — before settlement it is a charge still to come, after it a
# charge that never happened.
SETTLED = "BOOKED"


class TransactionAmountService:
    """
    Reads amounts off transactions. Stateless: a transaction in, a number or a label out.

    Callers do the grouping and summing. Four figures answer four different questions:

        paid      what the bank billed
        returned  what came back
        saved     what the user did not have to pay
        value     what the purchase was worth, whoever paid for it
    """

    # ── The two amounts, unpacked safely ──────────────────────────────────────────

    @staticmethod
    def _charged(transaction: Transaction) -> tuple[float | None, str | None]:
        amount = transaction.amount
        if not amount or not amount.chargedAmount:
            return None, None
        return amount.chargedAmount.amount, amount.chargedAmount.currency

    @staticmethod
    def _original(transaction: Transaction) -> tuple[float | None, str | None]:
        amount = transaction.amount
        if not amount or not amount.originalAmount:
            return None, None
        return amount.originalAmount.amount, amount.originalAmount.currency

    def _charged_amount(self, transaction: Transaction) -> float | None:
        return self._charged(transaction)[0]

    def _original_amount(self, transaction: Transaction) -> float | None:
        return self._original(transaction)[0]

    # ── What kind of row is this? ─────────────────────────────────────────────────

    @staticmethod
    def is_duplicate(transaction: Transaction) -> bool:
        return bool(transaction.isDuplicate)

    def direction(self, transaction: Transaction) -> str:
        """Which way the money moved, read from the sign of whichever amount the feed gave us."""
        charged = self._charged_amount(transaction)
        if charged is None or charged == 0:
            original = self._original_amount(transaction)
            if original is None or original == 0:
                return UNKNOWN
            return OUTFLOW if original < 0 else INFLOW
        return OUTFLOW if charged < 0 else INFLOW

    def is_coupon(self, transaction: Transaction) -> bool:
        """
        Settled, and the card was never billed for it: a loaded club card paid.

        A נטען card is topped up in advance and only spends at the club's own shops, so the
        purchase carried its discount before it reached the bank. The `BOOKED` check is what
        makes this safe — before settlement a blank charge means the billing has not happened
        yet, not that it never will.

        The feed says no money left the account. It does not say whose card it was, so nothing
        downstream may name the club.
        """
        if transaction.status != SETTLED:
            return False
        charged = self._charged_amount(transaction)
        if charged is not None and charged != 0:
            return False
        original = self._original_amount(transaction)
        return original is not None and original < 0

    def is_installment(self, transaction: Transaction) -> bool:
        """
        One payment of a plan, not a purchase at a quarter of the price.

        The feed says so outright in `isCreditCardInstallment`, and that is authoritative where
        it is present. The shape check is the fallback for a trimmed payload that has dropped
        the flag, where a plan can only be recognised by the charge dividing the full price a
        whole number of times. In that mode a genuine half-price sale is suppressed along with
        the plans; that is deliberate — see `SAVINGS`.
        """
        if transaction.isCreditCardInstallment:
            return True
        charged, charged_currency = self._charged(transaction)
        original, original_currency = self._original(transaction)
        if charged is None or original is None or charged == 0:
            return False
        if charged_currency != original_currency:
            return False
        ratio = abs(original) / abs(charged)
        payments = round(ratio)
        if not 2 <= payments <= SAVINGS.MAX_INSTALLMENTS:
            return False
        return abs(ratio - payments) <= SAVINGS.INSTALLMENT_RATIO_TOLERANCE

    def is_foreign(self, transaction: Transaction) -> bool:
        """The two amounts are in different currencies, so the gap between them is a rate."""
        _, charged_currency = self._charged(transaction)
        _, original_currency = self._original(transaction)
        return bool(charged_currency and original_currency and charged_currency != original_currency)

    def is_statement(self, transaction: Transaction) -> bool:
        """The issuer billed less than the merchant asked, in the same currency. A real discount."""
        charged = self._charged_amount(transaction)
        original = self._original_amount(transaction)
        if charged is None or original is None or charged == 0:
            return False
        return abs(original) > abs(charged)

    def detailed_kind_of(self, transaction: Transaction) -> str:
        """
        The one label that best describes this row.

        Ranked rather than combined, because a row can carry several of these traits at once —
        four of the Prague credits are both a refund and a foreign purchase — and a census that
        counted them twice would not sum to the transaction count.
        """
        if self.is_duplicate(transaction):
            return DUPLICATE
        if self.direction(transaction) == INFLOW:
            return REFUND
        if self.is_coupon(transaction):
            return COUPON
        if self.is_foreign(transaction):
            return FOREIGN
        if self.is_installment(transaction):
            return INSTALLMENT
        if self.is_statement(transaction):
            return STATEMENT
        return ORDINARY

    def kind_of(self, transaction: Transaction) -> str:
        """The same reading, folded to the four kinds the totals are built from."""
        detailed = self.detailed_kind_of(transaction)
        return REGULAR if detailed in REGULAR_SHAPES else detailed

    # ── How much money moved ──────────────────────────────────────────────────────

    def paid(self, transaction: Transaction) -> float:
        """What the bank billed for this row. A coupon cost nothing; a refund is not a payment."""
        if self.kind_of(transaction) not in (REGULAR, STATEMENT):
            return 0.0
        return self._billed_or_estimated(transaction)

    def returned(self, transaction: Transaction) -> float:
        """What came back on this row."""
        if self.kind_of(transaction) != REFUND:
            return 0.0
        charged = self._charged_amount(transaction)
        if charged is not None:
            return abs(charged)
        original = self._original_amount(transaction)
        return abs(original) if original is not None else 0.0

    def saved(self, transaction: Transaction) -> float:
        """
        What the user did not have to pay: the whole price on a coupon, the gap on a statement.

        A refund is not here. The feed reports a returned pair of shoes and a topcash cashback
        identically — both arrive as a positive amount — so calling either a saving would call
        both one. Money coming back reduces what was spent instead; see `spend`.
        """
        kind = self.kind_of(transaction)
        if kind == COUPON:
            return abs(self._original_amount(transaction) or 0.0)
        if kind == STATEMENT:
            return abs(self._original_amount(transaction)) - abs(self._charged_amount(transaction))
        return 0.0

    def value(self, transaction: Transaction) -> float:
        """
        What this purchase was worth, whoever paid for it, signed so a refund cancels a purchase.

        The figure for every question about *what the user buys* rather than what it cost them:
        shopping at TERMINAL X with a loaded card is still shopping at TERMINAL X, and a card
        used only for coupons would otherwise report no activity at all.
        """
        if self.is_duplicate(transaction):
            return 0.0
        kind = self.kind_of(transaction)
        if kind == COUPON:
            return abs(self._original_amount(transaction) or 0.0)
        return self.paid(transaction) - self.returned(transaction)

    def _billed_or_estimated(self, transaction: Transaction) -> float:
        """
        The billed figure, or the merchant's figure where billing has not happened yet.

        The substitution has to be positively safe. It is not safe for a plan, where the
        merchant's figure is the whole purchase rather than this month's payment, nor across a
        currency, where the figure is koruna and would be summed as shekels. A blank charge on
        a real row still carries its own currency ("amount": "", "currency": "ILS"), so a match
        can be confirmed where there is one; where it cannot be, the row is left out.
        """
        charged, charged_currency = self._charged(transaction)
        if charged is not None:
            return abs(charged)
        original, original_currency = self._original(transaction)
        if original is None or transaction.isCreditCardInstallment:
            return 0.0
        if charged_currency != original_currency:
            return 0.0
        return abs(original)

    def markup_fee(self, transaction: Transaction) -> float:
        """The issuer's cut for converting a foreign purchase — a fee, never a saving."""
        if self.is_duplicate(transaction) or not transaction.markupFee:
            return 0.0
        fee = transaction.markupFee.amount
        return abs(fee) if fee is not None else 0.0

    # ── Totals over a list ────────────────────────────────────────────────────────

    def spend(self, transactions: list[Transaction]) -> float:
        """What the bank statement shows: billed less returned. Coupons are absent, having cost nothing."""
        return sum(self.paid(t) for t in transactions) - sum(self.returned(t) for t in transactions)

    def savings(self, transactions: list[Transaction]) -> float:
        """Everything the user did not have to pay."""
        return sum(self.saved(t) for t in transactions)

    def total_value(self, transactions: list[Transaction]) -> float:
        """What they bought, whoever paid. Larger than `spend` by the coupons."""
        return sum(self.value(t) for t in transactions)

    def spend_breakdown(self, transactions: list[Transaction]) -> list[dict]:
        """Where `spend` comes from: regular, statements at what was billed, less refunds."""
        return [
            self._source_row(REGULAR, transactions, self.paid),
            self._source_row(STATEMENT, transactions, self.paid),
            self._source_row(REFUND, transactions, self.returned),
        ]

    def savings_breakdown(self, transactions: list[Transaction]) -> list[dict]:
        """Where `savings` comes from: the whole price on a coupon, the gap on a statement."""
        return [
            self._source_row(COUPON, transactions, self.saved),
            self._source_row(STATEMENT, transactions, self.saved),
        ]

    def _source_row(self, kind: str, transactions: list[Transaction], amount_of) -> dict:
        of_kind = [t for t in transactions if self.kind_of(t) == kind]
        return {"source": kind, "count": len(of_kind), "amount": sum(amount_of(t) for t in of_kind)}

    def mix(self, transactions: list[Transaction]) -> list[dict]:
        """
        What the period was made of, and how each part reaches the spend total.

        `amount` is what the client prints, always positive — a refund of 40 reads as "40 came
        back". `contributes` is the same money signed by which way it moved, so summing that
        column lands on `spend` exactly. A coupon contributes nothing: no money left the bank.
        """
        rows = []
        for kind in MIX_ORDER:
            of_kind = [t for t in transactions if self.detailed_kind_of(t) == kind]
            if not of_kind:
                continue
            rows.append(self._mix_row(kind, of_kind))
        return rows

    def _mix_row(self, kind: str, of_kind: list[Transaction]) -> dict:
        if kind == REFUND:
            amount = sum(self.returned(t) for t in of_kind)
            contributes = -amount
        elif kind == COUPON:
            amount = sum(self.saved(t) for t in of_kind)
            contributes = 0.0
        else:
            amount = sum(self.paid(t) for t in of_kind)
            contributes = amount

        row = {"kind": kind, "count": len(of_kind), "amount": amount, "contributes": contributes}
        if kind == FOREIGN:
            row["markup_fees"] = sum(self.markup_fee(t) for t in of_kind)
        if kind == INSTALLMENT:
            row["plan_count"] = self._distinct_plans(of_kind)
        return row

    @staticmethod
    def _distinct_plans(installment_rows: list[Transaction]) -> int:
        """A plan repeats the merchant, the full price and the payment count on every one of its rows."""
        return len({
            (
                transaction.merchantName,
                transaction.amount.originalAmount.amount if transaction.amount and transaction.amount.originalAmount else None,
                transaction.installments.total if transaction.installments else None,
            )
            for transaction in installment_rows
        })

    def kind_census(self, transactions: list[Transaction]) -> dict[str, int]:
        """How many rows of each kind, for the caller to log when a total looks wrong."""
        return dict(Counter(self.detailed_kind_of(t) for t in transactions))

    # ── Preparing a list for grouping ─────────────────────────────────────────────

    def countable(self, transactions: list[Transaction]) -> list[Transaction]:
        """Everything the provider has not told us to ignore. Refunds stay, so sums can net them out."""
        return [t for t in transactions if not self.is_duplicate(t)]

    def is_purchase(self, transaction: Transaction) -> bool:
        """The user buying something. A refund is not a visit."""
        return not self.is_duplicate(transaction) and self.direction(transaction) == OUTFLOW

    def purchases_only(self, transactions: list[Transaction]) -> list[Transaction]:
        return [t for t in transactions if self.is_purchase(t)]

    def purchase_count(self, transactions: list[Transaction]) -> int:
        return sum(1 for t in transactions if self.is_purchase(t))
