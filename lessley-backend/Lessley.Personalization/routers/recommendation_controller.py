import logging
import time
from fastapi import APIRouter, Request
from services.di_container import DIContainer
from .responses import BasicResponse
from .schemas import (
    RecommendationByCategoryRequestSchema,
    RecommendationByCategoryResponseSchema,
)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
logger = logging.getLogger(__name__)


# here
@router.post("/club-by-category")
async def get_club_recommendation_by_category(request: Request, payload: RecommendationByCategoryRequestSchema):
    """
    Gets club recommendations based on user's spending categories.
    """
    start_time = time.time()

    # Log API request
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
            payload.user_id,
            time_filter=True,
            days=90,
        )

        response_time_ms = (time.time() - start_time) * 1000

        # Log successful response
        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "user_id": payload.user_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "club_count": len(result.get("club_scores", [])),
                    "recommended_club": result.get("recommended_club", {}).get("club_name")
                    if result.get("recommended_club")
                    else None,
                },
            },
        )

        return BasicResponse(
            status="success",
            data=RecommendationByCategoryResponseSchema(**result),
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
