# Milestone 3 (Backend API Server) Analysis Report

This analysis report details the implementation plan and architectural design for the Backend API Server (Milestone 3) for the **Automotive AI Repair Engine (RAPP)**. It is structured to guide the implementer in writing clean, compliant, and robust code.

---

## 1. API Endpoint Specifications & Schemas

To satisfy the requirements of the E2E tests, the mock application, and the frontend flow, the backend must implement the following endpoints in a single flat file `backend/main.py`.

### 1.1 `GET /health`
- **Purpose**: Health check endpoint.
- **Response**: `{"status": "ok"}`
- **HTTP Status**: `200 OK`

### 1.2 `GET /api/vin/{vin}`
- **Purpose**: Decode the VIN using the NHTSA API.
- **NHTSA URL**: `https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json`
- **Parsing Rules**:
  - Iterate through the `"Results"` list of objects returned by the NHTSA API.
  - Extract values where `"Variable"` matches the keys below:
    - `year`: From `"Model Year"` (convert to integer if digits).
    - `make`: From `"Make"`.
    - `model`: From `"Model"`.
    - `drive_type`: From `"Drive Type"`.
    - Engine: Retrieve `"Displacement (L)"` and `"Engine Number of Cylinders"`. If both exist, format as `"{displacement_l}L {cylinders} Cylinders"`. If cylinders is missing, format as `"{displacement_l}L"`. If `"Displacement (L)"` is missing, check `"Displacement (CC)"` and format as `"{displacement_cc}CC"`. Fallback to `"Unknown"` if none are available.
- **Response Schema**:
  ```json
  {
    "year": 2021,
    "make": "HONDA",
    "model": "CIVIC",
    "engine": "1.5L 4 Cylinders",
    "drive_type": "FWD"
  }
  ```

### 1.3 `POST /api/diagnose`
- **Purpose**: Perform a free initial diagnosis and return safety flags.
- **Request Body**:
  ```json
  {
    "vin": "1HGBH41JXMN109186",
    "symptoms": "P0301 - Cylinder 1 Misfire Detected",
    "obd_codes": "P0301",
    "tools": ["Basic Hand Tools", "Jack & Stands"]
  }
  ```
- **Response Schema**:
  ```json
  {
    "summary": "Based on code P0301 and symptoms, a Cylinder 1 misfire is detected. Common causes include a faulty ignition coil or spark plug.",
    "is_high_risk": false,
    "high_risk_system": null,
    "warning_message": null
  }
  ```
- **High-Risk Flags Check**: Matches symptoms/OBD codes against high-risk system definitions (see Section 2).

### 1.4 `POST /api/repair`
- **Purpose**: Retrieve detailed RAG-verified repair steps and citations. Requires Stripe verification.
- **Request Body**:
  ```json
  {
    "vin": "1HGBH41JXMN109186",
    "symptoms": "P0301 - Cylinder 1 Misfire Detected",
    "obd_codes": "P0301",
    "tools": ["Basic Hand Tools", "Jack & Stands"],
    "stripe_session_id": "cs_test_123"
  }
  ```
- **Validation**: Verify `stripe_session_id` is not empty. If missing or empty, raise `HTTPException(status_code=402, detail="Payment Required")` or `HTTPException(status_code=400, detail="Invalid Stripe Session ID")`.
- **RAG Integration**: Call `retrieve(query, vin_meta, k=5)` using the decoded VIN metadata and symptom/code query (see Section 3).
- **Response Schema**:
  ```json
  {
    "repair_steps": [
      "1. Disconnect negative battery terminal.",
      "2. Replace ignition coil on Cylinder 1."
    ],
    "citations": [
      "Honda Civic ESM 2016-2021 Section 12-4"
    ]
  }
  ```

### 1.5 `POST /api/payments/create-checkout`
- **Purpose**: Generate a mock Stripe checkout URL.
- **Request Body**:
  ```json
  {
    "vin": "1HGBH41JXMN109186",
    "price_type": "single"
  }
  ```
- **Response Schema**:
  ```json
  {
    "checkout_url": "http://localhost:8000/api/payments/success-stub?session_id=cs_test_123&vin=1HGBH41JXMN109186"
  }
  ```

### 1.6 `GET /api/payments/success-stub`
- **Purpose**: Simulate successful payment redirect.
- **Parameters**: `session_id` (str), `vin` (str).
- **Behavior**: Responds with an HTTP 307 Temporary Redirect to the frontend route:
  `{FRONTEND_URL}/repair/success?session_id={session_id}&vin={vin}` (where `FRONTEND_URL` defaults to `http://localhost:3000` or read from request headers).

### 1.7 `POST /api/payments/webhook`
- **Purpose**: Receives Stripe webhooks (stub).
- **Response**: `{"status": "received"}` (HTTP 200).

---

## 2. High-Risk Safety Protocol Gating

To mitigate liability, the backend must programmatically intercept diagnostic inputs matching high-risk categories in `/api/diagnose`.

### 2.1 Keyword & Category Definitions
The diagnostic inputs (`symptoms` and `obd_codes`) should be concatenated and evaluated case-insensitively against:

1. **SRS / Airbags**
   - **Keywords**: `"airbag"`, `"srs"`, `"pretensioner"`, `"clockspring"`, `"side curtain"`
   - **Fields**:
     - `is_high_risk`: `True`
     - `high_risk_system`: `"airbag"`
     - `warning_message`: `"DANGER: SRS / Airbag systems are explosive and safety-critical. Professional service is highly recommended."`

2. **EV Battery / High-Voltage**
   - **Keywords**: `"ev battery"`, `"hybrid battery"`, `"high voltage"`, `"hv battery"`, `"traction battery"`
   - **Fields**:
     - `is_high_risk`: `True`
     - `high_risk_system`: `"EV battery"`
     - `warning_message`: `"DANGER: High-voltage EV/hybrid battery systems carry lethal voltage. Professional service is highly recommended."`

3. **Pressurized Fuel Line**
   - **Keywords**: `"fuel line"`, `"fuel rail"`, `"pressurized fuel"`, `"high pressure fuel"`, `"fuel leak"`
   - **Fields**:
     - `is_high_risk`: `True`
     - `high_risk_system`: `"fuel line"`
     - `warning_message`: `"DANGER: Pressurized fuel lines are highly flammable and run under extreme pressure. Professional service is highly recommended."`

---

## 3. RAG Retrieval Integration & Import Hygiene

To maintain codebase sanity, strict isolation of dependencies is required.

### 3.1 Function Invocation
The backend must retrieve document snippets using the dedicated retriever:
```python
from backend.rag.retriever import retrieve

# Usage
results = retrieve(query=query, vin_meta=vin_meta, k=5)
```
Where:
- `query` is a string constructed from symptoms and OBD codes.
- `vin_meta` is the dict returned from the VIN decoding logic (normalized make, model, year, engine, drive_type).
- `k` is the number of results to fetch (default: 5).

### 3.2 Import Bleed Prevention (ChromaDB)
- **Constraint**: **No** chromadb imports may exist outside of the `backend/rag/` folder.
- **Vigilance**: The file `backend/main.py` **must not** contain lines such as:
  ```python
  import chromadb
  from chromadb.config import Settings
  ```
- **Rationale**: The RAG layer encapsulates ChromaDB interactions. Importing `retrieve` is completely safe because `backend/rag/retriever.py` and `backend/rag/__init__.py` contain no top-level chromadb imports. The `ChromaVectorStore` class imports `chromadb` locally inside its `__init__` method, preventing dependency bleed during module import.

---

## 4. CORS, Layout, & Dependency Management

- **CORS Config**:
  Enable `CORSMiddleware` in FastAPI. Allow origins `http://localhost:3000` (development frontend) and `http://localhost:3099` (mock E2E runner), or configure via environment variable.
- **Flat Layout**:
  All routes and server configurations must reside strictly in `backend/main.py`.
- **No Auth**:
  Verify that **no** login/auth endpoints, user databases, or OAuth flows exist.
- **Requirements Clean Up**:
  The implementer must delete the legacy `backend/requirements.txt` file and manage all dependencies exclusively using Poetry (`pyproject.toml`).

---

## 5. Backend Testing Strategy

To verify the endpoints, the implementer should create a pytest test suite under `tests/unit/test_main.py` containing:

1. **Test `/health`**:
   Verify response is `{"status": "ok"}`.
2. **Test `/api/vin/{vin}` with Mocking**:
   Use `pytest-asyncio` and patch `httpx.AsyncClient.get` to return a mock NHTSA payload. Assert correct parsing of Make, Model, Year, Engine, and Drive Type.
3. **Test `/api/diagnose` Safety Flags**:
   Provide various symptoms matching high-risk keywords and check that `is_high_risk`, `high_risk_system`, and `warning_message` match the specifications.
4. **Test `/api/repair` Gate**:
   - Call `/api/repair` without `stripe_session_id` and assert 402/400 status.
   - Call with `stripe_session_id`, mock `retrieve` using `unittest.mock.patch`, and assert correct serialization of repair steps and citations.
5. **Test Payment Checkout Redirect**:
   Call `/api/payments/create-checkout`, verify checkout URL format, and test that `GET /api/payments/success-stub` returns a 307 redirect with correct parameters.
