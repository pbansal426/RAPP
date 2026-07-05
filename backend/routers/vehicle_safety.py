from fastapi import APIRouter, HTTPException, status

from backend.schemas import ComplaintsSummaryResponse, RecallsResponse
from backend.services.nhtsa_safety import get_complaints_summary, get_open_recalls

router = APIRouter(prefix="/api/vehicle-safety", tags=["vehicle-safety"])


def _require_vehicle_identity(year: str, make: str, model: str) -> None:
    if not year.strip() or not make.strip() or not model.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="year, make, and model are all required.",
        )


@router.get("/recalls", response_model=RecallsResponse)
async def recalls(year: str, make: str, model: str) -> RecallsResponse:
    _require_vehicle_identity(year, make, model)
    return await get_open_recalls(make, model, year)


@router.get("/complaints-summary", response_model=ComplaintsSummaryResponse)
async def complaints_summary(
    year: str, make: str, model: str
) -> ComplaintsSummaryResponse:
    _require_vehicle_identity(year, make, model)
    return await get_complaints_summary(make, model, year)
