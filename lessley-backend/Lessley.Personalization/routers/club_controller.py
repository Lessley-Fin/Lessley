import logging
import time
from fastapi import APIRouter, Request, Query
from services.di_container import DIContainer
from .schemas import ClubCalcRequests
from .responses import BasicResponse, ClubMccDistributionResponseSchema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clubs", tags=["Clubs"])


@router.get("/categories")
async def calculate_club_categories(request: Request, req: ClubCalcRequests = Query()):
    """
    Calculate MCC distribution for a specific club.

    Analyzes all stores in the specified club and returns a distribution of
    MCC codes sorted by the number of stores they appear in.

    Args:
        req: Request containing club_id

    Returns:
        BasicResponse with ClubMccDistributionResponseSchema
    """
    start_time = time.time()

    logger.info(
        "Club MCC distribution calculation requested",
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
        core_service = DIContainer.get_recommendation_core_service()
        result = core_service.get_club_mcc_distribution(req.club_id)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "Club MCC distribution calculation completed",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "club_id": req.club_id,
                    "response_time_ms": response_time_ms,
                    "mcc_count": len(result.get("categories", [])),
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )

        return BasicResponse(status="success", data=ClubMccDistributionResponseSchema(**result))

    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Error: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service execution failed",
                "extra_data": {
                    "club_id": req.club_id,
                    "response_time_ms": response_time_ms,
                    "error_type": type(e).__name__,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise
