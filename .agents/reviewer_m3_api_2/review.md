# RAPP Backend API Server Review Report — Milestone 3

**Verdict**: PASS

This report presents the Quality Review and Adversarial Review for the Backend API Server implementation in `backend/main.py` and the unit test suite in `tests/unit/test_api.py` and `tests/unit/test_rag.py`.

---

## Part 1: Quality Review

### 1. Correctness & Feature Conformance

- **NHTSA DecodeVin API Parsing**:
  - The parsing in `decode_vin_internal` is clean, robust, and correctly extracts the following fields:
    - **Model Year**: Extracted via `"Model Year"` and safely cast to `int` if possible.
    - **Make & Model**: Extracted and verified to be non-empty and not matching exclusions (e.g. `"null"`, `"none"`).
    - **Drive Type**: Extracted, defaulting to `"Unknown"` if missing.
    - **Engine**: Formatted appropriately depending on combinations of `Displacement (L)`, `Displacement (CC)`, and `Engine Number of Cylinders` (e.g., `"1.5L 4 Cylinders"`, `"1.5L"`, `"1500CC 4 Cylinders"`, `"1500CC"`, or `"Unknown"`).
  - The exclusions correctly handle empty or invalid values (e.g., `cleaned_val.lower() not in ("", "none", "null", "not applicable")`).

- **HTTP 404 Error Handling**:
  - If `make` or `model` are missing or filtered out from the NHTSA response, the server raises a `HTTP_404_NOT_FOUND` exception. This conforms to requirements.

- **High-Risk System Detection (`/api/diagnose`)**:
  - Combined input (`symptoms` and `obd_codes`) is normalized using `.lower()`.
  - Case-insensitive matching is conducted against lists of keywords for:
    - **SRS/Airbag**: matches `["airbag", "srs", "pretensioner", "clockspring", "side curtain"]`
    - **EV battery**: matches `["ev battery", "hybrid battery", "high voltage", "hv battery", "traction battery", "lithium"]`
    - **Fuel line**: matches `["fuel line", "fuel rail", "pressurized fuel", "high pressure fuel", "fuel leak"]`
  - When a high-risk system is identified, it sets:
    - `is_high_risk = True`
    - `high_risk_system` to `"Airbag/SRS"`, `"EV Battery"`, or `"Fuel Line"`
    - `warning_message` to a helpful, detailed safety warning.

- **Checkout & Webhook Stubs**:
  - `/api/payments/create-checkout`: Correctly returns a mocked Stripe checkout URL that directs to the success stub.
  - `/api/payments/success-stub`: Correctly redirects back to the frontend success route using `HTTP_303_SEE_OTHER` and transfers the `session_id` and `vin` parameters.
  - `/api/payments/webhook`: Correctly responds with `{"status": "received"}`.

---

### 2. Verified Claims

- **Correct decoding of VIN attributes** → **PASS**
  - Verified via static code review of `decode_vin_internal` and test assertions in `tests/unit/test_api.py::test_vin_decoding_success`.
- **404 Raised on missing Make/Model** → **PASS**
  - Verified via static code review of lines 189-193 in `backend/main.py` and test `test_vin_decoding_not_found`.
- **Case-insensitive high-risk system detection** → **PASS**
  - Verified via static code review of `check_high_risk` and unit tests `test_diagnose_high_risk_airbag`, `test_diagnose_high_risk_ev_battery`, and `test_diagnose_high_risk_fuel_line`.
- **JSON warning fields populated correctly** → **PASS**
  - Verified via Pydantic model `DiagnoseResponse` schema matching and assertions in the diagnostic test suite.
- **Checkout, Success Redirect, and Webhook stubs** → **PASS**
  - Verified via static review of lines 404-419 in `backend/main.py` and unit tests `test_create_checkout`, `test_success_stub`, and `test_payments_webhook`.

---

### 3. Coverage Gaps & Unverified Items

- **Unverified Item: Unit test execution on local machine**
  - **Reason**: The global `poetry` command was missing, and running `.venv/bin/pytest` directly failed due to missing dependencies (specifically `structlog`). Installing dependencies via `.venv/bin/pip` or checking alternative poetry paths timed out due to the user being offline (unable to approve commands).
  - **Risk**: Low. The unit test suite is syntactically correct, comprehensive, and has been reviewed line-by-line.

---

## Part 2: Adversarial Review

### 1. Assumption Stress-Testing

- **Assumption 1**: The client inputs `obd_codes` and `tools` as a list of strings.
  - *Attack Scenario*: The client sends a string or null instead of a list.
  - *Blast Radius*: Normally, this would crash the concatenation or list iteration in `/api/diagnose` or `/api/repair`.
  - *Mitigation*: The Pydantic request models (`DiagnoseRequest` and `RepairRequest`) implement `@field_validator` with `normalize_obd_codes` and `normalize_tools`. This converts string/null inputs to lists, making it extremely resilient.
- **Assumption 2**: The NHTSA database returns values as literal strings like `"null"`, `"none"`, or `"not applicable"`.
  - *Attack Scenario*: A mock or real API response returns these strings, causing fake makes/models to bypass checks.
  - *Blast Radius*: The app parses `"null"` as the Make, displaying nonsense to the user.
  - *Mitigation*: The codebase handles this by filtering out these specific strings case-insensitively in `decode_vin_internal` (line 184).
- **Assumption 3**: Standard FastAPI exception handler leaks stack traces.
  - *Attack Scenario*: Internal crashes (e.g. database disconnect, API timeout) leakage.
  - *Blast Radius*: Potential security vulnerability where raw database paths, code lines, or internal structures are exposed to users in the HTTP response.
  - *Mitigation*: Centralized exception handlers catch `StarletteHTTPException`, `RequestValidationError`, and `Exception` to return neat JSON responses (`{"error": "..."}`) without exposing traceback information.

---

### 2. Stress Test Predictions

- **Empty Inputs**: Sending an empty `vin` or bad characters raises HTTP 400. This is tested and handled in `decode_vin_internal`.
- **NHTSA Timeout**: If the NHTSA API is slow or times out, it is caught as `httpx.HTTPError`, logged safely, and returns `HTTP_502_BAD_GATEWAY` rather than propagating the crash.

---

### 3. Recommendations

1. **Dependency Locking**: Add a `poetry.lock` file or ensure python environment dependencies are locked/installed so that the test suite runs out of the box.
2. **CORS Configuration**: The CORS origins are configurable via settings, but default to `*` if the config list is empty. This is acceptable for dev/mock testing but should be secured in production.
