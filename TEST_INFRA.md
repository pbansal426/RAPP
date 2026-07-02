# RAPP E2E Test Infrastructure & Strategy

This document details the E2E testing infrastructure, architecture, setup steps, and testing strategy for the **Automotive AI Repair Engine (RAPP) Phase 1 MVP**.

---

## 1. E2E Test Strategy Overview

The testing strategy is designed to validate the core value proposition of the Phase 1 MVP: converting high-friction, hours-long vehicle diagnostic research into actionable, tool-aware, and RAG-verified instructions in under 10 seconds. 

Since RAPP has a frictionless, zero-authentication, one-shot input sequence, our testing focuses heavily on the user flow, input accuracy, accessibility, tool adaptation, and safety protocol gating.

### Core Testing Pillars

1. **User Flow Continuity**: Verify the 4-step sequence flows smoothly without 404s, login pages, or session blockages:
   $$\text{VIN Input (Home)} \rightarrow \text{Symptom \& Tool Selection} \rightarrow \text{Free Diagnosis} \rightarrow \text{Unlocked Detailed Repair Procedure}$$
2. **Grease-Monkey Clean UI Compliance**:
   - Verify that **dark mode** is the default across all pages.
   - Assert that all interactive touch targets (buttons, links, checkboxes) have a minimum height of **48px** for easy usage with dirty/greasy hands in low light.
   - Assert high-contrast readability (using Tailwind slate-900, black, zinc-950, and neon contrast classes).
3. **Safety & Escalation Protocol**:
   - Input symptoms triggering high-risk categories (e.g., SRS/Airbags, high-voltage EV battery systems, pressurized fuel lines).
   - Assert that non-dismissible, prominent safety warning banners are displayed with neon orange/yellow highlight colors before any repair instructions.
4. **Stripe Checkout Paywall & Local Storage State**:
   - Assert that detailed repair steps are locked/hidden behind the Payment CTA button by default.
   - Verify the Stripe redirect success handler (which receives `session_id` and `vin` parameters) correctly writes the unlock credentials `{vin, stripeSessionId}` to `localStorage` and transitions the UI to reveal the detailed procedures with OEM manual citations.
5. **Backend API Integrations & Mocks**:
   - Test live/mocked calls to the NHTSA public API endpoint for VIN decoding (extracting Year, Make, Model, Engine, and Drive Type).
   - Ensure CORS headers allow frontend access.

---

## 2. Environment Setup & Prerequisites

The development and testing environment has been initialized with the necessary runtimes and packages.

### Node.js & Playwright Setup
- **Node.js**: `v22.15.0`
- **npm**: `10.9.2`
- **Playwright**: `@playwright/test` (v1.61.1)

To run the Playwright setup:
```bash
# Install node dependencies
npm install

# Install Playwright browsers and dependencies
npx playwright install --with-deps
```

### Python API Server Setup
The backend runs using FastAPI and Uvicorn. To prevent interference with the system's Homebrew installation and comply with PEP 668, a local virtual environment has been created.
- **Python**: `3.14.2`
- **FastAPI / Uvicorn**: Installed in `.venv`

To set up or reactivate the Python virtual environment:
```bash
# Create virtual environment (already created)
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install requirements
pip install fastapi uvicorn
```

---

## 3. Directory & File Structure

The project root `/Users/prathambansal/Dev/RAPP/` contains the following test infrastructure files:

```
/Users/prathambansal/Dev/RAPP/
├── package.json              # NPM package definition (Playwright, Typescript, Node types)
├── playwright.config.ts      # Main Playwright config (parallelization, viewports, engines)
├── tests/
│   └── e2e-mvp-flow.spec.ts  # End-to-end integration tests covering Phase 1 user flows
├── .venv/                    # Python virtual environment (FastAPI, Uvicorn)
└── TEST_INFRA.md             # This E2E test strategy and guidelines document
```

---

## 4. Test Configuration (`playwright.config.ts`)

The Playwright configuration is located in `playwright.config.ts`. It includes:
- **Port Isolation**: Configured to run against `http://localhost:3099` to prevent conflicts with the developer's Next.js dev server (which uses port 3000).
- **Parallel Execution**: Enabled (`fullyParallel: true`) for rapid test execution.
- **Browser Matrices**: Tests against Chromium, Firefox, WebKit, and mobile viewports (Mobile Chrome on Pixel 5, Mobile Safari on iPhone 12) to simulate mobile-first garage environments.
- **CI Tuning**: Retries and worker throttling configured for CI runs.
- **Tracing**: Configured to capture traces on first failure to aid debugging.

---

## 5. End-to-End Test Spec (`tests/e2e-mvp-flow.spec.ts`)

The E2E tests are implemented inside `tests/e2e-mvp-flow.spec.ts`. The test suite targets:
1. **VIN Ingestion**:
   - Asserts page load, dark mode CSS rules, and oversized input elements.
   - Robustly asserts touch target size of the scan barcode and submit buttons by verifying the bounding box is NOT null/undefined first, and then checking height is >= 48px.
   - Types a real VIN (`1HGBH41JXMN109186`), submits, and verifies redirection.
2. **Diagnostic & Tool selection**:
   - Pre-populates the required `rapp_vin` state in `localStorage` before navigating directly to `/diagnose` to maintain E2E test isolation and avoid hardcoded facade fallbacks in the mock server.
   - Asserts text area symptom input.
   - Exercises checkboxes for tool profile inventory.
   - Robustly validates that label click heights are >= 48px after asserting the bounding box is not null/undefined.
3. **Paywall & Stripe Integration**:
   - Pre-populates required state (`rapp_vin`, `rapp_symptoms`) in `localStorage` using `page.evaluate(...)` prior to navigating directly to `/results`.
   - Asserts that detailed steps are gated behind the paywall CTA by default.
   - Simulates the Stripe Checkout success redirect (`/repair/success?session_id=cs_test_123&vin=1HGBH41JXMN109186`).
   - Asserts that `{vin, stripeSessionId}` is recorded in `localStorage` under `rapp_unlocked_{vin}`.
   - Verifies the page displays the unlocked RAG procedures and manual citations.
4. **Safety Protocols**:
   - Pre-populates `rapp_vin` state.
   - Inputs "Airbag deployment" diagnostic symptoms.
   - Asserts that a prominent warning banner is rendered.
   - Verifies that the banner does not contain any dismiss/close button (using a broadened check searching for `button, [role="button"], .close-btn`).

---

## 6. Execution Commands

### Running the Mock API Server:
The mock API server is used to validate the E2E test suite sensitivity under healthy and faulty conditions. It binds to port **3099** to isolate test traffic.
```bash
# Start the Mock Backend (from active virtualenv)
source .venv/bin/activate
python3 tests/mock_app.py
```

### Running the Live API and Frontend Servers locally:
In separate terminal windows:
```bash
# Start the Backend (from active virtualenv)
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Start the Next.js Frontend
npm run dev -- --port 3000
```

### Executing E2E Tests:
Run these commands from the root directory:
```bash
# Run all tests in headless mode (against mock server on port 3099)
npx playwright test

# Run tests in a specific browser (e.g., chromium)
npx playwright test --project=chromium

# Run tests in UI Mode (interactive)
npx playwright test --ui

# Debug a specific test file
npx playwright test tests/e2e-mvp-flow.spec.ts --debug
```
