from typing import Any

from fastapi import APIRouter, HTTPException, status

from backend.routers.vin import decode_vin_internal
from backend.schemas import RepairRequest, RepairResponse
from backend.services.llm import generate_repair_procedure

router = APIRouter()


@router.post("/api/repair", response_model=RepairResponse)
async def repair(request: RepairRequest) -> RepairResponse:
    if not request.stripe_session_id or not request.stripe_session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment Required: stripe_session_id is required.",
        )

    # Prefer the client-supplied vehicle identity (YMM selector covers makes the
    # synthetic-VIN decoder does not); fall back to decoding the VIN.
    vin_meta: dict[str, Any]
    if request.vehicle and request.vehicle.make:
        vin_meta = {
            "vin": request.vin,
            "year": str(request.vehicle.year or ""),
            "make": request.vehicle.make,
            "model": request.vehicle.model or "",
            "engine": request.vehicle.engine or "",
            "drive_type": request.vehicle.drive_type or "",
            "powertrain": request.vehicle.powertrain or "",
        }
    else:
        vin_meta = await decode_vin_internal(request.vin)

    obd_list: list[str] = (
        request.obd_codes
        if isinstance(request.obd_codes, list)
        else ([request.obd_codes] if request.obd_codes else [])
    )
    tools_list: list[str] = (
        request.tools
        if isinstance(request.tools, list)
        else ([request.tools] if request.tools else [])
    )

    repair_steps, citations = await generate_repair_procedure(
        vin_meta=vin_meta,
        symptoms=request.symptoms,
        obd_codes=obd_list,
        user_tools=tools_list,
    )

    return RepairResponse(repair_steps=repair_steps, citations=citations)
