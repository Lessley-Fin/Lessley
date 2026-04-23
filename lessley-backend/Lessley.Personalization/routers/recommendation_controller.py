import logging
import time
from fastapi import APIRouter, Request, Query
from services.di_container import DIContainer
from .responses import BasicResponse
from .schemas import (
    DealRequest,
    RecommendationByCategoryRequestSchema,
    ClubRecommendationResponseSchema,
    DealRecommendationResponseSchema,
)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
logger = logging.getLogger(__name__)


# here
@router.get("/club-by-category")
async def get_club_recommendation_by_category(
    request: Request, payload: RecommendationByCategoryRequestSchema = Query()
):
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
            payload.user_id, payload.time_filter, payload.days, payload.use_mock, payload.threshold
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


@router.post("/calculate-deal-recommendation")
async def calculate_deal_recommendation(request: Request, payload: DealRequest = Query()):
    """
    Gets a deal recommendation for a user based on their spending habits
    and the category fit of the store where the deal is offered.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "user_id": payload.user_id,
                "club_id": payload.club_id,
                "deal_id": payload.deal_id,
                "store_id": payload.store_id,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        # Call service to calculate recommendations
        service = DIContainer.get_recommendation_service()
        result = await service.calculate_deal_recommendation_for_user(
            payload.user_id, payload.club_id, payload.deal_id, payload.store_id
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
                    "is_recommended": result.get("is_recommended"),
                    "fit_score": result.get("fit_score"),
                },
            },
        )

        return BasicResponse(
            status="success",
            data=DealRecommendationResponseSchema(**result),
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
