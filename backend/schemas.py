"""Public API request/response Pydantic schemas, shared across routers.

Kept in one module so the shapes documented in CLAUDE.md's pinned
Claude/Gemini contract have a single, easy-to-audit source of truth.
"""

from typing import Any

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


class CheckoutRequest(BaseModel):
    vin: str
    price_type: str = "single"


class CheckoutResponse(BaseModel):
    checkout_url: str


class VinOcrResponse(BaseModel):
    vin: str
    confidence: float
    decoded_vehicle: dict[str, Any] | None = None


# --- Auth / user accounts ---


class SignupRequest(BaseModel):
    email: str
    password: str
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    email_verified: bool = False


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class UpdateAccountRequest(BaseModel):
    display_name: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: str


class ForgotPasswordResponse(BaseModel):
    message: str
    # Dev-mode only: no email provider is configured, so the reset link is
    # returned directly instead of emailed. Drop this field once a real
    # email provider (Resend/Postmark/SendGrid/...) is wired up.
    reset_link: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class SendVerificationResponse(BaseModel):
    message: str
    # Dev-mode only: see ForgotPasswordResponse.reset_link.
    verify_link: str


class VerifyEmailRequest(BaseModel):
    token: str


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
    saved_at: str | None = None
