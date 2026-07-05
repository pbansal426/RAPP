import re
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.core.config import settings
from backend.schemas import VinOcrResponse
from backend.services.gemini import GeminiRateLimitError, extract_vin_via_gemini

logger = structlog.get_logger()

router = APIRouter()

_NHTSA_USER_AGENT = (
    "RAPP-Backend/1.0 (+https://github.com/rapp; automotive VIN decoding)"
)
_NHTSA_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# NHTSA's EngineConfiguration values are long descriptive strings ("V-Shaped",
# "Inline", "Flat / Boxer", ...); this maps them to the short form used in
# everyday engine callouts ("V6", "I4", "Flat-6").
_ENGINE_CONFIG_ABBR: list[tuple[str, str]] = [
    ("V-SHAPED", "V"),
    ("INLINE", "I"),
    ("STRAIGHT", "I"),
    ("FLAT", "Flat-"),
    ("BOXER", "Flat-"),
    ("W-SERIES", "W"),
    ("ROTARY", "Rotary "),
    ("WANKEL", "Rotary "),
]


def _clean_str(val: Any) -> str | None:
    """Normalize an NHTSA field value: strips whitespace and treats the
    API's various "no data" sentinels ("", "Not Applicable", "None", ...) as
    absent so downstream code only ever sees a real value or ``None``."""
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("", "none", "null", "not applicable"):
        return None
    return s


def _config_abbr(config: str | None) -> str:
    if not config:
        return ""
    upper = config.upper()
    for needle, abbr in _ENGINE_CONFIG_ABBR:
        if needle in upper:
            return abbr
    return ""


def _build_engine_desc(
    disp_l: str | None, cylinders: str | None, config: str | None
) -> str:
    abbr = _config_abbr(config)
    parts = []
    if disp_l:
        parts.append(f"{disp_l}L")
    if cylinders:
        parts.append(f"{abbr}{cylinders}" if abbr else f"{cylinders}-Cylinder")
    elif abbr:
        parts.append(abbr.rstrip("-").strip() or abbr)
    return " ".join(parts) if parts else "Unknown"


def _derive_powertrain(fields: dict[str, str]) -> str | None:
    """Classify the vehicle's powertrain from NHTSA's fuel-type/electrification
    fields so an unambiguous result (e.g. a VIN that decodes to pure Gasoline)
    lets the frontend skip asking the user to pick a powertrain manually."""
    elec_level = (_clean_str(fields.get("ElectrificationLevel")) or "").upper()
    fuel_primary = (_clean_str(fields.get("FuelTypePrimary")) or "").upper()
    fuel_secondary = _clean_str(fields.get("FuelTypeSecondary"))

    if "PHEV" in elec_level or "PLUG-IN" in elec_level:
        return "Plug-in Hybrid"
    if "BEV" in elec_level:
        return "Electric (EV)"
    if (
        "HEV" in elec_level
        or "MHEV" in elec_level
        or "HYBRID" in elec_level
        or fuel_secondary
    ):
        return "Hybrid"
    if "ELECTRIC" in fuel_primary:
        return "Electric (EV)"
    if "DIESEL" in fuel_primary:
        return "Diesel"
    if fuel_primary:
        return "Gasoline"
    return None


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type(
        (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)
    ),
)
async def _fetch_nhtsa_vin_fields(vin: str) -> dict[str, str]:
    """Query NHTSA's DecodeVinValuesExtended endpoint, which returns one flat
    object per VIN (as opposed to DecodeVin's Variable/Value row list),
    covering trim, body class, drive type, and fuel/electrification fields in
    addition to the year/make/model/engine data the old endpoint provided.
    Retries transient network/5xx failures with exponential backoff."""
    url = f"{settings.nhtsa_base_url}/DecodeVinValuesExtended/{vin}?format=json"
    # Use a short-lived client rather than a shared pool: a long-running
    # shared AsyncClient can silently degrade (stale connections after the
    # process has been up for days), wedging every VIN decode. A fresh
    # client per call is cheap here and can't get stuck in that state.
    async with httpx.AsyncClient(timeout=_NHTSA_TIMEOUT) as client:
        response = await client.get(url, headers={"User-Agent": _NHTSA_USER_AGENT})
    response.raise_for_status()
    data = response.json()
    results = data.get("Results") or []
    if not results:
        raise httpx.HTTPError("NHTSA returned no Results for VIN decode")
    fields: dict[str, str] = results[0]
    return fields


def _extract_vehicle_data(fields: dict[str, str]) -> dict[str, Any]:
    make = _clean_str(fields.get("Make"))
    model = _clean_str(fields.get("Model"))
    if not make or not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle make or model not found in NHTSA database",
        )

    year_str = _clean_str(fields.get("ModelYear"))
    year: int | str | None = None
    if year_str:
        try:
            year = int(year_str)
        except ValueError:
            year = year_str

    disp_l = _clean_str(fields.get("DisplacementL"))
    cylinders = _clean_str(fields.get("EngineCylinders"))
    config = _clean_str(fields.get("EngineConfiguration"))

    return {
        "year": year,
        "make": make,
        "model": model,
        "trim": _clean_str(fields.get("Trim")) or _clean_str(fields.get("Trim2")),
        "engine": _build_engine_desc(disp_l, cylinders, config),
        "drive_type": _clean_str(fields.get("DriveType")) or "Unknown",
        "body_class": _clean_str(fields.get("BodyClass")),
        "vehicle_type": _clean_str(fields.get("VehicleType")),
        "fuel_type": _clean_str(fields.get("FuelTypePrimary")),
        "powertrain": _derive_powertrain(fields),
    }


async def decode_vin_internal(vin: str) -> dict[str, Any]:
    vin_upper = vin.upper()

    # Check for synthetic VIN
    if vin_upper.startswith("SYN"):
        if len(vin_upper) != 17 or not vin_upper.isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid VIN format. Must be exactly 17 alphanumeric characters.",
            )

        # Parse: SYN + YY (2 chars) + MAKE_CODE (5 chars) + MODEL_CODE (7 chars)
        yy_str = vin_upper[3:5]
        make_code = vin_upper[5:10]
        model_code = vin_upper[10:17]

        try:
            year = 2000 + int(yy_str)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid year format in synthetic VIN.",
            ) from err

        make_map = {
            "HONDA": "HONDA",
            "TOYOT": "TOYOTA",
            "FORDX": "FORD",
            "LEXUS": "LEXUS",
            "CHEVR": "CHEVROLET",
        }

        model_map = {
            "CIVICXX": "CIVIC",
            "ACCORDX": "ACCORD",
            "F150XXX": "F-150",
            "CAMRYXX": "CAMRY",
            "COROLLA": "COROLLA",
            "RX350XX": "RX350",
            "SILVERA": "SILVERADO",
        }

        if make_code not in make_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle make not found in synthetic mapping",
            )

        if model_code not in model_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle model not found in synthetic mapping",
            )

        make = make_map[make_code]
        model = model_map[model_code]

        make_specs = {
            "HONDA": {"engine": "1.5L 4-Cylinder", "drive_type": "FWD"},
            "TOYOT": {"engine": "2.5L 4-Cylinder", "drive_type": "FWD"},
            "FORDX": {"engine": "3.5L V6", "drive_type": "AWD"},
            "LEXUS": {"engine": "3.5L V6", "drive_type": "AWD"},
            "CHEVR": {"engine": "5.3L V8", "drive_type": "AWD"},
        }

        specs = make_specs[make_code]

        return {
            "year": year,
            "make": make,
            "model": model,
            "trim": None,
            "engine": specs["engine"],
            "drive_type": specs["drive_type"],
            "body_class": None,
            "vehicle_type": None,
            "fuel_type": "Gasoline",
            "powertrain": "Gasoline",
        }

    # Validate VIN format: exactly 17 alphanumeric characters
    if len(vin) != 17 or not vin.isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid VIN format. Must be exactly 17 alphanumeric characters.",
        )

    try:
        fields = await _fetch_nhtsa_vin_fields(vin)
    except httpx.HTTPError as err:
        from backend.vin_fallback import wmi_fallback_decode

        fallback = wmi_fallback_decode(vin)
        if fallback is not None:
            logger.warning(
                "NHTSA unreachable, using offline WMI fallback decode",
                error=str(err),
                vin=vin,
            )
            return fallback
        logger.error("NHTSA API communication error", error=str(err), vin=vin)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error communicating with NHTSA API",
        ) from err

    return _extract_vehicle_data(fields)


# VIN alphabet excludes I, O, Q (they're visually ambiguous with 1/0/9).
_VIN_ALLOWED_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")
_VIN_STRIP_RE = re.compile(r"[^A-Za-z0-9]")

# Standard VIN check-digit algorithm (position 9): each character is mapped
# to a numeric value, multiplied by a position weight, summed, then reduced
# mod 11 ("X" represents a remainder of 10). Primarily meaningful for
# North American VINs; VINs from other regions may legitimately fail this
# check, so callers should treat it as a confidence signal, not a hard gate.
_VIN_TRANSLITERATION: dict[str, int] = {
    **{str(d): d for d in range(10)},
    "A": 1,
    "B": 2,
    "C": 3,
    "D": 4,
    "E": 5,
    "F": 6,
    "G": 7,
    "H": 8,
    "J": 1,
    "K": 2,
    "L": 3,
    "M": 4,
    "N": 5,
    "P": 7,
    "R": 9,
    "S": 2,
    "T": 3,
    "U": 4,
    "V": 5,
    "W": 6,
    "X": 7,
    "Y": 8,
    "Z": 9,
}
_VIN_POSITION_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]


def _sanitize_vin_candidate(raw: str) -> str:
    """Strip spaces/dashes/other punctuation and uppercase, per the OCR spec."""
    return _VIN_STRIP_RE.sub("", raw).upper()


def _vin_check_digit_valid(vin: str) -> bool:
    if len(vin) != 17:
        return False
    total = 0
    for ch, weight in zip(vin, _VIN_POSITION_WEIGHTS, strict=True):
        value = _VIN_TRANSLITERATION.get(ch)
        if value is None:
            return False
        total += value * weight
    remainder = total % 11
    expected = "X" if remainder == 10 else str(remainder)
    return vin[8] == expected


async def _extract_vin_via_vision(
    image_bytes: bytes, content_type: str
) -> tuple[str | None, float]:
    """Scan a VIN tag/door-jamb-sticker/registration-document photo via
    Gemini's native vision and return a sanitized 17-char VIN candidate plus
    a 0-1 confidence score (blended with the check-digit result), or
    (None, 0.0) if nothing readable was found."""
    extraction = await extract_vin_via_gemini(image_bytes, content_type)
    if extraction is None:
        return None, 0.0

    vin_candidate = _sanitize_vin_candidate(extraction.vin)
    if not _VIN_ALLOWED_RE.match(vin_candidate):
        return None, 0.0

    model_confidence = min(max(extraction.confidence, 0.0), 1.0)
    confidence = model_confidence
    if not _vin_check_digit_valid(vin_candidate):
        # Not a hard rejection (non-NA VINs can legitimately fail this), but
        # it's a meaningful signal the OCR may have mis-read a character.
        confidence = min(confidence, 0.6)

    return vin_candidate, round(confidence, 2)


@router.get("/api/vin/{vin}")
async def decode_vin(vin: str) -> dict[str, Any]:
    res: dict[str, Any] = await decode_vin_internal(vin)
    return res


_OCR_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    # iOS/Safari frequently upload HEIC with a generic or empty content type,
    # so we can't rely on the MIME alone — we also accept by file extension.
    "application/octet-stream",
    "",
}
_OCR_ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif")
# Raw-upload abuse guard, checked before any decoding. Real phone photos
# (12MP+ PNG/HEIC straight off a camera) routinely land in the 8-15MB range,
# well above what an embossed VIN plate needs to stay legible -- those get
# downscaled below, not rejected here.
_OCR_MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20MB
_VISION_NATIVE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
# An embossed VIN plate is legible at well under 1MP; capping the longest
# edge keeps the Gemini request small (faster upload + inference) regardless
# of how large the source photo is.
_MAX_VISION_DIMENSION = 2048


def _normalize_image_for_vision(
    image_bytes: bytes, content_type: str, filename: str
) -> tuple[bytes, str]:
    """Ensure the image is a small JPEG the vision model can ingest quickly.

    Always decodes via Pillow (+ pillow-heif for HEIC/HEIF, what iPhones
    shoot) and re-encodes as JPEG, downscaling first if the longest edge
    exceeds _MAX_VISION_DIMENSION. This normalizes every upload -- including
    already-native mimes like PNG/JPEG -- since real phone photos are often
    10+ MB at full sensor resolution, which is both slower to upload and
    unnecessary for reading VIN text. Falls back to the original bytes if
    decoding fails, so a still-readable image is never blocked by a
    conversion error.
    """
    try:
        import io

        import pillow_heif
        from PIL import Image

        pillow_heif.register_heif_opener()
        img: Image.Image = Image.open(io.BytesIO(image_bytes))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        if max(img.size) > _MAX_VISION_DIMENSION:
            img.thumbnail(
                (_MAX_VISION_DIMENSION, _MAX_VISION_DIMENSION),
                Image.Resampling.LANCZOS,
            )
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue(), "image/jpeg"
    except Exception as err:  # noqa: BLE001
        logger.warning(
            "Image transcode for vision failed; sending original bytes",
            error=str(err),
            content_type=content_type,
            filename=filename,
        )
        # Best effort: pass through untouched if it's already a mime the
        # model accepts natively, otherwise label it JPEG as a last resort.
        if content_type in _VISION_NATIVE_MIMES:
            return image_bytes, content_type
        return image_bytes, "image/jpeg"


@router.post("/api/vin/ocr", response_model=VinOcrResponse)
async def vin_ocr(file: UploadFile = File(...)) -> VinOcrResponse:  # noqa: B008
    content_type = (file.content_type or "").lower()
    filename = (file.filename or "").lower()
    ext_ok = filename.endswith(_OCR_ALLOWED_EXTENSIONS)
    if content_type not in _OCR_ALLOWED_CONTENT_TYPES and not ext_ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type. Use JPEG, PNG, WEBP, or HEIC.",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty."
        )
    if len(image_bytes) > _OCR_MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image too large (max 20MB).",
        )

    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="VIN photo scanning is temporarily unavailable. Enter the VIN manually.",
        )

    # Gemini vision can't read HEIC/HEIF (or generic octet-stream), so
    # transcode to JPEG and hand the model a known-good MIME.
    image_bytes, vision_mime = _normalize_image_for_vision(
        image_bytes, content_type, filename
    )

    try:
        vin_candidate, confidence = await _extract_vin_via_vision(
            image_bytes, vision_mime
        )
    except GeminiRateLimitError as err:
        # Distinct from the 422 below: the photo may well be fine, Gemini's
        # quota is just exhausted. Blaming the photo here would send a
        # continuously-scanning caller (or a retrying user) in circles.
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="VIN scanning has hit its usage limit for now. Try again shortly, or use Upload / Manual entry.",
        ) from err
    if not vin_candidate:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not read a valid VIN from the photo. Try a clearer, well-lit photo of the VIN tag.",
        )

    decoded_vehicle: dict[str, Any] | None = None
    try:
        decoded_vehicle = await decode_vin_internal(vin_candidate)
    except HTTPException:
        decoded_vehicle = None

    return VinOcrResponse(
        vin=vin_candidate, confidence=confidence, decoded_vehicle=decoded_vehicle
    )
