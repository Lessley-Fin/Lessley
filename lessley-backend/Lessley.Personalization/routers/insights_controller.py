from fastapi import APIRouter, Depends, Request
from dependencies.auth import authenticated_email
from services.di_container import DIContainer
from .schemas import InsightsCalcRequests
from .responses import PaginatedResponse, BasicResponse
import logging
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/categories")
async def calculate_user_categories(
    request: Request,
    req: InsightsCalcRequests = Depends(),
    email: str = Depends(authenticated_email),
):
    """
    Triggers the calculation of optimal categories based on Open Finance data.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": email,
                "time_filter": req.time_filter,
                "days": req.days,
                "use_mock": req.use_mock,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        categories = await service.calculate_user_categories_async(email, req.time_filter, req.days, req.use_mock)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
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
                    "email": email,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


@router.get("/top-accounts")
async def calculate_top_accounts(
    request: Request,
    req: InsightsCalcRequests = Depends(),
    email: str = Depends(authenticated_email),
):
    """
    Triggers the calculation of top accounts based on Open Finance data.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": email,
                "time_filter": req.time_filter,
                "days": req.days,
                "use_mock": req.use_mock,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        accounts = await service.calculate_top_accounts_async(email, req.time_filter, req.days, req.use_mock)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
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
                    "email": email,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


@router.get("/top-stores")
async def calculate_top_stores(
    request: Request,
    req: InsightsCalcRequests = Depends(),
    email: str = Depends(authenticated_email),
):
    """
    Triggers the calculation of top stores based on Open Finance data.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": email,
                "time_filter": req.time_filter,
                "days": req.days,
                "use_mock": req.use_mock,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        stores = await service.calculate_top_stores_async(email, req.time_filter, req.days, req.use_mock)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
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
                    "email": email,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


@router.get("/spending-by-day-in-week")
async def calculate_spending_by_day_in_week(
    request: Request,
    req: InsightsCalcRequests = Depends(),
    email: str = Depends(authenticated_email),
):
    """
    Triggers the calculation of total spending per day of week based on Open Finance data.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": email,
                "time_filter": req.time_filter,
                "days": req.days,
                "use_mock": req.use_mock,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        spending_by_day = await service.calculate_spending_by_day_async(email, req.time_filter, req.days, req.use_mock)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
                    "time_filter": req.time_filter,
                    "days": req.days,
                    "use_mock": req.use_mock,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "record_count": len(spending_by_day),
                },
            },
        )

        return PaginatedResponse(status="success", data=spending_by_day, count=len(spending_by_day))

    except Exception as e:
        logger.error(
            f"Error calculating spending by day of week: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service call failed",
                "extra_data": {
                    "email": email,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


@router.get("/spending-difference-between-two-periods")
async def calculate_spending_difference_between_two_periods(
    request: Request,
    req: InsightsCalcRequests = Depends(),
    email: str = Depends(authenticated_email),
):
    """
    Triggers the calculation of the spending difference between the current and previous period.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": email,
                "time_filter": req.time_filter,
                "days": req.days,
                "use_mock": req.use_mock,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        difference = await service.calculate_spending_difference_async(email, req.time_filter, req.days, req.use_mock)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
                    "time_filter": req.time_filter,
                    "days": req.days,
                    "use_mock": req.use_mock,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    **difference,
                },
            },
        )

        return BasicResponse(status="success", data=difference)

    except Exception as e:
        logger.error(
            f"Error calculating spending difference between two periods: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service call failed",
                "extra_data": {
                    "email": email,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


@router.get("/spending-saved")
async def calculate_spending_saved(
    request: Request,
    req: InsightsCalcRequests = Depends(),
    email: str = Depends(authenticated_email),
):
    """
    Triggers the calculation of total spending saved (abs difference between charged and
    original amounts) based on Open Finance data.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": email,
                "time_filter": req.time_filter,
                "days": req.days,
                "use_mock": req.use_mock,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        total_saved = await service.calculate_spending_saved_async(email, req.time_filter, req.days, req.use_mock)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
                    "time_filter": req.time_filter,
                    "days": req.days,
                    "use_mock": req.use_mock,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "total_saved": total_saved,
                },
            },
        )

        return BasicResponse(status="success", data={"total_saved": total_saved})

    except Exception as e:
        logger.error(
            f"Error calculating spending saved: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service call failed",
                "extra_data": {
                    "email": email,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


@router.get("/spending-saved-by-account")
async def calculate_spending_saved_by_account(
    request: Request,
    req: InsightsCalcRequests = Depends(),
    email: str = Depends(authenticated_email),
):
    """
    Triggers the calculation of total spending saved, grouped by account.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": email,
                "time_filter": req.time_filter,
                "days": req.days,
                "use_mock": req.use_mock,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        saved_by_account = await service.calculate_spending_saved_by_account_async(
            email, req.time_filter, req.days, req.use_mock
        )

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
                    "time_filter": req.time_filter,
                    "days": req.days,
                    "use_mock": req.use_mock,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "record_count": len(saved_by_account),
                },
            },
        )

        return PaginatedResponse(status="success", data=saved_by_account, count=len(saved_by_account))

    except Exception as e:
        logger.error(
            f"Error calculating spending saved by account: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service call failed",
                "extra_data": {
                    "email": email,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise
