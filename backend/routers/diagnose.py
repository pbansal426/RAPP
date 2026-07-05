from fastapi import APIRouter

from backend.core.config import settings
from backend.schemas import DiagnoseRequest, DiagnoseResponse
from backend.services.gemini import call_gemini_text
from backend.services.llm import generate_diagnosis_summary

router = APIRouter()


def check_high_risk(
    symptoms: str, obd_codes: list[str] | None
) -> tuple[bool, str | None, str | None]:
    codes_str = " ".join(obd_codes) if obd_codes else ""
    combined = (symptoms + " " + codes_str).lower()

    # 1. SRS / Airbag
    airbag_kws = ["airbag", "srs", "pretensioner", "clockspring", "side curtain"]
    if any(kw in combined for kw in airbag_kws):
        return (
            True,
            "Airbag/SRS",
            "DANGER: SRS / Airbag systems are explosive and safety-critical. Professional service is highly recommended.",
        )

    # 2. EV Battery / High-Voltage
    ev_kws = [
        "ev battery",
        "hybrid battery",
        "high voltage",
        "hv battery",
        "traction battery",
        "lithium",
    ]
    if any(kw in combined for kw in ev_kws):
        return (
            True,
            "EV Battery",
            "DANGER: High-voltage EV/hybrid battery systems carry lethal voltage. Professional service is highly recommended.",
        )

    # 3. Pressurized Fuel Line
    fuel_kws = [
        "fuel line",
        "fuel rail",
        "pressurized fuel",
        "high pressure fuel",
        "fuel leak",
    ]
    if any(kw in combined for kw in fuel_kws):
        return (
            True,
            "Fuel Line",
            "DANGER: Pressurized fuel lines are highly flammable and run under extreme pressure. Professional service is highly recommended.",
        )

    return False, None, None


@router.post("/api/diagnose", response_model=DiagnoseResponse)
async def diagnose(request: DiagnoseRequest) -> DiagnoseResponse:
    obd_list: list[str] | None = (
        request.obd_codes
        if isinstance(request.obd_codes, list)
        else ([request.obd_codes] if request.obd_codes else None)
    )
    is_high_risk, high_risk_system, warning_message = check_high_risk(
        request.symptoms, obd_list
    )

    summary = f"Free Diagnosis Summary: Misfire or other symptom detected. Symptoms: {request.symptoms}."

    # Grounded in real retrieved OEM text when the vehicle is already known
    # from the request (no new VIN-decode network call added here -- this is
    # the free, pre-payment step, and it never depended on VIN decoding
    # before; only ground when that info is already cheaply available).
    # Falls back to the previous ungrounded free-text Gemini call, then to
    # the static default above, exactly as before, when vehicle info isn't
    # provided. See generate_diagnosis_summary for why this differs from
    # repair-step generation's stricter "skip Gemini entirely" fallback.
    if settings.gemini_api_key:
        if request.vehicle and request.vehicle.make:
            vin_meta = {
                "year": str(request.vehicle.year or ""),
                "make": request.vehicle.make,
                "model": request.vehicle.model or "",
                "engine": request.vehicle.engine or "",
                "drive_type": request.vehicle.drive_type or "",
            }
            ai_summary = await generate_diagnosis_summary(
                vin_meta=vin_meta, symptoms=request.symptoms, obd_codes=obd_list or []
            )
        else:
            prompt = (
                f"Diagnose this vehicle symptom: '{request.symptoms}'. OBD codes: "
                f"{request.obd_codes}. Provide a concise 2-sentence summary of the "
                f"likely root cause and immediate risks."
            )
            ai_summary = await call_gemini_text(prompt)
        if ai_summary:
            summary = ai_summary

    from backend.pricing import build_cost_breakdown, build_recommended_parts
    from backend.repair_templates import select_template

    template = select_template(request.symptoms, obd_list)
    vehicle_desc = ""
    if request.vehicle:
        vehicle_desc = " ".join(
            str(v)
            for v in (request.vehicle.year, request.vehicle.make, request.vehicle.model)
            if v
        ).strip()

    return DiagnoseResponse(
        summary=summary,
        is_high_risk=is_high_risk,
        high_risk_system=high_risk_system,
        warning_message=warning_message,
        recommended_parts=build_recommended_parts(template, vehicle_desc),  # type: ignore
        cost_breakdown=build_cost_breakdown(template),  # type: ignore
    )
