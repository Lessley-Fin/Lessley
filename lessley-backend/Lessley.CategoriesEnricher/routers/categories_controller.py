import logging
import time
import httpx
from fastapi import APIRouter, HTTPException, status, Request
from services.di_container import DIContainer
from .responses import BasicResponse
from config.settings import settings
from .schemas import (
    StoreCategoryRequestSchema,
    StoreCategoryResponseSchema,
    DealCategoryRequestSchema,
    DealCategoryResponseSchema,
    RecommendationByCategoryRequestSchema,
    RecommendationByCategoryResponseSchema,
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


@router.post("/recommendation-by-category")
async def get_club_recommendation_by_category(request: Request, payload: RecommendationByCategoryRequestSchema):
    """
    Gets club recommendations based on user's categories from the Personalization service.
    Fetches user categories, extracts MCC codes, and matches against available clubs.
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
        # Fetch user categories from Personalization service
        personalization_url = f"{settings.personalization_service_url}/insights/categories"
        
        logger.info(
            f"Fetching user categories from Personalization service",
            extra={
                "reason": "External service call",
                "extra_data": {
                    "user_id": payload.user_id,
                    "url": personalization_url,
                },
            },
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                personalization_url,
                params={
                    "user_id": payload.user_id,
                    "time_filter": True,
                    "days": 90,
                    "use_mock": False,
                },
                timeout=30.0,
            )
            
            if response.status_code != 200:
                error_detail = response.text
                logger.error(
                    f"Personalization service returned error: {response.status_code}\nResponse: {error_detail}",
                    extra={
                        "reason": "External service error response",
                        "extra_data": {
                            "user_id": payload.user_id,
                            "status_code": response.status_code,
                            "response_text": error_detail[:500],
                        },
                    },
                )
            
            response.raise_for_status()
            insights_data = response.json()

        # Log the full response for debugging
        logger.info(
            f"Personalization service response received",
            extra={
                "reason": "Service response debug",
                "extra_data": {
                    "user_id": payload.user_id,
                    "response_structure": str(type(insights_data)),
                    "response_keys": list(insights_data.keys()) if isinstance(insights_data, dict) else "not a dict",
                    "data_structure": str(insights_data.get("data", [])[:2]) if isinstance(insights_data, dict) else "no data key",
                },
            },
        )

        # Extract MCC codes from categories
        categories = insights_data.get("data", [])
        mcc_codes = []
        
        logger.info(
            f"Processing {len(categories)} categories",
            extra={
                "reason": "Category processing",
                "extra_data": {
                    "category_count": len(categories),
                    "first_category": str(categories[0]) if categories else "no categories",
                },
            },
        )
        
        for category in categories:
            if isinstance(category, dict) and "mcc_codes" in category:
                mcc_codes.extend(category.get("mcc_codes", []))
        
        # Convert string MCC codes to integers and remove duplicates
        try:
            mcc_codes = list(set(int(code) for code in mcc_codes if code))
        except (ValueError, TypeError):
            logger.warning(
                f"Some MCC codes could not be converted to integers",
                extra={
                    "reason": "MCC code conversion warning",
                    "extra_data": {
                        "user_id": payload.user_id,
                        "original_codes": mcc_codes,
                    },
                },
            )
            mcc_codes = list(set(int(code) for code in mcc_codes if code and str(code).isdigit()))

        logger.info(
            f"Extracted MCC codes from user categories",
            extra={
                "reason": "Data extraction complete",
                "extra_data": {
                    "user_id": payload.user_id,
                    "category_count": len(categories),
                    "mcc_codes_count": len(mcc_codes),
                    "mcc_codes_list": mcc_codes,
                },
            },
        )

        # Get club recommendations
        service = DIContainer.get_categories_service()
        result = service.get_club_recommendation_by_category(payload.user_id, mcc_codes)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "club_count": len(result.get("club_scores", [])),
                    "recommended_club": result.get("recommended_club", {}).get("club_name") if result.get("recommended_club") else None,
                },
            },
        )

        return BasicResponse(
            status="success",
            data=RecommendationByCategoryResponseSchema(**result),
        )

    except httpx.HTTPError as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Failed to fetch user categories from Personalization service: {str(e)}",
            exc_info=e,
            extra={
                "reason": "External service call failed",
                "extra_data": {
                    "user_id": payload.user_id,
                    "response_time_ms": response_time_ms,
                    "error_type": type(e).__name__,
                },
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch user categories from Personalization service",
        )

    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Club recommendation generation failed: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service processing error",
                "extra_data": {
                    "user_id": payload.user_id,
                    "response_time_ms": response_time_ms,
                    "error_type": type(e).__name__,
                },
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate club recommendations",
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
