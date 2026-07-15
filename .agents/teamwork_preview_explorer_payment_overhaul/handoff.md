# Handoff Report: RAPP Payment Overhaul & Polar MoR Exploration

## 1. Observation
I have inspected the following key files in the repository:
1. **Stripe Integration & Routing**:
   * `backend/services/stripe.py` defines the checkout creation and webhook verification. Lines 38-60:
     ```python
     session = await stripe.checkout.Session.create_async(
         mode="payment",
         line_items=[
             {
                 "price_data": {
                     "currency": "usd",
                     "product_data": {
                         "name": "RAPP Repair Guide",
                         "description": f"Step-by-step repair guide for VIN {vin}",
                     },
                     "unit_amount": _GUIDE_PRICE_USD_CENTS,
                 },
                 "quantity": 1,
             }
         ],
         ...
         metadata={"vin": vin, "symptoms": symptoms[:450], "user_id": user_id or ""},
     )
     ```
   * `backend/routers/payments.py` implements `/api/payments/create-checkout`, `/api/payments/success-stub`, and `/api/webhooks/stripe`. Lines 93-110 handle `checkout.session.completed` by logging rather than writing to database:
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
2. **Pricing & Cost Breakdown**:
   * `backend/pricing.py` calculates DIY guide totals using hardcoded `_RAPP_GUIDE_FEE = 4.00`. Line 164:
     ```python
     diy_total = round(_RAPP_GUIDE_FEE + parts_total, 2)
     ```
3. **Database Models**:
   * `backend/core/models.py` defines `DbUser`, which contains `saved_payment_method` and `last_payment_session_id`. `DbChatUsage` tracks rate limits via primary key `stripe_session_id`.
4. **Repair Router Endpoint Gating**:
   * `backend/routers/repair.py` checks for the presence of `stripe_session_id` to generate the repair steps. Line 25-29:
     ```python
     if not request.stripe_session_id or not request.stripe_session_id.strip():
         raise HTTPException(
             status_code=status.HTTP_402_PAYMENT_REQUIRED,
             detail="Payment Required: stripe_session_id is required.",
         )
     ```
5. **Frontend Results Page & Payment Integration**:
   * `frontend/src/app/results/page.tsx` triggers payments in `handlePay` and contains hardcoded references to the `$4.00` guide fee:
     ```typescript
     // Line 639
     Unlock Complete Guide — $4.00
     // Line 493
     {diagnosis?.cost_breakdown
       ? `$${(diagnosis.cost_breakdown.parts_total + 4.00).toFixed(2)}`
       : '$39.00'}
     ```
   * Upon successful checkout, `frontend/src/app/repair/success/page.tsx` stores `rapp_unlocked_${vin} = session_id` in `localStorage`, and `frontend/src/app/repair/page.tsx` verifies it locally.
6. **Tests**:
   * `tests/unit/test_stripe_payments.py` mocks Stripe checkout creation and tests HMAC webhooks.
   * `tests/unit/test_pricing.py` verifies cost calculations.
   * `tests/verify_tests.sh` runs Playwright integration scenarios.

---

## 2. Logic Chain
1. **Dynamic Tiered Pricing**: The RAPP Guide fee is currently hardcoded as a flat `$4.00` fee in `backend/pricing.py` and the frontend page. To implement tiered pricing ($4.99/$9.99/$14.99), `backend/pricing.py` must compute estimated dealership costs and map them to these thresholds, passing this dynamic `guide_fee` through the JSON response.
2. **Polar MoR Transition**: Polar checkout creation can replace Stripe checkout sessions in a new `backend/services/polar.py` service. It must accept the dynamic `guide_fee`, select the appropriate Polar Product ID, and attach vehicle/user metadata.
3. **Frontend Dynamic Adaptation**: The Next.js results page must be modified to read `guide_fee` from the `/api/diagnose` response and dynamically render it on the paywall CTA button and the cost comparison table.
4. **Database & API Generalization**: Since `stripe_session_id` is passed as a string validation key, we can rename the schema variables to a generic `payment_session_id` or `checkout_id` while updating `DbUser` to store `polar_customer_id` and adjusting `DbChatUsage` query parameters.

---

## 3. Caveats
* **Webhooks & DB Verification**: In the current MVP architecture, the webhook does not persist unlocked states in the database; instead, the success redirect populates `localStorage`. The proposed migration does not require adding a new database unlock verification step unless the product spec mandates moving away from the `localStorage` MVP flag.
* **External Sandbox IDs**: Product ID values for Polar are placeholders (`prod_tier1_xxx`) and must be configured in the Polar dashboard.
* **E2E Playwright Tests**: E2E tests (`make test-verify` / Playwright) require browser executable binaries to be installed locally (`npx playwright install`), which requires internet access. In this CODE_ONLY sandbox mode, the E2E verification test fails due to missing Playwright browser binaries. However, unit tests (`make test-unit`) run locally and pass successfully.

---

## 4. Conclusion
Transitioning to Polar MoR and tiered pricing ($4.99/$9.99/$14.99) is highly feasible. It requires:
1. Enhancing `backend/pricing.py` to calculate guide fee tiers dynamically from dealership cost estimates.
2. Adding a `polar.py` service to construct Polar checkout urls matching the correct tier.
3. Updating frontend results page components to dynamically display the dynamic guide fee rather than hardcoded `$4.00` values.
4. Migrating API schemas and unit tests to generic payment/checkout terminology.

---

## 5. Verification Method
1. **Backend Tests**: Run `pytest tests/unit/test_pricing.py` and `pytest tests/unit/test_polar_payments.py` (after renaming).
2. **E2E verification**: When online, run `npx playwright install` and then `make test-verify` to ensure Playwright scenarios continue to pass without failure.
