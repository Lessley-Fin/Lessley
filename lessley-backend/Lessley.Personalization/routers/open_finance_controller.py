import logging
import time
from fastapi import APIRouter, Query, Request
from services.di_container import DIContainer
from .schemas import UserRequests, GetTransactionsRequest, GetTransactionsByAccountRequest
from .responses import PaginatedResponse, BasicResponse

router = APIRouter(prefix="/open-finance", tags=["Open Finance"])
logger = logging.getLogger(__name__)


@router.get("/access-token")
async def get_user_access_token(
    request: Request,
    req: UserRequests = Query(),
):
    """
    Retrieves user access token for the given user ID.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": req.email,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_open_finance_service()
        token = await service.get_access_token_async(req.email)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": req.email,
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
                    "email": req.email,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


@router.get("/accounts")
async def get_user_accounts(
    request: Request,
    req: UserRequests = Query(),
):
    """
    Retrieves user accounts for the given user ID.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": req.email,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_open_finance_service()
        accounts = await service.get_user_accounts_async(req.email)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": req.email,
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
                    "email": req.email,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


@router.get("/transactions/by-account")
async def get_user_transactions_by_account(request: Request, req: GetTransactionsByAccountRequest = Query()):
    """
    Triggers the calculation of optimal clubs based on the last 3 months of Open Finance data.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": req.email,
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
            req.email, req.account_id, req.time_filter, req.days
        )

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": req.email,
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
                    "email": req.email,
                    "account_id": req.account_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise


@router.get("/transactions")
async def get_user_transactions(request: Request, req: GetTransactionsRequest = Query()):
    """
    Triggers the calculation of optimal clubs based on the last 3 months of Open Finance data.
    """
    start_time = time.time()

    logger.info(
        f"API request: {request.method} {request.url}",
        extra={
            "reason": "Request received",
            "extra_data": {
                "email": req.email,
                "time_filter": req.time_filter,
                "days": req.days,
                "method": request.method,
                "endpoint": request.url.path,
            },
        },
    )

    try:
        service = DIContainer.get_open_finance_service()
        transactions = await service.get_user_transactions_async(req.email, req.time_filter, req.days)

        response_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "API response: 200",
            extra={
                "reason": "Request completed",
                "extra_data": {
                    "email": req.email,
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
                    "email": req.email,
                    "method": request.method,
                    "endpoint": request.url.path,
                },
            },
        )
        raise
