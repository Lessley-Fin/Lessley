import logging
from typing import Dict, Optional
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

            result = {
                "store_name": store_name,
                "official_name": store_category.official_name,
                "primary_category": store_category.primary_category,
                "mcc_code": store_category.mcc_code,
                "confidence_level": store_category.confidence_level,
            }

            logger.info(
                "Store MCC retrieved successfully",
                extra={
                    "reason": "Store classification complete",
                    "extra_data": {"store_name": store_name, "mcc_code": store_category.mcc_code},
                },
            )

            return result

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
