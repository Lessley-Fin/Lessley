from fastapi import APIRouter, Query, HTTPException
from services.di_container import DIContainer

# The APIRouter acts just like a [Route("user")] attribute on a Controller class
router = APIRouter(prefix="/user", tags=["Open Finance / Personalization"])


@router.get("/access-token")
async def get_user_access_token(
    userId: str = Query(..., description="The unique identifier of the user"),
):
    """
    Retrieves user access token for the given user ID.
    """
    try:
        service = DIContainer.get_open_finance_service()
        token = await service.get_access_token_async(userId)

        return {
            "message": f"Successfully retrieved access token for user {userId}",
            "token": token,
            "status": "Access token retrieved",
        }
    except Exception as e:
        # Return a 500 error if the external API fails
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve access token: {str(e)}"
        )


@router.get("/accounts")
async def get_user_accounts(
    userId: str = Query(..., description="The unique identifier of the user"),
):
    """
    Retrieves user accounts for the given user ID.
    """
    try:
        service = DIContainer.get_open_finance_service()
        accounts = await service.get_user_accounts_async(userId)

        return {
            "message": f"Successfully retrieved data for user {userId}",
            "accounts_count": len(accounts),
            "items": accounts,
            "status": "Accounts retrieved",
        }
    except Exception as e:
        # Return a 500 error if the external API fails
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve accounts: {str(e)}"
        )


@router.get("/transactions")
async def get_user_transactions(
    userId: str = Query(..., description="The unique identifier of the user"),
    days: int = Query(
        ..., description="The number of days of transaction data to retrieve"
    ),
):
    """
    Triggers the calculation of optimal clubs based on the last 3 months of Open Finance data.
    """
    try:
        # Await the async service call
        service = DIContainer.get_open_finance_service()
        transactions = await service.get_user_transactions_async(userId, days)

        return {
            "message": f"Successfully retrieved data for user {userId}",
            "transactions_analyzed": len(transactions),
            "items": transactions,
            "status": "Calculation initiated",
        }
    except Exception as e:
        # Return a 500 error if the external API fails
        raise HTTPException(
            status_code=500, detail=f"Failed to calculate clubs: {str(e)}"
        )


@router.get("/categories")
async def get_user_categories(
    userId: str = Query(..., description="The unique identifier of the user"),
):
    """
    Triggers the calculation of optimal categories based on the last 3 months of Open Finance data.
    """
    try:
        # Await the async service call
        service = DIContainer.get_open_finance_service()
        categories = await service.get_user_categories(userId)

        return {"categories": categories}
    except Exception as e:
        # Return a 500 error if the external API fails
        raise HTTPException(
            status_code=500, detail=f"Failed to calculate categories: {str(e)}"
        )


@router.post("/calc-clubs")
async def calculate_clubs(
    userId: str = Query(..., description="The unique identifier of the user"),
):
    """
    Triggers the calculation of optimal clubs based on the last 3 months of Open Finance data.
    """
    try:
        # Await the async service call
        service = DIContainer.get_open_finance_service()
        categories = await service.calculate_user_categories_async(userId)

        return {
            "message": f"Successfully retrieved data for user {userId}",
            "categories": categories,
            "status": "Calculation initiated",
        }
    except Exception as e:
        # Return a 500 error if the external API fails
        raise HTTPException(
            status_code=500, detail=f"Failed to calculate clubs: {str(e)}"
        )
