import logging
from fastapi import APIRouter, Query, HTTPException, status
from services.di_container import DIContainer
from .responses import BasicResponse, PaginatedResponse

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
    if mcc == "Unknown Category":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCC code {category_code} not found",
        )
    return BasicResponse(status="success", data=mcc)
