import logging
from typing import Dict, List
from .recommendation_core_service import RecommendationCoreService
from .insights_service import InsightsService
from config.constants import LIMITS

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Service for recommending clubs based on user spending categories.
    Uses MCC codes from user spending to match against available clubs and their stores.
    """

    def __init__(
        self,
        recommendation_core_service: RecommendationCoreService,
        insights_service: InsightsService,
    ):
        self.recommendation_core_service = recommendation_core_service
        self.insights_service = insights_service

    def _extract_mcc_codes(self, categories: List[Dict]) -> List[int]:
        """
        Extract and convert MCC codes from category list.
        Handles both string and integer MCC codes.

        Args:
            categories: List of category dictionaries

        Returns:
            List of unique integer MCC codes
        """
        logger.info(
            "Extracting MCC codes",
            extra={
                "reason": "Data transformation",
                "extra_data": {
                    "category_count": len(categories),
                },
            },
        )

        all_mcc_codes = set()
        for category in categories:
            if isinstance(category, dict):
                for code in category.get("mcc_codes", []):
                    if code:  # Ensure code is not empty or None
                        try:
                            all_mcc_codes.add(int(code))
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Could not convert MCC code '{code}' to an integer. Skipping.",
                                extra={"reason": "Invalid data format", "extra_data": {"invalid_code": code}},
                            )

        return list(all_mcc_codes)

    async def calculate_club_recommendation_by_category(
        self,
        user_id: str,
        time_filter: bool,
        days: int = LIMITS.DAYS,
        use_mock: bool = False,
        threshold: float = LIMITS.HIT_THRESHOLD,
    ) -> Dict:
        """
        Orchestrates the process of generating club recommendations based on a user's spending analysis.

        Args:
            user_id: The user ID.
            time_filter: Whether to apply a time filter to transactions.
            days: The number of days of transaction history to analyze.
            threshold: The fit score threshold for a club to be recommended.

        Returns:
            A dictionary with club recommendations.
        """
        logger.info(
            "Service method called for spending-based club recommendation",
            extra={
                "reason": "Method invocation",
                "extra_data": {
                    "user_id": user_id,
                    "time_filter": time_filter,
                    "days": days,
                    "threshold": threshold,
                },
            },
        )

        try:
            # Fetch user categories from insights service
            categories = await self.insights_service.calculate_user_categories_async(
                user_id, time_filter, days, use_mock
            )

            # Extract and convert MCC codes from categories
            mcc_codes = self._extract_mcc_codes(categories)

            # Get club recommendations based on spending analysis
            recommendation_result = self.recommendation_core_service.get_club_recommendations_by_spending_analysis(
                user_id, mcc_codes, threshold
            )

            logger.info(
                "Spending-based club recommendation calculation complete",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {
                        "user_id": user_id,
                        "recommended_club_count": len(recommendation_result.get("recommendations", [])),
                    },
                },
            )

            return recommendation_result

        except Exception as e:
            logger.error(
                f"Error in calculate_club_recommendation_by_spending: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Service execution failure",
                    "extra_data": {"user_id": user_id, "error_type": type(e).__name__},
                },
            )
            raise

    async def calculate_deal_recommendation_for_user(
        self, user_id: str, club_id: str, deal_id: str, store_id: str
    ) -> Dict:
        """
            Check if a specific deal is recommended for the user based on their spending habits and the store's category fit.
        Args:
            user_id: The user ID.
            club_id: The club ID for which the deal is being analyzed.
            deal_id: The deal ID for which the recommendation is being calculated.
            store_id: The store ID where the deal is available.
        """
        logger.info(
            "Calculating deal recommendation for user",
            extra={
                "reason": "Method invocation",
                "extra_data": {
                    "user_id": user_id,
                    "club_id": club_id,
                    "deal_id": deal_id,
                    "store_id": store_id,
                },
            },
        )
        try:
            # step 1: Get user categories and MCC codes using insights_service
            categories = await self.insights_service.calculate_user_categories_async(
                user_id=user_id, time_filter=True, days=LIMITS.DAYS, use_mock=False
            )
            user_mcc_codes = self._extract_mcc_codes(categories)

            # step 2: Get the store's MCC codes, using logic from club_controller
            store_mcc_codes = []
            if self.recommendation_core_service._categories_data:
                for club in self.recommendation_core_service._categories_data:
                    if club.get("club_id") == club_id:
                        for store in club.get("stores", []):
                            if store.get("store_id") == store_id:
                                raw_codes = store.get("mcc_codes", [])
                                store_mcc_codes = [int(code) for code in raw_codes if str(code).isdigit()]
                                break
                        break

            if not store_mcc_codes:
                logger.warning(
                    f"Store '{store_id}' in club '{club_id}' not found or has no MCC codes.",
                    extra={
                        "reason": "Data lookup failed",
                        "extra_data": {"user_id": user_id, "club_id": club_id, "store_id": store_id},
                    },
                )

            # step 3: Check if the store's MCC codes are among the user's top MCC codes
            user_mcc_set = set(user_mcc_codes)
            matching_mcc_codes = [mcc for mcc in store_mcc_codes if mcc in user_mcc_set]

            # step 4: Determine if deal is recommended based on fit score and threshold
            fit_score = 0.0
            if store_mcc_codes:
                fit_score = len(matching_mcc_codes) / len(store_mcc_codes)

            is_recommended = fit_score >= LIMITS.HIT_THRESHOLD

            result = {
                "deal_id": deal_id,
                "user_id": user_id,
                "store_id": store_id,
                "club_id": club_id,
                "is_recommended": is_recommended,
                "fit_score": fit_score,
                "matching_mcc_codes": matching_mcc_codes,
                "user_mcc_codes": user_mcc_codes,
                "store_mcc_codes": store_mcc_codes,
            }

            logger.info(
                "Deal recommendation calculation complete",
                extra={
                    "reason": "Business logic complete",
                    "extra_data": {"user_id": user_id, "deal_id": deal_id, "is_recommended": is_recommended},
                },
            )

            return result

        except Exception as e:
            logger.error(
                f"Error in calculate_deal_recommendation_for_user: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Service execution failure",
                    "extra_data": {"user_id": user_id, "deal_id": deal_id, "error_type": type(e).__name__},
                },
            )
            raise
