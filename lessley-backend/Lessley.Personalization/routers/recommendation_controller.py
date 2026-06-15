import logging
import time
from fastapi import APIRouter, Request, Query
from services.di_container import DIContainer
from .responses import BasicResponse, ClubRecommendationResponseSchema, DealRecommendationResponseSchema
from .schemas import (
    DealRequest,
    RecommendationByCategoryRequestSchema,
)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
logger = logging.getLogger(__name__)


@router.get("/club-by-category")
async def calculate_club_recommendation_by_category(
    request: Request, payload: RecommendationByCategoryRequestSchema = Query()
):
    """
    Calculate club recommendations for a user based on their spending habits.

    Analyzes user spending patterns and recommends clubs where the user's
    spending categories match a significant percentage of the club's stores.

    Args:
        payload: Request containing user_id, time_filter, days, use_mock, and threshold

    Returns:
        BasicResponse with ClubRecommendationResponseSchema
    """
    start_time = time.time()

    logger.info(
        "Club recommendation calculation requested",
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
        service = DIContainer.get_recommendation_service()
        user_club_ids = None
        if payload.user_club_ids:
            user_club_ids = [club_id.strip() for club_id in payload.user_club_ids.split(",") if club_id.strip()]

        result = await service.calculate_club_recommendation_by_category(
            payload.user_id,
            payload.time_filter,
            payload.days,
            payload.use_mock,
            payload.threshold,
            user_club_ids,
        )

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "Club recommendation calculation completed",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "user_id": payload.user_id,
                    "response_time_ms": response_time_ms,
                    "recommendation_count": len(result.get("recommendations", [])),
                    "method": request.method,
                    "endpoint": request.url.path,
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
            f"Error calculating club recommendations: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service execution failed",
                "extra_data": {
                    "user_id": payload.user_id,
                    "response_time_ms": response_time_ms,
                    "error_type": type(e).__name__,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


@router.get("/calculate-deal-recommendation")
async def calculate_deal_recommendation(request: Request, payload: DealRequest = Query()):
    """
    Calculate deal recommendation for a user based on store category fit.

    Determines if a specific deal is recommended by analyzing the store's MCC
    codes against the user's spending patterns.

    Args:
        payload: Request containing user_id, club_id, deal_id, and store_id

    Returns:
        BasicResponse with DealRecommendationResponseSchema
    """
    start_time = time.time()

    logger.info(
        "Deal recommendation calculation requested",
        extra={
            "reason": "Request received",
            "extra_data": {
                "user_id": payload.user_id,
                "deal_id": payload.deal_id,
                "store_id": payload.store_id,
                "club_id": payload.club_id,
                "use_mock": payload.use_mock,
                "time_filter": payload.time_filter,
                "days": payload.days,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_recommendation_service()
        result = await service.calculate_deal_recommendation_for_user(
            payload.user_id,
            payload.club_id,
            payload.deal_id,
            payload.store_id,
            payload.use_mock,
            payload.time_filter,
            payload.days,
            payload.threshold,
        )

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "Deal recommendation calculation completed",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "user_id": payload.user_id,
                    "deal_id": payload.deal_id,
                    "response_time_ms": response_time_ms,
                    "is_recommended": result.get("is_recommended"),
                    "fit_score": result.get("fit_score"),
                    "method": request.method,
                    "endpoint": request.url.path,
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
            f"Error calculating deal recommendation: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service execution failed",
                "extra_data": {
                    "user_id": payload.user_id,
                    "deal_id": payload.deal_id,
                    "response_time_ms": response_time_ms,
                    "error_type": type(e).__name__,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise
