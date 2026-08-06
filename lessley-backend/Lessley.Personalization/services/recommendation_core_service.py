import logging
from typing import Dict, List
from models.db.entities import Club, Store, Deal

logger = logging.getLogger(__name__)


class RecommendationCoreService:
    """
    Service for recommending clubs based on user spending categories.
    Uses MCC codes from user spending to match against available clubs and their stores.
    Leverages dictionary-based lookups for efficient data access.
    """

    def __init__(self):
        logger.info(
            "RecommendationCoreService initialized. Call initialize() to load data.",
            extra={
                "reason": "Service creation",
                "extra_data": {},
            },
        )
        self._clubs_dict: Dict[str, Club] = {}  # {club_id: club_data}
        self._stores_dict: Dict[str, Store] = {}  # {store_id: store_data}
        self._deals_dict: Dict[str, Deal] = {}  # {deal_id: deal_data}

    async def initialize(self):
        """Load clubs and stores data from MongoDB into dictionaries."""
        logger.info("Loading clubs and stores data from MongoDB...")
        try:
            # Load clubs
            clubs_list = await Club.find_all().to_list()
            self._clubs_dict = {club.club_id: club for club in clubs_list}
            logger.info(
                "Clubs data loaded successfully from MongoDB",
                extra={
                    "reason": "Data loading",
                    "extra_data": {"count": len(self._clubs_dict)},
                },
            )

            # Load stores
            stores_list = await Store.find_all().to_list()
            self._stores_dict = {store.store_id: store for store in stores_list}
            logger.info(
                "Stores data loaded successfully from MongoDB",
                extra={
                    "reason": "Data loading",
                    "extra_data": {"count": len(self._stores_dict)},
                },
            )

            # Load deals (used to resolve a deal's category from its store for broadcasts)
            deals_list = await Deal.find_all().to_list()
            self._deals_dict = {deal.deal_id: deal for deal in deals_list}
            logger.info(
                "Deals data loaded successfully from MongoDB",
                extra={
                    "reason": "Data loading",
                    "extra_data": {"count": len(self._deals_dict)},
                },
            )
        except Exception as e:
            logger.error(
                f"Error loading data from MongoDB: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Database query failed",
                    "extra_data": {"error_type": type(e).__name__},
                },
            )
            raise

    def _get_store_mcc_codes_from_store(self, store_data: Store) -> List[str]:
        """
        Extract category names from store metadata.

        Args:
            store_data: The store document

        Returns:
            List of category name strings
        """
        if not store_data:
            return []

        try:
            return [code for code in store_data.metadata.mcc_codes if code]
        except Exception as e:
            logger.debug(
                f"Error extracting categories from store: {str(e)}",
                extra={"reason": "Data parsing", "extra_data": {"error_type": type(e).__name__}},
            )
            return []

    def _calculate_club_scores(self, mcc_codes: List[str]) -> List[Dict]:
        """
        Calculate hit counts for all clubs based on a list of MCCs using dictionary lookups.

        Args:
            mcc_codes: A list of user's spending MCC codes.

        Returns:
            A list of dictionaries, each containing a club's score.
        """
        club_scores = []
        mcc_codes_set = set(mcc_codes)

        # Iterate through clubs dictionary
        for club_id, club in self._clubs_dict.items():
            hit_count = 0
            store_ids = club.stores
            total_stores = len(store_ids) if store_ids else 0

            if total_stores > 0:
                # Look up each store in the stores dictionary
                for store_id in store_ids:
                    store = self._stores_dict.get(store_id)
                    if store:
                        store_mcc_codes = set(self._get_store_mcc_codes_from_store(store))
                        # If store has any matching MCC codes, count it as a hit
                        if store_mcc_codes & mcc_codes_set:
                            hit_count += 1

            club_scores.append(
                {
                    "club_id": club_id,
                    "club_name": club.name,
                    "hit_count": hit_count,
                    "total_stores": total_stores,
                }
            )
        return club_scores

    def get_club_recommendations_by_spending_analysis(
        self,
        user_id: str,
        mcc_codes: List[str],
        threshold: float = 0.20,
        user_club_ids: List[str] | None = None,
    ) -> Dict:
        """
        Analyzes all clubs against user's spending categories and recommends those that exceed a fit threshold.

        Args:
            user_id: The user ID.
            mcc_codes: List of MCC codes from user's spending.
            threshold: The minimum ratio of (matching stores / total stores) to be considered a recommendation.

        Returns:
            A dictionary containing a list of recommended clubs.
        """
        try:
            logger.info(
                f"Analyzing club fit for user: {user_id}",
                extra={
                    "reason": "Club fit analysis request received",
                    "extra_data": {
                        "user_id": user_id,
                        "mcc_codes_count": len(mcc_codes),
                        "threshold": threshold,
                    },
                },
            )

            # Use the helper method to get the base scores
            club_scores = self._calculate_club_scores(mcc_codes)
            member_club_ids = set(user_club_ids or [])

            recommended_clubs = []
            for score in club_scores:
                total_stores = score["total_stores"]
                if total_stores == 0:
                    continue  # Skip clubs with no stores

                fit_score = score["hit_count"] / total_stores

                recommended_clubs.append(
                    {
                        "club_id": score["club_id"],
                        "club_name": score["club_name"],
                        "hit_count": score["hit_count"],
                        "total_stores": score["total_stores"],
                        "fit_score": fit_score,
                        "is_recommended": fit_score >= threshold,
                        "is_member": score["club_id"] in member_club_ids,
                    }
                )

        except Exception as e:
            logger.error(
                f"Error during club fit analysis: {str(e)}",
                exc_info=e,
                extra={"reason": "Club fit analysis failed", "extra_data": {"user_id": user_id}},
            )
            raise

        # Sort recommended clubs by fit_score descending
        sorted_recommendations = sorted(recommended_clubs, key=lambda x: x["fit_score"], reverse=True)

        return {
            "email": user_id,
            "recommendations": sorted_recommendations,
        }

    def get_deal_categories(self, deal_id: str) -> List[str]:
        """
        Resolve a deal's categories from the store it belongs to.

        Looks up the deal → its store → the store's MCC codes. Those MCC codes are the deal's
        categories, used to broadcast the deal to the matching category groups. Returns an empty
        list if the deal or its store is unknown.
        """
        deal = self._deals_dict.get(deal_id)
        if not deal:
            logger.warning(
                "Deal not found",
                extra={"reason": "Deal lookup failed", "extra_data": {"deal_id": deal_id}},
            )
            return []

        store = self._stores_dict.get(deal.store_id)
        if not store:
            logger.warning(
                "Store for deal not found",
                extra={
                    "reason": "Store lookup failed",
                    "extra_data": {"deal_id": deal_id, "store_id": deal.store_id},
                },
            )
            return []

        mcc_codes = self._get_store_mcc_codes_from_store(store)
        logger.debug(
            "Deal categories resolved",
            extra={
                "reason": "Data lookup complete",
                "extra_data": {"deal_id": deal_id, "store_id": deal.store_id, "mcc_count": len(mcc_codes)},
            },
        )
        return mcc_codes
