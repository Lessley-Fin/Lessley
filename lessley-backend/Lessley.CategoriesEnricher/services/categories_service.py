import logging
from typing import Dict, List
from services.clients import llm_integration

logger = logging.getLogger(__name__)


class CategoriesService:
    """
    Service for enriching transactions with category information.
    Integrates with LLM for intelligent classification.
    """

    def __init__(self, mongo_repo=None):
        self._mongo_repo = mongo_repo

    def classify_deal(self, deal_id: str) -> Dict:
        if self._mongo_repo is None:
            raise ConnectionError("MongoDB is not configured for this service")

        try:
            logger.info(
                f"Classifying deal: {deal_id}",
                extra={
                    "reason": "Deal classification requested",
                    "extra_data": {"deal_id": deal_id},
                },
            )

            deal = self._mongo_repo.get_deal_by_id(deal_id)
            if not deal:
                raise ValueError(f"Deal not found: {deal_id}")

            store_id = deal["store_id"]
            store = self._mongo_repo.get_store_by_id(store_id)
            if not store:
                raise ValueError(f"Store not found: {store_id}")

            metadata = store.get("metadata", {})
            classification = llm_integration.classify_deal_store(
                deal_title=deal.get("title", ""),
                deal_description=deal.get("deal_description"),
                store_name=store.get("name", ""),
                store_url=metadata.get("store_url"),
                deal_url=deal.get("url"),
                benefit_url=deal.get("benefit_url"),
                store_image_urls=metadata.get("image_urls", []),
            )

            result = {
                "deal_id": deal_id,
                "deal_title": deal.get("title", ""),
                "store_id": store_id,
                "store_name": store.get("name", ""),
                "store_official_name": classification.store_official_name,
                "mcc_codes": [c.value for c in classification.mcc_codes],
                "confidence_level": classification.confidence_level,
                "reasoning": classification.reasoning,
            }

            logger.info(
                "Deal classification complete",
                extra={
                    "reason": "Deal classification success",
                    "extra_data": {
                        "deal_id": deal_id,
                        "store_name": store.get("name", ""),
                        "mcc_codes": result["mcc_codes"],
                        "confidence_level": classification.confidence_level,
                    },
                },
            )

            return result

        except (ValueError, ConnectionError):
            raise
        except Exception as e:
            logger.error(
                f"Error classifying deal: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Deal classification failed",
                    "extra_data": {
                        "deal_id": deal_id,
                        "error_type": type(e).__name__,
                    },
                },
            )
            raise

    def classify_all_stores(self, page: int = 1, page_size: int = 20) -> Dict:
        if self._mongo_repo is None:
            raise ConnectionError("MongoDB is not configured for this service")

        total = self._mongo_repo.count_stores()
        stores = self._mongo_repo.get_stores_page(page, page_size)
        classified = 0
        skipped = 0
        failed = 0
        results: List[Dict] = []

        logger.info(
            f"Starting batch classification: page {page}, page_size {page_size}, total {total}",
            extra={
                "reason": "Batch classification started",
                "extra_data": {"total_stores": total, "page": page, "page_size": page_size},
            },
        )

        for store in stores:
            store_id = store.get("id", "")
            store_name = store.get("name", "")

            deal = self._mongo_repo.get_first_deal_by_store_id(store_id)
            if not deal:
                skipped += 1
                results.append(
                    {
                        "store_id": store_id,
                        "store_name": store_name,
                        "store_official_name": store_name,
                        "mcc_codes": [],
                        "confidence_level": "",
                        "status": "skipped",
                        "error": "No deals found for store",
                    }
                )
                continue

            try:
                metadata = store.get("metadata", {})
                classification = llm_integration.classify_deal_store(
                    deal_title=deal.get("title", ""),
                    deal_description=deal.get("deal_description"),
                    store_name=store_name,
                    store_url=metadata.get("store_url"),
                    deal_url=deal.get("url"),
                    benefit_url=deal.get("benefit_url"),
                    store_image_urls=metadata.get("image_urls", []),
                )

                mcc_codes = [c.value for c in classification.mcc_codes]

                self._mongo_repo.update_store_mcc(
                    store_id=store_id,
                    mcc_codes=mcc_codes,
                    official_name=classification.store_official_name,
                    confidence=classification.confidence_level,
                )

                classified += 1
                results.append(
                    {
                        "store_id": store_id,
                        "store_name": store_name,
                        "store_official_name": classification.store_official_name,
                        "mcc_codes": mcc_codes,
                        "confidence_level": classification.confidence_level,
                        "status": "classified",
                    }
                )

                logger.info(
                    f"Classified store: {store_name} -> {mcc_codes}",
                    extra={
                        "reason": "Store classified in batch",
                        "extra_data": {"store_id": store_id, "mcc_codes": mcc_codes},
                    },
                )

            except Exception as e:
                failed += 1
                results.append(
                    {
                        "store_id": store_id,
                        "store_name": store_name,
                        "store_official_name": store_name,
                        "mcc_codes": [],
                        "confidence_level": "",
                        "status": "failed",
                        "error": str(e),
                    }
                )
                logger.error(
                    f"Failed to classify store: {store_name}: {e}",
                    exc_info=e,
                    extra={
                        "reason": "Batch classification error",
                        "extra_data": {"store_id": store_id, "error_type": type(e).__name__},
                    },
                )

        logger.info(
            f"Batch classification complete: {classified} classified, {skipped} skipped, {failed} failed",
            extra={
                "reason": "Batch classification finished",
                "extra_data": {"total": total, "classified": classified, "skipped": skipped, "failed": failed},
            },
        )

        return {
            "total_stores": total,
            "page": page,
            "page_size": page_size,
            "classified": classified,
            "skipped": skipped,
            "failed": failed,
            "results": results,
        }

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
