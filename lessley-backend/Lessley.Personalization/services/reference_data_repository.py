import logging
from typing import Dict, List

from functional import seq

from models.db.entities import Club, Deal, Store

logger = logging.getLogger(__name__)


class ReferenceDataRepository:
    """
    Holds the shop-side reference data — clubs, stores and deals — in memory.

    This is the only place that talks to MongoDB for these three collections. Everything is
    read once at startup and kept in dictionaries, because the insight calculations look the
    same records up thousands of times per request and must never wait on the database.
    """

    def __init__(self):
        self._clubs: Dict[str, Club] = {}  # club id            -> the club
        self._stores: Dict[str, Store] = {}  # store id           -> the store
        self._deals_by_id: Dict[str, Deal] = {}  # deal id            -> the deal
        self._deals_by_store: Dict[str, List[Deal]] = {}  # store id  -> that store's deals
        self._stores_by_category: Dict[str, List[Store]] = {}  # "GROCERIES" -> stores selling it
        self._loaded = False

    # ── Loading ───────────────────────────────────────────────────────────────

    async def load_async(self) -> None:
        """Read clubs, stores and deals from MongoDB once, and index them for fast lookups."""
        if self._loaded:
            logger.debug("Reference data already loaded, skipping reload")
            return

        logger.info("Loading clubs, stores, and deals from MongoDB...")
        try:
            stores = await Store.find_all().to_list()

            self._stores = (
                seq(stores)                                  # every store we know about
                .map(lambda store: (store.store_id, store))  # label each one with its id
                .to_dict()                                   # so we can find a store by id
            )

            self._stores_by_category = (
                seq(stores)                                                  # every store again
                .flat_map(lambda store: [                                    # a store can sell several categories,
                    (category, store)                                        # so list it once per category
                    for category in store.metadata.mcc_codes
                ])
                .group_by(lambda pair: pair[0])                              # gather stores under each category
                .map(lambda group: (group[0], [store for _, store in group[1]]))
                .to_dict()                                                   # "GROCERIES" -> [store, store, ...]
            )

            logger.info(
                "Stores loaded and indexed",
                extra={
                    "reason": "Data preparation for missed savings analysis",
                    "extra_data": {
                        "store_count": len(self._stores),
                        "mcc_unique_codes": len(self._stores_by_category),
                    },
                },
            )

            deals = await Deal.find_all().to_list()

            self._deals_by_id = (
                seq(deals)                                 # every deal
                .map(lambda deal: (deal.deal_id, deal))    # labelled with its own id
                .to_dict()                                 # so we can find a deal by id
            )

            self._deals_by_store = (
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
                        "stores_with_deals": len(self._deals_by_store),
                    },
                },
            )

            clubs = await Club.find_all().to_list()

            self._clubs = (
                seq(clubs)                                 # every club
                .map(lambda club: (club.club_id, club))    # labelled with its id
                .to_dict()                                 # so we can find a club by id
            )

            self._attach_club_stores()

            logger.info(
                "Clubs loaded",
                extra={
                    "reason": "Data preparation for missed savings analysis",
                    "extra_data": {
                        "club_count": len(self._clubs),
                        "club_store_links": sum(len(c.stores or []) for c in self._clubs.values()),
                    },
                },
            )

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

    def _attach_club_stores(self) -> None:
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
        """
        derived: Dict[str, set] = {}
        for deal in self._deals_by_id.values():
            if deal.club_id and deal.store_id:
                derived.setdefault(deal.club_id, set()).add(deal.store_id)

        for club_id, club in self._clubs.items():
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
