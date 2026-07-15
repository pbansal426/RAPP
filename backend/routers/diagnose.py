from typing import Any

from fastapi import APIRouter, HTTPException, status

from backend.core.config import settings
from backend.schemas import (
    DiagnoseRequest,
    DiagnoseResponse,
    ExternalAiVerifyRequest,
    ExternalAiVerifyResponse,
)
from backend.services.gemini import (
    GeminiRateLimitError,
    call_gemini_text,
    call_gemini_verify_external,
)
from backend.services.llm import generate_diagnosis_summary, refine_brake_category

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

    # Built once, regardless of Gemini key: RAG retrieval (used below to
    # disambiguate the parts template) doesn't need Gemini, only the summary
    # grounding does. No new VIN-decode network call added here -- this is
    # the free, pre-payment step, and it never depended on VIN decoding
    # before; only build vin_meta when that info is already cheaply
    # available from the request itself.
    vin_meta: dict[str, Any] | None = None
    if request.vehicle and request.vehicle.make:
        vin_meta = {
            "year": str(request.vehicle.year or ""),
            "make": request.vehicle.make,
            "model": request.vehicle.model or "",
            "engine": request.vehicle.engine or "",
            "drive_type": request.vehicle.drive_type or "",
        }

    # Falls back to the previous ungrounded free-text Gemini call, then to
    # the static default above, exactly as before, when vehicle info isn't
    # provided. See generate_diagnosis_summary for why this differs from
    # repair-step generation's stricter "skip Gemini entirely" fallback.
    if settings.gemini_api_key:
        if vin_meta:
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
    from backend.repair_templates import get_template, select_template

    template = select_template(request.symptoms, obd_list)
    # Keyword matching alone can't tell disc from drum brakes -- both grind
    # and squeal -- but this vehicle's own retrieved OEM text can. Only
    # matters for "brakes" specifically today; other categories don't yet
    # have a comparably ambiguous sub-type split.
    if template and template.category == "brakes" and vin_meta:
        refined_category = refine_brake_category(vin_meta, request.symptoms)
        if refined_category:
            refined_template = get_template(refined_category)
            if refined_template:
                template = refined_template

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


# ---------------------------------------------------------------------------
# Stage 2.6 – "Check My ChatGPT Answer" Verification Funnel
# ---------------------------------------------------------------------------


@router.post("/api/diagnose/verify-external", response_model=ExternalAiVerifyResponse)
async def verify_external(request: ExternalAiVerifyRequest) -> ExternalAiVerifyResponse:
    """Fact-check third-party AI repair advice against RAPP's OEM/TSB database.

    Retrieves vehicle-specific context (Technical Service Bulletins, OEM specs)
    from the Chroma DB vector store, then asks Gemini to compare the
    `external_ai_text` against that ground truth. Returns a structured scorecard
    with verified_claims, fitment_or_spec_errors, missing_safety_warnings, and
    an accuracy_score (0-100).

    When Gemini is unavailable (no API key / test mode) the endpoint still
    returns a valid response with accuracy_score=50 and a clear degraded-mode
    flag so the frontend can display a helpful message instead of erroring.
    """
    from backend.services.rag import retrieve

    # Build a minimal vin_meta from the request (no VIN-decode network call needed
    # here -- we only need make/model if provided; the VIN itself is sufficient
    # for ChromaDB metadata filtering).
    vin_meta: dict[str, Any] = {"vin": request.vin.strip().upper()}

    query = f"{request.symptoms} {request.external_ai_text[:300]}"
    results = retrieve(query=query, vin_meta=vin_meta, k=8) or []

    # Serialise retrieved TSB/OEM chunks to a compact plain-text block.
    rag_context_parts: list[str] = []
    for doc in results:
        text = doc.get("text", "").strip()
        source = doc.get("source", "")
        if text:
            rag_context_parts.append(f"[{source}] {text}" if source else text)
    rag_context = (
        "\n\n".join(rag_context_parts)
        if rag_context_parts
        else "(No OEM context retrieved for this vehicle/symptom combination.)"
    )

    # Graceful degraded-mode when no Gemini key is configured.
    if not settings.gemini_api_key:
        return ExternalAiVerifyResponse(
            verified_claims=[],
            fitment_or_spec_errors=[],
            missing_safety_warnings=[
                "AI verification is temporarily unavailable — Gemini API key not configured."
            ],
            accuracy_score=50,
        )

    try:
        result = await call_gemini_verify_external(
            external_ai_text=request.external_ai_text,
            rag_context=rag_context,
            symptoms=request.symptoms,
        )
    except GeminiRateLimitError as err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI verification has hit its usage limit. Please try again shortly.",
        ) from err

    if result is None:
        # Gemini call failed but did not raise — return degraded response.
        return ExternalAiVerifyResponse(
            verified_claims=[],
            fitment_or_spec_errors=[],
            missing_safety_warnings=[
                "AI verification is temporarily unavailable. Please try again later."
            ],
            accuracy_score=50,
        )

    return ExternalAiVerifyResponse(
        verified_claims=result.verified_claims,
        fitment_or_spec_errors=result.fitment_or_spec_errors,
        missing_safety_warnings=result.missing_safety_warnings,
        accuracy_score=result.accuracy_score,
    )
