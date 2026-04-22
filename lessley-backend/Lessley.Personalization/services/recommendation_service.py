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

        mcc_codes = []

        for category in categories:
            if isinstance(category, dict) and "mcc_codes" in category:
                mcc_codes.extend(category.get("mcc_codes", []))

            # Convert string MCC codes to integers and remove duplicates
            mcc_codes = list(set(int(code) for code in mcc_codes if code))

        return mcc_codes

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
