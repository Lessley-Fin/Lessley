from fastapi import APIRouter, Query, Request
from services.di_container import DIContainer
from .schemas import ClubCalcRequests
import logging
from .responses import BasicResponse, ClubMccDistributionResponseSchema
from collections import Counter
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clubs", tags=["Clubs"])


@router.post("/categories")
async def calculate_club_categories(request: Request, req: ClubCalcRequests = Query()):
    """
    For a given club, analyzes all its stores and returns a distribution of
    MCCs, sorted by the number of stores they appear in.
    """
    start_time = time.time()

    # Log API request
    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "club_id": req.club_id,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        # Get the recommendation core service to access categories.json data
        core_service = DIContainer.get_recommendation_core_service()

        # Find the specific club
        club_to_analyze = None
        # Accessing a protected member to avoid creating new service functions per user request
        for club in core_service._categories_data:
            if club.get("club_id") == req.club_id:
                club_to_analyze = club
                break

        if not club_to_analyze:
            raise ValueError(f"Club with id '{req.club_id}' not found.")

        # Count MCCs across all stores in the club
        mcc_counts = Counter()
        stores = club_to_analyze.get("stores", [])
        for store in stores:
            # Count each MCC only once per store to get store count
            unique_mcc_in_store = set(store.get("mcc_codes", []))
            mcc_counts.update(unique_mcc_in_store)

        # Format the result
        relevant_categories = [{"mcc": int(mcc), "store_count": count} for mcc, count in mcc_counts.items()]

        # Sort by store_count descending
        relevant_categories.sort(key=lambda x: x["store_count"], reverse=True)

        result = {
            "club_id": club_to_analyze.get("club_id"),
            "club_name": club_to_analyze.get("name"),
            "categories": relevant_categories,
        }

        response_time_ms = (time.time() - start_time) * 1000

        # Log successful response
        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "club_id": req.club_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "mcc_count": len(relevant_categories),
                },
            },
        )

        return BasicResponse(status="success", data=ClubMccDistributionResponseSchema(**result))

    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Error calculating club MCC distribution: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service call failed",
                "extra_data": {
                    "club_id": req.club_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                },
            },
        )
        raise
