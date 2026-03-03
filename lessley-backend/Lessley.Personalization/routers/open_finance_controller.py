from fastapi import APIRouter, Depends, Query, HTTPException
from services.open_finance_service import OpenFinanceService, get_open_finance_service

# The APIRouter acts just like a [Route("user")] attribute on a Controller class
router = APIRouter(prefix="/user", tags=["Open Finance / Personalization"])


@router.post("/calc-clubs")
async def calculate_clubs(
    userId: str = Query(..., description="The unique identifier of the user"),
    open_finance_service: OpenFinanceService = Depends(get_open_finance_service),
):
    """
    Triggers the calculation of optimal clubs based on the last 3 months of Open Finance data.
    """
    try:
        # Await the async service call
        transactions = await open_finance_service.get_user_transactions_last_3_months(
            userId
        )

        # TODO: Pass 'transactions' to your ML Gap Analysis logic here

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


@router.get("/accounts")
async def get_user_accounts(
    userId: str = Query(..., description="The unique identifier of the user"),
    open_finance_service: OpenFinanceService = Depends(get_open_finance_service),
):
    """
    Retrieves user accounts for the given user ID.
    """
    try:
        accounts = await open_finance_service.get_user_accounts(userId)

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


@router.get("/access-token")
async def get_user_access_token(
    userId: str = Query(..., description="The unique identifier of the user"),
    open_finance_service: OpenFinanceService = Depends(get_open_finance_service),
):
    """
    Retrieves user access token for the given user ID.
    """
    try:
        token = await open_finance_service.http_get_access_token(userId)

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


@router.post("/calc-categories")
async def calculate_categories(
    userId: str = Query(..., description="The unique identifier of the user"),
    open_finance_service: OpenFinanceService = Depends(get_open_finance_service),
):
    """
    Triggers the calculation of optimal categories based on the last 3 months of Open Finance data.
    """
    try:
        # Await the async service call
        categories = await open_finance_service.calc_user_categories(userId)

        return {"categories": categories}
    except Exception as e:
        # Return a 500 error if the external API fails
        raise HTTPException(
            status_code=500, detail=f"Failed to calculate categories: {str(e)}"
        )
