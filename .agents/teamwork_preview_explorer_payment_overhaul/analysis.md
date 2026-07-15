# RAPP Payment Overhaul Analysis & Polar MoR Migration Plan

## Executive Summary
This report analyzes RAPP's existing Stripe payment integration, pricing logic, database models, repair API, and frontend checkout flows. It outlines a proposed architecture for transitioning payment processing to **Polar MoR** (Merchant of Record) and implementing a value-based **tiered pricing structure** ($4.99 / $9.99 / $14.99) based on estimated dealership repair costs.

---

## 1. Analysis of Existing Payment & Pricing Components

### 1.1 Stripe Integration
* **File Locations**:
  * `backend/services/stripe.py`
  * `backend/routers/payments.py`
* **Mechanisms**:
  * **Configuration Check**: `stripe_is_configured()` checks for `settings.stripe_secret_key`.
  * **Mock Mode Fallback**: If Stripe is not configured, checkout requests degrade to a mock flow where `create_checkout` returns a backend URL stub: `{backend_url}/api/payments/success-stub?session_id=cs_test_123&vin={vin}`.
  * **Real Checkout Session Creation**: Created on `checkout.stripe.com` with a hardcoded product fee:
    ```python
    _GUIDE_PRICE_USD_CENTS = 399  # $3.99 flat price
    ```
    Session payload attaches metadata:
    ```python
    metadata={"vin": vin, "symptoms": symptoms[:450], "user_id": user_id or ""}
    ```
  * **Stripe Webhook Handler**:
    Listens for `checkout.session.completed`. Verification uses a strict HMAC signature check via `verify_webhook_signature`. 
    **Important Finding**: The webhook currently does *not* write to the database to persist unlocked status. Unlocking is handled client-side by storing a key in `localStorage`. The webhook exists solely as an audit log trail.
    ```python
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata") or {}
        logger.info(
            "stripe_checkout_completed",
            session_id=session.get("id"),
            vin=metadata.get("vin"),
            user_id=metadata.get("user_id") or None,
        )
    ```

### 1.2 Pricing & Dealership Estimation Logic
* **File Location**: `backend/pricing.py`
* **Mechanisms**:
  * Parts cost ranges are parsed from templates (e.g., `"$45-$90"`).
  * Dealership and independent shop labor rates, markups, and hours are defined as constants:
    ```python
    _DEALERSHIP_LABOR_RATE = (180.0, 220.0)
    _DEALERSHIP_PARTS_MARKUP = (1.3, 1.5)
    _RAPP_GUIDE_FEE = 4.00
    ```
  * Estimations are calculated dynamically based on labor hours and parsed parts costs:
    ```python
    dealership_low = round(parts_total * dealer_markup_low + labor_hours * dealer_rate_low, 2)
    dealership_high = round(parts_total * dealer_markup_high + labor_hours * dealer_rate_high, 2)
    ```
  * Currently, the DIY total assumes a flat guide fee:
    ```python
    diy_total = round(_RAPP_GUIDE_FEE + parts_total, 2)
    ```

### 1.3 Database Models
* **File Location**: `backend/core/models.py`
* **DbUser Model**:
  ```python
  class DbUser(Base):
      __tablename__ = "users"

      id: Mapped[str] = mapped_column(primary_key=True, index=True)  # UUID string
      email: Mapped[str] = mapped_column(unique=True, index=True)
      display_name: Mapped[str | None] = mapped_column(default=None)
      saved_payment_method: Mapped[bool] = mapped_column(default=False)
      last_payment_session_id: Mapped[str | None] = mapped_column(default=None)
      created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

      repairs: Mapped[list["DbSavedRepair"]] = relationship(
          back_populates="user", cascade="all, delete-orphan"
      )
  ```
* **Saved Repair & Chat Usage Models**:
  * `DbSavedRepair` stores individual repair instances using `payment_session_id`.
  * `DbChatUsage` enforces the 5-message rate limit per session under primary key `stripe_session_id`.

### 1.4 Repair API Endpoint
* **File Location**: `backend/routers/repair.py`
* **Mechanisms**:
  * The `POST /api/repair` endpoint gates guide generation by asserting that a non-empty `stripe_session_id` is supplied:
    ```python
    if not request.stripe_session_id or not request.stripe_session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment Required: stripe_session_id is required.",
        )
    ```
  * For chat (`POST /api/repair/chat`), the endpoint uses the `stripe_session_id` to query and increment `DbChatUsage.message_count` up to a maximum of 5 replies.

### 1.5 Next.js Frontend Flow
* **File Location**: `frontend/src/app/results/page.tsx`
* **Mechanisms**:
  * **Free Diagnosis**: Fetched via `/api/diagnose`.
  * **Price Comparison**: Renders the Dealership, Independent, and DIY routes. The DIY cost is calculated using a hardcoded `$4.00` fee:
    ```typescript
    {diagnosis?.cost_breakdown
      ? `$${(diagnosis.cost_breakdown.parts_total + 4.00).toFixed(2)}`
      : '$39.00'}
    ```
  * **Initiating Payment**: The checkout button calls `handlePay()`, sending a POST to `/api/payments/create-checkout`.
  * **Success Handler**:
    Redirects to `/repair/success?session_id=...&vin=...`.
    Saves `rapp_unlocked_${vin} = session_id` to `localStorage`.
    `/repair/page.tsx` verifies this key locally before loading the steps or calling `POST /api/repair`.

---

## 2. Proposed Migration to Polar MoR & Tiered Pricing

### 2.1 Polar MoR Setup
Polar serves as the Merchant of Record. We will configure 3 Products in Polar corresponding to our pricing tiers:
1. **Tier 1 (Low Cost)**: $4.99
2. **Tier 2 (Medium Cost)**: $9.99
3. **Tier 3 (High Cost)**: $14.99

We will update environment variables in `.env` and `Settings` (`backend/core/config.py`):
```python
polar_api_key: str | None = None
polar_webhook_secret: str | None = None
polar_product_id_tier_1: str = "prod_tier1_xxx"
polar_product_id_tier_2: str = "prod_tier2_xxx"
polar_product_id_tier_3: str = "prod_tier3_xxx"
```

### 2.2 Tiered Pricing Logic
We will map estimated dealership repair costs dynamically to determine the dynamic guide fee in `backend/pricing.py`:
```python
def determine_guide_fee(dealership_cost_high: float) -> float:
    """Determine dynamic guide fee tier based on high-end dealership cost."""
    if dealership_cost_high < 250.0:
        return 4.99
    elif dealership_cost_high < 750.0:
        return 9.99
    else:
        return 14.99
```
* **DIY Cost Update**: Modify `build_cost_breakdown` to call `determine_guide_fee(dealership_high)` and set:
  ```python
  guide_fee = determine_guide_fee(dealership_high)
  diy_total = round(guide_fee + parts_total, 2)
  ```
  We will expose `guide_fee` inside the dynamic `CostBreakdown` response schema.

### 2.3 DbUser & Database Schema Updates
To support Polar customer tracking and clean up Stripe naming conventions:
1. **User Table**:
   * Add `polar_customer_id: Mapped[str | None] = mapped_column(default=None)`
   * Optionally migrate `last_payment_session_id` to `last_payment_checkout_id` (or keep as a generic name).
2. **Saved Repair Table**:
   * Ensure `payment_session_id` persists Polar checkout/order IDs.
3. **Chat Usage Table**:
   * To prevent breaking changes, we can keep `stripe_session_id` as the primary key name in the database model `DbChatUsage` but treat it as a generic `payment_session_id` in logic, or run a database migration to rename the column to `payment_session_id`.

### 2.4 Polar Checkout & Webhook Endpoints
Create a new service module `backend/services/polar.py` (which replaces `backend/services/stripe.py`):
```python
import httpx
from backend.core.config import settings

def polar_is_configured() -> bool:
    return bool(settings.polar_api_key)

async def create_polar_checkout_session(
    vin: str, symptoms: str, user_id: str | None, guide_fee: float
) -> str:
    if not polar_is_configured():
        return f"{settings.backend_url}/api/payments/success-stub?session_id=pol_test_123&vin={vin}"

    # Map guide fee to the correct product ID
    if guide_fee == 4.99:
        product_id = settings.polar_product_id_tier_1
    elif guide_fee == 9.99:
        product_id = settings.polar_product_id_tier_2
    else:
        product_id = settings.polar_product_id_tier_3

    async with httpx.AsyncClient() as client:
        # Polar Custom Checkout API endpoint
        response = await client.post(
            "https://api.polar.sh/v1/checkouts/custom",
            headers={"Authorization": f"Bearer {settings.polar_api_key}"},
            json={
                "product_id": product_id,
                "success_url": f"{settings.frontend_url}/repair/success?session_id={{checkout_id}}&vin={vin}",
                "metadata": {
                    "vin": vin,
                    "symptoms": symptoms[:450],
                    "user_id": user_id or ""
                }
            }
        )
        response.raise_for_status()
        return response.json()["url"]
```
* **Webhook Endpoint** (`/api/webhooks/polar`):
  Verify signatures from Polar (which use a standard SHA256 HMAC of the payload) and handle `order.created` events:
  ```python
  import hmac
  import hashlib

  def verify_polar_signature(payload: bytes, signature: str, secret: str) -> bool:
      expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
      return hmac.compare_digest(expected, signature)
  ```

### 2.5 Next.js Frontend Updates
1. **Dynamic Price Display**:
   Update `results/page.tsx` to read the dynamic `guide_fee` from the API response instead of hardcoding `4.00`:
   ```typescript
   const guideFee = diagnosis?.cost_breakdown?.guide_fee || 4.99;
   const diyTotal = diagnosis?.cost_breakdown?.diy_total || (partsTotal + guideFee);
   ```
2. **Unlock CTA & Description**:
   Replace the hardcoded button text:
   ```typescript
   {payLoading
     ? 'Securing Access…'
     : `Unlock Complete Guide — $${guideFee.toFixed(2)}`}
   ```
   Update the table savings details description to dynamically interpolate `guideFee`.
3. **Session Parameter Updates**:
   Ensure `handlePay` passes any necessary price context or uses the dynamically computed price tier when hitting `/api/payments/create-checkout`.

---

## 3. Test Suite Integration Plan

### 3.1 Unit Tests (`tests/unit/test_polar_payments.py`)
1. Rename `test_stripe_payments.py` to `test_polar_payments.py`.
2. Mock `backend.services.polar.create_polar_checkout_session` and verify that the correct Polar Product ID is selected based on the estimated dealership pricing tier.
3. Test Polar webhook validation using simulated HMAC payloads matching Polar's event structure (`order.created`).

### 3.2 Pricing Unit Tests (`tests/unit/test_pricing.py`)
1. Add tests checking that `determine_guide_fee` outputs the correct price for different dealership ranges:
   * Dealership cost < $250 -> $4.99
   * Dealership cost between $250 and $750 -> $9.99
   * Dealership cost >= $750 -> $14.99
2. Assert that `build_cost_breakdown` incorporates the correct tiered `guide_fee` into the `diy_total`.

### 3.3 E2E & Mock App Updates
1. Update `tests/mock_app.py` to support dynamic guide fee rendering and dynamic calculations.
2. Update references to `stripe_session_id` in Playwright E2E files to `polar_checkout_id` (or the generalized parameter name).
