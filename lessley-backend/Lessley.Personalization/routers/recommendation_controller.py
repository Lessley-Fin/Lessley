import logging
import time
from fastapi import APIRouter, Request, Query
from services.di_container import DIContainer
from .responses import BasicResponse, ClubRecommendationResponseSchema, DealRecommendationResponseSchema
from .schemas import (
    DealRequest,
    RecommendationByCategoryRequestSchema,
    BroadcastDealRequest,
)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
logger = logging.getLogger(__name__)


@router.get("/matching-clubs")
async def calculate_matching_clubs(
    request: Request, payload: RecommendationByCategoryRequestSchema = Query()
):
    """
    Return club recommendations for a user based on their stored category tags.

    Tags are pre-computed by InsightsService and persisted via the Gateway.
    Returns 404 if the user is not registered in Lessley.
    """
    start_time = time.time()

    logger.info(
        "Club matching requested",
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
        result = await service.calculate_matching_clubs(payload.user_id)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "Club matching completed",
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
            f"Error calculating club matches: {str(e)}",
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
    Determine whether a deal is recommended for a user based on their stored category tags.

    Returns 404 if the user is not registered in Lessley.
    """
    start_time = time.time()

    logger.info(
        "Deal recommendation requested",
        extra={
            "reason": "Request received",
            "extra_data": {
                "user_id": payload.user_id,
                "deal_id": payload.deal_id,
                "store_id": payload.store_id,
                "club_id": payload.club_id,
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
        )

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "Deal recommendation completed",
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


@router.get("/broadcast-deal")
async def broadcast_deal_by_category(request: Request, payload: BroadcastDealRequest = Query()):
    """
    Broadcast a deal notification to every user in the given category tag group.

    The Gateway forwards the message to all active SignalR connections that belong
    to the deal_category group.
    """
    start_time = time.time()

    logger.info(
        "Deal broadcast requested",
        extra={
            "reason": "Request received",
            "extra_data": {
                "deal_category": payload.deal_category,
                "deal_id": payload.deal_id,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_recommendation_service()
        await service.publish_broadcast_deal_by_category(
            deal_category=payload.deal_category,
            deal_id=payload.deal_id,
            message=payload.message,
        )

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "Deal broadcast published",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "deal_category": payload.deal_category,
                    "deal_id": payload.deal_id,
                    "response_time_ms": response_time_ms,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )

        return BasicResponse(status="success", data={"deal_category": payload.deal_category, "deal_id": payload.deal_id})

    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Error broadcasting deal: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service execution failed",
                "extra_data": {
                    "deal_category": payload.deal_category,
                    "deal_id": payload.deal_id,
                    "response_time_ms": response_time_ms,
                    "error_type": type(e).__name__,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise
