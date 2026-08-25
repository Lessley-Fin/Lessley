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
from config.constants import BENEFIT_CARDS, LIMITS, SHOP_MATCH
from models.transaction import Transaction
from services.utils.store_similarity import EXACT, SIMILAR, STRONG, SURFACEABLE, WEAK
from routers.responses import (
    MissedShopPurchaseSchema,
    MissedShopSchema,
)


logger = logging.getLogger(__name__)

# Sunday first, because that is how the week is displayed to the user.
DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# We never show a user more than this many alternative shops for a single club.
MAX_ALTERNATIVE_STORES_PER_CLUB = 10

# Most confident first, for picking one reading of a shop over another.
_BAND_ORDER = {EXACT: 0, STRONG: 1, SIMILAR: 2, WEAK: 3}


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

    def _purchase_amount(self, transaction: Transaction) -> float:
        """
        What this purchase was worth, signed so a refund cancels what it reverses.

        Every breakdown below sums this rather than `amount_spent`, because they answer "what
        does the user buy" and not "what did it cost them". A voucher purchase is worth its full
        price here even though no money left the bank — otherwise a card used only for vouchers
        reports no activity at all.
        """
        return self.amount_service.net_purchase_value(transaction)

    def _purchase_count(self, transactions: list[Transaction]) -> int:
        """How many of these are the user buying something. A refund is not a visit."""
        return self.amount_service.purchase_count(transactions)

    def _amount_saved(self, transaction: Transaction) -> float:
        """How much this purchase actually knocked off the price."""
        return self.amount_service.amount_saved(transaction)

    def _countable(self, transactions: list[Transaction]) -> list[Transaction]:
        """Everything not flagged a duplicate. Refunds stay in, so the sums can net them out."""
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
            "total_amount": seq(purchases).sum(self._purchase_amount),
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
            "total_amount": seq(purchases).sum(self._purchase_amount),
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
            "transaction_amount": seq(purchases).sum(self._purchase_amount),
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
                                seq(group[1]).sum(self._purchase_amount)))  # money spent that day
            .to_dict()
        )

        # Always return all seven days, so a quiet Tuesday still shows up as zero.
        return [{"day": day, "total_amount": spent_on.get(day, 0.0)} for day in DAY_NAMES]

    def _day_name_of(self, transaction: Transaction) -> str:
        """Which weekday this purchase landed on."""
        return DAY_NAMES[(self._date_of(transaction).weekday() + 1) % 7]

    def spending_difference_between_two_periods(self, transactions: list[Transaction], days: int) -> dict:
        """Whether the user spent more or less than they did in the run-up to this period."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).date()
        dated_purchases = seq(self._countable(transactions)).where(lambda purchase: self._date_of(purchase))

        current_total = (
            dated_purchases                                                    # every dated purchase
            .where(lambda purchase: self._date_of(purchase) >= cutoff)         # the recent stretch
            .sum(self._purchase_amount)                                           # added up
        )
        previous_total = (
            dated_purchases                                                    # every dated purchase
            .where(lambda purchase: self._date_of(purchase) < cutoff)          # the stretch before that
            .sum(self._purchase_amount)                                           # added up
        )

        return {
            "current_period_total": current_total,
            "previous_period_total": previous_total,
            "difference": current_total - previous_total,
        }

    # ── How much did the user save? ───────────────────────────────────────────

    def spending_total(self, transactions: list[Transaction]) -> dict:
        """
        The headline total: how much worse off the account is over this period.

        Deliberately not the sum of the breakdowns. Those answer "what does the user buy" and
        count a voucher purchase at its full worth; this one answers "what did it cost", where
        a voucher cost nothing and a refund gives money back. The two disagreeing is the point,
        not a bug — `purchase_count` says how many purchases stand behind the figure.
        """
        countable = self.amount_service.countable(transactions)
        return {
            "total_amount": self.amount_service.total_spent(countable),
            "purchase_count": self.amount_service.purchase_count(countable),
            # What the year was made of, for the client to describe rather than just total.
            "composition": self.amount_service.composition(countable),
        }

    def spending_saved(self, transactions: list[Transaction]) -> float:
        """Total money the user did not have to pay, thanks to discounts."""
        return (
            seq(transactions)          # every purchase the user made
            .sum(self._amount_saved)   # add up what each one knocked off the price
        )

    def savings_exclusions(self, transactions: list[Transaction]) -> dict[str, int]:
        """How many purchases landed in each reason, for the caller to log."""
        return self.amount_service.savings_exclusions(transactions)

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
            "total_saved": seq(purchases).sum(self._amount_saved),
        }

    # ── Which clubs already paid off? ─────────────────────────────────────────

    @staticmethod
    def _clubs_already_used(transaction: Transaction, account_products: Dict[str, str] | None) -> set[str]:
        """
        The clubs whose own benefit card paid for this purchase.

        A Hever נטען card only spends at Hever's partner shops, so a purchase charged to one
        already took the discount — it is the opposite of a missed saving. The transaction
        cannot say so on its own: it names an ``accountId`` and nothing else, and the product
        string that gives the card away lives on the accounts feed. `account_products` is that
        feed, folded to ``{accountId: product}`` by the caller.

        An empty or missing map means we simply do not know, and nothing is suppressed — the
        answer degrades to what it was before this existed rather than to silence.
        """
        if not account_products or not transaction.accountId:
            return set()

        product = (account_products.get(transaction.accountId) or "").strip().lower()
        if not product:
            return set()

        return {
            club_id
            for club_id, keywords in BENEFIT_CARDS.PRODUCT_KEYWORDS_BY_CLUB.items()
            if any(keyword.strip().lower() in product for keyword in keywords)
        }

    # ── What could the user have saved elsewhere? ─────────────────────────────

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

    # ── The same answer, gathered by shop instead of by purchase ──────────────

    def missed_savings_by_store(
        self,
        transactions: list[Transaction],
        user_club_ids: List[str] | None = None,
        account_products: Dict[str, str] | None = None,
    ) -> List[MissedShopSchema]:
        """
        The shops that were running a deal, each with the purchases it could have covered.

        The same matching as `missed_savings`, gathered the other way round. A user does not
        want to hear about one coffee three separate times — they want to hear that קפה קפה
        has a coupon and they have bought coffee three times this month.

        `account_products` is ``{accountId: product}`` off the accounts feed. It splits each
        shop's purchases in two: the ones charged to an ordinary card, which genuinely missed
        out, and the ones charged to a club's own benefit card, which already took the discount
        at the till. Both stay on the shop — a purchase that already saved is worth saying out
        loud, and hiding it would leave the user wondering why a shop they clearly use went
        missing. Pass nothing and every purchase reads as missed, exactly as it did before.
        """
        if not transactions:
            return []

        # A refunded purchase is not a reason to suggest a coupon, and a duplicate would put
        # the same purchase under the shop twice. Unlike the breakdowns above, nothing is netted
        # here — this is a list of visits, not a total.
        gathered: Dict[str, dict] = {}
        for transaction in self.amount_service.purchases_only(transactions):
            if not transaction.id:
                continue
            # Which clubs this card *is* — read once, then narrowed to each shop's own clubs.
            paid_by_club = self._clubs_already_used(transaction, account_products)
            for match, clubs in self._shops_for(transaction, user_club_ids):
                entry = gathered.setdefault(
                    match.identity.store_id,
                    {"match": match, "clubs": set(), "purchases": [], "amount": 0.0},
                )
                # Keep the most confident reading of this shop across all the purchases.
                if _BAND_ORDER[match.band] < _BAND_ORDER[entry["match"].band]:
                    entry["match"] = match
                entry["clubs"].update(clubs)
                # Only a club that carries *this* shop can have paid off at it. Without the
                # intersection a Hever card would mark a purchase committed at a shop Hever
                # does not run, and the user would lose a saving they really did miss.
                entry["purchases"].append((transaction, sorted(paid_by_club & set(clubs))))
                entry["amount"] += self.amount_service.purchase_value(transaction)

        shops = [self._describe_shop(entry) for entry in gathered.values()]

        # Band first, then money. Sorting on money alone lets a single coffee produce a dozen
        # lookalike cafés that crowd a shop the user demonstrably visited out of the answer —
        # and being told about the shop you actually used is worth more than any number of
        # shops merely like it.
        #
        # Money here means *missed* money, so a shop where every visit already saved sinks to
        # the bottom rather than crowding out one where the user is still losing out.
        shops.sort(
            key=lambda shop: (
                _BAND_ORDER[shop.match_band],
                -shop.missed_amount,
                -shop.covered_amount,
                shop.store_name,
            )
        )
        shops = shops[: SHOP_MATCH.MAX_SHOPS]

        logger.info(
            "Missed savings by store completed",
            extra={
                "reason": "Batch processing complete",
                "extra_data": {
                    "transaction_count": len(transactions),
                    "shops_found": len(shops),
                    "same_store_shops": sum(1 for shop in shops if shop.is_same_store),
                    "committed_purchases": sum(shop.committed_transaction_count for shop in shops),
                    "fully_committed_shops": sum(1 for shop in shops if shop.missed_transaction_count == 0),
                },
            },
        )
        return shops

    def _describe_shop(self, entry: dict) -> MissedShopSchema:
        """Turn one shop's gathered purchases into the shape the client expects."""
        match = entry["match"]
        identity = match.identity

        # Each purchase arrives paired with the clubs that already paid off on it. Split the
        # money the same way, so the client can lead with what was missed and still say
        # "you already saved here" about the rest.
        missed_count = missed_amount = 0
        committed_count = committed_amount = 0
        committed_clubs: set[str] = set()
        for transaction, covered_by in entry["purchases"]:
            value = self.amount_service.purchase_value(transaction)
            if covered_by:
                committed_count += 1
                committed_amount += value
                committed_clubs.update(covered_by)
            else:
                missed_count += 1
                missed_amount += value

        return MissedShopSchema(
            store_id=identity.store_id,
            store_name=identity.name,
            match_band=match.band,
            is_same_store=match.is_confident,
            deal_count=len(identity.deals),
            deal_titles=[deal.title for deal in identity.deals[:3] if getattr(deal, "title", None)],
            club_ids=sorted(entry["clubs"]),
            also_known_as=identity.names[1:],
            covered_transaction_count=len(entry["purchases"]),
            covered_amount=entry["amount"],
            missed_transaction_count=missed_count,
            missed_amount=missed_amount,
            committed_transaction_count=committed_count,
            committed_amount=committed_amount,
            committed_club_ids=sorted(committed_clubs),
            purchases=[
                MissedShopPurchaseSchema(
                    transaction_id=transaction.id,
                    merchant_name=self._merchant_of(transaction),
                    amount=self.amount_service.purchase_value(transaction),
                    date=str(self._date_of(transaction)) if self._date_of(transaction) else None,
                    account_id=transaction.accountId,
                    covered_by_club_ids=covered_by,
                )
                for transaction, covered_by in entry["purchases"]
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

    async def _account_products_for(self, user_id: str, use_mock: bool) -> Dict[str, str]:
        """
        ``{accountId: product}`` for the user's accounts — what tells a club's own benefit card
        apart from an ordinary one.

        A second call to Open Finance, because the transaction feed does not carry the product
        and the missed-savings calculation cannot ask for it on its own. Failure is swallowed
        on purpose: not knowing which card paid costs us the "you already saved here" reading,
        and that is worth far less than the whole answer. Without this the endpoint would start
        500-ing on an outage that used to be invisible to it.

        Every distinct product string is logged. Nobody has yet seen a real Hever payload, so
        ``BENEFIT_CARDS.PRODUCT_KEYWORDS_BY_CLUB`` is matching a guess at the wording — these
        logs are how that guess gets confirmed or corrected.
        """
        if use_mock:
            return {}

        try:
            accounts = await self.open_finance_service.get_user_accounts_async(user_id)
        except Exception as e:
            logger.warning(
                f"Could not read account products, treating every purchase as missed: {str(e)}",
                exc_info=e,
                extra={"reason": "Accounts unavailable", "extra_data": {"user_id": user_id}},
            )
            return {}

        products = {
            account.get("id"): account.get("product")
            for account in accounts
            if account.get("id") and account.get("product")
        }

        logger.info(
            "Account products read",
            extra={
                "reason": "Identifying club benefit cards",
                "extra_data": {
                    "user_id": user_id,
                    "account_count": len(accounts),
                    "products": sorted(set(products.values())),
                },
            },
        )
        return products

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
    ) -> float:
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
            total_saved = self.spending_saved(transactions)

            logger.info(
                "Spending saved calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {
                        "user_id": user_id,
                        "total_saved": total_saved,
                        "excluded": self.savings_exclusions(transactions),
                    },
                },
            )
            return total_saved
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

    async def calculate_missed_savings_by_store_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> List[MissedShopSchema]:
        """
        The same analysis as `calculate_missed_savings_async`, gathered by shop.

        One row per shop that runs a deal, carrying the purchases it could have covered, so
        the user reads "קפה קפה has a coupon and you bought coffee four times" rather than the
        same suggestion repeated against four separate transactions.
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
            account_products = await self._account_products_for(user_id, use_mock)
            shops = self.missed_savings_by_store(
                transactions, user_club_ids=user_club_ids, account_products=account_products
            )

            logger.info(
                "Missed savings by store calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {"user_id": user_id, "shop_count": len(shops)},
                },
            )
            return shops
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={"reason": "Service execution failure", "extra_data": {"user_id": user_id}},
            )
            raise
