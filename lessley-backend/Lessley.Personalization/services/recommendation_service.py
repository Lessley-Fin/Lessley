import logging
from typing import Dict, List

from fastapi import HTTPException

from .recommendation_core_service import RecommendationCoreService
from .user_repository import UserRepository
from .publisher_service import PublisherService
from .mcc_service import MccService

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Orchestrates club recommendations and deal broadcast notifications.

    Tags are read from UserRepository (pre-computed by InsightsService and stored via the
    Gateway) instead of recalculating them on every call.
    """

    def __init__(
        self,
        recommendation_core_service: RecommendationCoreService,
        user_repository: UserRepository,
        publisher_service: PublisherService,
        mcc_service: MccService,
    ):
        self.recommendation_core_service = recommendation_core_service
        self.user_repository = user_repository
        self.publisher_service = publisher_service
        self.mcc_service = mcc_service

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _mcc_codes_from_tags(self, tags: List[str]) -> List[int]:
        """Convert stored category tags (MCC string labels) to MCC codes."""
        mcc_set: set[int] = set()
        for tag in tags:
            mcc_set.update(self.mcc_service.get_mcc_codes_by_tag(tag))
        return list(mcc_set)

    # ── Club matching ─────────────────────────────────────────────────────────

    async def calculate_matching_clubs(self, user_id: str) -> Dict:
        """
        Recommend clubs for user_id based on their pre-computed category tags.

        Fetches stored tags from UserRepository (raises 404 if user not registered),
        converts them to MCC codes, and scores every club against those codes.
        """
        logger.info(
            "Club matching started",
            extra={"reason": "Service method invoked", "extra_data": {"email": user_id}},
        )

        try:
            tags = await self.user_repository.get_user_tags(user_id)
            mcc_codes = self._mcc_codes_from_tags(tags)

            result = self.recommendation_core_service.get_club_recommendations_by_spending_analysis(
                user_id, mcc_codes
            )

            if self.publisher_service:
                await self.publisher_service.publish_matching_clubs_calculated(user_id, result)

            logger.info(
                "Club matching completed",
                extra={
                    "reason": "Service execution complete",
                    "extra_data": {
                        "email": user_id,
                        "tag_count": len(tags),
                        "mcc_code_count": len(mcc_codes),
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
                    "extra_data": {"email": user_id, "error_type": type(e).__name__},
                },
            )
            raise

    # ── Broadcast ─────────────────────────────────────────────────────────────

    async def publish_broadcast_deal(self, deal_id: str, message: str) -> List[str]:
        """
        Broadcast a deal notification to the deal's category group(s).

        The deal's category is read from the store the deal belongs to (its MCC codes); the
        Gateway routes the DealGroupNotification to all active SignalR connections in each
        category group. Raises 404 if the deal is unknown or has no resolvable category.
        """
        logger.info(
            "Broadcasting deal",
            extra={"reason": "Service method invoked", "extra_data": {"deal_id": deal_id}},
        )

        try:
            categories = self.recommendation_core_service.get_deal_categories(deal_id)
            if not categories:
                raise HTTPException(
                    status_code=404,
                    detail=f"Deal '{deal_id}' not found or has no resolvable category",
                )

            category_tags = [str(mcc) for mcc in categories]
            await self.publisher_service.publish_deal_notification(
                deal_id=deal_id,
                message=message,
                categories=category_tags,
            )

            logger.info(
                "Deal broadcast published",
                extra={
                    "reason": "Service execution complete",
                    "extra_data": {"deal_id": deal_id, "categories": category_tags},
                },
            )
            return category_tags

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Service execution failure",
                    "extra_data": {"deal_id": deal_id, "error_type": type(e).__name__},
                },
            )
            raise
