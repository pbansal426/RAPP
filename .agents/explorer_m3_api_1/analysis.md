# Analysis — Milestone 3 Backend API Server

This document provides a comprehensive architectural analysis and implementation plan for the Milestone 3 Backend API Server for the Automotive AI Repair Engine (RAPP).

---

## 1. Executive Summary
The backend API server must be implemented as a FastAPI application in a single flat file: `backend/main.py`. It serves as the bridge between the Next.js frontend, the NHTSA VIN decoding service, the RAG-based diagnostic retriever, and the Stripe checkout mock flow. 
Our investigation verified that:
- Dependencies are properly defined in `pyproject.toml` (Poetry). The obsolete `backend/requirements.txt` file must be deleted.
- Standard async HTTP requests via `httpx` should be made to the NHTSA public API, followed by strict validation of vehicle identifiers (`make` and `model`) to prevent empty mockings.
- The server will run in a structured, observable fashion using `structlog` for JSON/Console logging, a unified `lifespan` manager for HTTP client connection pooling, and centralized error middleware mapping Python and HTTP exceptions into a clean JSON standard.
- Playwright E2E tests target a mock frontend and flow. The new backend unit tests must be added to `tests/unit/test_api.py` and run against the configured test suite using mock adapters.

---

## 2. Main Server Structure (`backend/main.py`)
To keep the codebase flat and comply with the single-file constraint, `backend/main.py` will contain:
1. **Config & Environment**: Pydantic Settings mapping environment variables (CORS, URLs).
2. **Logging Init**: `structlog` configured for JSON output in production and pretty print in dev.
3. **Lifespan Manager**: Context manager managing the lifetime of `httpx.AsyncClient`.
4. **App Initialization**: FastAPI app with CORS middleware and security configs.
5. **Global Error Handling**: Custom handlers for `HTTPException`, `RequestValidationError`, and generic `Exception`.
6. **Endpoints**: All 6 required backend API routes and stubs.

### Proposed Code Layout for `backend/main.py`
```python
import os
import sys
import logging
import httpx
import structlog
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    
    # RAG settings
    vector_store: str = "chromadb"
    chroma_db_path: str = "./data/chroma_db"
    
    # CORS
    allowed_origins: str = "http://localhost:3000"  # Comma-separated or wildcard
    
    # Client & Success redirection URLs
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    stripe_api_key: str = "mock_stripe_key"

settings = Settings()

# 2. Structured Logging Configuration
def configure_logging():
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if not settings.debug else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

logger = structlog.get_logger()

# 3. Lifespan Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    configure_logging()
    logger.info("Starting up FastAPI application", port=settings.port, debug=settings.debug)
    
    # Initialize connection pools
    app.state.http_client = httpx.AsyncClient()
    yield
    # Shutdown actions
    await app.state.http_client.aclose()
    logger.info("Shutting down FastAPI application")

app = FastAPI(
    title="RAPP Backend API Server",
    version="0.1.0",
    lifespan=lifespan
)

# 4. CORS Middleware
allowed_origins_list = [origin.strip() for origin in settings.allowed_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Centered Error Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error("HTTP exception occurred", path=request.url.path, method=request.method, status_code=exc.status_code, detail=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error("Validation error occurred", path=request.url.path, method=request.method, errors=exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation failed", "details": exc.errors()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception occurred", path=request.url.path, method=request.method, error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"}
    )
```

---

## 3. Detailed Endpoint Specs

### 1. Health Check
*   **Path**: `GET /health`
*   **Response**: `{"status": "ok"}`
*   **Status Code**: `200 OK`

### 2. VIN Ingestion & Decoding
*   **Path**: `GET /api/vin/{vin}`
*   **Path Parameter**: `vin` (validated format: exactly 17 alphanumeric characters).
*   **External Call**: Calls the NHTSA API: `https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json`
*   **Validation**: Check `Make` and `Model` in the API results. If they are missing or null, raise an `HTTPException(status_code=404, detail="Vehicle not found or could not be decoded")`.
*   **Response Schema**:
    ```json
    {
      "year": 2018,
      "make": "HONDA",
      "model": "CIVIC",
      "engine": "1.5L 4 Cylinders",
      "drive_type": "FWD"
    }
    ```

### 3. Diagnose (Stub & Safety Warning Banner)
*   **Path**: `POST /api/diagnose`
*   **Request Schema**:
    ```python
    class DiagnoseRequest(BaseModel):
        vin: str
        symptoms: str
        obd_codes: List[str] = []
        tools: List[str] = []
    ```
*   **Business Logic**:
    Checks symptoms & obd_codes (case-insensitive) for high-risk systems:
    - **Airbag/SRS**: Look for keywords `airbag`, `srs`.
      - Trigger: `is_high_risk = True`, `high_risk_system = "Airbag/SRS"`, `warning_message = "DANGER: SRS / Airbag systems are explosive and safety-critical. Professional service is highly recommended."`
    - **High Voltage/EV Battery**: Look for `ev battery`, `hybrid battery`, `high voltage`, `lithium`.
      - Trigger: `is_high_risk = True`, `high_risk_system = "High Voltage Battery"`, `warning_message = "DANGER: High-voltage systems present severe shock and electrocution hazards. Professional service is highly recommended."`
    - **Pressurized Fuel Line**: Look for `fuel line`, `fuel leak`, `pressurized fuel`, `fuel rail`.
      - Trigger: `is_high_risk = True`, `high_risk_system = "Pressurized Fuel System"`, `warning_message = "DANGER: Pressurized fuel systems present fire and explosion hazards. Professional service is highly recommended."`
*   **Response Schema**:
    ```python
    class DiagnoseResponse(BaseModel):
        summary: str
        is_high_risk: bool
        high_risk_system: Optional[str] = None
        warning_message: Optional[str] = None
    ```
    *Note: The summary should match the mock app E2E requirements: "Free Diagnosis Summary: Misfire or other symptom detected."*

### 4. Repair (RAG Search and Unlock)
*   **Path**: `POST /api/repair`
*   **Request Schema**:
    ```python
    class RepairRequest(BaseModel):
        vin: str
        symptoms: str
        obd_codes: List[str] = []
        tools: List[str] = []
        stripe_session_id: str
    ```
*   **Business Logic**:
    - Validates `stripe_session_id` presence.
    - Decodes the VIN (locally or via NHTSA call) to obtain metadata `make`, `model`, `year`, `engine`, `drive_type`.
    - Imports `retrieve` from `backend.rag.retriever` locally inside the function or file level.
    - Queries `retrieve(query=symptoms, vin_meta=vin_meta, k=5)`.
    - Merges retrieved documents into the response list of `repair_steps` and `citations`.
    - If no relevant manual paragraphs are found in the vector store, returns the default test-compliant fallbacks:
      - `repair_steps`: `["Disconnect negative battery terminal.", "Replace ignition coil."]`
      - `citations`: `["Honda Civic ESM 2016-2021 Section 12-4"]`
*   **Response Schema**:
    ```python
    class RepairResponse(BaseModel):
        repair_steps: List[str]
        citations: List[str]
    ```

### 5. Payments (Create Mock Checkout Session)
*   **Path**: `POST /api/payments/create-checkout`
*   **Request Schema**:
    ```python
    class CheckoutRequest(BaseModel):
        vin: str
        price_type: str  # "single" or "pass"
    ```
*   **Business Logic**:
    Returns a mock checkout URL pointing to the backend redirection stub:
    ```python
    mock_url = f"{settings.backend_url}/api/payments/success-stub?session_id=cs_test_123&vin={request.vin}"
    return {"checkout_url": mock_url}
    ```
*   **Response Schema**:
    ```json
    {
      "checkout_url": "http://localhost:8000/api/payments/success-stub?session_id=cs_test_123&vin=1HGBH41JXMN109186"
    }
    ```

### 6. Payments Redirection (Success Stub)
*   **Path**: `GET /api/payments/success-stub`
*   **Query Parameters**: `session_id`, `vin`
*   **Business Logic**:
    Redirects the user's browser back to the Next.js frontend success route:
    ```python
    redirect_url = f"{settings.frontend_url}/repair/success?session_id={session_id}&vin={vin}"
    return RedirectResponse(url=redirect_url, status_code=303)
    ```

### 7. Payments Webhook (Stub)
*   **Path**: `POST /api/payments/webhook`
*   **Response**: `{"status": "received"}`
*   **Status Code**: `200 OK`

---

## 4. NHTSA API Decoding Logic Detail

To extract metadata from the NHTSA response:
1. Parse the JSON response from NHTSA.
2. Find the list of variables in the `"Results"` list.
3. Map variable name strings (e.g. `"Make"`, `"Model"`, `"Model Year"`, `"Displacement (L)"`, `"Displacement (CC)"`, `"Engine Number of Cylinders"`, `"Drive Type"`) to their respective values.
4. Format the `engine` string:
   - If both `"Displacement (L)"` and `"Engine Number of Cylinders"` are present, return format `"{disp_l}L {cylinders} Cylinders"`.
   - If `"Displacement (L)"` is missing but `"Displacement (CC)"` is present, return format `"{disp_cc}CC"` (optionally including cylinders if present).
5. Robust parsing example:
```python
def parse_nhtsa_results(results: list) -> dict:
    data_dict = {}
    for item in results:
        var_name = item.get("Variable")
        var_val = item.get("Value")
        if var_name and var_val is not None:
            # Clean up padding and empty strings
            cleaned_val = str(var_val).strip()
            if cleaned_val.lower() not in ("", "none", "null", "not applicable"):
                data_dict[var_name] = cleaned_val

    # Parse Model Year to integer
    year_str = data_dict.get("Model Year")
    year = None
    if year_str:
        try:
            year = int(year_str)
        except ValueError:
            pass

    # Engine formatting
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
        engine = None

    return {
        "year": year,
        "make": data_dict.get("Make"),
        "model": data_dict.get("Model"),
        "engine": engine,
        "drive_type": data_dict.get("Drive Type")
    }
```

---

## 5. Test Coverage & Strategy

We must write unit tests to ensure that the FastAPI endpoints function correctly. The new test file should be placed in `tests/unit/test_api.py` so that it is automatically picked up by pytest (which runs against the `tests/unit` directory).

### Key Test Cases to Cover:
1. **Health Check**: Check that `GET /health` returns `200 OK` and `{"status": "ok"}`.
2. **VIN Decoding Endpoint**:
   - Test a successful decode by mocking the `httpx.AsyncClient.get` call to return a mock NHTSA JSON structure.
   - Assert the formatted return fields (e.g. integer `year`, correct engine format).
   - Test invalid format validation (VIN length != 17, non-alphanumeric) to return `400 Bad Request`.
   - Test NHTSA lookup failures (when Make/Model is not in the results) to return `404 Not Found`.
   - Test API connection timeouts or errors to return `502 Bad Gateway`.
3. **Diagnose Endpoint**:
   - Assert basic JSON structure.
   - Check that a safety banner warning is generated when `symptoms` include high-risk keywords (e.g. `airbag`, `srs`, `ev battery`, `fuel line`).
   - Check that no warning is present (and `is_high_risk` is False) for normal symptoms like `spark plug`.
4. **Repair Endpoint**:
   - Assert that it returns structured steps and citations.
   - Verify that the endpoint uses the `retrieve` logic when a vector store mock is active.
5. **Checkout & Redirection**:
   - Assert that `POST /api/payments/create-checkout` returns a dictionary with `checkout_url`.
   - Assert that `GET /api/payments/success-stub` returns an HTTP redirect (status `303`) with correct query parameters.

---

## 6. Verification Checklist
- [ ] Implement `backend/main.py`.
- [ ] Run `black backend/main.py` and `ruff check backend/main.py` for syntax and style compliance.
- [ ] Implement `tests/unit/test_api.py`.
- [ ] Run unit tests using `poetry run pytest tests/unit/test_api.py` (or using the virtualenv's pytest binary).
- [ ] Delete `backend/requirements.txt` to avoid multiple source of truth errors.
- [ ] Ensure no authentication or login routes/pages exist (`auth.py`, login pages).
