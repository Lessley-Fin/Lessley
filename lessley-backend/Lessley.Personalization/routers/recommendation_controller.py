import logging
import time
from fastapi import APIRouter, Request
from services.di_container import DIContainer
from .responses import BasicResponse, ClubRecommendationResponseSchema, PaginatedResponse
from .schemas import RecommendationByCategoryRequestSchema

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
logger = logging.getLogger(__name__)


@router.post("/missed-savings")
async def calculate_missed_savings(request: Request, req: RecommendationByCategoryRequestSchema):
    """
    Triggers async missed-savings analysis for the user.
    Result is published back to Gateway via RabbitMQ and stored in the notifications DB.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {"email": req.email, "method": request.method, "endpoint": request.url.path},
        },
    )

    try:
        service = DIContainer.get_insights_service()
        missed_savings = await service.calculate_missed_savings_async(
            req.email, time_filter=True, days=90, use_mock=False
        )

        response_time_ms = (time.time() - start_time) * 1000
        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": req.email,
                    "response_time_ms": response_time_ms,
                    "record_count": len(missed_savings),
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )

        return PaginatedResponse(status="success", data=missed_savings, count=len(missed_savings))

    except Exception as e:
        logger.error(
            f"Error calculating missed savings: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service call failed",
                "extra_data": {"email": req.email, "method": request.method, "endpoint": request.url.path},
            },
        )
        raise


@router.post("/matching-clubs")
async def calculate_matching_clubs(request: Request, payload: RecommendationByCategoryRequestSchema):
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
