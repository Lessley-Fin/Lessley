from fastapi import APIRouter, Query, HTTPException
from services.di_container import DIContainer

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/categories")
async def calculate_user_categories(
    userId: str = Query(..., description="The unique identifier of the user"),
    timeFilter: bool = Query(True, description="Whether to filter transactions by time"),
    days: int = Query(..., description="The number of days of transaction data to analyze"),
    useMock: bool = Query(False, description="Whether to use mock data instead of real transactions"),
):
    """
    Triggers the calculation of optimal categories based on Open Finance data.
    """
    try:
        # Await the async service call
        service = DIContainer.get_insights_service()
        categories = await service.calculate_user_categories_async(userId, timeFilter, days, useMock)

        return {"categories": categories}
    except Exception as e:
        # Return a 500 error if the external API fails
        raise HTTPException(status_code=500, detail=f"Failed to calculate categories: {str(e)}")


@router.get("/top-accounts")
async def calculate_top_accounts(
    userId: str = Query(..., description="The unique identifier of the user"),
    timeFilter: bool = Query(True, description="Whether to filter transactions by time"),
    days: int = Query(..., description="The number of days of transaction data to analyze"),
    useMock: bool = Query(False, description="Whether to use mock data instead of real transactions"),
):
    """
    Triggers the calculation of top accounts based on Open Finance data.
    """
    try:
        # Await the async service call
        service = DIContainer.get_insights_service()
        accounts = await service.calculate_top_accounts_async(userId, timeFilter, days, useMock)

        return {
            "message": f"Successfully retrieved data for user {userId}",
            "accounts": accounts,
            "status": "Calculation initiated",
        }
    except Exception as e:
        # Return a 500 error if the external API fails
        raise HTTPException(status_code=500, detail=f"Failed to calculate top accounts: {str(e)}")


@router.get("/top-stores")
async def calculate_top_stores(
    userId: str = Query(..., description="The unique identifier of the user"),
    timeFilter: bool = Query(True, description="Whether to filter transactions by time"),
    days: int = Query(60, description="The number of days of transaction data to analyze"),
    useMock: bool = Query(True, description="Whether to use mock data instead of real transactions"),
):
    """
    Triggers the calculation of top stores based on Open Finance data.
    """
    try:
        # Await the async service call
        service = DIContainer.get_insights_service()
        stores = await service.calculate_top_stores_async(userId, timeFilter, days, useMock)

        return {
            "message": f"Successfully retrieved data for user {userId}",
            "stores": stores,
            "status": "Calculation initiated",
        }
    except Exception as e:
        # Return a 500 error if the external API fails
        raise HTTPException(status_code=500, detail=f"Failed to calculate top stores: {str(e)}")
