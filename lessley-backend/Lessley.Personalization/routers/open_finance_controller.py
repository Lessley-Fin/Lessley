import logging
import time
from fastapi import APIRouter, Depends, Query, Request
from dependencies.auth import authenticated_email
from services.di_container import DIContainer
from .schemas import GetTransactionsRequest, GetTransactionsByAccountRequest
from .responses import PaginatedResponse, BasicResponse

router = APIRouter(prefix="/open-finance", tags=["Open Finance"])
logger = logging.getLogger(__name__)


@router.get("/access-token")
async def get_user_access_token(
    request: Request,
    email: str = Depends(authenticated_email),
):
    """
    Retrieves user access token for the authenticated user.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": email,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_open_finance_service()
        token = await service.get_access_token_async(email)

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
                },
            },
        )

        return BasicResponse(status="success", data={"access_token": token})

    except Exception as e:
        logger.error(
            f"Error retrieving access token: {str(e)}",
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


@router.get("/accounts")
async def get_user_accounts(
    request: Request,
    email: str = Depends(authenticated_email),
):
    """
    Retrieves bank accounts for the authenticated user.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": email,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_open_finance_service()
        accounts = await service.get_user_accounts_async(email)

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
                    "record_count": len(accounts),
                },
            },
        )

        return PaginatedResponse(status="success", data=accounts, count=len(accounts))

    except Exception as e:
        logger.error(
            f"Error retrieving user accounts: {str(e)}",
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


@router.get("/transactions/by-account")
async def get_user_transactions_by_account(
    request: Request,
    req: GetTransactionsByAccountRequest = Query(),
    email: str = Depends(authenticated_email),
):
    """
    Returns the authenticated user's transactions for a specific bank account.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": email,
                "account_id": req.account_id,
                "time_filter": req.time_filter,
                "days": req.days,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_open_finance_service()
        transactions = await service.get_user_transactions_by_account_async(
            email, req.account_id, req.time_filter, req.days
        )
        transactions = service.sort_transactions(transactions)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": email,
                    "account_id": req.account_id,
                    "time_filter": req.time_filter,
                    "days": req.days,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "response_time_ms": response_time_ms,
                    "record_count": len(transactions),
                },
            },
        )

        return PaginatedResponse(status="success", data=transactions, count=len(transactions))

    except Exception as e:
        logger.error(
            f"Error retrieving transactions by account: {str(e)}",
            exc_info=e,
            extra={
                "reason": "Service call failed",
                "extra_data": {
                    "email": email,
                    "account_id": req.account_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


@router.get("/transactions")
async def get_user_transactions(
    request: Request,
    req: GetTransactionsRequest = Query(),
    email: str = Depends(authenticated_email),
):
    """
    Returns the authenticated user's transactions across all of their accounts.
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
        service = DIContainer.get_open_finance_service()
        transactions = await service.get_user_transactions_async(email, req.time_filter, req.days)
        transactions = service.sort_transactions(transactions)
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
                    "record_count": len(transactions),
                },
            },
        )

        return PaginatedResponse(status="success", data=transactions, count=len(transactions))

    except Exception as e:
        logger.error(
            f"Error retrieving transactions: {str(e)}",
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
