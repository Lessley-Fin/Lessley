import logging
from typing import Dict, List

from functional import seq

from models.db.entities import Club, Deal, Store, StoreAlias
from services.utils.place_vocabulary import PlaceVocabulary
from services.utils.store_identity import StoreIdentity, build_identities
from services.utils.store_index import StoreIndex
from services.utils.store_name_matcher import NO_MATCH, StoreMatch, match_store
from services.utils.store_similarity import DealShopFinder, ShopMatch

logger = logging.getLogger(__name__)


class ReferenceDataRepository:
    """
    Holds the shop-side reference data — clubs, stores and deals — in memory.

    This is the only place that talks to MongoDB for these three collections. Everything is
    kept in dictionaries, because the insight calculations look the same records up thousands
    of times per request and must never wait on the database.

    The cache is rebuilt on a timer (see ``refresh_reference_data`` in main.py) rather than
    only at startup: deals are scraped continuously, and a cache loaded once means every deal
    added after boot stays invisible to missed-savings and club matching until the process
    restarts — a failure with no symptom except quietly thinner results.

    A rebuild publishes its snapshot in a single block at the end of ``load_async``. Readers
    take no lock, so a half-rebuilt cache must never be observable, and a rebuild that throws
    must leave the previous snapshot serving.
    """

    def __init__(self):
        self._clubs: Dict[str, Club] = {}  # club id            -> the club
        self._stores: Dict[str, Store] = {}  # store id           -> the store
        self._deals_by_id: Dict[str, Deal] = {}  # deal id            -> the deal
        self._deals_by_store: Dict[str, List[Deal]] = {}  # store id  -> that store's deals
        self._stores_by_category: Dict[str, List[Store]] = {}  # "GROCERIES" -> stores selling it
        self._store_index: StoreIndex | None = None  # shop names, arranged for lookup by name
        self._place_words = PlaceVocabulary()  # mall/street words, learned from merchant names
        self._identities: Dict[str, StoreIdentity] = {}  # one entry per real brand
        self._identity_of_store: Dict[str, str] = {}  # store id -> the identity it folded into
        self._deal_shops: DealShopFinder | None = None  # shops running deals, by name
        self._loaded = False

    # ── Loading ───────────────────────────────────────────────────────────────

    async def load_async(self, force: bool = False) -> None:
        """Read clubs, stores and deals from MongoDB, and index them for fast lookups.

        Returns immediately if the cache is already populated; the periodic refresh passes
        ``force=True`` to rebuild it. Everything below is built into locals and only published
        onto ``self`` once every piece has succeeded.
        """
        if self._loaded and not force:
            logger.debug("Reference data already loaded, skipping reload")
            return

        logger.info("Loading clubs, stores, and deals from MongoDB...")
        try:
            stores = await Store.find_all().to_list()

            stores_by_id = (
                seq(stores)                                  # every store we know about
                .map(lambda store: (store.store_id, store))  # label each one with its id
                .to_dict()                                   # so we can find a store by id
            )

            stores_by_category = (
                seq(stores)                                                  # every store again
                .flat_map(lambda store: [                                    # a store can sell several categories,
                    (category, store)                                        # so list it once per category
                    for category in store.metadata.mcc_codes
                ])
                .group_by(lambda pair: pair[0])                              # gather stores under each category
                .map(lambda group: (group[0], [store for _, store in group[1]]))
                .to_dict()                                                   # "GROCERIES" -> [store, store, ...]
            )

            store_index = StoreIndex(stores)

            logger.info(
                "Stores loaded and indexed",
                extra={
                    "reason": "Data preparation for missed savings analysis",
                    "extra_data": {
                        "store_count": len(stores_by_id),
                        "mcc_unique_codes": len(stores_by_category),
                    },
                },
            )

            # Deals the source has stopped offering are excluded here rather than at every
            # use site: recommending a benefit that no longer exists is worse than missing
            # one. ``$ne`` also keeps rows that predate the field, which are still live.
            deals = await Deal.find({"status": {"$ne": "expired"}}).to_list()

            deals_by_id = (
                seq(deals)                                 # every deal
                .map(lambda deal: (deal.deal_id, deal))    # labelled with its own id
                .to_dict()                                 # so we can find a deal by id
            )

            deals_by_store = (
                seq(deals)                                          # every deal again
                .group_by(lambda deal: deal.store_id)               # gathered under the store offering it
                .to_dict()                                          # store id -> [deal, deal, ...]
            )

            logger.info(
                "Deals loaded and indexed",
                extra={
                    "reason": "Data preparation for missed savings analysis",
                    "extra_data": {
                        "deal_count": len(deals),
                        "stores_with_deals": len(deals_by_store),
                    },
                },
            )

            clubs = await Club.find_all().to_list()

            clubs_by_id = (
                seq(clubs)                                 # every club
                .map(lambda club: (club.club_id, club))    # labelled with its id
                .to_dict()                                 # so we can find a club by id
            )

            self._attach_club_stores(clubs_by_id, deals_by_id)

            logger.info(
                "Clubs loaded",
                extra={
                    "reason": "Data preparation for missed savings analysis",
                    "extra_data": {
                        "club_count": len(clubs_by_id),
                        "club_store_links": sum(len(c.stores or []) for c in clubs_by_id.values()),
                    },
                },
            )

            identities, identity_of_store, deal_shops = await self._build_deal_shops(stores, deals_by_store)

            # Publish the finished snapshot. Nothing above this line touched self, so a reader
            # mid-refresh saw the previous cache in full and a failure leaves it serving.
            self._stores = stores_by_id
            self._stores_by_category = stores_by_category
            self._store_index = store_index
            self._deals_by_id = deals_by_id
            self._deals_by_store = deals_by_store
            self._clubs = clubs_by_id
            self._identities = identities
            self._identity_of_store = identity_of_store
            self._deal_shops = deal_shops
            self._loaded = True
        except Exception as e:
            logger.error(
                f"Error loading reference data from MongoDB: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Database query failed",
                    "extra_data": {"error_type": type(e).__name__},
                },
            )
            raise

    async def _build_deal_shops(self, stores: List[Store], deals_by_store: Dict[str, List[Deal]]):
        """Fold the store list into real brands and index the ones running a deal.

        Aliases are the spellings a human already approved during deal review, and they are
        what lets a Hebrew card feed reach a shop filed under its English name — 'פיצה האט'
        onto 'pizza hut', 'נייקי' onto 'nike'. Several large chains are filed exactly that way
        and are otherwise unreachable.

        A missing or unreadable ``store_aliases`` collection is survivable: matching still
        works off the shops' own names, just without the cross-script bridge. It must not take
        the service down at startup.
        """
        try:
            aliases = await StoreAlias.find_all().to_list()
        except Exception as error:
            logger.warning(
                f"Could not read store aliases, continuing without them: {error}",
                extra={"reason": "Optional reference data unavailable", "extra_data": {}},
            )
            aliases = []

        identities = build_identities(stores, aliases, deals_by_store)
        identity_of_store = {
            store_id: identity.store_id
            for identity in identities.values()
            for store_id in identity.store_ids
        }
        deal_shops = DealShopFinder(list(identities.values()))

        logger.info(
            "Deal shops indexed",
            extra={
                "reason": "Data preparation for missed savings analysis",
                "extra_data": {
                    "alias_count": len(aliases),
                    "identity_count": len(identities),
                    "shops_with_deals": len(deal_shops),
                },
            },
        )

        return identities, identity_of_store, deal_shops

    def _attach_club_stores(
        self,
        clubs: Dict[str, Club] | None = None,
        deals_by_id: Dict[str, Deal] | None = None,
    ) -> None:
        """Give every club the shops it actually has deals at.

        Both club-aware features — club recommendations and missed-savings alternatives —
        answer "which of this club's shops sell what the user buys" by reading
        ``club.stores``. That field is filled incrementally by the pipeline's
        ``PersistStage._update_club_stores`` as deals are persisted, so a database whose
        clubs were imported rather than scraped has it empty on every club. The symptom is
        silent: ``recommend_clubs`` drops any club with no stores, so every recommendation
        list comes back empty with nothing logged.

        The relation is already implied by the data we just loaded — a deal names both its
        club and its store — so it is derived here instead of depended upon. Whatever the
        stored field holds is kept and unioned in, so an explicitly curated membership is
        never lost; deriving only ever adds the shops a club currently has live deals at.

        Both arguments default to the published cache; ``load_async`` passes the locals it is
        still assembling, so a rebuild derives against its own snapshot rather than the live one.
        """
        clubs = self._clubs if clubs is None else clubs
        deals_by_id = self._deals_by_id if deals_by_id is None else deals_by_id

        derived: Dict[str, set] = {}
        for deal in deals_by_id.values():
            if deal.club_id and deal.store_id:
                derived.setdefault(deal.club_id, set()).add(deal.store_id)

        for club_id, club in clubs.items():
            from_deals = derived.get(club_id, set())
            if not from_deals:
                continue
            club.stores = sorted(set(club.stores or []) | from_deals)

    # ── Lookups ───────────────────────────────────────────────────────────────

    def get_club(self, club_id: str) -> Club | None:
        """The club with this id, or nothing if we have never heard of it."""
        return self._clubs.get(club_id)

    def all_clubs(self) -> Dict[str, Club]:
        """Every club, keyed by id — used when scoring a user against all of them."""
        return self._clubs

    def get_store(self, store_id: str) -> Store | None:
        """The store with this id, or nothing if we have never heard of it."""
        return self._stores.get(store_id)

    def get_deal(self, deal_id: str) -> Deal | None:
        """The deal with this id, or nothing if we have never heard of it."""
        return self._deals_by_id.get(deal_id)

    def stores_by_category(self, category_name: str) -> List[Store]:
        """Every store that sells this kind of thing (e.g. "GROCERIES")."""
        return self._stores_by_category.get(category_name, [])

    def has_active_deal(self, store_id: str) -> bool:
        """True when this store is currently running at least one deal."""
        return len(self._deals_by_store.get(store_id, [])) > 0

    def find_store_by_merchant_name(self, merchant_name: str | None, town_name: str | None = None) -> Store | None:
        """
        The shop a card-feed merchant name refers to, or nothing when we cannot tell.

        Feed names are messy — branch numbers, mall names, company suffixes, truncation —
        so this is a real match rather than a lookup. `town_name` comes from the
        transaction's own `merchantAddress` and is what lets us tell a branch's town apart
        from the shop's actual name.
        """
        return self.match_merchant_name(merchant_name, town_name).store

    def match_merchant_name(self, merchant_name: str | None, town_name: str | None = None) -> StoreMatch:
        """As `find_store_by_merchant_name`, but keeps the reasoning — used by the debug view."""
        if self._store_index is None:
            return StoreMatch(status=NO_MATCH, rejected_by="NOT_LOADED")
        return match_store(merchant_name, town_name, self._store_index, self._place_words)

    def find_deal_shops(
        self,
        merchant_name: str | None,
        town_name: str | None = None,
        transaction_category: str | None = None,
    ) -> List[ShopMatch]:
        """
        Shops running a deal that this merchant name could refer to, best first.

        Deliberately more forgiving than `match_merchant_name`: it is answering "was there a
        coupon here", where a near miss still lands on a shop selling the same thing. Read
        `ShopMatch.band` before wording anything — only EXACT and STRONG mean "this shop".
        """
        if self._deal_shops is None:
            return []
        return self._deal_shops.find(merchant_name, town_name, transaction_category)

    def identity_for_store(self, store_id: str) -> StoreIdentity | None:
        """The brand a given store row folded into."""
        key = self._identity_of_store.get(store_id)
        return self._identities.get(key) if key else None

    def clubs_for_identity(self, identity: StoreIdentity) -> List[str]:
        """Which clubs carry this brand, under any of the store rows it was folded from."""
        return [
            club_id
            for club_id, club in self._clubs.items()
            if identity.store_ids & set(club.stores or [])
        ]

    def teach_place_words(self, merchant_names: List[str]) -> None:
        """
        Let the matcher learn which words name a *place* rather than a shop, from the
        merchant names we have actually seen.

        Worth calling with as many distinct merchant names as are on hand: 'קניון' and
        'רננים' only reveal themselves as places by turning up against many unrelated
        shops, so the vocabulary is only as good as the variety it has been shown.
        """
        if self._store_index is None:
            return
        self._place_words = PlaceVocabulary.learn_from_merchant_names(merchant_names, self._store_index)
