import logging
from typing import Dict, List
from models.db.entities import Club, Store

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

    def _get_store_mcc_codes_from_store(self, store_data: Store) -> List[int]:
        """
        Extract MCC codes from store metadata.

        Args:
            store_data: The store dictionary

        Returns:
            List of integer MCC codes
        """
        if not store_data:
            return []

        try:
            mcc_codes = store_data.metadata.mcc_codes
            # Convert to int, filtering out non-numeric codes
            return [int(code) for code in mcc_codes if code and str(code).isdigit()]
        except Exception as e:
            logger.debug(
                f"Error extracting MCC codes from store: {str(e)}",
                extra={"reason": "Data parsing", "extra_data": {"error_type": type(e).__name__}},
            )
            return []

    def _calculate_club_scores(self, mcc_codes: List[int]) -> List[Dict]:
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
        self, user_id: str, mcc_codes: List[int], threshold: float = 0.20
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
            "user_id": user_id,
            "recommendations": sorted_recommendations,
        }

    def get_store_mcc_codes(self, club_id: str, store_id: str) -> List[int]:
        """
        Retrieve MCC codes for a specific store in a club using direct dictionary lookups.

        Args:
            club_id: The club ID
            store_id: The store ID

        Returns:
            List of MCC codes for the store, or empty list if not found
        """
        logger.debug(
            "Retrieving store MCC codes",
            extra={
                "reason": "Store data lookup",
                "extra_data": {"club_id": club_id, "store_id": store_id},
            },
        )

        try:
            # Verify club exists and store is in its stores list
            club = self._clubs_dict.get(club_id)
            if not club:
                logger.warning(
                    "Club not found",
                    extra={
                        "reason": "Club lookup failed",
                        "extra_data": {"club_id": club_id},
                    },
                )
                return []

            store_ids = club.stores
            if store_id not in store_ids:
                logger.warning(
                    "Store not in club",
                    extra={
                        "reason": "Store validation failed",
                        "extra_data": {"club_id": club_id, "store_id": store_id},
                    },
                )
                return []

            # Direct lookup in stores dictionary
            store = self._stores_dict.get(store_id)
            if not store:
                logger.warning(
                    "Store not found in stores dictionary",
                    extra={
                        "reason": "Store lookup failed",
                        "extra_data": {"store_id": store_id},
                    },
                )
                return []

            mcc_codes = self._get_store_mcc_codes_from_store(store)
            logger.debug(
                "Store MCC codes retrieved",
                extra={
                    "reason": "Data lookup complete",
                    "extra_data": {
                        "club_id": club_id,
                        "store_id": store_id,
                        "mcc_count": len(mcc_codes),
                    },
                },
            )
            return mcc_codes

        except Exception as e:
            logger.error(
                f"Error retrieving store MCC codes: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Store lookup failed",
                    "extra_data": {
                        "club_id": club_id,
                        "store_id": store_id,
                        "error_type": type(e).__name__,
                    },
                },
            )
            return []

    def get_club_mcc_distribution(self, club_id: str) -> Dict:
        """
        Get MCC distribution for a specific club across all its stores using dictionary lookups.

        Args:
            club_id: The club ID

        Returns:
            Dictionary with club info and MCC distribution
        """
        logger.info(
            "Retrieving club MCC distribution",
            extra={
                "reason": "Club data lookup",
                "extra_data": {"club_id": club_id},
            },
        )

        try:
            # Direct lookup in clubs dictionary
            club_data = self._clubs_dict.get(club_id)

            if not club_data:
                logger.warning(
                    "Club not found",
                    extra={
                        "reason": "Club lookup failed",
                        "extra_data": {"club_id": club_id},
                    },
                )
                raise ValueError(f"Club with id '{club_id}' not found")

            # Count MCCs across all stores in the club
            mcc_counts = {}
            store_ids = club_data.stores

            for store_id in store_ids:
                # Look up store in stores dictionary
                store = self._stores_dict.get(store_id)
                if store:
                    # Get unique MCCs in this store
                    unique_mcc_in_store = set(self._get_store_mcc_codes_from_store(store))
                    for mcc in unique_mcc_in_store:
                        mcc_counts[mcc] = mcc_counts.get(mcc, 0) + 1

            # Format and sort results
            categories = [
                {"mcc": mcc, "store_count": count}
                for mcc, count in sorted(mcc_counts.items(), key=lambda x: x[1], reverse=True)
            ]

            result = {
                "club_id": club_id,
                "club_name": club_data.name,
                "categories": categories,
            }

            logger.info(
                "Club MCC distribution retrieved successfully",
                extra={
                    "reason": "Data lookup complete",
                    "extra_data": {
                        "club_id": club_id,
                        "mcc_count": len(categories),
                        "store_count": len(store_ids),
                    },
                },
            )

            return result

        except ValueError as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Club lookup failed",
                    "extra_data": {
                        "club_id": club_id,
                        "error_type": type(e).__name__,
                    },
                },
            )
            raise

        except Exception as e:
            logger.error(
                f"Error retrieving club MCC distribution: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Service execution failed",
                    "extra_data": {
                        "club_id": club_id,
                        "error_type": type(e).__name__,
                    },
                },
            )
            raise
