import logging
import time
from fastapi import APIRouter, Request
from services.di_container import DIContainer
from .responses import BasicResponse
from .schemas import (
    RecommendationByCategoryRequestSchema,
    RecommendationByCategoryResponseSchema,
    ClubRecommendationResponseSchema,
)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
logger = logging.getLogger(__name__)


# here
@router.get("/club-by-category")
async def get_club_recommendation_by_category(request: Request, payload: RecommendationByCategoryRequestSchema):
    """
    Gets club recommendations for a user based on their spending habits.
    Recommends clubs where the user's spending categories match a significant
    percentage of the club's stores (e.g., >20%).
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "user_id": payload.user_id,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        # Call service to calculate recommendations
        service = DIContainer.get_recommendation_service()
        result = await service.calculate_club_recommendation_by_category(
            payload.user_id, payload.time_filter, days=payload.days, threshold=payload.threshold
        )

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "user_id": payload.user_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "recommended_club_count": len(result.get("recommendations", [])),
                },
            },
        )

        return BasicResponse(
            status="success",
            data=ClubRecommendationResponseSchema(**result),
        )

    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Error: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service call failed",
                "extra_data": {
                    "user_id": payload.user_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                },
            },
        )
        raise
