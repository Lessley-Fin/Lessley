import logging
from typing import Dict, List

from fastapi import HTTPException
from functional import seq

from .reference_data_repository import ReferenceDataRepository
from .user_repository import UserRepository
from .publisher_service import PublisherService
from .mcc_service import MccService
from config.constants import LIMITS
from models.db.entities import Store

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Decides which clubs are worth joining, and announces deals to the people who care.

    Tags are read from UserRepository (pre-computed by InsightsService and stored via the
    Gateway) instead of recalculating them on every call. Clubs, stores and deals are read
    from ReferenceDataRepository.
    """

    def __init__(
        self,
        reference_data_repository: ReferenceDataRepository,
        user_repository: UserRepository,
        publisher_service: PublisherService,
        mcc_service: MccService,
    ):
        self.reference_data_repository = reference_data_repository
        self.user_repository = user_repository
        self.publisher_service = publisher_service
        self.mcc_service = mcc_service

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _mcc_codes_from_tags(self, tags: List[str]) -> List[str]:
        """Convert stored category tags to category name strings."""
        category_set: set[str] = set()
        for tag in tags:
            category_set.update(self.mcc_service.get_mcc_codes_by_tag(tag))
        return list(category_set)

    @staticmethod
    def _categories_sold_by(store: Store) -> List[str]:
        """The kinds of things this shop sells."""
        if not store:
            return []
        try:
            return (
                seq(store.metadata.mcc_codes)          # the categories on the shop's record
                .where(lambda category: category)      # ignoring blank ones
                .to_list()
            )
        except Exception as e:
            logger.debug(
                f"Error extracting categories from store: {str(e)}",
                extra={"reason": "Data parsing", "extra_data": {"error_type": type(e).__name__}},
            )
            return []

    # ── Club matching ─────────────────────────────────────────────────────────

    def score_clubs(self, mcc_codes: List[str]) -> List[Dict]:
        """How well each club fits a user who spends on these categories."""
        spends_on = set(mcc_codes)

        return (
            seq(self.reference_data_repository.all_clubs().values())    # every club we know
            .select(lambda club: self._score_one_club(club, spends_on))  # scored against this user
            .to_list()
        )

    def _score_one_club(self, club, spends_on: set) -> Dict:
        """Count how many of this club's shops sell something the user actually buys."""
        store_ids = club.stores or []

        matching_stores = (
            seq(store_ids)                                                        # the club's shops
            .select(self.reference_data_repository.get_store)                     # looked up in full
            .where(lambda store: store)                                           # skipping ones we lack
            .where(lambda store: set(self._categories_sold_by(store)) & spends_on)  # selling what the user buys
            .size()                                                               # how many matched
        )

        return {
            "club_id": club.club_id,
            "club_name": club.name,
            "hit_count": matching_stores,
            "total_stores": len(store_ids),
        }

    def recommend_clubs(
        self,
        user_id: str,
        mcc_codes: List[str],
        threshold: float = LIMITS.HIT_THRESHOLD,
        user_club_ids: List[str] | None = None,
    ) -> Dict:
        """
        Analyzes all clubs against user's spending categories and recommends those that exceed a fit threshold.

        Args:
            user_id: The user ID.
            mcc_codes: List of MCC codes from user's spending.
            threshold: The minimum ratio of (matching stores / total stores) to be considered a recommendation.
            user_club_ids: The clubs the user has already joined.

        Returns:
            A dictionary containing a list of recommended clubs.
        """
        try:
            logger.info(
                f"Analyzing club fit for user: {user_id}",
                extra={
                    "reason": "Club fit analysis request received",
                    "extra_data": {
                        "user_id": user_id,
                        "mcc_codes_count": len(mcc_codes),
                        "threshold": threshold,
                    },
                },
            )

            already_joined = set(user_club_ids or [])

            recommendations = (
                seq(self.score_clubs(mcc_codes))                             # every club, scored
                .where(lambda score: score["total_stores"] > 0)              # ignoring empty clubs
                .select(lambda score: self._describe_fit(score, threshold, already_joined))
                .sorted(key=lambda club: club["fit_score"], reverse=True)    # best fit on top
                .to_list()
            )

        except Exception as e:
            logger.error(
                f"Error during club fit analysis: {str(e)}",
                exc_info=e,
                extra={"reason": "Club fit analysis failed", "extra_data": {"user_id": user_id}},
            )
            raise

        return {
            "email": user_id,
            "recommendations": recommendations,
        }

    @staticmethod
    def _describe_fit(score: Dict, threshold: float, already_joined: set) -> Dict:
        """Turn a raw club score into the verdict the client shows the user."""
        fit_score = score["hit_count"] / score["total_stores"]
        return {
            "club_id": score["club_id"],
            "club_name": score["club_name"],
            "hit_count": score["hit_count"],
            "total_stores": score["total_stores"],
            "fit_score": fit_score,
            "is_recommended": fit_score >= threshold,
            "is_member": score["club_id"] in already_joined,
        }

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
            user_club_ids = await self.user_repository.get_user_clubs(user_id)

            result = self.recommend_clubs(user_id, mcc_codes, user_club_ids=user_club_ids)

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

    def get_deal_categories(self, deal_id: str) -> List[str]:
        """
        Resolve a deal's categories from the store it belongs to.

        Looks up the deal → its store → the store's MCC codes. Those MCC codes are the deal's
        categories, used to broadcast the deal to the matching category groups. Returns an empty
        list if the deal or its store is unknown.
        """
        deal = self.reference_data_repository.get_deal(deal_id)
        if not deal:
            logger.warning(
                "Deal not found",
                extra={"reason": "Deal lookup failed", "extra_data": {"deal_id": deal_id}},
            )
            return []

        store = self.reference_data_repository.get_store(deal.store_id)
        if not store:
            logger.warning(
                "Store for deal not found",
                extra={
                    "reason": "Store lookup failed",
                    "extra_data": {"deal_id": deal_id, "store_id": deal.store_id},
                },
            )
            return []

        mcc_codes = self._categories_sold_by(store)
        logger.debug(
            "Deal categories resolved",
            extra={
                "reason": "Data lookup complete",
                "extra_data": {"deal_id": deal_id, "store_id": deal.store_id, "mcc_count": len(mcc_codes)},
            },
        )
        return mcc_codes

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
            categories = self.get_deal_categories(deal_id)
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
