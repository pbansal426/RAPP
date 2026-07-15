# PROJECT: Payment & Monetization Overhaul

## Architecture
- **Backend API**: FastAPI server exposing endpoints for VIN decoding, diagnosis, repair procedures, and payments.
- **Frontend App**: Next.js 14 TypeScript client with page routing.
- **Database**: SQLAlchemy with SQLite database (`data/rapp.db`).
- **Payment Processor**: Polar MoR (Merchant of Record) with HMAC signed webhooks.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | DB & Pricing | Update DbUser model with subscription fields; Implement estimate_pricing tiers in backend/pricing.py; Update schemas | None | DONE |
| 2 | Polar Service & Webhooks | Create backend/services/payments_mor.py; Re-wire backend/routers/payments.py & repair.py | M1 | DONE |
| 3 | Frontend Overhaul | Implement Dual-Card UI & dynamic price lock in results page; update repair logic to check subscriptionStatus | M2 | DONE |
| 4 | Verification & Tests | Update unit tests, mock_app.py, verify E2E suite via verify_tests.sh | M3 | DONE |

## Interface Contracts
### payments_mor ↔ routers/payments.py
- `create_polar_checkout_session(vin: str, price_type: str, symptoms: str, user_id: str | None) -> str`
- `verify_webhook_signature(payload: bytes, signature: str) -> bool`

### backend/pricing.py
- `estimate_pricing(category: str | None, dealership_cost: float) -> float`
- `build_cost_breakdown(template: RepairTemplate | None) -> dict` (now includes `"guide_fee"`)

### schemas.py (CheckoutRequest & CheckoutResponse)
- `CheckoutRequest(vin: str, price_type: str = "single", symptoms: str = "")`
- `CheckoutResponse(checkout_url: str, mode: Literal["mock", "live"] = "mock")`
