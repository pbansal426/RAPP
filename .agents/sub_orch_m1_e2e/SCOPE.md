# Scope: Milestone 1 - E2E Testing Track

## Objective
Establish a comprehensive, requirement-driven, opaque-box E2E test suite. Design test cases spanning Tiers 1-4. The test suite must run against the application and verify correctness. Publish `TEST_READY.md` and `TEST_INFRA.md` upon completion.

## Feature Inventory to Cover
1. **Frictionless VIN Ingestion & Decoding**: Input VIN, fetch decoded vehicle info from FastAPI backend (via NHTSA public API).
2. **Diagnostic Input & Tool Constraints**: Input symptoms/OBD codes, specify tool profile, and get structured free diagnosis response.
3. **Safety & Escalation Protocol**: Highlight high-risk systems (Airbags, EV Batteries, Fuel Lines) and render non-dismissible warning banners.
4. **Stripe Paywall & Unlock**: Verify free diagnosis is visible, paywall CTA gates repair steps, mock checkout session success updates `localStorage`, and `/api/repair` unlocks detailed steps.

## Expected Deliverables
- `/Users/prathambansal/Dev/RAPP/tests/` directory containing E2E test cases.
- A test runner command configured and documented.
- `TEST_INFRA.md` detailing features, scenarios, and coverage metrics.
- `TEST_READY.md` signaling completion.

## Code Constraints
- Opaque-box testing only. Do not depend on implementation internal modules.
- No `auth.py`, login route, or `/login` page may exist or be tested.
- Verify touch targets are visually/functionally oversized (>=48px height) where possible, and check for high-contrast dark mode styling.
