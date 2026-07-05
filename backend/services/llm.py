"""RAG-grounded repair-step generation.

The single entry point routers call for turning a symptom/OBD query into
repair steps + citations. Retrieval and generation are strictly coupled:
Gemini only ever formats/cross-references text that RAG actually retrieved
from the local vector store -- it never runs a free-generation pass, so it
can't invent a procedure or torque spec that isn't backed by real OEM text.
When RAG finds nothing, the deterministic template/generic fallback is
returned unmodified and Gemini is never called.
"""

from typing import Any

import structlog

from backend.repair_templates import select_template
from backend.services.gemini import call_gemini_repair_steps
from backend.services.rag import retrieve

logger = structlog.get_logger()

_GROUNDED_SYSTEM_PROMPT = (
    "You are a formatting engine. Use ONLY the provided OEM text to generate "
    "repair steps -- do not invent torque specs or procedures that are not "
    "present in that text. Cross-reference the tools required by the OEM "
    "text against the User_Tools list provided in the prompt; if a required "
    "tool is missing from User_Tools, add an explicit step stating which "
    "tool is missing before the step that needs it."
)

_GENERIC_FALLBACK_STEPS = [
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


def _no_source_citation(vin_meta: dict[str, Any]) -> str:
    """Honest citation for the template/generic fallback path -- never name
    a specific OEM manual here, since no vehicle-specific document was
    actually retrieved (naming one that doesn't match the queried vehicle,
    e.g. citing a Honda manual for a Toyota query, is a real accuracy/
    liability problem, not just cosmetic)."""
    make = vin_meta.get("make") or ""
    model = vin_meta.get("model") or ""
    vehicle_str = f"{make} {model}".strip() or "this vehicle"
    return (
        f"RAPP curated procedure -- no vehicle-specific NHTSA TSB or OEM "
        f"documentation was found for {vehicle_str}. This is a general "
        f"reference procedure; verify torque specs and part fitment against "
        f"your vehicle's official service documentation before performing "
        f"this repair."
    )


def _citation_for(doc: dict[str, Any], vin_meta: dict[str, Any]) -> str:
    meta = doc.get("metadata") or {}

    # Every source ingested today is source_authority="official" (NHTSA TSBs
    # -- see etl/load/vector_loader.py), so this is a no-op currently. It's
    # here so that whenever a non-official source type (community/forum/UGC)
    # gets added, its citations are visibly flagged rather than presented
    # with the same implied authority as an official government/OEM source.
    source_authority = meta.get("source_authority")
    prefix = (
        ""
        if source_authority in (None, "official")
        else "[Unverified/community-sourced] "
    )

    bulletin = meta.get("bulletin_number")
    source_url = meta.get("source_url")
    if bulletin:
        return (
            f"{prefix}NHTSA TSB {bulletin} ({source_url})"
            if source_url
            else f"{prefix}NHTSA TSB {bulletin}"
        )
    citation = meta.get("citation") or meta.get("source")
    if citation:
        return f"{prefix}{citation}"
    make_str = meta.get("make", vin_meta.get("make", ""))
    model_str = meta.get("model", vin_meta.get("model", ""))
    year_str = meta.get("year", vin_meta.get("year", ""))
    return f"{prefix}{make_str} {model_str} Manual ({year_str})".strip()


async def generate_repair_procedure(
    vin_meta: dict[str, Any],
    symptoms: str,
    obd_codes: list[str],
    user_tools: list[str],
) -> tuple[list[str], list[str]]:
    """Retrieve OEM text for the query/vehicle and generate grounded repair
    steps from it. Returns (repair_steps, citations).

    Falls back to the curated template library, then a generic placeholder
    procedure, when retrieval finds nothing -- Gemini is not called in
    either fallback case, since there is no OEM text to ground it in.
    """
    user_query = f"{symptoms} " + " ".join(obd_codes)
    user_query = user_query.strip()
    results = retrieve(query=user_query, vin_meta=vin_meta, k=5)

    if not results:
        citation = _no_source_citation(vin_meta)
        template = select_template(symptoms, obd_codes)
        if template:
            return list(template.steps), [citation]
        return list(_GENERIC_FALLBACK_STEPS), [citation]

    repair_steps = [doc["text"] for doc in results]
    citations = [_citation_for(doc, vin_meta) for doc in results]

    tools_str = ", ".join(user_tools) or "no tools specified"
    powertrain = vin_meta.get("powertrain") or ""
    powertrain_note = f" Powertrain: {powertrain}." if powertrain else ""
    oem_text = "\n\n".join(f"- {doc['text']}" for doc in results)
    prompt = (
        f"Vehicle: {vin_meta.get('year')} {vin_meta.get('make')} {vin_meta.get('model')} "
        f"(engine: {vin_meta.get('engine') or 'unspecified'}).{powertrain_note}\n"
        f"User query: {user_query}\n"
        f"User_Tools: {tools_str}\n\n"
        f"OEM text:\n{oem_text}\n\n"
        f"Generate repair steps strictly from the OEM text above. Each step is one "
        f"item in the steps array. For any step whose text is a bolt/fastener torque "
        f"specification, set is_torque_spec to true and write the text WITHOUT the "
        f"word 'Torque' at the start -- it will be prepended automatically. No emojis."
    )

    gemini_steps = await call_gemini_repair_steps(
        prompt, system_prompt=_GROUNDED_SYSTEM_PROMPT
    )
    if gemini_steps:
        return gemini_steps, citations

    return repair_steps, citations
