from fastapi import APIRouter, Query, Request
from services.di_container import DIContainer
from .schemas import InsightsCalcRequests
from .responses import PaginatedResponse
import logging
from config.structured_logging import StructuredLogger, log_api_request, log_api_response
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/categories")
async def calculate_user_categories(request: Request, req: InsightsCalcRequests = Query()):
    """
    Triggers the calculation of optimal categories based on Open Finance data.
    """
    start_time = time.time()

    # Log API request
    log_api_request(
        logger,
        endpoint="/insights/categories",
        method="GET",
        user_id=req.user_id,
        params={"time_filter": req.time_filter, "days": req.days},
    )

    try:
        # Await the async service call
        service = DIContainer.get_insights_service()
        categories = await service.calculate_user_categories_async(req.user_id, req.time_filter, req.days, req.use_mock)

        response_time_ms = (time.time() - start_time) * 1000

        # Log successful response
        log_api_response(
            logger,
            endpoint="/insights/categories",
            status_code=200,
            response_time_ms=response_time_ms,
            record_count=len(categories),
        )

        return PaginatedResponse(status="success", data=categories, count=len(categories))

    except Exception as e:
        StructuredLogger.log_with_context(
            logger,
            "error",
            f"Error calculating user categories: {str(e)}",
            reason="Service call failed",
            extra_data={"user_id": req.user_id, "endpoint": "/insights/categories"},
        )
        raise
# logger("info", "Received request for top accounts calculation", extra={"user_id": req.user_id, "time_filter": req.time_filter, "days": req.days})

@router.get("/top-accounts")
async def calculate_top_accounts(request: Request, req: InsightsCalcRequests = Query()):
    """
    Triggers the calculation of top accounts based on Open Finance data.
    """
    start_time = time.time()

    log_api_request(
        logger,
        endpoint="/insights/top-accounts",
        method="GET",
        user_id=req.user_id,
        params={"time_filter": req.time_filter, "days": req.days},
    )

    try:
        # Await the async service call
        service = DIContainer.get_insights_service()
        accounts = await service.calculate_top_accounts_async(req.user_id, req.time_filter, req.days, req.use_mock)

        response_time_ms = (time.time() - start_time) * 1000

        log_api_response(
            logger,
            endpoint="/insights/top-accounts",
            status_code=200,
            response_time_ms=response_time_ms,
            record_count=len(accounts),
        )

        return PaginatedResponse(status="success", data=accounts, count=len(accounts))

    except Exception as e:
        StructuredLogger.log_with_context(
            logger,
            "error",
            f"Error calculating top accounts: {str(e)}",
            reason="Service call failed",
            extra_data={"user_id": req.user_id, "endpoint": "/insights/top-accounts"},
        )
        raise


@router.get("/top-stores")
async def calculate_top_stores(request: Request, req: InsightsCalcRequests = Query()):
    """
    Triggers the calculation of top stores based on Open Finance data.
    """
    start_time = time.time()

    log_api_request(
        logger,
        endpoint="/insights/top-stores",
        method="GET",
        user_id=req.user_id,
        params={"time_filter": req.time_filter, "days": req.days},
    )

    try:
        # Await the async service call
        service = DIContainer.get_insights_service()
        stores = await service.calculate_top_stores_async(req.user_id, req.time_filter, req.days, req.use_mock)

        response_time_ms = (time.time() - start_time) * 1000

        log_api_response(
            logger,
            endpoint="/insights/top-stores",
            status_code=200,
            response_time_ms=response_time_ms,
            record_count=len(stores),
        )

        return PaginatedResponse(status="success", data=stores, count=len(stores))

    except Exception as e:
        StructuredLogger.log_with_context(
            logger,
            "error",
            f"Error calculating top stores: {str(e)}",
            reason="Service call failed",
            extra_data={"user_id": req.user_id, "endpoint": "/insights/top-stores"},
        )
        raise
