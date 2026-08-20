"""
The one place that reads money off a transaction.

Every insight in this codebase — what the user spends on, where, when, and what they saved —
comes down to turning one row of the Open Finance card feed into a number. That turn is where
the bugs live, because the feed's two amounts do not mean what their names suggest:

    "amount": {
        "originalAmount": { "amount": -41328.00, "currency": "CZK" },
        "chargedAmount":  { "amount":  -6815.43, "currency": "ILS" }
    }

`originalAmount` is not the sticker price before a discount. It is the amount *before the issuer
touched it* — before converting the currency, before splitting it into payments. Read naively,
that hotel bill in Prague looks like ILS 34,512 saved.

So the rules live here, once, instead of being re-derived at each call site:

  - **A refund is not spending.** A credit arrives as the mirror of the purchase — positive
    where the purchase was negative. `abs()` turned every one of them back into spending.
  - **A conversion is not a discount.** When the two amounts carry different currencies, the
    gap between them is an exchange rate. The issuer's cut on it is a *fee*, in `markupFee`.
  - **An installment is not a discount.** A four-payment plan is four rows, each carrying the
    whole purchase in `originalAmount` and one payment in `chargedAmount`. The feed says so
    outright in `isCreditCardInstallment`.
  - **But a settled purchase billed at nothing *is* a saving.** `chargedAmount.amount` arrives
    as `""` on real rows. Where the row is still `PENDING` that means "not billed yet" and the
    charge is coming. Where it is `BOOKED` — settlement final, `isInvoiced` true — it means the
    merchant recorded the sale and the card was charged nothing: a voucher, a gift card, points,
    or a fee the issuer waived. No money left the account, so it is not spending, and the user
    genuinely did not pay the price the merchant asked. That is the one gap in this feed that
    is a real saving.
  - **A duplicate is not a second purchase.** `isDuplicate` marks rows the provider has already
    told us are the same transaction seen twice.

Measured against a real year (355 transactions, `data/shmer.json`): the naive readings reported
ILS 53,456.67 of spending against an actual outflow of 52,447.43, and ILS 51,499.36 of savings
against a genuine 1.99.

This is a Layer-2 service in the sense of the repo's architecture: pure business logic, no
database, no HTTP, no I/O. It takes a `Transaction` and gives back a number.
"""

import logging
from collections import Counter

from config.constants import SAVINGS
from models.transaction import Transaction

logger = logging.getLogger(__name__)


# ── Why a purchase did or did not contribute to the savings total ─────────────────
# Only `SAVING_COUNTED` carries money. The rest name a gap between the original and charged
# amount that exists for a reason other than a discount. They are logged, not shown, so that a
# savings figure that looks wrong can be explained without re-reading the feed by hand.

SAVING_COUNTED = "counted"
SAVING_NOT_CHARGED = "not_charged"
SAVING_NO_GAP = "no_gap"
SAVING_MISSING_AMOUNT = "missing_amount"
SAVING_FOREIGN_CURRENCY = "foreign_currency"
SAVING_REFUND = "refund"
SAVING_INSTALLMENT = "installment"
SAVING_INSTALLMENT_INFERRED = "installment_inferred"
SAVING_DUPLICATE = "duplicate"

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
    Reads amounts off transactions, and says why when it declines to.

    Stateless and side-effect free: every method takes a transaction and returns a number or a
    label. Callers do the grouping and summing; this class only decides what one row is worth.
    """

    # ── The two amounts, unpacked safely ──────────────────────────────────────────

    @staticmethod
    def _charged(transaction: Transaction) -> tuple[float | None, str | None]:
        """What the issuer billed, and in which currency. `None` when the feed left it blank."""
        amount = transaction.amount
        if not amount or not amount.chargedAmount:
            return None, None
        return amount.chargedAmount.amount, amount.chargedAmount.currency

    @staticmethod
    def _original(transaction: Transaction) -> tuple[float | None, str | None]:
        """What the merchant asked for, before conversion or splitting, and in which currency."""
        amount = transaction.amount
        if not amount or not amount.originalAmount:
            return None, None
        return amount.originalAmount.amount, amount.originalAmount.currency

    # ── Is this row worth counting at all? ────────────────────────────────────────

    @staticmethod
    def is_duplicate(transaction: Transaction) -> bool:
        """Whether the provider has flagged this as the same transaction seen twice."""
        return bool(transaction.isDuplicate)

    def was_never_charged(self, transaction: Transaction) -> bool:
        """
        Whether this purchase settled without the card being billed for it.

        The signature is a blank (or zero) `chargedAmount` on a row the issuer has finished
        with, against a merchant figure that is an expense. On real data every such row is
        `BOOKED` and `isInvoiced` — the invoice went out and the amount on it was nothing —
        while the one `PENDING` row in the feed carries an ordinary charge. A voucher, a gift
        card, points, or a waived fee all land here; the feed does not say which, and for the
        purpose of "did the user pay this" it does not matter.

        The `BOOKED` check is what makes this safe. Before settlement a blank charge means the
        billing has not happened yet, not that it never will, and counting it as a saving would
        reverse itself the moment the charge lands.
        """
        if transaction.status != SETTLED:
            return False
        charged, _ = self._charged(transaction)
        if charged is not None and charged != 0:
            return False
        original, _ = self._original(transaction)
        # A blank charge against a *credit* is a refund that has not been paid out, which is
        # the opposite of a saving.
        return original is not None and original < 0

    def direction(self, transaction: Transaction) -> str:
        """
        Which way the money moved: out of the account, into it, or not enough information.

        Read from the sign of the billed amount. A purchase is negative; a refund, a chargeback
        or a cashback credit is positive. Zero counts as `UNKNOWN` rather than as a free
        purchase — a real charge is never exactly nothing, so a zero is a blank in disguise.
        """
        charged, _ = self._charged(transaction)
        if charged is None or charged == 0:
            # Nothing was billed — either not yet, or never. Either way the merchant's own
            # figure is what says which way this row points, and it is the only figure a
            # pending row has at all.
            original, _ = self._original(transaction)
            if original is None or original == 0:
                return UNKNOWN
            return OUTFLOW if original < 0 else INFLOW
        return OUTFLOW if charged < 0 else INFLOW

    def is_purchase(self, transaction: Transaction) -> bool:
        """
        Whether this row is the user buying something, as opposed to money coming back.

        This is the question the *counts* ask — "how many times did you shop here" — and a
        refund is not a visit. The sums ask a different question and keep refunds, so that a
        credit can cancel the purchase it reverses.
        """
        return not self.is_duplicate(transaction) and self.direction(transaction) == OUTFLOW

    # ── How much money moved ──────────────────────────────────────────────────────
    #
    # There are two different questions here and they have two different answers, because a
    # voucher purchase is worth something without costing anything:
    #
    #   amount_spent    — what left the bank. A voucher costs nothing, so it is zero.
    #   purchase_value  — what the purchase was worth, however it was paid for.
    #
    # "How much did I spend in total" is the first. Everything else — what the user buys, where,
    # when, on which card — is the second: shopping at TERMINAL X with a gift card is still
    # shopping at TERMINAL X, and a voucher account that reports zero activity is worse than
    # useless. Do not collapse these two back into one.

    def purchase_value(self, transaction: Transaction) -> float:
        """
        What this purchase was worth, as a positive number, regardless of how it was paid for.

        The billed figure where there is one, and the merchant's figure where the card was never
        charged — the voucher covered the price, but the price is what the user bought.
        """
        if self.is_duplicate(transaction) or self.direction(transaction) != OUTFLOW:
            return 0.0
        if self.was_never_charged(transaction):
            original, _ = self._original(transaction)
            return abs(original) if original is not None else 0.0
        return self._billed_or_estimated(transaction)

    def net_purchase_value(self, transaction: Transaction) -> float:
        """
        `purchase_value`, signed so that a refund cancels the purchase it reverses.

        This is what the per-category, per-shop, per-account and per-day sums add up, so that a
        refunded hotel stops counting as a holiday the user took.
        """
        if self.is_duplicate(transaction):
            return 0.0
        return self.purchase_value(transaction) - self.amount_received(transaction)

    def amount_spent(self, transaction: Transaction) -> float:
        """
        How much money left the account on this row, as a positive number. Zero if none did.

        The billed figure is the right one to sum even for an installment plan: each row bills
        one payment, so the rows of a four-payment plan add up to the purchase exactly once.

        A purchase that settled without being billed cost nothing, whatever the merchant asked
        — the voucher paid for it, not the account. It is a saving instead; see `saving_of`.

        That leaves the row still waiting to be billed, where the merchant's figure stands in as
        the best estimate of the charge to come — see `_billed_or_estimated`.

        This is the *only* figure that answers "how much did I spend". Everywhere the question
        is what the user bought rather than what it cost them, use `purchase_value`.
        """
        if not self.is_purchase(transaction):
            return 0.0
        if self.was_never_charged(transaction):
            return 0.0
        return self._billed_or_estimated(transaction)

    def _billed_or_estimated(self, transaction: Transaction) -> float:
        """
        The billed figure, or the merchant's figure where billing has not happened yet.

        The substitution has to be *positively* safe, not merely unobjectionable. It is not safe
        for a plan, where the merchant's figure is the whole purchase rather than this month's
        payment. It is not safe across a currency, where the figure is koruna or dollars and
        would be summed as shekels — and a blank charge on a real row still carries its own
        currency ("amount": "", "currency": "ILS"), so a match can be confirmed where there is
        one. Where it cannot be, the row is left out rather than guessed at.
        """
        charged, charged_currency = self._charged(transaction)
        if charged is not None:
            return abs(charged)

        original, original_currency = self._original(transaction)
        if original is None:
            return 0.0
        if transaction.isCreditCardInstallment:
            return 0.0
        if charged_currency != original_currency:
            return 0.0
        return abs(original)

    def amount_received(self, transaction: Transaction) -> float:
        """How much money came back on this row — a refund, a chargeback, a credit."""
        if self.is_duplicate(transaction) or self.direction(transaction) != INFLOW:
            return 0.0
        charged, _ = self._charged(transaction)
        if charged is not None:
            return abs(charged)
        original, _ = self._original(transaction)
        return abs(original) if original is not None else 0.0

    def net_amount(self, transaction: Transaction) -> float:
        """
        The signed effect on the balance: negative for a purchase, positive for a refund.

        Summing this over a period answers "how much worse off am I", which is a different — and
        for a period comparison, more honest — question than `amount_spent`, because a refund
        cancels the purchase it reverses instead of being ignored.
        """
        if self.is_duplicate(transaction):
            return 0.0
        return self.amount_received(transaction) - self.amount_spent(transaction)

    def markup_fee(self, transaction: Transaction) -> float:
        """
        The issuer's cut for converting a foreign purchase, as a positive number.

        Present on exactly the rows whose two amounts differ in currency. It is the real cost of
        spending abroad, and the honest thing to show where the naive reading of those rows was
        showing a windfall.
        """
        if self.is_duplicate(transaction) or not transaction.markupFee:
            return 0.0
        fee = transaction.markupFee.amount
        return abs(fee) if fee is not None else 0.0

    # ── How much of it was a discount ─────────────────────────────────────────────

    def saving_of(self, transaction: Transaction) -> tuple[float, str]:
        """
        The discount on this purchase, and why it is — or is not — counted.

        The gap between the merchant's figure and the billed one is only a discount once every
        other thing that opens a gap has been ruled out. The checks run in order and the first
        one to apply wins; each is there because it fired on real data.
        """
        if self.is_duplicate(transaction):
            return 0.0, SAVING_DUPLICATE

        charged, charged_currency = self._charged(transaction)
        original, original_currency = self._original(transaction)

        # The whole price, saved: the sale settled and the card was never billed for it. This
        # is checked before the blank-amount rule below, because the two look identical in the
        # amounts alone and are told apart only by the row having settled.
        if self.was_never_charged(transaction):
            return abs(original), SAVING_NOT_CHARGED

        # A figure the bank has not sent *yet* is not a free purchase, and neither is a zero
        # one. Reading either as "paid nothing" booked the whole amount as savings.
        if charged is None or original is None or charged == 0:
            return 0.0, SAVING_MISSING_AMOUNT

        # 41,328 koruna billed as 6,815 shekels is a conversion, not 34,512 saved. What the
        # conversion actually cost is in `markup_fee`, and it is a fee, not a saving.
        if charged_currency != original_currency:
            return 0.0, SAVING_FOREIGN_CURRENCY

        # A refund mirrors the purchase it reverses. Subtracting one figure from the other
        # counts the transaction twice over rather than finding a discount in it.
        if (charged > 0) != (original > 0):
            return 0.0, SAVING_REFUND

        # The feed says so itself. This is the authoritative answer where it is present.
        if transaction.isCreditCardInstallment:
            return 0.0, SAVING_INSTALLMENT

        paid, sticker = abs(charged), abs(original)
        if sticker <= paid:
            return 0.0, SAVING_NO_GAP

        # Not every caller's feed carries the flag — a trimmed payload drops it — so a plan is
        # also recognised by its shape: the billed amount divides the merchant's figure a whole
        # number of times. Reported under its own name so that a pile of these is a visible
        # sign the flag is missing upstream rather than a silent guess.
        if self._looks_like_installments(sticker, paid):
            return 0.0, SAVING_INSTALLMENT_INFERRED

        return sticker - paid, SAVING_COUNTED

    @staticmethod
    def _looks_like_installments(sticker: float, paid: float) -> bool:
        """
        Whether the charge divides the full price a whole number of times.

        The fallback for feeds without `isCreditCardInstallment`. It cannot tell a plan from an
        exact half-price sale, and it resolves that tie in favour of the plan — see ``SAVINGS``
        for why that trade is worth making.
        """
        ratio = sticker / paid  # `paid` is non-zero: a zero charge never reaches here
        payments = round(ratio)
        if not 2 <= payments <= SAVINGS.MAX_INSTALLMENTS:
            return False
        return abs(ratio - payments) <= SAVINGS.INSTALLMENT_RATIO_TOLERANCE

    def amount_saved(self, transaction: Transaction) -> float:
        """How much this purchase actually knocked off the price."""
        return self.saving_of(transaction)[0]

    # ── Explaining a total ────────────────────────────────────────────────────────

    def savings_exclusions(self, transactions: list[Transaction]) -> dict[str, int]:
        """
        How many purchases landed in each reason, for the caller to log.

        Kept apart from the sum so the calculation itself stays a plain addition. Most of a year
        is expected to come back as `no_gap`; a sudden pile of `foreign_currency` or
        `installment` is what explains a savings figure that looks too good, and a pile of
        `installment_inferred` says the feed has stopped sending the flag.
        """
        return dict(Counter(self.saving_of(purchase)[1] for purchase in transactions))

    def total_spent(self, transactions: list[Transaction]) -> float:
        """
        The headline figure: how much worse off the account is over these transactions.

        Money that left, less money that came back. Vouchers are absent by construction — they
        cost nothing — which is what separates this from every per-category, per-shop and
        per-account total, where the same voucher purchase is counted at its full worth.
        """
        return sum(self.amount_spent(t) for t in transactions) - sum(
            self.amount_received(t) for t in transactions
        )

    # ── Preparing a list for grouping ─────────────────────────────────────────────

    def countable(self, transactions: list[Transaction]) -> list[Transaction]:
        """
        Everything the provider has not told us to ignore — duplicates removed, refunds kept.

        Refunds stay because the per-group sums net them out: a credit has to reach the category
        it belongs to in order to cancel the purchase it reverses. The *counts* filter them out
        separately, with `is_purchase`.
        """
        return [t for t in transactions if not self.is_duplicate(t)]

    def purchases_only(self, transactions: list[Transaction]) -> list[Transaction]:
        """Just the buying — no refunds, no duplicates. For questions about shopping habits."""
        return [t for t in transactions if self.is_purchase(t)]

    def purchase_count(self, transactions: list[Transaction]) -> int:
        """How many of these rows are the user actually buying something."""
        return sum(1 for t in transactions if self.is_purchase(t))
