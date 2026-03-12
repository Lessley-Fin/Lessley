from fastapi import APIRouter, HTTPException, status, Query
from services.di_container import DIContainer
from .schemas import InsightsCalcRequests
import logging

# TODO: add logging to this file
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/categories")
async def calculate_user_categories(request: InsightsCalcRequests = Query()):
    """
    Triggers the calculation of optimal categories based on Open Finance data.
    """
    try:
        # Await the async service call
        service = DIContainer.get_insights_service()
        categories = await service.calculate_user_categories_async(
            request.user_id, request.time_filter, request.days, request.use_mock
        )

        return {"categories": categories}
    except ValueError as e:
        logger.warning(f"Invalid input for user {request.user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parameters")

    except Exception as e:
        logger.error(f"Unexpected error calculating categories: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service error")


@router.get("/top-accounts")
async def calculate_top_accounts(request: InsightsCalcRequests = Query()):
    """
    Triggers the calculation of top accounts based on Open Finance data.
    """
    try:
        # Await the async service call
        service = DIContainer.get_insights_service()
        accounts = await service.calculate_top_accounts_async(
            request.user_id, request.time_filter, request.days, request.use_mock
        )

        return {
            "message": f"Successfully retrieved data for user {request.user_id}",
            "accounts": accounts,
            "status": "Calculation initiated",
        }

    except ValueError as e:
        logger.warning(f"Invalid input for user {request.user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parameters")

    except Exception as e:
        logger.error(f"Unexpected error calculating top accounts: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service error")


@router.get("/top-stores")
async def calculate_top_stores(request: InsightsCalcRequests = Query()):
    """
    Triggers the calculation of top stores based on Open Finance data.
    """
    try:
        # Await the async service call
        service = DIContainer.get_insights_service()
        stores = await service.calculate_top_stores_async(
            request.user_id, request.time_filter, request.days, request.use_mock
        )

        return {
            "message": f"Successfully retrieved data for user {request.user_id}",
            "stores": stores,
            "status": "Calculation initiated",
        }

    except ValueError as e:
        logger.warning(f"Invalid input for user {request.user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parameters")

    except Exception as e:
        logger.error(f"Unexpected error calculating top stores: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service error")
