import logging
from typing import Dict, List

from functional import seq

from .reference_data_repository import ReferenceDataRepository
from .user_repository import UserRepository
from .mcc_service import MccService
from config.constants import LIMITS
from models.db.entities import Store

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Decides which clubs are worth joining.

    Tags are read from UserRepository (pre-computed by InsightsService and stored via the
    Gateway) instead of recalculating them on every call. Clubs and stores are read from
    ReferenceDataRepository, which holds them in memory — so this publishes nothing and waits
    on nothing, and its answer goes straight back to the caller.
    """

    def __init__(
        self,
        reference_data_repository: ReferenceDataRepository,
        user_repository: UserRepository,
        mcc_service: MccService,
    ):
        self.reference_data_repository = reference_data_repository
        self.user_repository = user_repository
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

        Answered synchronously over HTTP. It reads stored tags and scores them against
        reference data already held in memory — no upstream call, no transaction fetch — so
        the fire-and-forget command and the notification that used to carry the result back
        were machinery around an answer that could simply be returned.
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
