import logging
from fastapi import APIRouter, Query
from services.di_container import DIContainer
from .responses import PaginatedResponse

router = APIRouter(prefix="/mcc", tags=["MCC Codes"])
logger = logging.getLogger(__name__)


@router.get("/all")
async def get_mcc():
    """
    Retrieves all MCC codes.
    """
    service = DIContainer.get_mcc_service()
    mcc = service.get_mcc()

    return PaginatedResponse(status="success", data=mcc, count=len(mcc))


@router.get("/")
async def get_mcc_by_id(
    category_code: str = Query(..., description="The MCC category code"),
):
    """
    Retrieves the description for a specific MCC code.
    """
    service = DIContainer.get_mcc_service()
    mcc = service.get_mcc_by_id(category_code)

    return PaginatedResponse(status="success", data=mcc, count=len(mcc))
