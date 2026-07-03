import base64
import json
import logging
import re
import sys
from contextlib import asynccontextmanager
from typing import Any

import httpx
import structlog
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


# 1. Configuration Settings
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = "rapp-backend"
    debug: bool = False
    port: int = 8000
    host: str = "127.0.0.1"

    # API endpoints and URLs
    nhtsa_base_url: str = "https://vpic.nhtsa.dot.gov/api/vehicles"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    # Keys / Secrets (Stubbed / optional)
    openai_api_key: str | None = None
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_single: str = "price_xxx"
    stripe_price_vin_pass: str = "price_xxx"

    # RAG settings
    vector_store: str = "chromadb"
    chroma_db_path: str = "./data/chroma_db"

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:3099"

    # Logging
    log_format: str = "dev"

settings = Settings()

# 2. Structured Logging Configuration
def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

configure_logging(settings)
logger = structlog.get_logger()

# 3. Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    # Startup: configure logger & initialize httpx async client pool
    logger.info("Starting up FastAPI application", port=settings.port, debug=settings.debug)
    app.state.http_client = httpx.AsyncClient()
    yield
    # Shutdown: close httpx async client pool
    await app.state.http_client.aclose()
    logger.info("Shutting down FastAPI application")

app = FastAPI(
    title="RAPP Backend API Server",
    version="0.1.0",
    lifespan=lifespan
)

# 4. CORS Middleware Setup
allowed_origins_list = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list if allowed_origins_list else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Centralized Exception Handlers (never leak stack traces to client)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    logger.warning(
        "HTTP exception occurred",
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning(
        "Validation error occurred",
        path=request.url.path,
        method=request.method,
        errors=exc.errors()
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation failed", "details": exc.errors()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception occurred",
        path=request.url.path,
        method=request.method,
        error=str(exc)
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"}
    )


# 6. Helper Functions
_NHTSA_USER_AGENT = "RAPP-Backend/1.0 (+https://github.com/rapp; automotive VIN decoding)"
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
    if "HEV" in elec_level or "MHEV" in elec_level or "HYBRID" in elec_level or fuel_secondary:
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
    response = await app.state.http_client.get(
        url, headers={"User-Agent": _NHTSA_USER_AGENT}, timeout=_NHTSA_TIMEOUT
    )
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
                detail="Invalid VIN format. Must be exactly 17 alphanumeric characters."
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
                detail="Invalid year format in synthetic VIN."
            ) from err

        make_map = {
            "HONDA": "HONDA",
            "TOYOT": "TOYOTA",
            "FORDX": "FORD",
            "LEXUS": "LEXUS",
            "CHEVR": "CHEVROLET"
        }

        model_map = {
            "CIVICXX": "CIVIC",
            "ACCORDX": "ACCORD",
            "F150XXX": "F-150",
            "CAMRYXX": "CAMRY",
            "COROLLA": "COROLLA",
            "RX350XX": "RX350",
            "SILVERA": "SILVERADO"
        }

        if make_code not in make_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle make not found in synthetic mapping"
            )

        if model_code not in model_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle model not found in synthetic mapping"
            )

        make = make_map[make_code]
        model = model_map[model_code]

        make_specs = {
            "HONDA": {"engine": "1.5L 4-Cylinder", "drive_type": "FWD"},
            "TOYOT": {"engine": "2.5L 4-Cylinder", "drive_type": "FWD"},
            "FORDX": {"engine": "3.5L V6", "drive_type": "AWD"},
            "LEXUS": {"engine": "3.5L V6", "drive_type": "AWD"},
            "CHEVR": {"engine": "5.3L V8", "drive_type": "AWD"}
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
            detail="Invalid VIN format. Must be exactly 17 alphanumeric characters."
        )

    try:
        fields = await _fetch_nhtsa_vin_fields(vin)
    except httpx.HTTPError as err:
        from backend.vin_fallback import wmi_fallback_decode

        fallback = wmi_fallback_decode(vin)
        if fallback is not None:
            logger.warning(
                "NHTSA unreachable, using offline WMI fallback decode",
                error=str(err), vin=vin,
            )
            return fallback
        logger.error(
            "NHTSA API communication error", error=str(err), vin=vin
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error communicating with NHTSA API"
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
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
    "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "P": 7, "R": 9,
    "S": 2, "T": 3, "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9,
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


@retry(
    reraise=True,
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
)
async def _call_vision_completion(payload: dict[str, Any]) -> httpx.Response:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    return await app.state.http_client.post(
        url, headers=headers, json=payload, timeout=httpx.Timeout(20.0, connect=5.0)
    )


async def _extract_vin_via_vision(
    image_bytes: bytes, content_type: str
) -> tuple[str | None, float]:
    """Scan a VIN tag/door-jamb-sticker/registration-document photo with a
    vision-capable OpenAI model and return a sanitized 17-char VIN candidate
    plus a 0-1 confidence score (blended with the check-digit result), or
    (None, 0.0) if nothing readable was found."""
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{content_type};base64,{b64}"

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You extract Vehicle Identification Numbers (VINs) from photos "
                    "of windshield tags, door jamb stickers, or registration "
                    "documents. A VIN is exactly 17 characters using only digits "
                    "and uppercase letters, and never contains the letters I, O, "
                    "or Q. Respond with strict JSON only: "
                    '{"vin": "<17-char VIN, or empty string if not confidently '
                    'readable>", "confidence": <0.0-1.0>}.'
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract the VIN from this image."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        "temperature": 0.0,
        "max_tokens": 100,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = await _call_vision_completion(payload)
    except httpx.HTTPError as err:
        logger.warning("VIN OCR vision call failed", error=str(err))
        return None, 0.0

    if resp.status_code != 200:
        logger.warning("VIN OCR vision call non-200", status_code=resp.status_code)
        return None, 0.0

    try:
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except (KeyError, IndexError, ValueError) as err:
        logger.warning("VIN OCR vision response unparseable", error=str(err))
        return None, 0.0

    vin_candidate = _sanitize_vin_candidate(str(parsed.get("vin") or ""))
    if not _VIN_ALLOWED_RE.match(vin_candidate):
        return None, 0.0

    model_confidence = min(max(float(parsed.get("confidence") or 0.0), 0.0), 1.0)
    confidence = model_confidence
    if not _vin_check_digit_valid(vin_candidate):
        # Not a hard rejection (non-NA VINs can legitimately fail this), but
        # it's a meaningful signal the OCR may have mis-read a character.
        confidence = min(confidence, 0.6)

    return vin_candidate, round(confidence, 2)


def check_high_risk(symptoms: str, obd_codes: list[str] | None) -> tuple[bool, str | None, str | None]:
    codes_str = " ".join(obd_codes) if obd_codes else ""
    combined = (symptoms + " " + codes_str).lower()

    # 1. SRS / Airbag
    airbag_kws = ["airbag", "srs", "pretensioner", "clockspring", "side curtain"]
    if any(kw in combined for kw in airbag_kws):
        return (
            True,
            "Airbag/SRS",
            "DANGER: SRS / Airbag systems are explosive and safety-critical. Professional service is highly recommended."
        )

    # 2. EV Battery / High-Voltage
    ev_kws = ["ev battery", "hybrid battery", "high voltage", "hv battery", "traction battery", "lithium"]
    if any(kw in combined for kw in ev_kws):
        return (
            True,
            "EV Battery",
            "DANGER: High-voltage EV/hybrid battery systems carry lethal voltage. Professional service is highly recommended."
        )

    # 3. Pressurized Fuel Line
    fuel_kws = ["fuel line", "fuel rail", "pressurized fuel", "high pressure fuel", "fuel leak"]
    if any(kw in combined for kw in fuel_kws):
        return (
            True,
            "Fuel Line",
            "DANGER: Pressurized fuel lines are highly flammable and run under extreme pressure. Professional service is highly recommended."
        )

    return False, None, None


# 7. Request / Response Pydantic Schemas
class VehicleInfo(BaseModel):
    """Client-provided vehicle identity for flows without a decodable VIN
    (e.g. the Year/Make/Model selector, which covers every NHTSA make).
    Also doubles as the shape of ``rapp_vin_data``, so it carries the
    richer fields (trim, body_class, vehicle_type, fuel_type) that
    /api/vin/{vin} now returns even though the repair/diagnose endpoints
    only read year/make/model/engine/drive_type/powertrain today."""

    year: str | int | None = None
    make: str | None = None
    model: str | None = None
    trim: str | None = None
    engine: str | None = None
    drive_type: str | None = None
    body_class: str | None = None
    vehicle_type: str | None = None
    fuel_type: str | None = None
    powertrain: str | None = None


class DiagnoseRequest(BaseModel):
    vin: str
    symptoms: str
    obd_codes: list[str] | str | None = None
    tools: list[str] | str | None = None
    vehicle: VehicleInfo | None = None

    @field_validator("obd_codes")
    @classmethod
    def normalize_obd_codes(cls, v: list[str] | str | None) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v

    @field_validator("tools")
    @classmethod
    def normalize_tools(cls, v: list[str] | str | None) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


class PartOption(BaseModel):
    """One purchasable option for a recommended part, at a specific tier."""

    tier: str  # "OEM" | "Aftermarket / Budget" | "Upgrade"
    brand: str
    part_number: str | None = None
    title: str
    estimated_price: float
    purchase_url: str
    rationale: str


class RecommendedPart(BaseModel):
    part_name: str
    options: list[PartOption]


class CostBreakdown(BaseModel):
    dealership_cost_range: list[float]
    independent_shop_range: list[float]
    parts_total: float
    diy_total: float
    estimated_labor_hours: float


class DiagnoseResponse(BaseModel):
    summary: str
    is_high_risk: bool
    high_risk_system: str | None = None
    warning_message: str | None = None
    recommended_parts: list[RecommendedPart] = []
    cost_breakdown: CostBreakdown | None = None


class RepairRequest(BaseModel):
    vin: str
    symptoms: str
    obd_codes: list[str] | str | None = None
    tools: list[str] | str | None = None
    stripe_session_id: str
    vehicle: VehicleInfo | None = None

    @field_validator("obd_codes")
    @classmethod
    def normalize_obd_codes(cls, v: list[str] | str | None) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v

    @field_validator("tools")
    @classmethod
    def normalize_tools(cls, v: list[str] | str | None) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


class RepairResponse(BaseModel):
    repair_steps: list[str]
    citations: list[str]


class CheckoutRequest(BaseModel):
    vin: str
    price_type: str = "single"


class CheckoutResponse(BaseModel):
    checkout_url: str


class VinOcrResponse(BaseModel):
    vin: str
    confidence: float
    decoded_vehicle: dict[str, Any] | None = None


# 8. Endpoints
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/vin/{vin}")
async def decode_vin(vin: str) -> dict[str, Any]:
    res: dict[str, Any] = await decode_vin_internal(vin)
    return res


_OCR_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
_OCR_MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8MB


@app.post("/api/vin/ocr", response_model=VinOcrResponse)
async def vin_ocr(file: UploadFile = File(...)) -> VinOcrResponse:  # noqa: B008
    content_type = file.content_type or ""
    if content_type not in _OCR_ALLOWED_CONTENT_TYPES:
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
            detail="Image too large (max 8MB).",
        )

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="VIN photo scanning is temporarily unavailable. Enter the VIN manually.",
        )

    vin_candidate, confidence = await _extract_vin_via_vision(
        image_bytes, content_type
    )
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


async def call_openai_completion(prompt: str, system_prompt: str = "You are an automotive AI expert mechanic.") -> str | None:
    if not settings.openai_api_key:
        return None
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }
    try:
        resp = await app.state.http_client.post(url, headers=headers, json=payload, timeout=6.0)
        if resp.status_code == 200:
            data = resp.json()
            return str(data["choices"][0]["message"]["content"]).strip()
    except Exception as e:
        logger.warning("OpenAI API call failed, falling back to RAG/mock data", error=str(e))
    return None


@app.post("/api/diagnose", response_model=DiagnoseResponse)
async def diagnose(request: DiagnoseRequest) -> DiagnoseResponse:
    obd_list: list[str] | None = request.obd_codes if isinstance(request.obd_codes, list) else ([request.obd_codes] if request.obd_codes else None)
    is_high_risk, high_risk_system, warning_message = check_high_risk(
        request.symptoms, obd_list
    )

    summary = f"Free Diagnosis Summary: Misfire or other symptom detected. Symptoms: {request.symptoms}."

    # Attempt OpenAI enhancement if key is provided
    if settings.openai_api_key:
        prompt = f"Diagnose this vehicle symptom: '{request.symptoms}'. OBD codes: {request.obd_codes}. Provide a concise 2-sentence summary of the likely root cause and immediate risks."
        ai_summary = await call_openai_completion(prompt)
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
        recommended_parts=build_recommended_parts(template, vehicle_desc),
        cost_breakdown=build_cost_breakdown(template)
    )


@app.post("/api/repair", response_model=RepairResponse)
async def repair(request: RepairRequest) -> RepairResponse:
    if not request.stripe_session_id or not request.stripe_session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment Required: stripe_session_id is required."
        )

    # Prefer the client-supplied vehicle identity (YMM selector covers makes the
    # synthetic-VIN decoder does not); fall back to decoding the VIN.
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
    from backend.rag.retriever import retrieve

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
                "Reconnect the electrical harness plug ensuring the click sound is heard, reinstall the engine cover, and reconnect the negative battery terminal."
            ]
            citations = [
                "Honda Civic ESM 2016-2021 Section 12-4",
                "Lexus ESM 2016-2022 Section 14-8",
                "Toyota Master Workshop Manual Pub. No. T3-094"
            ]

    if settings.openai_api_key:
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
            f"Ensure steps include specific socket sizes (e.g. 10mm deep socket) and exact bolt torque specifications phrased starting with the word 'Torque' (e.g. 'Torque the bolts to 7.5 ft-lbs') where appropriate. No emojis."
        )
        ai_steps_text = await call_openai_completion(prompt)
        if ai_steps_text:
            parsed_steps = [line.lstrip("1234567890. -").strip() for line in ai_steps_text.split("\n") if line.strip() and len(line.strip()) > 5]
            if len(parsed_steps) >= 2:
                repair_steps = parsed_steps

    return RepairResponse(
        repair_steps=repair_steps,
        citations=citations
    )


@app.post("/api/payments/create-checkout", response_model=CheckoutResponse)
async def create_checkout(request: CheckoutRequest) -> CheckoutResponse:
    # Simply point mock Stripe success stub
    mock_url = f"{settings.backend_url}/api/payments/success-stub?session_id=cs_test_123&vin={request.vin}"
    return CheckoutResponse(checkout_url=mock_url)


@app.get("/api/payments/success-stub")
async def success_stub(request: Request, session_id: str, vin: str) -> RedirectResponse:
    # Forward all query params (including extras like promo, referrer) to the frontend
    extra = {k: v for k, v in request.query_params.items() if k not in ("session_id", "vin")}
    params = f"session_id={session_id}&vin={vin}"
    if extra:
        params += "&" + "&".join(f"{k}={v}" for k, v in extra.items())
    redirect_url = f"{settings.frontend_url}/repair/success?{params}"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@app.post("/api/payments/webhook")
async def webhook() -> dict[str, str]:
    return {"status": "received"}
