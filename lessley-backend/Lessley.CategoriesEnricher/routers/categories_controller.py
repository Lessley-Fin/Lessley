import logging
import time
from fastapi import APIRouter, HTTPException, status, Request
from services.di_container import DIContainer
from .responses import BasicResponse, PaginatedResponse
from .schemas import CategoryEnrichmentRequestSchema

router = APIRouter(prefix="/categories", tags=["Categories"])
logger = logging.getLogger(__name__)


@router.post("/enrich")
async def enrich_categories(request: Request, payload: CategoryEnrichmentRequestSchema):
    """
    Enriches transactions with category information.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "method": request.method,
                "endpoint": request.url.path,
                "user_id": payload.user_id,
            },
        },
    )

    try:
        service = DIContainer.get_categories_service()
        enriched_transactions = service.enrich_categories(payload.transactions, payload.user_id)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "record_count": len(enriched_transactions),
                },
            },
        )

        return PaginatedResponse(status="success", data=enriched_transactions, count=len(enriched_transactions))

    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Category enrichment failed: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service processing error",
                "extra_data": {
                    "response_time_ms": response_time_ms,
                    "error_type": type(e).__name__,
                },
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enrich categories",
        )


@router.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint for the categories enricher service.
    """
    logger.info(
        "Health check",
        extra={
            "reason": "Health check endpoint called",
            "extra_data": {"endpoint": request.url.path},
        },
    )
    return BasicResponse(status="success", data={"service": "categories_enricher", "status": "healthy"})
