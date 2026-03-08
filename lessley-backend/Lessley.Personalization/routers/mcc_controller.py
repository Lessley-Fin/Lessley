from fastapi import APIRouter, Query, HTTPException
from services.di_container import DIContainer

# The APIRouter acts just like a [Route("mcc")] attribute on a Controller class
router = APIRouter(prefix="/mcc", tags=["MCC Codes"])


@router.get("/all")
async def get_mcc():
    """
    Retrieves all MCC codes.
    """
    try:
        service = DIContainer.get_mcc_service()
        mcc = service.get_mcc()

        return {"mcc": mcc}
    except Exception as e:
        # Return a 500 error if loading MCC data fails
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve MCC codes: {str(e)}"
        )


@router.get("/")
async def get_mcc_by_id(
    categoryCode: str = Query(..., description="The MCC category code"),
):
    """
    Retrieves the description for a specific MCC code.
    """
    try:
        service = DIContainer.get_mcc_service()
        mcc = service.get_mcc_by_id(categoryCode)

        return {"mcc": mcc}
    except Exception as e:
        # Return a 500 error if loading MCC data fails
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve MCC code: {str(e)}"
        )
