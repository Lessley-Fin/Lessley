import logging
import time
from fastapi import APIRouter, HTTPException, status, Request
from services.di_container import DIContainer
from .responses import BasicResponse
from .schemas import (
    StoreCategoryRequestSchema,
    StoreCategoryResponseSchema,
    DealCategoryRequestSchema,
    DealCategoryResponseSchema,
    ClassifyDealRequestSchema,
    ClassifyDealResponseSchema,
    ClassifyAllStoresRequestSchema,
    ClassifyAllStoresResponseSchema,
)

router = APIRouter(prefix="/categories", tags=["Categories"])
logger = logging.getLogger(__name__)


@router.post("/store-mcc")
async def get_store_mcc(request: Request, payload: StoreCategoryRequestSchema):
    """
    Classifies a store and returns its primary category and MCC code.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "method": request.method,
                "endpoint": request.url.path,
                "store_name": payload.store_name,
            },
        },
    )

    try:
        service = DIContainer.get_categories_service()
        result = service.get_store_mcc(payload.store_name)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                },
            },
        )

        return BasicResponse(
            status="success",
            data=StoreCategoryResponseSchema(**result),
        )

    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Store MCC classification failed: {str(e)}",
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
            detail="Failed to classify store",
        )


@router.post("/deal-category")
async def get_deal_category(request: Request, payload: DealCategoryRequestSchema):
    """
    Classifies a deal/promotion and returns its category and relevance.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "method": request.method,
                "endpoint": request.url.path,
                "deal_name": payload.deal_name,
            },
        },
    )

    try:
        service = DIContainer.get_categories_service()
        result = service.get_deal_category(payload.deal_name, payload.deal_description)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                },
            },
        )

        return BasicResponse(
            status="success",
            data=DealCategoryResponseSchema(**result),
        )

    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Deal category classification failed: {str(e)}",
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
            detail="Failed to classify deal",
        )


@router.post("/classify-deal")
async def classify_deal(request: Request, payload: ClassifyDealRequestSchema):
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "method": request.method,
                "endpoint": request.url.path,
                "deal_id": payload.deal_id,
            },
        },
    )

    try:
        service = DIContainer.get_categories_service()
        result = service.classify_deal(payload.deal_id)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "deal_id": payload.deal_id,
                },
            },
        )

        return BasicResponse(
            status="success",
            data=ClassifyDealResponseSchema(**result),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Deal classification failed: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service processing error",
                "extra_data": {
                    "response_time_ms": response_time_ms,
                    "error_type": type(e).__name__,
                    "deal_id": payload.deal_id,
                },
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to classify deal",
        )


@router.post("/classify-all-stores")
async def classify_all_stores(request: Request, payload: ClassifyAllStoresRequestSchema):
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "method": request.method,
                "endpoint": request.url.path,
                "page": payload.page,
                "page_size": payload.page_size,
            },
        },
    )

    try:
        service = DIContainer.get_categories_service()
        result = service.classify_all_stores(page=payload.page, page_size=payload.page_size)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "classified": result["classified"],
                    "total": result["total_stores"],
                },
            },
        )

        return BasicResponse(
            status="success",
            data=ClassifyAllStoresResponseSchema(**result),
        )

    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Batch classification failed: {str(e)}",
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
            detail="Failed to classify stores",
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
