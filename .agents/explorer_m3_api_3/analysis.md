# Milestone 3 (Backend API Server) Requirement Analysis

## Executive Summary
This document analyzes the requirements for implementing the FastAPI backend API server (`backend/main.py`) for the Automotive AI Repair Engine (RAPP) Phase 1 MVP, focusing on:
1. Production-ready Gunicorn/Uvicorn configuration.
2. Comprehensive testing, linting, and formatting setup.
3. Verification procedures to ensure no auth/login mechanisms exist, and steps to clean up redundant requirements files.

All findings are based on a read-only exploration of the workspace `/Users/prathambansal/Dev/RAPP` and its existing configurations in `pyproject.toml`.

---

## 1. Gunicorn/Uvicorn Production Configuration
FastAPI application files (`backend/main.py`) are typically run via Uvicorn in development. However, for production stability, resource utilization, and concurrency, Gunicorn is utilized as a process manager supervising Uvicorn worker processes (`uvicorn.workers.UvicornWorker`).

### Recommended Gunicorn CLI Run Command
The FastAPI app can be launched in production using the following command executed from the root directory:
```bash
poetry run gunicorn backend.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 60 \
  --keep-alive 5 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

### Proposed `gunicorn_conf.py` (Production Configuration File)
To avoid long CLI invocations and centralize configurations, a `gunicorn_conf.py` file can be placed in the project root:
```python
# gunicorn_conf.py
import multiprocessing
import os

# Port and interface binding
bind = "0.0.0.0:8000"

# Process management: calculate workers dynamically based on CPU count
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))

# Worker settings
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 60
keepalive = 5

# Logging: output to stdout/stderr for container friendliness
loglevel = "info"
accesslog = "-"
errorlog = "-"
```
This can be run via:
```bash
poetry run gunicorn -c gunicorn_conf.py backend.main:app
```

---

## 2. Testing, Linting, and Formatting Setup

### A. Code Quality (Linting & Formatting)
The current `pyproject.toml` defines tools and configurations for linting (`ruff`), formatting (`black`), and type checking (`mypy`).

To verify and enforce code quality, the following commands should be executed:
- **Format Code**: `poetry run black backend/` (checks style compliance)
- **Lint Code**: `poetry run ruff check backend/` (checks for code issues and imports order)
- **Type Check**: `poetry run mypy backend/` (runs strict static analysis on `backend/` except excluded folders)

### B. Testing Framework Configuration
Unit tests are configured to run under `pytest` with `testpaths = ["tests/unit"]` in `pyproject.toml`.
For testing the new FastAPI endpoints, we recommend adding a `tests/unit/test_api.py` unit test file that exercises the routes. Since `httpx` is already listed as a dependency (`httpx = "^0.27.0"`), `httpx.AsyncClient` or FastAPI's `TestClient` can be used to perform async requests against the app in a test context.

### Proposed Test File: `tests/unit/test_api.py`
This test file validates all endpoints and mock behaviors:
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("httpx.AsyncClient.get")
def test_vin_decoding_success(mock_get):
    # Mocking NHTSA DecodeVin API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Results": [
            {"Variable": "Model Year", "Value": "2018"},
            {"Variable": "Make", "Value": "HONDA"},
            {"Variable": "Model", "Value": "CIVIC"},
            {"Variable": "Displacement (L)", "Value": "1.5"},
            {"Variable": "Engine Number of Cylinders", "Value": "4"},
            {"Variable": "Drive Type", "Value": "FWD"},
        ]
    }
    mock_get.return_value = mock_response

    response = client.get("/api/vin/1HGBH41JXMN109186")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2018 or data["year"] == "2018"
    assert data["make"] == "HONDA"
    assert data["model"] == "CIVIC"
    assert "1.5" in data["engine"]
    assert data["drive_type"] == "FWD"

def test_diagnose_stub_low_risk():
    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "P0301 - misfire on cylinder 1",
        "obd_codes": "P0301",
        "tools": ["basic hand tools"]
    }
    response = client.post("/api/diagnose", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_high_risk"] is False
    assert "diagnosis" in data

def test_diagnose_stub_high_risk():
    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "SRS warning light is on, airbag failure",
        "obd_codes": "B1000",
        "tools": ["multimeter"]
    }
    response = client.post("/api/diagnose", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_high_risk"] is True
    assert "airbag" in data["high_risk_system"].lower()
    assert "warning_message" in data

def test_repair_stub():
    payload = {
        "vin": "1HGBH41JXMN109186",
        "symptoms": "P0301 - misfire on cylinder 1",
        "obd_codes": "P0301",
        "tools": ["basic hand tools"],
        "stripe_session_id": "cs_test_123"
    }
    response = client.post("/api/repair", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "steps" in data
    assert "citations" in data

def test_create_checkout():
    payload = {
        "vin": "1HGBH41JXMN109186",
        "price_type": "standard"
    }
    response = client.post("/api/payments/create-checkout", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "checkout_url" in data
    assert "success-stub" in data["checkout_url"]

def test_payments_webhook():
    payload = {
        "id": "evt_test",
        "type": "checkout.session.completed"
    }
    response = client.post("/api/payments/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "received"}
```

---

## 3. Auth/Login Cleanliness & Dependency Deletion

### A. Verification Procedures for No Auth/Login Routes
To guarantee that no user authentication or login flows leak into the codebase (Milestone 3 constraints), the following inspection steps must be followed:

1. **Filename Scan**: Verify no Python source file or page file contains terms related to auth or login.
   ```bash
   # Search for auth or login in file names, ignoring venv, git, node_modules
   find . -type f \( -name "*auth*.py" -o -name "*login*" \) \
     -not -path "*/node_modules/*" \
     -not -path "*/.venv/*" \
     -not -path "*/.git/*"
   ```
2. **Codebase Grep Scan**: Ensure no routes or routes definitions matching `/login` or auth decorators exist.
   ```bash
   # Search for login/auth routes or patterns in source files
   grep -rnw backend/ -e "login" -e "auth" --exclude-dir={.venv,node_modules,.git,__pycache__}
   ```
3. **Frontend Page Scan**: Assert that no `/login` route or page is defined in the frontend directory.
   ```bash
   find frontend/src/app frontend/src/pages -name "*login*" -not -path "*/node_modules/*" 2>/dev/null
   ```

### B. Redundant `backend/requirements.txt` Deletion
- **Location**: `/Users/prathambansal/Dev/RAPP/backend/requirements.txt`
- **Verification of Dependencies**: All dependencies listed in `backend/requirements.txt` are fully declared in `pyproject.toml` with compatible or more recent versions (e.g. `fastapi = "^0.111.0"`, `uvicorn`, `chromadb = "^0.5.3"`, `pytest = "^8.2.0"`).
- **Execution Command**: Since dependencies are consolidated in `pyproject.toml` (managed via Poetry), `backend/requirements.txt` must be deleted.
  ```bash
  rm /Users/prathambansal/Dev/RAPP/backend/requirements.txt
  ```
