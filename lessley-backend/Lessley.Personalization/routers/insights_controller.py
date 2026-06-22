from fastapi import APIRouter, Query, Request
from services.di_container import DIContainer
from .schemas import InsightsCalcRequests
from .responses import PaginatedResponse
import logging
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
    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": req.email,
                "time_filter": req.time_filter,
                "days": req.days,
                "use_mock": req.use_mock,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        # Await the async service call
        service = DIContainer.get_insights_service()
        categories = await service.calculate_user_categories_async(req.email, req.time_filter, req.days, req.use_mock)

        response_time_ms = (time.time() - start_time) * 1000

        # Log successful response
        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": req.email,
                    "time_filter": req.time_filter,
                    "days": req.days,
                    "use_mock": req.use_mock,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "record_count": len(categories),
                },
            },
        )

        return PaginatedResponse(status="success", data=categories, count=len(categories))

    except Exception as e:
        logger.error(
            f"Error calculating user categories: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service call failed",
                "extra_data": {
                    "email": req.email,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


# logger("info", "Received request for top accounts calculation", extra={"email": req.email, "time_filter": req.time_filter, "days": req.days})


@router.get("/top-accounts")
async def calculate_top_accounts(request: Request, req: InsightsCalcRequests = Query()):
    """
    Triggers the calculation of top accounts based on Open Finance data.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": req.email,
                "time_filter": req.time_filter,
                "days": req.days,
                "use_mock": req.use_mock,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        # Await the async service call
        service = DIContainer.get_insights_service()
        accounts = await service.calculate_top_accounts_async(req.email, req.time_filter, req.days, req.use_mock)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": req.email,
                    "time_filter": req.time_filter,
                    "days": req.days,
                    "use_mock": req.use_mock,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "record_count": len(accounts),
                },
            },
        )

        return PaginatedResponse(status="success", data=accounts, count=len(accounts))

    except Exception as e:
        logger.error(
            f"Error calculating top accounts: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service call failed",
                "extra_data": {
                    "email": req.email,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


@router.get("/top-stores")
async def calculate_top_stores(request: Request, req: InsightsCalcRequests = Query()):
    """
    Triggers the calculation of top stores based on Open Finance data.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": req.email,
                "time_filter": req.time_filter,
                "days": req.days,
                "use_mock": req.use_mock,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        # Await the async service call
        service = DIContainer.get_insights_service()
        stores = await service.calculate_top_stores_async(req.email, req.time_filter, req.days, req.use_mock)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": req.email,
                    "time_filter": req.time_filter,
                    "days": req.days,
                    "use_mock": req.use_mock,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "record_count": len(stores),
                },
            },
        )

        return PaginatedResponse(status="success", data=stores, count=len(stores))

    except Exception as e:
        logger.error(
            f"Error calculating top stores: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service call failed",
                "extra_data": {
                    "email": req.email,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


@router.get("/missed-savings")
async def calculate_missed_savings(request: Request, req: InsightsCalcRequests = Query()):
    """
    Triggers the calculation of missed savings opportunities based on user transactions and available deals.
    Analyzes if the user could have received better discounts at alternative stores.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": req.email,
                "time_filter": req.time_filter,
                "days": req.days,
                "use_mock": req.use_mock,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        # Await the async service call
        service = DIContainer.get_insights_service()
        missed_savings = await service.calculate_missed_savings_async(
            req.email, req.time_filter, req.days, req.use_mock
        )

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": req.email,
                    "time_filter": req.time_filter,
                    "days": req.days,
                    "use_mock": req.use_mock,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "record_count": len(missed_savings),
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
                "extra_data": {
                    "email": req.email,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise
