import logging
from typing import Dict, List

from .recommendation_core_service import RecommendationCoreService
from .user_repository import UserRepository
from .publisher_service import PublisherService
from .mcc_service import MccService
from config.constants import LIMITS

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Orchestrates club/deal recommendations and deal broadcast notifications.

    Tags are read from UserRepository (pre-computed by InsightsService and stored via the
    Gateway) instead of recalculating them on every call (task 10).
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
        """Convert stored category tags back to MCC codes via reverse MCC lookup."""
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
        No threshold parameter — uses the project default (LIMITS.HIT_THRESHOLD).
        """
        logger.info(
            "Club matching started",
            extra={"reason": "Service method invoked", "extra_data": {"user_id": user_id}},
        )

        try:
            tags = await self.user_repository.get_user_tags(user_id)
            mcc_codes = self._mcc_codes_from_tags(tags)

            result = self.recommendation_core_service.get_club_recommendations_by_spending_analysis(
                user_id, mcc_codes
            )

            logger.info(
                "Club matching completed",
                extra={
                    "reason": "Service execution complete",
                    "extra_data": {
                        "user_id": user_id,
                        "tag_count": len(tags),
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
                    "extra_data": {"user_id": user_id, "error_type": type(e).__name__},
                },
            )
            raise

    # ── Deal recommendation ───────────────────────────────────────────────────

    async def calculate_deal_recommendation_for_user(
        self,
        user_id: str,
        club_id: str,
        deal_id: str,
        store_id: str,
    ) -> Dict:
        """
        Determine whether a specific deal is recommended for user_id.

        Reads pre-computed category tags from UserRepository (raises 404 if user not
        registered), converts to MCC codes, and computes store fit score.
        No threshold parameter — uses the project default (LIMITS.HIT_THRESHOLD).
        """
        logger.info(
            "Deal recommendation started",
            extra={
                "reason": "Service method invoked",
                "extra_data": {"user_id": user_id, "deal_id": deal_id},
            },
        )

        try:
            tags = await self.user_repository.get_user_tags(user_id)
            user_mcc_codes = self._mcc_codes_from_tags(tags)

            store_mcc_codes = self.recommendation_core_service.get_store_mcc_codes(club_id, store_id)

            user_mcc_set = set(user_mcc_codes)
            matching_codes = [code for code in store_mcc_codes if code in user_mcc_set]
            fit_score = len(matching_codes) / len(store_mcc_codes) if store_mcc_codes else 0.0
            is_recommended = fit_score >= LIMITS.HIT_THRESHOLD

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
                "Deal recommendation completed",
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
                    "extra_data": {"user_id": user_id, "error_type": type(e).__name__},
                },
            )
            raise

    # ── Broadcast ─────────────────────────────────────────────────────────────

    async def publish_broadcast_deal_by_category(
        self, deal_category: str, deal_id: str, message: str
    ) -> None:
        """
        Broadcast a deal notification to every user that belongs to deal_category tag group.
        Gateway routes the DealGroupNotification to all active SignalR connections in that group.
        """
        logger.info(
            "Broadcasting deal to category group",
            extra={
                "reason": "Service method invoked",
                "extra_data": {"deal_category": deal_category, "deal_id": deal_id},
            },
        )

        try:
            await self.publisher_service.publish_group_notification(
                group_tag=deal_category,
                message=message,
                deal_id=deal_id,
            )
            logger.info(
                "Deal broadcast published",
                extra={
                    "reason": "Service execution complete",
                    "extra_data": {"deal_category": deal_category, "deal_id": deal_id},
                },
            )
        except Exception as e:
            logger.error(
                f"Error: {str(e)}",
                exc_info=e,
                extra={
                    "reason": "Service execution failure",
                    "extra_data": {"deal_category": deal_category, "error_type": type(e).__name__},
                },
            )
            raise
