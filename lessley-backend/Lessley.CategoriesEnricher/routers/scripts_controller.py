import logging
import time
from fastapi import APIRouter, HTTPException, status, Request
from services.di_container import DIContainer
from .responses import BasicResponse
from .schemas import DeleteInvalidStoresResponseSchema

router = APIRouter(prefix="/scripts", tags=["Scripts"])
logger = logging.getLogger(__name__)


@router.delete("/invalid-stores")
async def delete_invalid_stores(request: Request):
    """
    Deletes every store that has no deals or no store url.

    A store must include at least one deal AND a store url to be kept.
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
        service = DIContainer.get_scripts_service()
        result = service.delete_invalid_stores()

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "deleted": result["deleted"],
                },
            },
        )

        return BasicResponse(
            status="success",
            data=DeleteInvalidStoresResponseSchema(**result),
        )

    except ConnectionError:
        raise
    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Delete invalid stores failed: {str(e)}",
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
            detail="Failed to delete invalid stores",
        )
