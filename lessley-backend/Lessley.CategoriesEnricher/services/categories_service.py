import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class CategoriesService:
    """
    Service for enriching transactions with category information.
    """

    def __init__(self):
        logger.info(
            "CategoriesService initialized",
            extra={
                "reason": "Service creation",
                "extra_data": {},
            },
        )

    def enrich_categories(self, transactions: List[Dict], user_id: Optional[str] = None) -> List[Dict]:
        """
        Enriches transactions with category information.

        Args:
            transactions: List of transaction dictionaries
            user_id: Optional user ID for context

        Returns:
            List of enriched transaction dictionaries
        """
        enriched = []

        try:
            for transaction in transactions:
                enriched_transaction = {
                    **transaction,
                    "category": transaction.get("category") or self._infer_category(transaction.get("description", "")),
                }
                enriched.append(enriched_transaction)

            logger.info(
                f"Transactions enriched successfully",
                extra={
                    "reason": "Category enrichment complete",
                    "extra_data": {
                        "user_id": user_id,
                        "transaction_count": len(enriched),
                    },
                },
            )

            return enriched

        except Exception as e:
            logger.error(
                f"Error enriching categories: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Category enrichment failed",
                    "extra_data": {
                        "user_id": user_id,
                        "error_type": type(e).__name__,
                    },
                },
            )
            raise

    def _infer_category(self, description: str) -> str:
        """
        Infers a category from transaction description.

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
