import logging
from fastapi import APIRouter, Query
from services.di_container import DIContainer
from .schemas import UserRequests, GetTransactionsRequest, GetTransactionsByAccountRequest
from .responses import PaginatedResponse, BasicResponse

router = APIRouter(prefix="/open-finance", tags=["Open Finance"])
logger = logging.getLogger(__name__)


@router.get("/access-token")
async def get_user_access_token(
    request: UserRequests = Query(),
):
    """
    Retrieves user access token for the given user ID.
    """
    service = DIContainer.get_open_finance_service()
    token = await service.get_access_token_async(request.user_id)

    return BasicResponse(status="success", data={"access_token": token})


@router.get("/accounts")
async def get_user_accounts(
    request: UserRequests = Query(),
):
    """
    Retrieves user accounts for the given user ID.
    """
    service = DIContainer.get_open_finance_service()
    accounts = await service.get_user_accounts_async(request.user_id)

    return PaginatedResponse(status="success", data=accounts, count=len(accounts))


@router.get("/transactions/by-account")
async def get_user_transactions_by_account(request: GetTransactionsByAccountRequest = Query()):
    """
    Triggers the calculation of optimal clubs based on the last 3 months of Open Finance data.
    """
    service = DIContainer.get_open_finance_service()
    transactions = await service.get_user_transactions_by_account_async(
        request.user_id, request.account_id, request.time_filter, request.days
    )

    return PaginatedResponse(status="success", data=transactions, count=len(transactions))


@router.get("/transactions")
async def get_user_transactions(request: GetTransactionsRequest = Query()):
    """
    Triggers the calculation of optimal clubs based on the last 3 months of Open Finance data.
    """
    service = DIContainer.get_open_finance_service()
    transactions = await service.get_user_transactions_async(request.user_id, request.time_filter, request.days)

    return PaginatedResponse(status="success", data=transactions, count=len(transactions))
