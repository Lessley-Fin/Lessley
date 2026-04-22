from fastapi import APIRouter, Query, Request
from services.di_container import DIContainer
from .schemas import (
    InsightsCalcRequests,
    ClubMccDistributionResponseSchema,
)
from .responses import PaginatedResponse, BasicResponse
import logging
from collections import Counter
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/categories")
async def calculate_user_categories(request: Request, req: InsightsCalcRequests = Query()):
    """
    For a given club, analyzes all its stores and returns a distribution of
    MCCs, sorted by the number of stores they appear in.
    """
    start_time = time.time()

    # Log API request
    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "user_id": req.user_id,
                "club_id": req.club_id,
                "time_filter": req.time_filter,
                "days": req.days,
                "use_mock": req.use_mock,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        # Get the recommendation core service to access categories.json data
        core_service = DIContainer.get_recommendation_core_service()

        # Find the specific club
        club_to_analyze = None
        # Accessing a protected member to avoid creating new service functions per user request
        for club in core_service._categories_data:
            if club.get("club_id") == req.club_id:
                club_to_analyze = club
                break

        if not club_to_analyze:
            raise ValueError(f"Club with id '{req.club_id}' not found.")

        # Count MCCs across all stores in the club
        mcc_counts = Counter()
        stores = club_to_analyze.get("stores", [])
        for store in stores:
            # Count each MCC only once per store to get store count
            unique_mcc_in_store = set(store.get("mcc_codes", []))
            mcc_counts.update(unique_mcc_in_store)

        # Format the result
        relevant_categories = [{"mcc": int(mcc), "store_count": count} for mcc, count in mcc_counts.items()]

        # Sort by store_count descending
        relevant_categories.sort(key=lambda x: x["store_count"], reverse=True)

        result = {
            "club_id": club_to_analyze.get("club_id"),
            "club_name": club_to_analyze.get("name"),
            "relevant_category": relevant_categories,
        }

        response_time_ms = (time.time() - start_time) * 1000

        # Log successful response
        logger.info(
            "API response: 200",
            extra={"reason": "Request completed", "extra_data": {"user_id": req.user_id, "club_id": req.club_id, "method": request.method, "endpoint": request.url.path, "response_time_ms": response_time_ms, "mcc_count": len(relevant_categories)}},
        )

        return BasicResponse(status="success", data=ClubMccDistributionResponseSchema(**result))

    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Error calculating club MCC distribution: {str(e)}",
            exc_info=e,
            extra={"reason": "Service call failed", "extra_data": {"user_id": req.user_id, "club_id": req.club_id, "method": request.method, "endpoint": request.url.path, "response_time_ms": response_time_ms}},
        )
        raise

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
                "user_id": req.user_id,
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
        accounts = await service.calculate_top_accounts_async(req.user_id, req.time_filter, req.days, req.use_mock)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "user_id": req.user_id,
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
                    "user_id": req.user_id,
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
                "user_id": req.user_id,
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
        stores = await service.calculate_top_stores_async(req.user_id, req.time_filter, req.days, req.use_mock)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "user_id": req.user_id,
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
                    "user_id": req.user_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise
