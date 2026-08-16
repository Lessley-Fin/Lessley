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
from config.constants import LIMITS, SHOP_MATCH
from models.transaction import Transaction
from services.utils.store_similarity import EXACT, SIMILAR, STRONG, SURFACEABLE, WEAK
from routers.responses import (
    TransactionInsightSchema,
    MissedShopPurchaseSchema,
    MissedShopSchema,
    MissedStoreDiscountSchema,
    MissedStoreSchema,
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
    ):
        self.open_finance_service = open_finance_service
        self.files_service = files_service
        self.publisher_service = publisher_service
        self.user_repository = user_repository
        self.reference_data_repository = reference_data_repository
        self.mcc_service = mcc_service

    # ── Reading a single purchase ─────────────────────────────────────────────
    # Small helpers so the chains below can stay one idea per line.

    @staticmethod
    def _date_of(transaction: Transaction):
        """When the purchase happened — whichever date the bank actually gave us."""
        if not transaction.date:
            return None
        return transaction.date.transactionDate or transaction.date.bookingDate or transaction.date.valueDate

    @staticmethod
    def _amount_spent(transaction: Transaction) -> float:
        """How much money left the account, as a positive number."""
        amount = transaction.amount
        if amount and amount.chargedAmount and amount.chargedAmount.amount is not None:
            return abs(amount.chargedAmount.amount)
        if amount and amount.originalAmount and amount.originalAmount.amount is not None:
            return abs(amount.originalAmount.amount)
        return 0.0

    @staticmethod
    def _amount_charged(transaction: Transaction) -> float:
        """The billed figure exactly as the bank reported it — sign and all."""
        amount = transaction.amount
        if amount and amount.chargedAmount and amount.chargedAmount.amount is not None:
            return amount.chargedAmount.amount
        if amount and amount.originalAmount and amount.originalAmount.amount is not None:
            return amount.originalAmount.amount
        return 0.0

    @staticmethod
    def _amount_saved(transaction: Transaction) -> float:
        """The gap between the sticker price and what was actually charged."""
        amount = transaction.amount
        charged = amount.chargedAmount.amount if amount and amount.chargedAmount else None
        original = amount.originalAmount.amount if amount and amount.originalAmount else None
        return abs((charged or 0.0) - (original or 0.0))

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
            seq(transactions)                                  # every purchase the user made
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
            "total_count": len(purchases),
            "total_amount": seq(purchases).sum(self._amount_spent),
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
            seq(transactions)                                     # every purchase the user made
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
            "total_count": len(purchases),
            "total_amount": seq(purchases).sum(self._amount_spent),
        }

    # ── Which shops take the user's money? ────────────────────────────────────

    def top_spending_stores(self, transactions: list[Transaction], limit: int = LIMITS.TOP_STORES) -> list[dict]:
        """The shops the user spends the most at, each broken down by the account used."""
        if not transactions:
            return []

        # First work out, for every shop-and-account pairing, how much went through it.
        per_shop_and_account = (
            seq(transactions)                                                 # every purchase the user made
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
            "transaction_count": len(purchases),
            "transaction_amount": seq(purchases).sum(self._amount_spent),
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
            seq(transactions)                                      # every purchase the user made
            .where(lambda purchase: self._date_of(purchase))       # those we know the date of
            .group_by(self._day_name_of)                           # one pile per weekday
            .map(lambda group: (group[0],                          # weekday ->
                                seq(group[1]).sum(self._amount_spent)))  # money spent that day
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
        dated_purchases = seq(transactions).where(lambda purchase: self._date_of(purchase))

        current_total = (
            dated_purchases                                                    # every dated purchase
            .where(lambda purchase: self._date_of(purchase) >= cutoff)         # the recent stretch
            .sum(self._amount_spent)                                           # added up
        )
        previous_total = (
            dated_purchases                                                    # every dated purchase
            .where(lambda purchase: self._date_of(purchase) < cutoff)          # the stretch before that
            .sum(self._amount_spent)                                           # added up
        )

        return {
            "current_period_total": current_total,
            "previous_period_total": previous_total,
            "difference": current_total - previous_total,
        }

    # ── How much did the user save? ───────────────────────────────────────────

    def spending_saved(self, transactions: list[Transaction]) -> float:
        """Total money the user did not have to pay, thanks to discounts."""
        return (
            seq(transactions)          # every purchase the user made
            .sum(self._amount_saved)   # add up what each one knocked off the price
        )

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

    # ── What could the user have saved elsewhere? ─────────────────────────────

    def missed_savings(
        self, transactions: list[Transaction], user_club_ids: List[str] | None = None
    ) -> list[TransactionInsightSchema]:
        """
        For each purchase, the shops in the user's clubs that were running a deal on the
        same kind of thing — the money that was on the table and left there.
        """
        if not transactions:
            return []

        insights = (
            seq(transactions)                                                  # every purchase the user made
            .where(lambda purchase: purchase.id and purchase.categoryCode)     # those we can actually analyse
            .select(lambda purchase: self._missed_savings_for(purchase, user_club_ids))
            .to_list()                                                         # hand back a plain list
        )

        logger.info(
            "Missed savings analysis completed",
            extra={
                "reason": "Batch processing complete",
                "extra_data": {
                    "transaction_count": len(transactions),
                    "processed_count": len(insights),
                    "transactions_with_deals": seq(insights).count(lambda insight: insight.had_discount),
                    "total_alternative_stores": seq(insights).sum(
                        lambda insight: seq(insight.missed_store_discont).sum(lambda missed: missed.store_count)
                    ),
                    "insights_returned": len(insights),
                },
            },
        )
        return insights

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

    def _missed_savings_for(
        self, transaction: Transaction, user_club_ids: List[str] | None
    ) -> TransactionInsightSchema:
        """Work out what the user missed on this one purchase."""
        shops = self._shops_for(transaction, user_club_ids)

        by_club: Dict[str, List] = {}
        for match, clubs in shops:
            for club_id in clubs:
                by_club.setdefault(club_id, []).append(match.identity)

        return TransactionInsightSchema(
            transaction_id=transaction.id,
            had_discount=len(shops) > 0,
            missed_store_discont=self._describe_missed_stores(by_club),
            store_name=transaction.merchantName or "N/A",
            mcc_code=self.mcc_service.get_mcc_by_id(transaction.categoryCode),
            mcc_description=self._category_of(transaction),
            amount=self._amount_charged(transaction),
        )

    def _describe_missed_stores(self, stores_by_club: Dict[str, List]) -> List[MissedStoreDiscountSchema]:
        """Turn the shops-per-club map into the shape the client expects."""
        return (
            seq(stores_by_club.items())                                             # each club and its shops
            .where(lambda entry: self.reference_data_repository.get_club(entry[0]))  # skip clubs we cannot name
            .select(lambda entry: MissedStoreDiscountSchema(
                club_id=entry[0],
                missed_store=[
                    MissedStoreSchema(store_id=shop.store_id, store_name=shop.name)
                    for shop in entry[1][:MAX_ALTERNATIVE_STORES_PER_CLUB]
                ],
                store_count=min(len(entry[1]), MAX_ALTERNATIVE_STORES_PER_CLUB),
            ))
            .to_list()
        )

    # ── The same answer, gathered by shop instead of by purchase ──────────────

    def missed_savings_by_store(
        self, transactions: list[Transaction], user_club_ids: List[str] | None = None
    ) -> List[MissedShopSchema]:
        """
        The shops that were running a deal, each with the purchases it could have covered.

        The same matching as `missed_savings`, gathered the other way round. A user does not
        want to hear about one coffee three separate times — they want to hear that קפה קפה
        has a coupon and they have bought coffee three times this month.
        """
        if not transactions:
            return []

        gathered: Dict[str, dict] = {}
        for transaction in transactions:
            if not transaction.id:
                continue
            for match, clubs in self._shops_for(transaction, user_club_ids):
                entry = gathered.setdefault(
                    match.identity.store_id,
                    {"match": match, "clubs": set(), "purchases": [], "amount": 0.0},
                )
                # Keep the most confident reading of this shop across all the purchases.
                if _BAND_ORDER[match.band] < _BAND_ORDER[entry["match"].band]:
                    entry["match"] = match
                entry["clubs"].update(clubs)
                entry["purchases"].append(transaction)
                entry["amount"] += self._amount_spent(transaction)

        shops = [self._describe_shop(entry) for entry in gathered.values()]

        # Band first, then money. Sorting on money alone lets a single coffee produce a dozen
        # lookalike cafés that crowd a shop the user demonstrably visited out of the answer —
        # and being told about the shop you actually used is worth more than any number of
        # shops merely like it.
        shops.sort(key=lambda shop: (_BAND_ORDER[shop.match_band], -shop.covered_amount, shop.store_name))
        shops = shops[: SHOP_MATCH.MAX_SHOPS]

        logger.info(
            "Missed savings by store completed",
            extra={
                "reason": "Batch processing complete",
                "extra_data": {
                    "transaction_count": len(transactions),
                    "shops_found": len(shops),
                    "same_store_shops": sum(1 for shop in shops if shop.is_same_store),
                },
            },
        )
        return shops

    def _describe_shop(self, entry: dict) -> MissedShopSchema:
        """Turn one shop's gathered purchases into the shape the client expects."""
        match = entry["match"]
        identity = match.identity
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
            purchases=[
                MissedShopPurchaseSchema(
                    transaction_id=transaction.id,
                    merchant_name=self._merchant_of(transaction),
                    amount=self._amount_spent(transaction),
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
    def _extract_mcc_tags(categories: list) -> list[str]:
        """
        Flatten the user's categories to a de-duplicated list of MCC codes (as strings).
        Categories are represented system-wide by their MCC code ("MCC string labels").
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
        Calculates user categories from spending transactions, then publishes the derived
        tags to the Gateway via publisher_service so they are stored on the user profile
        and become readable through UserRepository by other services (task 9).
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

            # Task 5: send the recalculated categories (MCC codes) to the Gateway over HTTP so it
            # updates the user's profile (and SignalR groups). Other services read them back via
            # UserRepository instead of re-running this calculation.
            mcc_tags = self._extract_mcc_tags(categories)
            if self.publisher_service and mcc_tags:
                await self.publisher_service.publish_user_tag_assigned(user_id, mcc_tags)

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
                    "extra_data": {"user_id": user_id, "total_saved": total_saved},
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
                    "extra_data": {"user_id": user_id, "account_count": len(saved_by_account)},
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

    async def calculate_missed_savings_async(
        self, user_id: str, time_filter: bool, days: int = LIMITS.DAYS, use_mock: bool = False
    ) -> list[TransactionInsightSchema]:
        """
        Analyzes user transactions to identify missed savings opportunities.
        For each transaction, identifies alternative stores with active deals for the same MCC category.

        Args:
            user_id: User ID for transaction retrieval
            time_filter: Whether to apply time-based filtering
            days: Number of past days to analyze
            use_mock: Whether to use mock data

        Returns:
            List of TransactionInsightSchema objects with missed savings analysis
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
            insights = self.missed_savings(transactions, user_club_ids=user_club_ids)

            if self.publisher_service:
                serialized = [i.dict() if hasattr(i, "dict") else i for i in insights]
                await self.publisher_service.publish_missed_savings_calculated(user_id, serialized)

            logger.info(
                "Missed savings calculated successfully",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {"user_id": user_id, "insight_count": len(insights)},
                },
            )
            return insights
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
            shops = self.missed_savings_by_store(transactions, user_club_ids=user_club_ids)

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
