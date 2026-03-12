import logging
from fastapi import APIRouter, Query, HTTPException, status
from services.di_container import DIContainer

router = APIRouter(prefix="/mcc", tags=["MCC Codes"])
logger = logging.getLogger(__name__)


@router.get("/all")
async def get_mcc():
    """
    Retrieves all MCC codes.
    """
    try:
        service = DIContainer.get_mcc_service()
        mcc = service.get_mcc()

        return {"mcc": mcc}

    except ValueError as e:
        logger.warning(f"Invalid input for MCC codes: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parameters")
    except Exception as e:
        logger.error(f"Failed to retrieve MCC codes: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service error")


@router.get("/")
async def get_mcc_by_id(
    category_code: str = Query(..., description="The MCC category code"),
):
    """
    Retrieves the description for a specific MCC code.
    """
    try:
        service = DIContainer.get_mcc_service()
        mcc = service.get_mcc_by_id(category_code)

        return {"mcc": mcc}
    except ValueError as e:
        logger.warning(f"Invalid input for Mcc code {category_code}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parameters")
    except Exception as e:
        logger.error(f"Failed to retrieve MCC code {category_code}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service error")
