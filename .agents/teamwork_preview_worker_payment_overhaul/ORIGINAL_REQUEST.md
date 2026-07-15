## 2026-07-15T09:00:00Z
You are worker_payment_overhaul. Your working directory is /Users/prathambansal/Dev/RAPP/.agents/teamwork_preview_worker_payment_overhaul/.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your objective is to implement and verify the following Milestones:

Milestone 1: Database & Pricing Models Integration
1. Update backend/core/models.py:
   Add subscription tracking fields to DbUser:
   - subscription_status: Mapped[str] = mapped_column(default="free") # "free", "active", "cancelled", "expired"
   - mor_customer_id: Mapped[str | None] = mapped_column(default=None)
   - mor_subscription_id: Mapped[str | None] = mapped_column(default=None)
   - subscription_expires_at: Mapped[datetime | None] = mapped_column(default=None)
2. Update backend/pricing.py:
   Implement estimate_pricing(category: str | None, dealership_cost: float) -> float.
   - Tier 1 ($4.99): dealer quote < $150
   - Tier 2 ($9.99): dealer quote $150 - $600
   - Tier 3 ($14.99): dealer quote > $600
   Update build_cost_breakdown to resolve guide_fee using estimate_pricing and dealership_high as dealer quote. Update diy_total = round(guide_fee + parts_total, 2). Include guide_fee in the returned dict.
3. Update backend/schemas.py:
   - Add guide_fee: float to CostBreakdown model.
   - Update CheckoutRequest: accept price_type: str = "single" and symptoms: str = "".
   - Update UserResponse: add subscription_status: str = "free".
   - Update backend/routers/auth.py to serialize subscription_status in UserResponse.

Milestone 2: Polar MoR Integration & Webhooks
1. Create backend/services/payments_mor.py (replacing backend/services/stripe.py):
   - Implement polar_is_configured() checking Settings.polar_access_token.
   - Implement build_mock_checkout_url(vin: str, price_type: str) -> str.
   - Implement build_success_redirect_url(session_id: str, vin: str, extra: dict) -> str.
   - Implement create_polar_checkout_session(vin: str, price_type: str, symptoms: str, user_id: str | None) -> str. Map price_type ("tier_1", "tier_2", "tier_3", "annual") to product IDs configured in settings.
   - Implement verify_webhook_signature(payload: bytes, signature: str) -> bool: Verifies HMAC signature with settings.polar_webhook_secret.
2. Update backend/core/config.py and .env.example:
   - Add Settings fields: polar_access_token (str | None), polar_webhook_secret (str | None), polar_product_id_tier_1 (str), polar_product_id_tier_2 (str), polar_product_id_tier_3 (str), polar_product_id_annual (str).
3. Re-wire backend/routers/payments.py:
   - Make create_checkout use create_polar_checkout_session and support mock/live mode and price_type.
   - Add POST /api/webhooks/payments endpoint. Verify X-Polar-Signature header. Handle "subscription.created", "subscription.updated", "subscription.cancelled" to update DbUser fields, and checkout/order completions.
   - Handle POST /api/webhooks/stripe: Return HTTP 410 Gone with deprecation message.
4. Update backend/routers/repair.py:
   - Update POST /api/repair and /api/repair/chat to authorize if either user has subscription_status == "active" or a non-empty session_id is supplied.

Milestone 3: Next.js Frontend Overhaul
1. Update frontend/src/lib/types.ts & auth.ts:
   - Expose subscriptionStatus in AuthUser and subscription_status in UserResponse.
2. Update frontend/src/app/results/page.tsx:
   - Fetch dynamic guide_fee and diy_total from backend.
   - Render Dual-Card Checkout UI:
     - ⭐ Annual Pass ($19.99/yr) [RECOMMENDED]
     - Single Job Unlock (price locked to $4.99 / $9.99 / $14.99)
   - Update handlePay(priceType: 'single' | 'annual') to pass price_type to backend.
3. Update frontend/src/app/repair/page.tsx:
   - Grant access if authUser.subscriptionStatus === 'active' or rapp_unlocked_{vin} is present.
   - Pass Bearer token in Authorization header for API calls.

Milestone 4: Verification
1. Rename tests/unit/test_stripe_payments.py to tests/unit/test_payments.py and update it for Polar webhooks/checkout.
2. Create tests/unit/test_payments_mor.py testing polar session creation, pricing intervals, and webhook signatures.
3. Update tests/mock_app.py to support the dual-card UI, dynamic pricing, and the new frontend flow.
4. Verify builds: 'npm run build' (or npx next build) in frontend/ and make sure 'tests/verify_tests.sh' and 'pytest tests/unit/' pass successfully.

Write a handoff report at `/Users/prathambansal/Dev/RAPP/.agents/teamwork_preview_worker_payment_overhaul/handoff.md` once complete and send a message.
