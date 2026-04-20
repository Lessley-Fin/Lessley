import logging
from typing import Dict, Optional, List
import json
import os
from services.clients import llm_integration

logger = logging.getLogger(__name__)


class CategoriesService:
    """
    Service for enriching transactions with category information.
    Integrates with LLM for intelligent classification.
    """

    def __init__(self):
        logger.info(
            "CategoriesService initialized",
            extra={
                "reason": "Service creation",
                "extra_data": {},
            },
        )
        self._categories_data = None
        self._load_categories_data()

    def _load_categories_data(self):
        """Load categories data from JSON file."""
        try:
            categories_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "data", "categories.json"
            )
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

    def get_store_mcc(self, store_name: str) -> Dict:
        """
        Retrieves the MCC (Merchant Category Code) for a store using LLM classification.

        Args:
            store_name: The name of the store

        Returns:
            Dictionary with store classification information
        """
        try:
            logger.info(
                f"Getting MCC for store: {store_name}",
                extra={
                    "reason": "Store MCC classification requested",
                    "extra_data": {"store_name": store_name},
                },
            )

            store_category = llm_integration.get_store_category(store_name)

            logger.info(
                "Store MCC retrieved successfully",
                extra={
                    "reason": "Store classification complete",
                    "extra_data": {"store_name": store_name},
                },
            )

            return store_category.dict()

        except Exception as e:
            logger.error(
                f"Error getting store MCC: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Store classification failed",
                    "extra_data": {
                        "store_name": store_name,
                        "error_type": type(e).__name__,
                    },
                },
            )
            raise

    def get_deal_category(self, deal_name: str, deal_description: Optional[str] = None) -> Dict:
        """
        Retrieves the category for a deal/promotion using LLM classification.

        Args:
            deal_name: The name/title of the deal
            deal_description: Optional description of the deal

        Returns:
            Dictionary with deal classification information
        """
        try:
            logger.info(
                f"Getting category for deal: {deal_name}",
                extra={
                    "reason": "Deal category classification requested",
                    "extra_data": {"deal_name": deal_name},
                },
            )

            deal_category = llm_integration.get_deal_category(deal_name, deal_description)

            result = {
                "deal_name": deal_name,
                "category": deal_category.category,
                "subcategory": deal_category.subcategory,
                "relevance_score": deal_category.relevance_score,
                "confidence_level": deal_category.confidence_level,
            }

            logger.info(
                "Deal category retrieved successfully",
                extra={
                    "reason": "Deal classification complete",
                    "extra_data": {
                        "deal_name": deal_name,
                        "category": deal_category.category,
                        "relevance_score": deal_category.relevance_score,
                    },
                },
            )

            return result

        except Exception as e:
            logger.error(
                f"Error getting deal category: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Deal classification failed",
                    "extra_data": {
                        "deal_name": deal_name,
                        "error_type": type(e).__name__,
                    },
                },
            )
            raise

    def _infer_category(self, description: str) -> str:
        """
        Infers a category from transaction description using fallback logic.

        Args:
            description: Transaction description

        Returns:
            Inferred category string
        """
        description_lower = description.lower()

        # Simple category inference logic
        if any(word in description_lower for word in ["grocery", "supermarket", "food", "restaurant", "cafe"]):
            return "Food & Dining"
        elif any(word in description_lower for word in ["gas", "fuel", "parking", "uber", "taxi", "transit"]):
            return "Transportation"
        elif any(word in description_lower for word in ["subscri", "netflix", "spotify", "entertainment"]):
            return "Entertainment"
        elif any(word in description_lower for word in ["health", "doctor", "hospital", "pharmacy", "medical"]):
            return "Healthcare"
        elif any(word in description_lower for word in ["utility", "electricity", "water", "internet", "phone"]):
            return "Utilities"
        elif any(word in description_lower for word in ["shopping", "store", "mall", "amazon", "department"]):
            return "Shopping"
        else:
            return "Other"

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

                club_scores.append({
                    "club_id": club_id,
                    "club_name": club_name,
                    "hit_count": hit_count,
                    "total_stores": total_stores,
                })

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
