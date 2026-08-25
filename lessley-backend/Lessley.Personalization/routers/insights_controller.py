from fastapi import APIRouter, Depends, Request
from dependencies.auth import authenticated_email
from services.di_container import DIContainer
from .schemas import InsightsCalcRequests
from .responses import BasicResponse, ClubRecommendationResponseSchema, PaginatedResponse
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
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        categories = await service.calculate_user_categories_async(email, req.time_filter, req.days)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
                    "time_filter": req.time_filter,
                    "days": req.days,
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
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        accounts = await service.calculate_top_accounts_async(email, req.time_filter, req.days)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
                    "time_filter": req.time_filter,
                    "days": req.days,
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
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        stores = await service.calculate_top_stores_async(email, req.time_filter, req.days)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
                    "time_filter": req.time_filter,
                    "days": req.days,
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
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        spending_by_day = await service.calculate_spending_by_day_async(email, req.time_filter, req.days)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
                    "time_filter": req.time_filter,
                    "days": req.days,
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
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        difference = await service.calculate_spending_difference_async(email, req.time_filter, req.days)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
                    "time_filter": req.time_filter,
                    "days": req.days,
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


@router.get("/spending-total")
async def calculate_spending_total(
    request: Request,
    req: InsightsCalcRequests = Depends(),
    email: str = Depends(authenticated_email),
):
    """
    Triggers the calculation of the headline spending total: money that left the account,
    less money that came back. Vouchers cost nothing and so do not appear here, unlike in the
    per-category and per-account breakdowns.
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
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        total = await service.calculate_spending_total_async(email, req.time_filter, req.days)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
                    "time_filter": req.time_filter,
                    "days": req.days,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    **total,
                },
            },
        )

        return BasicResponse(status="success", data=total)

    except Exception as e:
        logger.error(
            f"Error calculating spending total: {str(e)}",
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
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        saved = await service.calculate_spending_saved_async(email, req.time_filter, req.days)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
                    "time_filter": req.time_filter,
                    "days": req.days,
                        "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "total_saved": saved["total_amount"],
                },
            },
        )

        return BasicResponse(status="success", data=saved)

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
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        saved_by_account = await service.calculate_spending_saved_by_account_async(
            email, req.time_filter, req.days
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


@router.get("/matching-clubs")
async def matching_clubs(
    request: Request,
    email: str = Depends(authenticated_email),
):
    """
    Loyalty clubs worth joining, scored against the user's stored categories.

    Lives under /insights rather than /recommendations because the edge only routes
    /insights/* and /open-finance/* to this service. It answers from stored tags and
    in-memory reference data, so it returns its result directly instead of going through a
    command and a notification to deliver the same thing later.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {"email": email, "method": request.method, "endpoint": request.url.path},
        },
    )

    try:
        service = DIContainer.get_recommendation_service()
        result = await service.calculate_matching_clubs(email)

        response_time_ms = (time.time() - start_time) * 1000
        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "recommendation_count": len(result.get("recommendations", [])),
                },
            },
        )

        return BasicResponse(status="success", data=ClubRecommendationResponseSchema(**result))

    except Exception as e:
        logger.error(
            f"Error calculating club matches: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service call failed",
                "extra_data": {"email": email, "method": request.method, "endpoint": request.url.path},
            },
        )
        raise


@router.get("/savings-opportunities")
async def savings_opportunities(
    request: Request,
    req: InsightsCalcRequests = Depends(),
    email: str = Depends(authenticated_email),
):
    """
    What the user missed and what their club card already took, ready to render.

    Lives here rather than under /recommendations because it answers a question about the
    user's own spending and returns its answer directly. The /recommendations endpoints are
    fire-and-forget triggers whose results come back through RabbitMQ, and the edge only
    routes /insights/* and /open-finance/* to this service.

    Every figure on screen is in this payload. Clients render it and total nothing: the band
    subtotals sum to `missed.total_amount` by construction, because each purchase is counted
    under its strongest band only. A client re-deriving any of it is a second implementation
    of the same rules and will eventually disagree with this one.

    Read `match_band` on a shop before wording anything: EXACT and STRONG mean the user shopped
    there; SIMILAR means only a line-of-business word matched ('קפה'), so it is somewhere
    *like* theirs and must be worded that way.
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
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_insights_service()
        answer = await service.calculate_savings_opportunities_async(
            email, req.time_filter, req.days
        )

        response_time_ms = (time.time() - start_time) * 1000
        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
                    "days": req.days,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "missed_purchases": answer.missed.purchase_count,
                    "applied_purchases": answer.applied.purchase_count,
                },
            },
        )

        # A single object, not a page of rows: the two halves are one answer, and `count` over
        # a list of shops was never a number any caller had a use for.
        return BasicResponse(status="success", data=answer)

    except Exception as e:
        logger.error(
            f"Error calculating savings opportunities: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service call failed",
                "extra_data": {"email": email, "method": request.method, "endpoint": request.url.path},
            },
        )
        raise
