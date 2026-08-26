import logging
from datetime import datetime, timedelta
from typing import Dict, List

from functional import seq

from services.transaction_stash_service import TransactionStashService
from services.open_finance_service import OpenFinanceService
from services.publisher_service import PublisherService
from services.user_repository import UserRepository
from services.reference_data_repository import ReferenceDataRepository
from services.mcc_service import MccService
from services.transaction_amount_service import TransactionAmountService
from config.constants import LIMITS, SHOP_MATCH
from models.transaction import Transaction
from services.transaction_amount_service import COUPON
from services.utils.store_similarity import EXACT, SIMILAR, STRONG, SURFACEABLE, WEAK
from routers.responses import (
    AppliedSavingsSchema,
    MissedSavingsSchema,
    SavingsAnswerSchema,
    SavingsBandSchema,
    SavingsMerchantSchema,
    SavingsPurchaseSchema,
    SavingsShopSchema,
)


logger = logging.getLogger(__name__)

# Sunday first, because that is how the week is displayed to the user.
DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# We never show a user more than this many alternative shops for a single club.
MAX_ALTERNATIVE_STORES_PER_CLUB = 10

# Most confident first, for picking one reading of a shop over another.
_BAND_ORDER = {EXACT: 0, STRONG: 1, SIMILAR: 2, WEAK: 3}

# The bands a purchase can be counted under, strongest first. WEAK never surfaces.
_BANDS_BY_CONFIDENCE = [EXACT, STRONG, SIMILAR]

# A merchant card has room for a handful of shops. The cap is on what is *shown* under a
# merchant, never on which purchases are counted — the totals must describe every purchase.
MAX_SHOPS_PER_MERCHANT = 8


def trim_categories_by_match_level(categories: list, matching_score) -> list:
    """
    Keep only the most relevant categories based on the user's match level (Process 2).

    `categories` is expected sorted by relevance (highest spend first). `matching_score`
    is the fraction X of least-relevant categories to drop:
      keep = round(len * (1 - X))   →  16 @ 0.25 → 12, @ 0.50 → 8, @ 0.75 → 4.

    A null/None score means "no trim" (keep all). At least one category is always kept
    when any exist.
    """
    if not categories:
        return []
    if matching_score is None:
        return categories

    x = max(0.0, min(1.0, float(matching_score)))
    keep = max(1, round(len(categories) * (1 - x)))
    return categories[:keep]


class InsightsService:
    """
    Works out what the user's spending actually says about them.

    Every calculation below reads top-to-bottom like a sentence: start with the user's
    purchases, narrow them down, put them into piles, add up the money, sort, and hand back
    the answer. Nothing here touches the database — data arrives as arguments and reference
    data is asked for from ReferenceDataRepository.
    """

    def __init__(
        self,
        open_finance_service: OpenFinanceService,
        files_service: TransactionStashService,
        publisher_service: PublisherService,
        user_repository: UserRepository,
        reference_data_repository: ReferenceDataRepository,
        mcc_service: MccService,
        amount_service: TransactionAmountService | None = None,
    ):
        self.open_finance_service = open_finance_service
        self.files_service = files_service
        self.publisher_service = publisher_service
        self.user_repository = user_repository
        self.reference_data_repository = reference_data_repository
        self.mcc_service = mcc_service
        # Every reading of money off a transaction goes through here. Defaulted rather than
        # required because it holds no state and has no collaborators — there is nothing for a
        # caller to configure, and nothing to mock.
        self.amount_service = amount_service or TransactionAmountService()

    # ── Reading a single purchase ─────────────────────────────────────────────
    # Small helpers so the chains below can stay one idea per line.

    @staticmethod
    def _date_of(transaction: Transaction):
        """When the purchase happened — whichever date the bank actually gave us."""
        if not transaction.date:
            return None
        return transaction.date.transactionDate or transaction.date.bookingDate or transaction.date.valueDate

    # Money is never read off a transaction here — `TransactionAmountService` owns that, so
    # that "what is this row worth" has one answer across every insight below. These stay as
    # thin names because the `seq(...).sum(...)` chains read better with them.

    def _value(self, transaction: Transaction) -> float:
        """What this purchase was worth, whoever paid for it. Signed, so a refund cancels one."""
        return self.amount_service.value(transaction)

    def _spend(self, transaction: Transaction) -> float:
        """This row as the bank statement shows it. A coupon is zero."""
        return self.amount_service.spend_of(transaction)

    def _purchase_count(self, transactions: list[Transaction]) -> int:
        return self.amount_service.purchase_count(transactions)

    def _saved(self, transaction: Transaction) -> float:
        return self.amount_service.saved(transaction)

    def _countable(self, transactions: list[Transaction]) -> list[Transaction]:
        return self.amount_service.countable(transactions)

    @staticmethod
    def _category_of(transaction: Transaction) -> str:
        """What kind of purchase this was ("GROCERIES"), or "N/A" if the bank did not say."""
        if transaction.category and transaction.category.sub:
            return transaction.category.sub
        return "N/A"

    @staticmethod
    def _merchant_of(transaction: Transaction) -> str:
        """Which shop this was, tidied up, or "N/A" if the bank did not say."""
        name = transaction.merchantName
        if name is not None and str(name).strip() != "":
            return str(name).strip()
        return "N/A"

    @staticmethod
    def _by_totals(row: dict) -> tuple:
        """Ranking rule for category and account lines: most purchases wins, then most money."""
        return (row["total_count"], row["total_amount"])

    @staticmethod
    def _by_transactions(row: dict) -> tuple:
        """The same ranking rule for shop lines, which name their columns differently."""
        return (row["transaction_count"], row["transaction_amount"])

    # ── What does the user spend on? ──────────────────────────────────────────

    def top_spending_categories(
        self, transactions: list[Transaction], limit: int = LIMITS.TOP_CATEGORIES
    ) -> list[dict]:
        """The kinds of things the user spends the most on."""
        if not transactions:
            return []

        return (
            seq(self._countable(transactions))             # every purchase the user made
            .group_by(self._category_of)                       # one pile per kind of purchase
            .select(self._summarise_category)                  # each pile becomes one summary line
            .sorted(key=lambda row: row["category"])           # settle ties alphabetically
            .sorted(key=self._by_totals, reverse=True)         # then put the biggest spend on top
            .take(limit)                                       # keep only the leading few
            .to_list()                                         # hand back a plain list
        )

    def _summarise_category(self, group: tuple) -> dict:
        """Turn one pile of same-category purchases into a single summary line."""
        category_name, purchases = group
        return {
            "category": category_name,
            "total_count": self._purchase_count(purchases),
            "total_amount": seq(purchases).sum(self._value),
            "mcc_codes": (
                seq(purchases)                                            # the purchases in this pile
                .where(lambda purchase: purchase.categoryCode)            # those the bank gave a code for
                # turn each numeric code into the category name it stands for
                .select(lambda purchase: self.mcc_service.get_mcc_by_id(str(purchase.categoryCode)))
                .where(lambda category: category != "N/A")                # drop codes we cannot name
                .distinct()                                               # each code mentioned once
                .sorted()                                                 # stable order for the client
                .to_list()                                                # hand back a plain list
            ),
        }

    # ── Which of the user's accounts is doing the spending? ───────────────────

    def top_spending_accounts(self, transactions: list[Transaction], limit: int = LIMITS.TOP_ACCOUNTS) -> list[dict]:
        """The user's own accounts, busiest first."""
        if not transactions:
            return []

        return (
            seq(self._countable(transactions))                # every purchase the user made
            .group_by(lambda purchase: purchase.accountId)        # one pile per account it came from
            .select(self._summarise_account)                      # each pile becomes one summary line
            .sorted(key=lambda row: row["accountId"] or "")       # settle ties by account id
            .sorted(key=self._by_totals, reverse=True)            # then put the busiest account on top
            .take(limit)                                          # keep only the leading few
            .to_list()                                            # hand back a plain list
        )

    def _summarise_account(self, group: tuple) -> dict:
        """Turn one pile of same-account purchases into a single summary line."""
        account_id, purchases = group
        return {
            "accountId": account_id,
            "accountNumber": purchases[0].accountNumber,
            "total_count": self._purchase_count(purchases),
            "total_amount": seq(purchases).sum(self._value),
        }

    # ── Which shops take the user's money? ────────────────────────────────────

    def top_spending_stores(self, transactions: list[Transaction], limit: int = LIMITS.TOP_STORES) -> list[dict]:
        """The shops the user spends the most at, each broken down by the account used."""
        if not transactions:
            return []

        # First work out, for every shop-and-account pairing, how much went through it.
        per_shop_and_account = (
            seq(self._countable(transactions))                            # every purchase the user made
            .group_by(lambda purchase: (self._merchant_of(purchase),          # one pile per shop
                                        purchase.accountNumber))              #   and account together
            .select(self._summarise_shop_account_pair)                        # each pile becomes one line
            .sorted(key=lambda row: (row["normalized_merchantName"],          # settle ties by shop name
                                     row["accountNumber"] or ""))             #   then account number
            .sorted(key=self._by_transactions, reverse=True)                  # then busiest pairing on top
            .to_list()
        )

        # Then fold those lines together so each shop appears once, with its accounts nested inside.
        return (
            seq(per_shop_and_account)                                          # the shop-and-account lines
            .group_by(lambda row: row["normalized_merchantName"])              # regroup them per shop
            .select(self._summarise_shop)                                      # each shop becomes one entry
            .sorted(key=self._by_transactions, reverse=True)                   # busiest shop on top
            .take(limit)                                                       # keep only the leading few
            .to_list()                                                         # hand back a plain list
        )

    def _summarise_shop_account_pair(self, group: tuple) -> dict:
        """Turn one pile of same-shop, same-account purchases into a single line."""
        (merchant_name, account_number), purchases = group
        return {
            "normalized_merchantName": merchant_name,
            "accountNumber": account_number,
            "transaction_count": self._purchase_count(purchases),
            "transaction_amount": seq(purchases).sum(self._value),
        }

    def _summarise_shop(self, group: tuple) -> dict:
        """Turn one shop's per-account lines into a single entry with the accounts nested inside."""
        merchant_name, rows = group
        return {
            "normalized_merchantName": merchant_name,
            "transaction_count": seq(rows).sum(lambda row: row["transaction_count"]),
            "transaction_amount": seq(rows).sum(lambda row: row["transaction_amount"]),
            "spend_by_account": (
                seq(rows)                                                  # this shop's per-account lines
                .select(lambda row: {                                      # renamed for the client
                    "accountNumber": row["accountNumber"],
                    "account_total_count": row["transaction_count"],
                    "account_total_amount": row["transaction_amount"],
                })
                .sorted(key=lambda row: (row["account_total_count"],       # busiest account first
                                         row["account_total_amount"]), reverse=True)
                .to_list()
            ),
        }

    # ── When does the user spend? ─────────────────────────────────────────────

    def spending_by_day_of_week(self, transactions: list[Transaction]) -> list[dict]:
        """How much the user spends on each day of the week, Sunday through Saturday."""
        spent_on = (
            seq(self._countable(transactions))                 # every purchase the user made
            .where(lambda purchase: self._date_of(purchase))       # those we know the date of
            .group_by(self._day_name_of)                           # one pile per weekday
            .map(lambda group: (group[0],                          # weekday ->
                                seq(group[1]).sum(self._value)))  # money spent that day
            .to_dict()
        )

        # Always return all seven days, so a quiet Tuesday still shows up as zero.
        return [{"day": day, "total_amount": spent_on.get(day, 0.0)} for day in DAY_NAMES]

    def _day_name_of(self, transaction: Transaction) -> str:
        """Which weekday this purchase landed on."""
        return DAY_NAMES[(self._date_of(transaction).weekday() + 1) % 7]

    def spending_difference_between_two_periods(self, transactions: list[Transaction], days: int) -> dict:
        """
        Whether the bank billed the user more or less than it did in the run-up to this period.

        The bank figure rather than what was bought, so this reads against the same number as
        the headline total. A coupon counts zero on both sides: comparing two periods on money
        that never left the account would move the bars for a month the user paid nothing extra.
        """
        cutoff = (datetime.utcnow() - timedelta(days=days)).date()
        dated_purchases = seq(self._countable(transactions)).where(lambda purchase: self._date_of(purchase))

        current_total = (
            dated_purchases                                                    # every dated purchase
            .where(lambda purchase: self._date_of(purchase) >= cutoff)         # the recent stretch
            .sum(self._spend)                                                  # as the bank billed it
        )
        previous_total = (
            dated_purchases                                                    # every dated purchase
            .where(lambda purchase: self._date_of(purchase) < cutoff)          # the stretch before that
            .sum(self._spend)                                                  # as the bank billed it
        )

        return {
            "current_period_total": current_total,
            "previous_period_total": previous_total,
            "difference": current_total - previous_total,
        }

    # ── How much did the user save? ───────────────────────────────────────────

    def spending_total(self, transactions: list[Transaction]) -> dict:
        """
        What the bank statement shows over this period, and what it is made of.

        Not the sum of the breakdowns elsewhere. Those answer "what does the user buy" and count
        a coupon purchase at its full worth; this one answers "what did it cost", where a coupon
        cost nothing because no money left the account.
        """
        countable = self._countable(transactions)
        return {
            "total_amount": self.amount_service.spend(countable),
            "purchase_count": self._purchase_count(countable),
            "breakdown": self.amount_service.spend_breakdown(countable),
            "mix": self.amount_service.mix(countable),
        }

    def spending_saved(self, transactions: list[Transaction]) -> dict:
        """
        Every shekel the user did not have to pay, and which kind of discount did it.

        Refunds are not here. The feed reports a returned purchase and a cashback identically,
        so counting either as a saving would count both — see `TransactionAmountService.saved`.
        """
        countable = self._countable(transactions)
        return {
            "total_amount": self.amount_service.savings(countable),
            "breakdown": self.amount_service.savings_breakdown(countable),
        }

    def savings_exclusions(self, transactions: list[Transaction]) -> dict[str, int]:
        """How many rows of each kind, for the caller to log."""
        return self.amount_service.kind_census(transactions)

    def spending_saved_by_account(self, transactions: list[Transaction]) -> list[dict]:
        """The same savings total, split by which account earned it."""
        return (
            seq(transactions)                                              # every purchase the user made
            .where(lambda purchase: purchase.accountId)                    # those tied to a known account
            .group_by(lambda purchase: purchase.accountId)                 # one pile per account
            .select(self._summarise_account_savings)                       # each pile becomes one line
            .sorted(key=lambda row: row["total_saved"], reverse=True)      # biggest saver on top
            .to_list()                                                     # hand back a plain list
        )

    def _summarise_account_savings(self, group: tuple) -> dict:
        """Turn one account's purchases into its savings total."""
        account_id, purchases = group
        return {
            "accountId": account_id,
            "accountNumber": purchases[0].accountNumber,
            "total_saved": seq(purchases).sum(self._saved),
        }

    # ── What could the user have saved elsewhere? ────────────────────────

    def _shops_for(self, transaction: Transaction, user_club_ids: List[str] | None) -> list:
        """
        The deal-running shops this purchase could have earned a coupon at.

        Matched on the shop's *name* rather than its category. Category matching answered a
        different question — "name me any shop that sells this kind of thing" — and with 3,641
        deal-running shops filed under SHOPPING_OTHER alone, the answer was an arbitrary ten
        with nothing to do with where the user actually shopped.

        Shops outside the user's clubs are dropped: the deal exists, but they cannot use it.
        """
        matches = self.reference_data_repository.find_deal_shops(
            transaction.merchantName,
            (transaction.merchantAddress.townName if transaction.merchantAddress else None),
            self._category_of(transaction),
        )

        member_of = set(user_club_ids) if user_club_ids is not None else None
        kept = []
        for match in matches:
            if match.band not in SURFACEABLE:
                continue
            clubs = self.reference_data_repository.clubs_for_identity(match.identity)
            if member_of is not None:
                clubs = [club_id for club_id in clubs if club_id in member_of]
            if not clubs:
                continue
            kept.append((match, clubs))
        return kept

    # ── The savings answer, in the shape the screen renders ─────────────────

    def savings_opportunities(
        self, transactions: list[Transaction], user_club_ids: List[str] | None = None
    ) -> SavingsAnswerSchema:
        """
        What the user missed, and what they already took, over these purchases.

        **Missed** is everything that is not a coupon and could have been one: a regular or
        statement purchase whose merchant matches a deal-running shop in one of their clubs.
        It is counted at what the bank billed. Every purchase is assigned to its *strongest*
        match and appears under that band only, so the three band subtotals sum to the total
        exactly — reported per shop, a single coffee matching a café and two lookalikes was
        counted three times and the tabs added up to more than the headline.

        **Applied** is every discount that actually landed: a coupon at the whole price it
        covered, a statement at the gap between what was asked and what was billed. Neither
        needs a shop match — the discount is evidence in itself.

        A statement purchase is in both, at different amounts. It took a statement discount and
        could still have used a coupon, so it is a saving made *and* a saving missed.
        """
        empty = SavingsAnswerSchema(
            missed=MissedSavingsSchema(total_amount=0.0, purchase_count=0, bands=[]),
            applied=AppliedSavingsSchema(total_amount=0.0, purchase_count=0, merchants=[]),
        )
        if not transactions:
            return empty

        purchases = [t for t in self.amount_service.purchases_only(transactions) if t.id]

        missed_rows = []
        for transaction in purchases:
            if self.amount_service.kind_of(transaction) == COUPON:
                continue
            shops = self._shops_for(transaction, user_club_ids)
            if not shops:
                continue
            best = min(shops, key=lambda pair: _BAND_ORDER[pair[0].band])[0].band
            missed_rows.append((transaction, best, shops))

        applied_rows = [
            (transaction, self.amount_service.kind_of(transaction), self._shops_for(transaction, user_club_ids))
            for transaction in purchases
            if self.amount_service.saved(transaction) > 0
        ]

        bands = [
            self._band_of(band, [row for row in missed_rows if row[1] == band])
            for band in _BANDS_BY_CONFIDENCE
            if any(row[1] == band for row in missed_rows)
        ]

        applied_merchants = self._merchants_from(applied_rows, "", self.amount_service.saved)
        answer = SavingsAnswerSchema(
            missed=MissedSavingsSchema(
                total_amount=sum(band.total_amount for band in bands),
                purchase_count=sum(band.purchase_count for band in bands),
                bands=bands,
            ),
            applied=AppliedSavingsSchema(
                total_amount=sum(merchant.amount for merchant in applied_merchants),
                purchase_count=sum(merchant.purchase_count for merchant in applied_merchants),
                merchants=applied_merchants,
            ),
        )

        logger.info(
            "Savings opportunities calculated",
            extra={
                "reason": "Batch processing complete",
                "extra_data": {
                    "transaction_count": len(transactions),
                    "missed_amount": answer.missed.total_amount,
                    "missed_purchases": answer.missed.purchase_count,
                    "applied_amount": answer.applied.total_amount,
                    "applied_purchases": answer.applied.purchase_count,
                    "by_band": {band.band: band.purchase_count for band in answer.missed.bands},
                },
            },
        )
        return answer

    def _band_of(self, band: str, rows: list[tuple]) -> SavingsBandSchema:
        """One band's merchants, totalled from the merchants actually returned."""
        merchants = self._merchants_from(rows, band, self.amount_service.paid)
        return SavingsBandSchema(
            band=band,
            total_amount=sum(merchant.amount for merchant in merchants),
            purchase_count=sum(merchant.purchase_count for merchant in merchants),
            merchants=merchants,
        )

    def _merchants_from(self, rows: list[tuple], band: str, amount_of) -> List[SavingsMerchantSchema]:
        """
        Gather purchases into the merchants the screen shows, biggest first.

        The user thinks in terms of what they bought, not which catalogue row it matched, so a
        merchant carries every shop its purchases matched rather than the other way round. A
        purchase reaches this exactly once, so nothing here has to de-duplicate.
        """
        gathered: Dict[str, dict] = {}
        for transaction, source, shops in rows:
            entry = gathered.setdefault(
                self._merchant_of(transaction),
                {"purchases": [], "amount": 0.0, "shops": {}, "clubs": set(), "accounts": [], "sources": set()},
            )
            entry["sources"].add(source)
            entry["purchases"].append(transaction)
            entry["amount"] += amount_of(transaction)
            if transaction.accountId and transaction.accountId not in entry["accounts"]:
                entry["accounts"].append(transaction.accountId)
            for match, clubs in shops:
                # Keep the most confident reading of a shop the user hit more than once.
                existing = entry["shops"].get(match.identity.store_id)
                if existing is None or _BAND_ORDER[match.band] < _BAND_ORDER[existing[0].band]:
                    entry["shops"][match.identity.store_id] = (match, clubs)
                entry["clubs"].update(clubs)

        merchants = [self._describe_merchant(name, entry, band, amount_of) for name, entry in gathered.items()]
        # Most money first: the point of the list is what is at stake at each place.
        merchants.sort(key=lambda merchant: (-merchant.amount, merchant.merchant_name))
        return merchants[: SHOP_MATCH.MAX_SHOPS]

    def _describe_merchant(self, name: str, entry: dict, band: str, amount_of) -> SavingsMerchantSchema:
        """Turn one merchant's gathered purchases into the shape the client renders."""
        shops = sorted(entry["shops"].values(), key=lambda pair: _BAND_ORDER[pair[0].band])
        return SavingsMerchantSchema(
            merchant_name=name,
            band=band,
            purchase_count=len(entry["purchases"]),
            amount=entry["amount"],
            deal_count=sum(len(match.identity.deals) for match, _ in shops),
            account_ids=entry["accounts"],
            # Named only for a missed purchase, where the club is the deal the user could have
            # claimed. On an applied one it would read as "this club paid", and the feed cannot
            # say that: a blank charge means no money left the account, not whose card it was.
            # The shops below still carry their own clubs, which is a fact about the shop.
            club_ids=sorted(entry["clubs"]) if band else [],
            sources=sorted(source for source in entry["sources"] if source),
            shops=[
                SavingsShopSchema(
                    store_id=match.identity.store_id,
                    store_name=match.identity.name,
                    match_band=match.band,
                    is_same_store=match.is_confident,
                    deal_count=len(match.identity.deals),
                    deal_titles=[
                        deal.title for deal in match.identity.deals[:3] if getattr(deal, "title", None)
                    ],
                    club_ids=sorted(clubs),
                    also_known_as=match.identity.names[1:],
                )
                for match, clubs in shops[:MAX_SHOPS_PER_MERCHANT]
            ],
            purchases=[
                SavingsPurchaseSchema(
                    transaction_id=transaction.id,
                    amount=amount_of(transaction),
                    source=self.amount_service.kind_of(transaction),
                    date=str(self._date_of(transaction)) if self._date_of(transaction) else None,
                    account_id=transaction.accountId,
                )
                for transaction in entry["purchases"]
            ],
        )

    # ── Orchestration ─────────────────────────────────────────────────────────
    # Fetch the user's transactions, run one of the calculations above, announce the result.

    async def _require_user(self, email: str):
        """
        Ensure the user exists in the Lessley DB before doing any work.
        Returns the user document, or raises HTTP 404 (via UserRepository) if not registered.
        """
        if self.user_repository is None:
            return None
        return await self.user_repository.get_user(email)

    @staticmethod
    def extract_mcc_tags(categories: list) -> list[str]:
        """
        Flatten the user's categories to the de-duplicated tag list stored on their profile.

        Public because the command handler publishes these tags: the calculation itself must
        stay free of side effects so the client-facing GET can share it without writing.
        """
        tags: list[str] = []
        for category in categories or []:
            for code in category.get("mcc_codes") or []:
                code_str = str(code).strip()
                if code_str and code_str != "N/A" and code_str not in tags:
                    tags.append(code_str)
        return tags

    async def _transactions_for(
        self, user_id: str, time_filter: bool, days: int, use_mock: bool, sort: bool = False
    ) -> list[Transaction]:
        """Fetch the user's purchases — from the mock file when asked, otherwise from Open Finance."""
        if use_mock:
            return self.files_service.read_json("transactions_roee_all.json")

        transactions = await self.open_finance_service.get_user_transactions_async(user_id, time_filter, days)
        if sort:
            transactions = self.open_finance_service.sort_transactions(transactions)
        return transactions

    async def calculate_user_categories_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> list[dict]:
        """
        Calculate the user's spending categories and return them. Nothing is published here.

        Two callers share this: the client-facing GET, which only displays the answer, and the
        Gateway command handler, which publishes the derived tags for the Gateway to persist.
        Publishing from inside the calculation made a read request write to the user's profile
        — the GET returned immediately while the write travelled the bus behind it, so a client
        could act on categories the database did not have yet. The handler owns that step now.
        """
        logger.info(
            "Service method called",
            extra={
                "reason": "Method invocation",
                "extra_data": {"user_id": user_id, "time_filter": time_filter, "days": days, "use_mock": use_mock},
            },
        )

        try:
            # Task 1: stop early (HTTP 404) if the user is not registered in Lessley.
            user = await self._require_user(user_id)

            transactions = await self._transactions_for(user_id, time_filter, days, use_mock)
            categories = self.top_spending_categories(transactions)

            # Process 2: keep only the top (Len - X%) categories based on the user's match level.
            matching_score = user.get("MatchingScore") if user else None
            categories = trim_categories_by_match_level(categories, matching_score)

            logger.info(
                "User categories calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {"user_id": user_id, "category_count": len(categories)},
                },
            )
            return categories
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise

    async def calculate_top_accounts_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> list[dict]:
        """
        Calculates top accounts based on transactions.
        """
        logger.info(
            "Service method called",
            extra={
                "reason": "Method invocation",
                "extra_data": {"user_id": user_id, "time_filter": time_filter, "days": days, "use_mock": use_mock},
            },
        )

        try:
            transactions = await self._transactions_for(user_id, time_filter, days, use_mock)
            accounts = self.top_spending_accounts(transactions)

            logger.info(
                "Top accounts calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {"user_id": user_id, "account_count": len(accounts)},
                },
            )
            return accounts
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise

    async def calculate_top_stores_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> list[dict]:
        """
        Calculates top stores based on transactions.
        """
        logger.info(
            "Service method called",
            extra={
                "reason": "Method invocation",
                "extra_data": {"user_id": user_id, "time_filter": time_filter, "days": days, "use_mock": use_mock},
            },
        )

        try:
            transactions = await self._transactions_for(user_id, time_filter, days, use_mock)
            stores = self.top_spending_stores(transactions)

            logger.info(
                "Top stores calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {"user_id": user_id, "store_count": len(stores)},
                },
            )
            return stores
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise

    async def calculate_spending_by_day_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> list[dict]:
        """
        Calculates total spending per day of week (Sunday..Saturday) from transactions.
        """
        logger.info(
            "Service method called",
            extra={
                "reason": "Method invocation",
                "extra_data": {"user_id": user_id, "time_filter": time_filter, "days": days, "use_mock": use_mock},
            },
        )

        try:
            transactions = await self._transactions_for(user_id, time_filter, days, use_mock)
            spending_by_day = self.spending_by_day_of_week(transactions)

            logger.info(
                "Spending by day of week calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {"user_id": user_id, "day_count": len(spending_by_day)},
                },
            )
            return spending_by_day
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise

    async def calculate_spending_difference_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> dict:
        """
        Calculates the spending difference between the current period (last `days` days) and the
        previous period of equal length, from a single fetch covering both periods.
        """
        logger.info(
            "Service method called",
            extra={
                "reason": "Method invocation",
                "extra_data": {"user_id": user_id, "time_filter": time_filter, "days": days, "use_mock": use_mock},
            },
        )

        try:
            # One fetch covering both periods, then split by date on our side.
            transactions = await self._transactions_for(user_id, time_filter, days * 2, use_mock)
            difference = self.spending_difference_between_two_periods(transactions, days)

            logger.info(
                "Spending difference between two periods calculated successfully",
                extra={"reason": "Business logic complete", "extra_data": {"user_id": user_id, **difference}},
            )
            return difference
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise

    async def calculate_spending_total_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> dict:
        """
        Calculates the headline spending total: money out, less money that came back.
        """
        logger.info(
            "Service method called",
            extra={
                "reason": "Method invocation",
                "extra_data": {"user_id": user_id, "time_filter": time_filter, "days": days, "use_mock": use_mock},
            },
        )

        try:
            transactions = await self._transactions_for(user_id, time_filter, days, use_mock)
            total = self.spending_total(transactions)

            logger.info(
                "Spending total calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {"user_id": user_id, **total},
                },
            )
            return total
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise

    async def calculate_spending_saved_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> dict:
        """
        Calculates total spending saved (abs difference between charged and original amounts).
        """
        logger.info(
            "Service method called",
            extra={
                "reason": "Method invocation",
                "extra_data": {"user_id": user_id, "time_filter": time_filter, "days": days, "use_mock": use_mock},
            },
        )

        try:
            transactions = await self._transactions_for(user_id, time_filter, days, use_mock)
            saved = self.spending_saved(transactions)

            logger.info(
                "Spending saved calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {
                        "user_id": user_id,
                        "total_saved": saved["total_amount"],
                        "kinds": self.savings_exclusions(transactions),
                    },
                },
            )
            return saved
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise

    async def calculate_spending_saved_by_account_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> list[dict]:
        """
        Calculates total spending saved (abs difference between charged and original amounts),
        grouped by account.
        """
        logger.info(
            "Service method called",
            extra={
                "reason": "Method invocation",
                "extra_data": {"user_id": user_id, "time_filter": time_filter, "days": days, "use_mock": use_mock},
            },
        )

        try:
            transactions = await self._transactions_for(user_id, time_filter, days, use_mock)
            saved_by_account = self.spending_saved_by_account(transactions)

            logger.info(
                "Spending saved by account calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {
                        "user_id": user_id,
                        "account_count": len(saved_by_account),
                        "excluded": self.savings_exclusions(transactions),
                    },
                },
            )
            return saved_by_account
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise

    async def calculate_savings_opportunities_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> SavingsAnswerSchema:
        """
        The savings picture for a period: what was missed, and what the club card already took.

        One call rather than two, because both sides come out of the same matching pass. Asking
        for them separately would let the two answers drift apart between requests, and a
        purchase could plausibly appear as missed in one and already-taken in the other.
        """
        logger.info(
            "Service method called",
            extra={
                "reason": "Method invocation",
                "extra_data": {"user_id": user_id, "time_filter": time_filter, "days": days, "use_mock": use_mock},
            },
        )

        try:
            transactions = await self._transactions_for(user_id, time_filter, days, use_mock, sort=True)
            user_club_ids = await self.user_repository.get_user_clubs(user_id)
            answer = self.savings_opportunities(transactions, user_club_ids=user_club_ids)

            logger.info(
                "Savings opportunities calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {
                        "user_id": user_id,
                        "missed_purchases": answer.missed.purchase_count,
                        "applied_purchases": answer.applied.purchase_count,
                    },
                },
            )
            return answer
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise
