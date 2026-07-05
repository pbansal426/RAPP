"""Backward-compatible entry point.

``backend/main.py`` used to be the entire application (per the original
"all routes flat in a single main.py" spec). It has since been split into
backend/core, backend/services, and backend/routers, with backend/app.py as
the real FastAPI bootstrap -- see CLAUDE.md's Architecture section.

This module now only re-exports ``app``/``settings`` (and a handful of
internals a few tests/scripts still reach for directly) so that existing
entry points -- ``uvicorn backend.main:app``, the Dockerfile's gunicorn CMD,
docker-compose.dev.yml -- keep working without modification.
"""

from backend.app import app
from backend.core.config import Settings, settings
from backend.routers.diagnose import check_high_risk
from backend.routers.vin import (
    _sanitize_vin_candidate,
    _vin_check_digit_valid,
    decode_vin_internal,
)
from backend.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    CostBreakdown,
    DiagnoseRequest,
    DiagnoseResponse,
    PartOption,
    RecommendedPart,
    RepairRequest,
    RepairResponse,
    VehicleInfo,
    VinOcrResponse,
)
from backend.services.gemini import (
    GEMINI_MODEL,
    RepairStep,
    RepairStepsSchema,
    call_gemini_repair_steps,
    call_gemini_text,
    get_genai_client,
)

__all__ = [
    "app",
    "Settings",
    "settings",
    "check_high_risk",
    "_sanitize_vin_candidate",
    "_vin_check_digit_valid",
    "decode_vin_internal",
    "CheckoutRequest",
    "CheckoutResponse",
    "CostBreakdown",
    "DiagnoseRequest",
    "DiagnoseResponse",
    "PartOption",
    "RecommendedPart",
    "RepairRequest",
    "RepairResponse",
    "VehicleInfo",
    "VinOcrResponse",
    "GEMINI_MODEL",
    "RepairStep",
    "RepairStepsSchema",
    "call_gemini_repair_steps",
    "call_gemini_text",
    "get_genai_client",
]
