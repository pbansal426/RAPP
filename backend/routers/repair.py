from typing import Any

from fastapi import APIRouter, HTTPException, status

from backend.core.config import settings
from backend.routers.vin import decode_vin_internal
from backend.schemas import RepairRequest, RepairResponse
from backend.services.gemini import call_gemini_repair_steps
from backend.services.rag import retrieve

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
        }
    else:
        vin_meta = await decode_vin_internal(request.vin)

    obd_list: list[str] = (
        request.obd_codes
        if isinstance(request.obd_codes, list)
        else ([request.obd_codes] if request.obd_codes else [])
    )

    # Retrieve relevant steps from RAG store
    query = f"{request.symptoms} " + " ".join(obd_list)
    results = retrieve(query=query.strip(), vin_meta=vin_meta, k=5)

    repair_steps = []
    citations = []

    if results:
        repair_steps = [doc["text"] for doc in results]
        for doc in results:
            meta = doc.get("metadata") or {}
            citation = meta.get("citation") or meta.get("source")
            if not citation:
                make_str = meta.get("make", vin_meta.get("make", ""))
                model_str = meta.get("model", vin_meta.get("model", ""))
                year_str = meta.get("year", vin_meta.get("year", ""))
                citation = f"{make_str} {model_str} Manual ({year_str})".strip()
            citations.append(citation)
    else:
        # Fall back to the curated procedure template matched to the symptoms
        # and OBD codes; only if nothing matches use the generic steps.
        from backend.repair_templates import select_template

        template = select_template(request.symptoms, obd_list)
        if template:
            repair_steps = list(template.steps)
            citations = list(template.citations)
        else:
            repair_steps = [
                "Disconnect negative battery terminal.",
                "Replace ignition coil.",
                "Disconnect negative battery terminal using a 10mm wrench to prevent accidental short-circuits during disassembly.",
                "Remove the plastic engine beauty cover by loosening the 4 retaining nuts with a 10mm socket.",
                "Locate the target component and disconnect the harness plug by pressing the lock tab and pulling gently.",
                "Unscrew the mounting bolt using a 10mm socket and lift the old component straight out of the mounting well.",
                "Compare the new component to the old one to verify fitment, then apply a thin layer of dielectric grease to the seal boot.",
                "Insert the new component into the well, seating it firmly, and hand-tighten the mounting bolt first.",
                "Torque the mounting bolt to exactly 7.5 ft-lbs using a torque wrench. Do not overtighten.",
                "Reconnect the electrical harness plug ensuring the click sound is heard, reinstall the engine cover, and reconnect the negative battery terminal.",
            ]
            citations = [
                "Honda Civic ESM 2016-2021 Section 12-4",
                "Lexus ESM 2016-2022 Section 14-8",
                "Toyota Master Workshop Manual Pub. No. T3-094",
            ]

    if settings.gemini_api_key:
        tools_str = ", ".join(request.tools or []) or "standard basic hand tools"
        powertrain = (request.vehicle.powertrain if request.vehicle else None) or ""
        powertrain_note = (
            f" The vehicle powertrain is {powertrain} — adapt procedures accordingly "
            f"(e.g. high-voltage isolation for hybrid/EV, no spark plugs on diesel/EV)."
            if powertrain
            else ""
        )
        prompt = (
            f"Generate a detailed, clinic-grade repair or modification procedure for VIN {request.vin} ({vin_meta.get('year')} {vin_meta.get('make')} {vin_meta.get('model')}, engine: {vin_meta.get('engine') or 'unspecified'}).{powertrain_note} "
            f"Symptoms/Target: {request.symptoms}. Available tools: {tools_str}. "
            f"Reference procedure to improve upon: {repair_steps}. "
            f"Provide a comprehensive, step-by-step guide (from safety/preparation to access, replacement, and reassembly/verification) that takes the user to the very end of the project for a complete and full fix. "
            f"Each step is one item in the steps array. Include specific socket sizes (e.g. 10mm deep socket) in the step text. "
            f"For any step whose text is a bolt/fastener torque specification (e.g. 'the bolts to 7.5 ft-lbs'), set is_torque_spec to true and write the text WITHOUT the word 'Torque' at the start -- it will be prepended automatically. "
            f"No emojis."
        )
        gemini_steps = await call_gemini_repair_steps(prompt)
        if gemini_steps:
            repair_steps = gemini_steps

    return RepairResponse(repair_steps=repair_steps, citations=citations)
