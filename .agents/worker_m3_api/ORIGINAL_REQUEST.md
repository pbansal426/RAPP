## 2026-06-30T23:28:50Z
You are the Worker for Milestone 3 (Backend API Server). Your working directory is /Users/prathambansal/Dev/RAPP/.agents/worker_m3_api.

Your task is to implement the Backend API Server according to the specifications in /Users/prathambansal/Dev/RAPP/.agents/sub_orch_m3_api/SCOPE.md and the Explorer analyses in:
- /Users/prathambansal/Dev/RAPP/.agents/explorer_m3_api_1/analysis.md
- /Users/prathambansal/Dev/RAPP/.agents/explorer_m3_api_2/analysis.md
- /Users/prathambansal/Dev/RAPP/.agents/explorer_m3_api_3/analysis.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Ensure:
1. Implement a FastAPI application in a single flat file backend/main.py.
   - Server must use a lifespan context manager.
   - Use structlog for structured logging.
   - Centralized exception handlers for HTTPExceptions, validation errors, and general Exception that log details but never leak stack traces to clients.
   - Configuration must use pydantic-settings with startup validation.
   - Set up CORS allowing origins (like http://localhost:3000, etc.).
2. The endpoints must be flat in backend/main.py:
   - GET /health -> returns {"status": "ok"}
   - GET /api/vin/{vin} -> Calls the NHTSA API, parses and formats make, model, year, engine, drive_type. Validates that make/model are found, raising 404 if not.
   - POST /api/diagnose -> checks symptoms and obd_codes for high-risk flags (airbag/srs, ev battery, fuel line) case-insensitively, returns is_high_risk, high_risk_system, warning_message, and a summary.
   - POST /api/repair -> RAG-verified repair steps. Requires stripe_session_id. Call `retrieve` from `backend.rag.retriever`. Fallback to standard steps and citations if not found in RAG.
   - POST /api/payments/create-checkout -> returns {"checkout_url": ...} pointing to the success stub.
   - GET /api/payments/success-stub -> redirects to the frontend (/repair/success).
   - POST /api/payments/webhook -> returns {"status": "received"}.
3. No chromadb imports may exist outside the backend/rag/ module. Do NOT import chromadb in backend/main.py.
4. No auth.py, login route, or /login page exists. Delete backend/requirements.txt.
5. Create tests/unit/test_api.py to comprehensively test all endpoints and logic.
6. Verify and run code quality checks via Poetry:
   - Format: `poetry run black backend/ tests/unit/test_api.py`
   - Lint: `poetry run ruff check backend/`
   - Type check: `poetry run mypy backend/`
   - Unit tests: `poetry run pytest tests/unit/ -v`
Include all command lines, output, and test results in your handoff report handoff.md in your working directory.
