import logging
import time
from fastapi import APIRouter, Query, HTTPException, status, Request
from services.di_container import DIContainer
from .responses import BasicResponse, PaginatedResponse

router = APIRouter(prefix="/mcc", tags=["MCC Codes"])
logger = logging.getLogger(__name__)


@router.get("/all")
async def get_mcc(request: Request):
    """
    Retrieves all MCC codes.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_mcc_service()
        mcc = service.get_mcc()

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "record_count": len(mcc),
                },
            },
        )

        return PaginatedResponse(status="success", data=mcc, count=len(mcc))

    except Exception as e:
        logger.error(
            f"Error retrieving all MCC codes: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service call failed",
                "extra_data": {
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


@router.get("/")
async def get_mcc_by_id(
    request: Request,
    category_code: str = Query(..., description="The MCC category code"),
):
    """
    Retrieves the description for a specific MCC code.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "category_code": category_code,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_mcc_service()
        mcc = service.get_mcc_by_id(category_code)
        
        response_time_ms = (time.time() - start_time) * 1000

        if mcc == "Unknown Category":
            logger.warning(
                f"MCC code {category_code} not found",
                extra={
                    "reason": "Category not found",
                    "extra_data": {
                        "category_code": category_code,
                        "method": request.method,
                        "endpoint": request.url.path,
                        "response_time_ms": response_time_ms,
                    },
                },
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCC code {category_code} not found",
            )

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "category_code": category_code,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                },
            },
        )
        return BasicResponse(status="success", data=mcc)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving MCC code {category_code}: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service call failed",
                "extra_data": {
                    "category_code": category_code,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise
