"""Public API request/response Pydantic schemas, shared across routers.

Kept in one module so the shapes documented in CLAUDE.md's pinned
Claude/Gemini contract have a single, easy-to-audit source of truth.
"""

from typing import Any, Literal

from pydantic import BaseModel, field_validator


class VehicleInfo(BaseModel):
    """Client-provided vehicle identity for flows without a decodable VIN
    (e.g. the Year/Make/Model selector, which covers every NHTSA make).
    Also doubles as the shape of ``rapp_vin_data``, so it carries the
    richer fields (trim, body_class, vehicle_type, fuel_type) that
    /api/vin/{vin} now returns even though the repair/diagnose endpoints
    only read year/make/model/engine/drive_type/powertrain today."""

    year: str | int | None = None
    make: str | None = None
    model: str | None = None
    trim: str | None = None
    engine: str | None = None
    drive_type: str | None = None
    body_class: str | None = None
    vehicle_type: str | None = None
    fuel_type: str | None = None
    powertrain: str | None = None


class DiagnoseRequest(BaseModel):
    vin: str
    symptoms: str
    obd_codes: list[str] | str | None = None
    tools: list[str] | str | None = None
    vehicle: VehicleInfo | None = None

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


class PartOption(BaseModel):
    """One purchasable option for a recommended part, at a specific tier."""

    tier: str  # "OEM" | "Aftermarket / Budget" | "Upgrade"
    brand: str
    part_number: str | None = None
    title: str
    estimated_price: float
    purchase_url: str
    rationale: str


class RecommendedPart(BaseModel):
    part_name: str
    options: list[PartOption]


class CostBreakdown(BaseModel):
    dealership_cost_range: list[float]
    independent_shop_range: list[float]
    parts_total: float
    guide_fee: float
    diy_total: float
    estimated_labor_hours: float


class DiagnoseResponse(BaseModel):
    summary: str
    is_high_risk: bool
    high_risk_system: str | None = None
    warning_message: str | None = None
    recommended_parts: list[RecommendedPart] = []
    cost_breakdown: CostBreakdown | None = None


class RepairRequest(BaseModel):
    vin: str
    symptoms: str
    obd_codes: list[str] | str | None = None
    tools: list[str] | str | None = None
    stripe_session_id: str
    vehicle: VehicleInfo | None = None
    skill_level: str | None = None

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
    is_blocked_safety: bool = False
    warning_message: str | None = None


class RepairChatRequest(BaseModel):
    """Context for one chat turn in the repair-guide side panel. The client
    sends the exact repair_steps already shown (not just vin/symptoms) so the
    reply is grounded in the same procedure the user is looking at, rather
    than a fresh, possibly-different RAG query."""

    vin: str
    vehicle: VehicleInfo | None = None
    symptoms: str
    repair_steps: list[str]
    message: str
    stripe_session_id: str


class RepairChatResponse(BaseModel):
    # None means Gemini is unavailable/failed/quota-exhausted -- the client
    # falls back to its own local canned response rather than erroring.
    reply: str | None


class CheckoutRequest(BaseModel):
    vin: str
    price_type: str = "single"
    symptoms: str = ""


class CheckoutResponse(BaseModel):
    checkout_url: str
    # "live" means checkout_url is a real checkout.stripe.com page -- the
    # frontend must do a genuine full-page redirect, not the SPA shortcut
    # used for "mock" (our own success-stub, which just 303s straight back).
    mode: Literal["mock", "live"] = "mock"


class VinOcrResponse(BaseModel):
    vin: str
    confidence: float
    decoded_vehicle: dict[str, Any] | None = None


# --- Auth / user accounts ---


class RequestLinkRequest(BaseModel):
    email: str
    # Only used the first time this email signs in (creates the account);
    # ignored on subsequent requests for an existing account.
    display_name: str | None = None


class RequestLinkResponse(BaseModel):
    message: str
    # Dev-mode only: populated when no email provider (Resend) is
    # configured, so the link is returned directly instead of emailed. Drop
    # this field once RESEND_API_KEY is set in every environment that needs
    # real delivery -- see backend/services/email.py.
    magic_link: str | None = None


class VerifyLinkRequest(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    subscription_status: str = "free"
    skill_level: str = "Beginner"
    completed_jobs_count: int = 0
    skill_badges: list[str] = []


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class UpdateAccountRequest(BaseModel):
    display_name: str | None = None
    skill_level: str | None = None


# --- Saved repairs ---


class SavedRepairCreate(BaseModel):
    vin: str
    year: str | None = None
    make: str | None = None
    model: str | None = None
    engine: str | None = None
    powertrain: str | None = None
    symptoms: str
    payment_session_id: str | None = None
    citations: list[str] | None = None


class SavedRepairResponse(BaseModel):
    id: str
    vin: str
    year: str | None = None
    make: str | None = None
    model: str | None = None
    engine: str | None = None
    powertrain: str | None = None
    symptoms: str
    payment_session_id: str | None = None
    citations: list[str] | None = None
    saved_at: str | None = None


# --- Repair outcomes: post-job "what actually happened" capture, powering
# the social-proof stats badge on /results (imp.md Stage 2.1/2.2) ---


class OutcomeCreateRequest(BaseModel):
    vin: str
    make: str
    model: str
    year: str | None = None
    symptoms: str
    obd_codes: list[str] | str | None = None
    actual_cost_usd: float
    actual_duration_minutes: int
    saved_repair_id: str | None = None

    @field_validator("obd_codes")
    @classmethod
    def normalize_obd_codes(cls, v: list[str] | str | None) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


class OutcomeResponse(BaseModel):
    id: str
    make: str
    model: str
    year: str | None = None
    category: str
    actual_cost_usd: float
    actual_duration_minutes: int
    completed_at: str


class OutcomeStatsResponse(BaseModel):
    count: int
    avg_duration_minutes: float | None = None
    avg_cost_usd: float | None = None


# --- Vehicle safety: live NHTSA recalls/complaints lookups (never ingested
# into the RAG vector store -- see backend/services/nhtsa_safety.py) ---


class RecallInfo(BaseModel):
    campaign_number: str
    component: str
    summary: str
    consequence: str
    remedy: str
    report_received_date: str


class RecallsResponse(BaseModel):
    open_recalls: list[RecallInfo]
    count: int


class ComplaintComponentFrequency(BaseModel):
    component: str
    count: int


class ComplaintsSummaryResponse(BaseModel):
    total_complaints: int
    # Sorted by count descending, capped to a handful -- a full per-complaint
    # breakdown isn't useful in a summary card.
    top_components: list[ComplaintComponentFrequency]


# --- Stage 2.4: Mid-Repair Photo Checkpoint Pipeline ---
# Response shape for POST /api/repair/checkpoint/verify.
# is_milestone_met=True means Gemini vision confirmed the physical work
# matches the step description; confidence is 0.0–1.0; explanation gives the
# user a plain-English reason, e.g. "Belt routing aligns with all four pulleys."


class CheckpointVerifyResponse(BaseModel):
    is_milestone_met: bool
    confidence: float
    explanation: str


# --- Stage 2.6: "Check My ChatGPT Answer" Verification Funnel ---
# Schemas for POST /api/diagnose/verify-external.


class ExternalAiVerifyRequest(BaseModel):
    vin: str
    symptoms: str
    external_ai_text: str


class ExternalAiVerifyResponse(BaseModel):
    verified_claims: list[str]
    fitment_or_spec_errors: list[str]  # wrong torque specs, wrong part numbers, etc.
    missing_safety_warnings: list[str]  # e.g. missed SRS or fuel-line depressurisation
    accuracy_score: int  # 0–100
