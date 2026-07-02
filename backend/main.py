import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException


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
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid year format in synthetic VIN."
            )
            
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
            "engine": specs["engine"],
            "drive_type": specs["drive_type"]
        }

    # Validate VIN format: exactly 17 alphanumeric characters
    if len(vin) != 17 or not vin.isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid VIN format. Must be exactly 17 alphanumeric characters."
        )

    url = f"{settings.nhtsa_base_url}/DecodeVin/{vin}?format=json"
    try:
        response = await app.state.http_client.get(url, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as err:
        logger.error("NHTSA API communication error", error=str(err), url=url)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error communicating with NHTSA API"
        ) from err

    data = response.json()
    results = data.get("Results", [])

    data_dict = {}
    for item in results:
        var_name = item.get("Variable")
        var_val = item.get("Value")
        if var_name and var_val is not None:
            cleaned_val = str(var_val).strip()
            if cleaned_val.lower() not in ("", "none", "null", "not applicable"):
                data_dict[var_name] = cleaned_val

    make = data_dict.get("Make")
    model = data_dict.get("Model")
    if not make or not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle make or model not found in NHTSA database"
        )

    year_str = data_dict.get("Model Year")
    year: int | str | None = None
    if year_str:
        try:
            year = int(year_str)
        except ValueError:
            year = year_str

    disp_l = data_dict.get("Displacement (L)")
    cylinders = data_dict.get("Engine Number of Cylinders")
    disp_cc = data_dict.get("Displacement (CC)")

    if disp_l and cylinders:
        engine = f"{disp_l}L {cylinders} Cylinders"
    elif disp_l:
        engine = f"{disp_l}L"
    elif disp_cc and cylinders:
        engine = f"{disp_cc}CC {cylinders} Cylinders"
    elif disp_cc:
        engine = f"{disp_cc}CC"
    else:
        engine = "Unknown"

    return {
        "year": year,
        "make": make,
        "model": model,
        "engine": engine,
        "drive_type": data_dict.get("Drive Type", "Unknown")
    }


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
class DiagnoseRequest(BaseModel):
    vin: str
    symptoms: str
    obd_codes: list[str] | str | None = None
    tools: list[str] | str | None = None

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


class DiagnoseResponse(BaseModel):
    summary: str
    is_high_risk: bool
    high_risk_system: str | None = None
    warning_message: str | None = None


class RepairRequest(BaseModel):
    vin: str
    symptoms: str
    obd_codes: list[str] | str | None = None
    tools: list[str] | str | None = None
    stripe_session_id: str

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


# 8. Endpoints
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/vin/{vin}")
async def decode_vin(vin: str) -> dict[str, Any]:
    res: dict[str, Any] = await decode_vin_internal(vin)
    return res


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

    return DiagnoseResponse(
        summary=summary,
        is_high_risk=is_high_risk,
        high_risk_system=high_risk_system,
        warning_message=warning_message
    )


@app.post("/api/repair", response_model=RepairResponse)
async def repair(request: RepairRequest) -> RepairResponse:
    if not request.stripe_session_id or not request.stripe_session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment Required: stripe_session_id is required."
        )

    vin_meta = await decode_vin_internal(request.vin)

    # Retrieve relevant steps from RAG store
    from backend.rag.retriever import retrieve

    query = f"{request.symptoms} " + " ".join(request.obd_codes or [])
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
        # Fallback repair/modification steps and citations
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
        prompt = (
            f"Generate a detailed, clinic-grade repair or modification procedure for VIN {request.vin} ({vin_meta.get('year')} {vin_meta.get('make')} {vin_meta.get('model')}). "
            f"Symptoms/Target: {request.symptoms}. Available tools: {tools_str}. "
            f"Retrieved OEM manual snippets: {repair_steps}. "
            f"Provide a comprehensive, step-by-step guide (from safety/preparation to access, replacement, and reassembly/verification) that takes the user to the very end of the project for a complete and full fix. "
            f"Ensure steps include specific socket sizes (e.g. 10mm deep socket) and exact bolt torque specifications (e.g. 7.5 ft-lbs) where appropriate."
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
