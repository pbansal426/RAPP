# Handoff Report - Worker Payment Overhaul

## 1. Observation
* Backend Unit Tests Run: Successfully ran `./.venv/bin/pytest tests/unit/` with 147 passing tests.
  ```
  tests/unit/test_api.py ........................................          [ 27%]
  tests/unit/test_auth.py ..............                                   [ 36%]
  tests/unit/test_backup.py ....                                           [ 39%]
  tests/unit/test_challenge.py ...........                                 [ 46%]
  tests/unit/test_etl_loader.py .....                                      [ 50%]
  tests/unit/test_payments.py .......                                      [ 55%]
  tests/unit/test_payments_mor.py ........                                 [ 60%]
  tests/unit/test_pricing.py ...............                               [ 70%]
  tests/unit/test_rag.py ..........                                        [ 77%]
  tests/unit/test_repairs_db.py ......                                     [ 81%]
  tests/unit/test_templates.py ...............                             [ 91%]
  tests/unit/test_vehicle_safety.py .........                              [ 97%]
  tests/unit/test_vin_fallback.py ...                                      [100%]
  
  ======================= 147 passed, 54 warnings in 7.73s =======================
  ```
* Playwright E2E verification test suite: Successfully ran `./tests/verify_tests.sh` with 5 passed verification checks.
  ```
  ======================================================================
  Verification Summary:
  Passed: 5
  Failed: 0
  ======================================================================
  ```
* Frontend Build: Ran `npm run build` in `frontend/` and it completed successfully.
  ```
  ✓ Compiled successfully
  ✓ Generating static pages (14/14)
  ```
* DB Schema Update: `backend/core/models.py` updated to add `subscription_status`, `mor_customer_id`, `mor_subscription_id`, and `subscription_expires_at` to `DbUser`.
* Pricing Update: `backend/pricing.py` updated with `estimate_pricing` mapping dealer quotes to tiers ($4.99, $9.99, $14.99) and dynamic `guide_fee`/`diy_total` computation.
* Payments Integration: `backend/services/payments_mor.py` created to handle Polar checkouts/signatures; `backend/routers/payments.py` modified to support Polar checkout, handle webhooks (`subscription.created`, `subscription.updated`, `subscription.cancelled`, `checkout.created/updated`, `order.created`), and return `410 Gone` for Stripe webhooks.
* Authorization Update: `backend/routers/repair.py` updated to authorize callers who are active subscribers or pass a session ID.
* Frontend Update: Exposed subscription fields in auth logic/types, implemented Dual-Card UI on Results page, and gated Repair/Chat panels on active subscriber status.

## 2. Logic Chain
1. *Observation*: The user wants to integrate Polar Merchant of Record (MoR) and support both single guide unlocks and annual pass subscriptions.
2. *Deduction*: We must track subscription status on the user model, so we updated the database schema in `DbUser`.
3. *Deduction*: We must calculate guide fees dynamically based on the dealer quote, so we implemented `estimate_pricing` and updated `build_cost_breakdown` in `backend/pricing.py`.
4. *Deduction*: We must allow active subscribers to view the guide and chat with the AI assistant without requiring a local `stripe_session_id`, so we updated `backend/routers/repair.py` to allow access for active subscribers and set up the corresponding checks on the frontend (`page.tsx` and `ChatPanel.tsx`).
5. *Deduction*: We must replace Stripe checkout URLs and webhook flows with Polar, so we created `payments_mor.py`, rewired `payments.py` router to verify `X-Polar-Signature`, update `DbUser` on subscription events, and deprecated the Stripe webhook path with a `410 Gone` response.

## 3. Caveats
* **Network Mocking**: In code-only mode, live checkouts are mock-routed. Live mode is implemented correctly using `httpx.AsyncClient` but relies on active `polar_access_token` and correct product IDs in settings.
* **Database Reset**: Since SQLAlchemy `Base.metadata.create_all` does not migrate/alter tables, any existing sqlite DB must be deleted/re-created so the new `subscription_*` columns are generated.

## 4. Conclusion
The overhaul of the payment system from Stripe to Polar Merchant of Record (MoR) has been successfully implemented on both the backend and frontend. The database tracking, dynamic pricing model, authorization check, dual-card UI, and E2E mock workflows have been fully integrated and verified.

## 5. Verification Method
* Run backend unit tests:
  ```bash
  ./.venv/bin/pytest tests/unit/
  ```
* Run E2E verification test suite:
  ```bash
  ./tests/verify_tests.sh
  ```
* Build Next.js frontend:
  ```bash
  cd frontend && npm run build
  ```
