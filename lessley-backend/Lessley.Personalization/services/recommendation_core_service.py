import logging
from typing import Dict, List
import json
import os

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
            # Go up from services -> Personalization -> lessley-backend -> Lessley to the root project dir
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            categories_path = os.path.join(project_root, "main", "resources", "categories.json")
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

    def get_club_recommendation_by_category(self, user_id: str, mcc_codes: List[int]) -> Dict:
        """
        Gets club recommendations based on MCC codes from user's transaction history.
        Counts hits (stores with matching MCC codes) for each club and returns ranked results.

        Args:
            user_id: The user ID
            mcc_codes: List of MCC codes from user's spending categories

        Returns:
            Dictionary with club scores and recommended club
        """
        try:
            logger.info(
                f"Getting club recommendation for user: {user_id}",
                extra={
                    "reason": "Club recommendation request received",
                    "extra_data": {
                        "user_id": user_id,
                        "mcc_codes_count": len(mcc_codes),
                    },
                },
            )

            club_scores = []
            mcc_codes_set = set(mcc_codes)

            # Iterate through all clubs and count hits
            for club in self._categories_data:
                club_id = club.get("club_id")
                club_name = club.get("name")
                hit_count = 0

                # Count stores with matching MCC codes
                stores = club.get("stores", [])
                total_stores = len(stores)

                for store in stores:
                    store_mcc_codes = set(store.get("mcc_codes", []))
                    # If store has any matching MCC codes, count it as a hit
                    if store_mcc_codes & mcc_codes_set:
                        hit_count += 1

                club_scores.append(
                    {
                        "club_id": club_id,
                        "club_name": club_name,
                        "hit_count": hit_count,
                        "total_stores": total_stores,
                    }
                )

            # Sort by hit count (descending) to get recommended club
            sorted_clubs = sorted(club_scores, key=lambda x: x["hit_count"], reverse=True)
            recommended_club = sorted_clubs[0] if sorted_clubs else None

            logger.info(
                "Club recommendation generated successfully",
                extra={
                    "reason": "Club recommendation generation complete",
                    "extra_data": {
                        "user_id": user_id,
                        "club_count": len(club_scores),
                        "recommended_club": recommended_club.get("club_name") if recommended_club else None,
                    },
                },
            )

            return {
                "user_id": user_id,
                "club_scores": sorted_clubs,
                "recommended_club": recommended_club,
            }

        except Exception as e:
            logger.error(
                f"Error getting club recommendation: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Club recommendation generation failed",
                    "extra_data": {
                        "user_id": user_id,
                        "error_type": type(e).__name__,
                    },
                },
            )
            raise
