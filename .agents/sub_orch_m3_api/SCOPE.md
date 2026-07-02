# Scope: Milestone 3 - Backend API Server

## Objective
Implement a FastAPI application in a single flat file `backend/main.py` containing a live VIN decoding endpoint, a health check, and stubs for diagnosis, repair, and Stripe checkout/webhook.

## Requirements
1. **Health Check**:
   - `GET /health` returns `{"status": "ok"}`
2. **VIN Ingestion & Decoding**:
   - `GET /api/vin/{vin}` calls the NHTSA API: `https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json`
   - Parses the JSON response to extract:
     - `year` (from "Model Year")
     - `make` (from "Make")
     - `model` (from "Model")
     - `engine` (from "Displacement (L)" + "Engine Number of Cylinders", or "Displacement (CC)" if Displacement (L) is missing)
     - `drive_type` (from "Drive Type")
   - Returns structured JSON containing: `year`, `make`, `model`, `engine`, `drive_type`.
3. **Stubs (Returning HTTP 200 with appropriate payload schemas for the frontend)**:
   - `POST /api/diagnose`: Receive `vin`, `symptoms`, `obd_codes`, `tools`. Perform RAG search using `retrieve` from `backend.rag.retriever` if needed, or return a stub with a diagnosis summary and check for high-risk flags (airbags, EV battery, fuel line) to set `is_high_risk`, `high_risk_system`, and `warning_message`.
   - `POST /api/repair`: Receive `vin`, `symptoms`, `obd_codes`, `tools`, `stripe_session_id`. Return detailed repair steps with RAG citations.
   - `POST /api/payments/create-checkout`: Receive `vin`, `price_type`. Return a mock Stripe checkout URL that redirects to `/api/payments/success-stub?session_id=cs_test_123` which then redirects back to the frontend `/repair/success`.
   - `POST /api/payments/webhook`: Stub returning `{"status": "received"}` with HTTP 200.
4. **CORS & Layout**:
   - Enable CORS allowing the Next.js frontend origin (`http://localhost:3000` or wildcard in development).
   - All backend API routes must be flat inside `backend/main.py`.
5. **No Auth/Login**:
   - No `auth.py`, login routes, or `/login` page may exist in the codebase.

## Expected Deliverables
- `backend/main.py` containing the FastAPI application.
- Dependencies managed via `pyproject.toml` (Poetry). Delete `backend/requirements.txt` if it exists.
- Backend unit tests to verify all routes.
