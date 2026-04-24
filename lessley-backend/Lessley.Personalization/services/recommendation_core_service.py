import logging
from typing import Dict, List
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class RecommendationCoreService:
    """
    Service for recommending clubs based on user spending categories.
    Uses MCC codes from user spending to match against available clubs and their stores.
    """

    def __init__(self):
        logger.info(
            "RecommendationService initialized",
            extra={
                "reason": "Service creation",
                "extra_data": {},
            },
        )
        self._categories_data = None
        self._load_categories_data()

    def _load_categories_data(self):
        """Load categories/clubs data from JSON file."""
        try:
            categories_path = Path("./resources/categories.json")
            if os.path.exists(categories_path):
                with open(categories_path, "r", encoding="utf-8") as f:
                    self._categories_data = json.load(f)
                logger.info(
                    "Categories data loaded successfully",
                    extra={
                        "reason": "Data file loaded",
                        "extra_data": {"file_path": categories_path},
                    },
                )
            else:
                logger.warning(
                    f"Categories data file not found: {categories_path}",
                    extra={
                        "reason": "Missing data file",
                        "extra_data": {"file_path": categories_path},
                    },
                )
                self._categories_data = []
        except Exception as e:
            logger.error(
                f"Error loading categories data: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Data file load failed",
                    "extra_data": {"error_type": type(e).__name__},
                },
            )
            self._categories_data = []

    def _calculate_club_scores(self, mcc_codes: List[int]) -> List[Dict]:
        """
        A private helper to calculate hit counts for all clubs based on a list of MCCs.

        Args:
            mcc_codes: A list of user's spending MCC codes.

        Returns:
            A list of dictionaries, each containing a club's score.
        """
        club_scores = []
        mcc_codes_set = set(mcc_codes)

        # Iterate through all clubs and count hits
        for club in self._categories_data:
            hit_count = 0
            stores = club.get("stores", [])
            total_stores = len(stores)

            if total_stores > 0:
                for store in stores:
                    store_mcc_codes = set(store.get("mcc_codes", []))
                    # If store has any matching MCC codes, count it as a hit
                    if store_mcc_codes & mcc_codes_set:
                        hit_count += 1

            club_scores.append(
                {
                    "club_id": club.get("club_id"),
                    "club_name": club.get("name"),
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
        Retrieve MCC codes for a specific store in a club.

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
            for club in self._categories_data:
                if club.get("club_id") == club_id:
                    for store in club.get("stores", []):
                        if store.get("store_id") == store_id:
                            raw_codes = store.get("mcc_codes", [])
                            # Convert to int, filtering out non-numeric codes
                            mcc_codes = [int(code) for code in raw_codes if str(code).isdigit()]
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

            logger.warning(
                "Store not found",
                extra={
                    "reason": "Store lookup failed",
                    "extra_data": {"club_id": club_id, "store_id": store_id},
                },
            )
            return []

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
        Get MCC distribution for a specific club across all its stores.

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
            # Find the specific club
            club_data = None
            for club in self._categories_data:
                if club.get("club_id") == club_id:
                    club_data = club
                    break

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
            stores = club_data.get("stores", [])

            for store in stores:
                # Count each MCC only once per store to get store count
                unique_mcc_in_store = set(store.get("mcc_codes", []))
                for mcc in unique_mcc_in_store:
                    try:
                        mcc_int = int(mcc)
                        mcc_counts[mcc_int] = mcc_counts.get(mcc_int, 0) + 1
                    except (ValueError, TypeError):
                        logger.debug(
                            "Invalid MCC code in store",
                            extra={
                                "reason": "Data validation",
                                "extra_data": {"club_id": club_id, "mcc": str(mcc)},
                            },
                        )

            # Format and sort results
            categories = [
                {"mcc": mcc, "store_count": count}
                for mcc, count in sorted(mcc_counts.items(), key=lambda x: x[1], reverse=True)
            ]

            result = {
                "club_id": club_data.get("club_id"),
                "club_name": club_data.get("name"),
                "categories": categories,
            }

            logger.info(
                "Club MCC distribution retrieved successfully",
                extra={
                    "reason": "Data lookup complete",
                    "extra_data": {
                        "club_id": club_id,
                        "mcc_count": len(categories),
                        "store_count": len(stores),
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
