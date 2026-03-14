from fastapi import APIRouter, Query
from services.di_container import DIContainer
from .schemas import InsightsCalcRequests
from .responses import PaginatedResponse
import logging

# TODO: add logging to this file
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/categories")
async def calculate_user_categories(request: InsightsCalcRequests = Query()):
    """
    Triggers the calculation of optimal categories based on Open Finance data.
    """
    # Await the async service call
    service = DIContainer.get_insights_service()
    categories = await service.calculate_user_categories_async(
        request.user_id, request.time_filter, request.days, request.use_mock
    )

    return PaginatedResponse(status="success", data=categories, count=len(categories))


@router.get("/top-accounts")
async def calculate_top_accounts(request: InsightsCalcRequests = Query()):
    """
    Triggers the calculation of top accounts based on Open Finance data.
    """
    # Await the async service call
    service = DIContainer.get_insights_service()
    accounts = await service.calculate_top_accounts_async(
        request.user_id, request.time_filter, request.days, request.use_mock
    )

    return PaginatedResponse(status="success", data=accounts, count=len(accounts))


@router.get("/top-stores")
async def calculate_top_stores(request: InsightsCalcRequests = Query()):
    """
    Triggers the calculation of top stores based on Open Finance data.
    """
    # Await the async service call
    service = DIContainer.get_insights_service()
    stores = await service.calculate_top_stores_async(
        request.user_id, request.time_filter, request.days, request.use_mock
    )

    return PaginatedResponse(status="success", data=stores, count=len(stores))
