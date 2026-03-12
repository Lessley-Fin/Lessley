import logging
from fastapi import APIRouter, Query, HTTPException, status
from services.di_container import DIContainer
from .schemas import UserRequests, GetTransactionsRequest, GetTransactionsByAccountRequest

router = APIRouter(prefix="/open-finance", tags=["Open Finance"])
logger = logging.getLogger(__name__)


@router.get("/access-token")
async def get_user_access_token(
    request: UserRequests = Query(),
):
    """
    Retrieves user access token for the given user ID.
    """
    try:
        service = DIContainer.get_open_finance_service()
        token = await service.get_access_token_async(request.user_id)

        return {
            "message": f"Successfully retrieved access token for user {request.user_id}",
            "token": token,
            "status": "Access token retrieved",
        }
    except ValueError as e:
        logger.warning(f"Invalid input for userId {request.user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parameters")
    except Exception as e:
        logger.error(f"Failed to retrieve access token for user {request.user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service error")


@router.get("/accounts")
async def get_user_accounts(
    request: UserRequests = Query(),
):
    """
    Retrieves user accounts for the given user ID.
    """
    try:
        service = DIContainer.get_open_finance_service()
        accounts = await service.get_user_accounts_async(request.user_id)

        return {
            "message": f"Successfully retrieved data for user {request.user_id}",
            "accounts_count": len(accounts),
            "items": accounts,
            "status": "Accounts retrieved",
        }
    except ValueError as e:
        logger.warning(f"Invalid input for userId {request.user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parameters")
    except Exception as e:
        logger.error(f"Failed to retrieve user accounts for user {request.user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service error")


@router.get("/transactions/by-account")
async def get_user_transactions_by_account(request: GetTransactionsByAccountRequest = Query()):
    """
    Triggers the calculation of optimal clubs based on the last 3 months of Open Finance data.
    """
    try:
        # Await the async service call
        service = DIContainer.get_open_finance_service()
        transactions = await service.get_user_transactions_by_account_async(
            request.user_id, request.account_id, request.time_filter, request.days
        )

        return {
            "message": f"Successfully retrieved data for user {request.user_id}",
            "transactions_analyzed": len(transactions),
            "items": transactions,
            "status": "Calculation initiated",
        }
    except ValueError as e:
        logger.warning(f"Invalid input for userId {request.user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parameters")
    except Exception as e:
        logger.error(f"Failed to retrieve user transactions for user {request.user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service error")


@router.get("/transactions")
async def get_user_transactions(request: GetTransactionsRequest = Query()):
    """
    Triggers the calculation of optimal clubs based on the last 3 months of Open Finance data.
    """
    try:
        # Await the async service call
        service = DIContainer.get_open_finance_service()
        transactions = await service.get_user_transactions_async(request.user_id, request.time_filter, request.days)

        return {
            "message": f"Successfully retrieved data for user {request.user_id}",
            "transactions_analyzed": len(transactions),
            "items": transactions,
            "status": "Calculation initiated",
        }
    except ValueError as e:
        logger.warning(f"Invalid input for userId {request.user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parameters")
    except Exception as e:
        logger.error(f"Failed to retrieve user transactions for user {request.user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service error")
