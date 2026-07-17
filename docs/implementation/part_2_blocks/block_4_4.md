# Block 4.4 — Backend Boundary Validation, Typing Resilience (`price_type`, `symptoms`), & Rate Limits

**Parent plan**: [`../imp_part_2.md`](../imp_part_2.md) Section 5 Stage 4 Block 4.4
**Model specced**: Sonnet 5 | **Thinking specced**: Medium
**Status**: ⬜ Not started

---

## 1. Goal

Harden backend API boundaries, protect Gemini token quotas, and defend external upstream endpoints against malformed payloads and DoS scraping:
1. Enforce strict character length limits (`max_length=2000`) on `symptoms` fields across request schemas (`backend/schemas.py`).
2. Type `price_type` in `CheckoutRequest` strictly as `Literal["single", "annual"]` (`backend/schemas.py`).
3. Add a per-IP rate limit safeguard (`20 requests per minute`) to `GET /api/vin/{vin}` (`backend/routers/vin.py`).

---

## 2. Exactly what to change

### Step 1: Add `max_length` and `Literal` validation in `backend/schemas.py`

In `backend/schemas.py`, import `Literal` from `typing` and `Field` from `pydantic` (if not already imported):

```typescript
from typing import Any, Literal
from pydantic import BaseModel, Field
```

1. Locate `CheckoutRequest` (`schemas.py` ~line 170) and update `price_type`:
   ```diff
    class CheckoutRequest(BaseModel):
        vin: str
   -    price_type: str
   +    price_type: Literal["single", "annual"] = "single"
        symptoms: str = ""
   ```

2. Locate `DiagnoseRequest` (`schemas.py` ~line 100) and enforce `max_length=2000` on `symptoms`:
   ```diff
    class DiagnoseRequest(BaseModel):
        vin: str
   -    symptoms: str = ""
   +    symptoms: str = Field(default="", max_length=2000, description="Max 2000 characters.")
        obd_codes: list[str] = []
   ```

3. Locate `RepairRequest` (`schemas.py` ~line 120) and enforce `max_length=2000` on `symptoms`:
   ```diff
    class RepairRequest(BaseModel):
        vin: str
   -    symptoms: str = ""
   +    symptoms: str = Field(default="", max_length=2000, description="Max 2000 characters.")
        obd_codes: list[str] = []
   ```

4. Locate `RepairChatRequest` (`schemas.py` ~line 145) and enforce limits on both `symptoms` and `message`:
   ```diff
    class RepairChatRequest(BaseModel):
        vin: str
        vehicle: VehicleInfo | None = None
   -    symptoms: str = ""
   +    symptoms: str = Field(default="", max_length=2000)
        repair_steps: list[str] = []
   -    message: str
   +    message: str = Field(..., max_length=1000, description="Chat query max 1000 characters.")
        stripe_session_id: str = ""
   ```

### Step 2: Add rate limiting to `GET /api/vin/{vin}` in `backend/routers/vin.py`

1. Check if `slowapi` is already installed or configured in `backend/main.py`. If `slowapi` limiter is available (`from backend.core.limiter import limiter` or similar):
   ```python
   @router.get("/api/vin/{vin}", response_model=VinData)
   @limiter.limit("20/minute")
   async def decode_vin(vin: str, request: Request, db: Session = Depends(get_db)):
   ```
2. If `slowapi` is not yet globally configured, implement a lightweight in-memory sliding-window or IP check helper directly inside `backend/routers/vin.py` or `backend/core/limiter.py` to prevent rapid automated loops against `api.nhtsa.gov`:
   ```python
   import time
   from collections import defaultdict
   from fastapi import APIRouter, Depends, HTTPException, Request, status

   _IP_REQUEST_HISTORY: dict[str, list[float]] = defaultdict(list)
   _MAX_VIN_REQUESTS_PER_MIN = 25

   def _check_vin_rate_limit(request: Request) -> None:
       client_ip = request.client.host if request.client else "unknown"
       now = time.time()
       history = _IP_REQUEST_HISTORY[client_ip]
       # Prune timestamps older than 60 seconds
       _IP_REQUEST_HISTORY[client_ip] = [t for t in history if now - t < 60.0]
       if len(_IP_REQUEST_HISTORY[client_ip]) >= _MAX_VIN_REQUESTS_PER_MIN:
           raise HTTPException(
               status_code=status.HTTP_429_TOO_MANY_REQUESTS,
               detail="Too many VIN lookup requests. Please try again in a minute.",
           )
       _IP_REQUEST_HISTORY[client_ip].append(now)
   ```
   Then call `_check_vin_rate_limit(request)` at the top of `decode_vin`:
   ```python
   @router.get("/api/vin/{vin}", response_model=VinData)
   async def decode_vin(vin: str, request: Request, db: Session = Depends(get_db)):
       _check_vin_rate_limit(request)
       # ... rest of function unchanged
   ```

---

## 3. Verification

Run the exact checks below from repository root before committing:

```bash
uv run ruff check backend/ && uv run black --check backend/ && uv run mypy backend/
uv run pytest tests/unit/ -v
```

**Expected output**:
- All linters pass with zero warnings (`All checks passed!`).
- All 196+ unit tests (`tests/unit/`) pass cleanly.

To verify boundary rejection via `pytest` or Python one-liner:
```bash
uv run python -c 'from backend.schemas import CheckoutRequest; CheckoutRequest(vin="1HGCR2F8XHA000000", price_type="invalid")'
# Raises pydantic.ValidationError: Input should be 'single' or 'annual'
```
