import logging
from typing import Dict, List
from .recommendation_core_service import RecommendationCoreService
from .insights_service import InsightsService
from config.constants import LIMITS

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Service for recommending clubs based on user spending categories.
    Orchestrates insights service and core recommendation logic.
    """

    def __init__(
        self,
        recommendation_core_service: RecommendationCoreService = None,
        insights_service: InsightsService = None,
    ):
        self.recommendation_core_service = recommendation_core_service
        self.insights_service = insights_service

    def _extract_mcc_codes_from_categories(self, categories: List[Dict]) -> List[int]:
        """
        Extract and convert MCC codes from category list.
        Handles both string and integer MCC codes with graceful error handling.

        Args:
            categories: List of category dictionaries containing mcc_codes

        Returns:
            List of unique integer MCC codes
        """
        mcc_set = set()
        conversion_errors = 0

        for category in categories:
            if not isinstance(category, dict):
                continue

            for code in category.get("mcc_codes", []):
                if not code:
                    continue

                try:
                    mcc_set.add(int(code))
                except (ValueError, TypeError):
                    conversion_errors += 1

        return list(mcc_set)

    async def calculate_club_recommendation_by_category(
        self,
        user_id: str,
        time_filter: bool,
        days: int,
        use_mock: bool = False,
        threshold: LIMITS = LIMITS.HIT_THRESHOLD,
    ) -> Dict:
        """
        Calculate club recommendations based on user spending patterns.

        Args:
            user_id: The user ID
            time_filter: Whether to apply time filter to transactions
            days: Number of days of history to analyze
            use_mock: Whether to use mock data for testing
            threshold: Fit score threshold (0-1) for recommendation

        Returns:
            Dictionary containing recommendations list
        """
        logger.info(
            "Club recommendation calculation started",
            extra={
                "reason": "Service method invoked",
                "extra_data": {
                    "user_id": user_id,
                    "threshold": threshold,
                },
            },
        )

        try:
            categories = await self.insights_service.calculate_user_categories_async(
                user_id, time_filter, days, use_mock
            )

            mcc_codes = self._extract_mcc_codes_from_categories(categories)
            result = self.recommendation_core_service.get_club_recommendations_by_spending_analysis(
                user_id, mcc_codes, threshold
            )

            logger.info(
                "Club recommendation calculation completed",
                extra={
                    "reason": "Service execution complete",
                    "extra_data": {
                        "user_id": user_id,
                        "recommendation_count": len(result.get("recommendations", [])),
                    },
                },
            )

            return result

        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Service execution failure",
                    "extra_data": {
                        "user_id": user_id,
                        "error_type": type(e).__name__,
                    },
                },
            )
            raise

    async def calculate_deal_recommendation_for_user(
        self,
        user_id: str,
        club_id: str,
        deal_id: str,
        store_id: str,
        threshold: LIMITS = LIMITS.HIT_THRESHOLD,
    ) -> Dict:
        """
        Calculate deal recommendation based on store-user category fit.

        Args:
            user_id: The user ID
            club_id: The club ID
            deal_id: The deal ID
            store_id: The store ID
            threshold: Fit score threshold for recommendation

        Returns:
            Dictionary with deal recommendation details
        """
        logger.info(
            "Deal recommendation calculation started",
            extra={
                "reason": "Service method invoked",
                "extra_data": {
                    "user_id": user_id,
                    "deal_id": deal_id,
                },
            },
        )

        try:
            categories = await self.insights_service.calculate_user_categories_async(user_id, True, 30, False)
            user_mcc_codes = self._extract_mcc_codes_from_categories(categories)
            store_mcc_codes = self.recommendation_core_service.get_store_mcc_codes(club_id, store_id)

            user_mcc_set = set(user_mcc_codes)
            matching_codes = [code for code in store_mcc_codes if code in user_mcc_set]
            fit_score = len(matching_codes) / len(store_mcc_codes) if store_mcc_codes else 0.0
            is_recommended = fit_score >= threshold

            result = {
                "deal_id": deal_id,
                "user_id": user_id,
                "store_id": store_id,
                "club_id": club_id,
                "is_recommended": is_recommended,
                "fit_score": fit_score,
                "matching_mcc_codes": matching_codes,
            }

            logger.info(
                "Deal recommendation calculation completed",
                extra={
                    "reason": "Service execution complete",
                    "extra_data": {
                        "user_id": user_id,
                        "deal_id": deal_id,
                        "is_recommended": is_recommended,
                    },
                },
            )

            return result

        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Service execution failure",
                    "extra_data": {
                        "user_id": user_id,
                        "error_type": type(e).__name__,
                    },
                },
            )
            raise
