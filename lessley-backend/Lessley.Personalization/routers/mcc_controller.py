from fastapi import APIRouter, Depends, Query, HTTPException
from services.mcc_service import MccService, get_mcc_service

# The APIRouter acts just like a [Route("mcc")] attribute on a Controller class
router = APIRouter(prefix="/mcc", tags=["MCC Codes"])


@router.get("/all")
async def get_mcc(
    mcc_service: MccService = Depends(get_mcc_service),
):
    """
    Retrieves MCC codes.
    """
    try:
        # Await the async service call
        mcc = mcc_service.get_mcc()

        return {"mcc": mcc}
    except Exception as e:
        # Return a 500 error if the external API fails
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve MCC codes: {str(e)}"
        )


@router.get("/")
async def get_mcc_by_id(
    categoryCode: str = Query(..., description="The unique identifier of the user"),
    mcc_service: MccService = Depends(get_mcc_service),
):
    """
    Retrieves MCC codes.
    """
    try:
        # Await the async service call
        mcc = mcc_service.get_mcc_by_id(categoryCode)

        return {"mcc": mcc}
    except Exception as e:
        # Return a 500 error if the external API fails
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve MCC codes: {str(e)}"
        )
