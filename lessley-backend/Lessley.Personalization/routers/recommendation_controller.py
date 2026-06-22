import logging
import time
from fastapi import APIRouter, Request, Query
from services.di_container import DIContainer
from .responses import BasicResponse, ClubRecommendationResponseSchema
from .schemas import (
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
                "email": payload.email,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_recommendation_service()
        result = await service.calculate_matching_clubs(payload.email)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "Club matching completed",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": payload.email,
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
                    "email": payload.email,
                    "response_time_ms": response_time_ms,
                    "error_type": type(e).__name__,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


@router.get("/broadcast-deal")
async def broadcast_deal(request: Request, payload: BroadcastDealRequest = Query()):
    """
    Broadcast a deal notification to the deal's category group.

    Only the deal_id and message are supplied: the deal's category is resolved from the
    store the deal belongs to (the store's MCC code). The Gateway forwards the message to
    all active SignalR connections in that category group. Returns 404 if the deal is unknown.
    """
    start_time = time.time()

    logger.info(
        "Deal broadcast requested",
        extra={
            "reason": "Request received",
            "extra_data": {
                "deal_id": payload.deal_id,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_recommendation_service()
        categories = await service.publish_broadcast_deal(
            deal_id=payload.deal_id,
            message=payload.message,
        )

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "Deal broadcast published",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "deal_id": payload.deal_id,
                    "categories": categories,
                    "response_time_ms": response_time_ms,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )

        return BasicResponse(status="success", data={"deal_id": payload.deal_id, "categories": categories})

    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Error broadcasting deal: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service execution failed",
                "extra_data": {
                    "deal_id": payload.deal_id,
                    "response_time_ms": response_time_ms,
                    "error_type": type(e).__name__,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise
