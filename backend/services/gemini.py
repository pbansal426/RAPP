"""Centralized Gemini (google-genai) client and call sites.

All LLM interaction — free-text diagnosis summaries, structured repair-step
generation, and VIN-photo vision OCR — goes through this module instead of
being called inline from routers.
"""

import structlog
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from pydantic import BaseModel

from backend.core.config import settings

logger = structlog.get_logger()

GEMINI_MODEL = "gemini-3.5-flash"


class GeminiRateLimitError(Exception):
    """Gemini rejected the call with 429 (quota/rate limit exhausted).

    Deliberately not swallowed to None like other failures: the caller needs
    to tell a real quota exhaustion apart from "nothing readable in this
    photo" (422) -- retrying a rate-limited request on the same cadence, or
    telling the user the *photo* is the problem, would both be wrong.
    """


_genai_client: genai.Client | None = None


def get_genai_client() -> genai.Client | None:
    """Lazily construct the native Gemini client, or None if no key is
    configured. genai.Client() reads GEMINI_API_KEY from the environment
    itself (backend.core.config loads .env into the process environment on
    import) -- never pass the key explicitly here.

    Always returns None in CI/test mode, even if a real GEMINI_API_KEY is
    present in the environment -- test runs must never dial out."""
    global _genai_client
    if settings.is_test_mode or not settings.gemini_api_key:
        return None
    if _genai_client is None:
        _genai_client = genai.Client()
    return _genai_client


async def call_gemini_text(
    prompt: str, system_prompt: str = "You are an automotive AI expert mechanic."
) -> str | None:
    """Plain text-in/text-out generation via the native Gemini SDK."""
    client = get_genai_client()
    if not client:
        return None
    try:
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
                max_output_tokens=500,
            ),
        )
        text = response.text
        return text.strip() if text else None
    except Exception as e:
        logger.warning(
            "Gemini API call failed, falling back to RAG/mock data", error=str(e)
        )
    return None


# Internal-only: Gemini structured-output schema for repair step generation.
# is_torque_spec is enforced by the response shape (not prompt-following), so
# the frontend's "Torque " prefix regex (repair/page.tsx) can never miss a
# step the model forgot to phrase that way -- callers prepend it in code.
class RepairStep(BaseModel):
    text: str
    is_torque_spec: bool


class RepairStepsSchema(BaseModel):
    steps: list[RepairStep]


async def call_gemini_repair_steps(
    prompt: str,
    system_prompt: str = "You are an automotive AI expert mechanic.",
) -> list[str] | None:
    """Generate repair steps via Gemini structured output. The torque-callout
    contract (frontend regex requires literal "Torque " prefix -- see
    repair/page.tsx) is guaranteed by is_torque_spec in the response schema
    and applied here in code, not left to the model to phrase correctly."""
    client = get_genai_client()
    if not client:
        return None
    try:
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=RepairStepsSchema,
            ),
        )
        parsed = response.parsed
        if not isinstance(parsed, RepairStepsSchema) or len(parsed.steps) < 2:
            return None
        return [
            f"Torque {step.text}" if step.is_torque_spec else step.text
            for step in parsed.steps
        ]
    except Exception as e:
        logger.warning(
            "Gemini repair-steps call failed, falling back to template/RAG data",
            error=str(e),
        )
    return None


# Internal-only: Gemini structured-output schema for VIN photo OCR.
class VinOcrExtraction(BaseModel):
    vin: str
    confidence: float


_VIN_OCR_SYSTEM_PROMPT = (
    "You extract Vehicle Identification Numbers (VINs) from photos of "
    "windshield tags, door jamb stickers, or registration documents. A VIN "
    "is exactly 17 characters using only digits and uppercase letters, and "
    "never contains the letters I, O, or Q. If no VIN is confidently "
    "readable, return an empty string for vin and 0.0 for confidence."
)


async def extract_vin_via_gemini(
    image_bytes: bytes, mime_type: str
) -> VinOcrExtraction | None:
    """Scan a VIN tag/door-jamb-sticker/registration-document photo with
    Gemini's native multimodal vision and return the raw structured
    extraction, or None if no client is configured or the call failed.
    Sanitizing/validating the extracted string is the caller's job (see
    backend.routers.vin), same as any other user-controlled input."""
    client = get_genai_client()
    if not client:
        return None
    try:
        image_part = genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        text_part = genai_types.Part.from_text(text="Extract the VIN from this image.")
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            # list[Part] is a valid Content per the google-genai docs, but its
            # overloaded stub's Union of list[...] alternatives is invariant
            # and doesn't include this exact combination.
            contents=[image_part, text_part],  # type: ignore[arg-type]
            config=genai_types.GenerateContentConfig(
                system_instruction=_VIN_OCR_SYSTEM_PROMPT,
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=VinOcrExtraction,
            ),
        )
        parsed = response.parsed
        if not isinstance(parsed, VinOcrExtraction):
            return None
        return parsed
    except genai_errors.APIError as e:
        if e.code == 429:
            logger.warning("Gemini VIN OCR call rate-limited", error=str(e))
            raise GeminiRateLimitError(str(e)) from e
        logger.warning("Gemini VIN OCR call failed", error=str(e))
    except Exception as e:
        logger.warning("Gemini VIN OCR call failed", error=str(e))
    return None
