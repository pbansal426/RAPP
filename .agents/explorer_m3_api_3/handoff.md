# Handoff Report — Milestone 3 (Backend API Server) Requirement Analysis

## 1. Observation
- **Requirement Source File**: `/Users/prathambansal/Dev/RAPP/.agents/sub_orch_m3_api/SCOPE.md`
  - Line 4: `Implement a FastAPI application in a single flat file backend/main.py...`
  - Line 25: `All backend API routes must be flat inside backend/main.py.`
  - Line 27: `No auth.py, login routes, or /login page may exist in the codebase.`
  - Line 31: `Dependencies managed via pyproject.toml (Poetry). Delete backend/requirements.txt if it exists.`
- **Configuration File**: `/Users/prathambansal/Dev/RAPP/pyproject.toml`
  - Line 12: `uvicorn = { extras = ["standard"], version = "^0.30.0" }`
  - Line 22: `gunicorn = "^22.0.0"`
  - Line 26: `ruff = "^0.4.0"`
  - Line 27: `black = "^24.4.0"`
  - Line 28: `mypy = "^1.10.0"`
  - Line 29: `pytest = "^8.2.0"`
- **Legacy Dependencies File**: `/Users/prathambansal/Dev/RAPP/backend/requirements.txt`
  - Contains:
    ```
    fastapi
    uvicorn
    chromadb>=0.4.0
    pytest
    ```
- **Codebase Scan**:
  - Found no files containing `auth` or `login` in `/Users/prathambansal/Dev/RAPP` (except documentation, requirements, and node_modules).
  - Search command `find . -type f \( -name "*auth*.py" -o -name "*login*" \) -not -path "*/node_modules/*" -not -path "*/.venv/*" -not -path "*/.git/*"` yielded 0 results.

## 2. Logic Chain
1. Based on `SCOPE.md` requirements, the backend API server must be placed in a single flat file `backend/main.py` using FastAPI.
2. Based on `pyproject.toml`, the dependencies list includes both `gunicorn` and `uvicorn`, indicating a standard ASGI production setup is needed where Gunicorn supervises Uvicorn workers.
3. Code formatting, linting, and type checking are configured in `pyproject.toml` using `black`, `ruff`, and `mypy` (strict mode). The backend codebase can be validated using these tools via Poetry.
4. Unit testing is set up using `pytest` pointing to `tests/unit`. To verify the backend endpoints, a unit test suite (e.g. `tests/unit/test_api.py`) needs to be added that uses FastAPI's `TestClient` or `httpx` to test API routes with mocked integrations (such as NHTSA public API).
5. All dependencies listed in `backend/requirements.txt` are already represented in `pyproject.toml`. Thus, the file `backend/requirements.txt` is redundant and can be safely deleted.
6. The codebase contains no existing authentication or login files, adhering to the "No Auth" constraint. This can be verified continuously using targeted `find` and `grep` commands.

## 3. Caveats
- The backend `backend/main.py` is not yet implemented (we are in explorer/read-only mode), so the proposed Gunicorn run configuration and test file `tests/unit/test_api.py` are design proposals that must be verified once `backend/main.py` is created.
- High-risk symptoms warning mechanism (airbags, EV battery, fuel line) must be mapped to specific keywords (e.g. "airbag", "srs", "ev battery", "fuel line", "pressurized fuel") in the symptom text.

## 4. Conclusion
The requirements for Milestone 3 are fully analyzed. To proceed with implementation:
1. Gunicorn should be run with 4 UvicornWorker instances on port 8000 for production.
2. Linting and formatting can be validated using `black`, `ruff`, and `mypy`. Endpoints should be verified via a new unit test suite using `pytest` and `fastapi.testclient`.
3. The legacy `backend/requirements.txt` should be deleted.
4. Continuous check commands should be integrated into verification to guarantee zero leakage of auth/login components.

## 5. Verification Method
- **Dependency Redundancy**: Compare `/Users/prathambansal/Dev/RAPP/backend/requirements.txt` with `/Users/prathambansal/Dev/RAPP/pyproject.toml` to ensure all packages are declared. Run `rm backend/requirements.txt` to remove it.
- **Auth/Login Absence**: Run the following validation script commands to verify no auth files or routes are present:
  ```bash
  find . -type f \( -name "*auth*.py" -o -name "*login*" \) -not -path "*/node_modules/*" -not -path "*/.venv/*" -not -path "*/.git/*"
  grep -rnw backend/ -e "login" -e "auth" --exclude-dir={.venv,node_modules,.git,__pycache__}
  ```
- **Linting & Formatting Validation**: Run:
  ```bash
  poetry run black --check backend/
  poetry run ruff check backend/
  poetry run mypy backend/
  ```
- **Tests Execution**: Once implemented, run:
  ```bash
  poetry run pytest tests/unit/
  ```
