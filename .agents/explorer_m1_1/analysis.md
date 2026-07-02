# E2E Test Strategy & Framework Analysis

## Executive Summary
This document provides a comprehensive environment scan, evaluates E2E testing framework candidates, proposes an opaque-box directory structure and execution plan, outlines a detailed test case plan across Tiers 1-4, and details a dual-purpose mock application mechanism to verify the test suite before the main codebase is implemented. 

---

## 1. Environment Scan
A system scan of `/Users/prathambansal/Dev/RAPP` was conducted on June 30, 2026. The results are as follows:

*   **Operating System**: macOS
*   **Python Runtime**: `3.14.2` (located at `/opt/homebrew/bin/python3`)
*   **Node.js Runtime**: `v22.15.0` (located at `/Users/prathambansal/.nvm/versions/node/v22.15.0/bin/node`)
*   **npm Package Manager**: `10.9.2` (located at `/Users/prathambansal/.nvm/versions/node/v22.15.0/bin/npm`)
*   **Yarn Package Manager**: `1.22.22` (located at `/opt/homebrew/bin/yarn`)
*   **pip Package Manager**: `25.3` (installed modules: `ndiff`, `pip`, `wheel`)
*   **Missing/Not Found Tools**: `poetry`, `pnpm`, `uv`
*   **Global npm Packages**: `@ionic/cli@7.2.1`, `cordova-res@0.15.4`, `corepack@0.32.0`, `native-run@2.0.1`
*   **Repository State**: Uninitialized workspace containing only `.agents/`, `ORIGINAL_REQUEST.md`, and `PHASE_1_SPEC.md` (no source code or commits yet).

---

## 2. Test Framework Investigation & Recommendation

### Comparison of Candidates for E2E Testing

| Metric / Feature | Option A: Node.js Playwright (`@playwright/test`) | Option B: Python Playwright (`pytest-playwright`) | Option C: Cypress | Option D: Selenium |
| :--- | :--- | :--- | :--- | :--- |
| **Language** | TypeScript / JavaScript | Python | JavaScript / TypeScript | Python / JS / Java etc. |
| **Test Runner** | Native Playwright Runner | `pytest` | Native Cypress Runner | External (e.g. `pytest`, `mocha`) |
| **Execution Speed** | Extremely Fast (native browser contexts) | Fast | Moderate (runs inside browser) | Slow (WebDriver overhead) |
| **Network Mocking** | Native `page.route()` (excellent) | Native `page.route` (good) | Good `cy.intercept` | Hard, requires proxies |
| **UI Mode & Reporting**| Industry-leading HTML Report, Trace Viewer, UI Mode | Good CLI and trace viewer (HTML report via pytest plugins) | Great UI runner (local-only, harder in CI) | Basic |
| **Next.js Integration**| Standard recommendation | Moderate | Standard recommendation | Low |
| **Setup Overhead** | Very Low | Low | Moderate | High (driver management) |

### Core Recommendation: Node.js Playwright (`@playwright/test` with TypeScript)
We recommend **Node.js Playwright** for the E2E testing track. 

**Strategic Rationale**:
1.  **Frontend Tech Alignment**: Next.js 14 is a Node/TypeScript-based framework. Storing E2E tests in the same language environment allows frontend engineers to contribute easily and leverage shared IDE settings, formatting (Prettier/ESLint), and path mapping.
2.  **State-of-the-Art Developer Experience**: The official Node.js Playwright runner provides `playwright test --ui` (interactive test debugging), native visual trace viewers (`npx playwright show-trace`), and automatic locators/codegen tools.
3.  **Powerful Network Interception**: Built-in network mocking (`page.route()`) allows direct interception of NHTSA API calls and Stripe Checkout sessions in a clean, declarative syntax.
4.  **No Driver Dependencies**: It manages its own browser binaries natively (`npx playwright install`) and isolates contexts, allowing parallel, headless execution in CI out-of-the-box.

---

## 3. Proposed Directory Structure & Execution Flow

### Recommended Node.js Playwright Directory Layout
The E2E test suite should be placed in the `/Users/prathambansal/Dev/RAPP/tests/` directory as requested.

```
/Users/prathambansal/Dev/RAPP/
├── package.json                    # Project configuration, test scripts, and dependencies
├── playwright.config.ts            # Playwright global configurations (base URLs, retries, browsers)
└── tests/
    └── e2e/
        ├── specs/                  # Test files (specifications)
        │   ├── ingestion.spec.ts   # VIN Ingestion & NHTSA decoding tests
        │   ├── diagnostic.spec.ts  # Symptoms input & tool constraint profile tests
        │   ├── safety.spec.ts      # SRS, EV Battery, Fuel Line safety warning & escalation tests
        │   └── paywall.spec.ts     # Stripe payment simulation & repair details unlock tests
        ├── pages/                  # Page Object Model (POM) abstractions
        │   ├── base.page.ts        # Shared base page assertions (theme, layout compliance)
        │   ├── ingestion.page.ts   # VIN input and barcode scanning components
        │   ├── diagnostic.page.ts  # Symptoms form and tools checklist components
        │   ├── output.page.ts      # Diagnosis and repair procedure UI components
        │   └── stripe.page.ts      # Stub page simulating Stripe checkout
        └── utils/
            ├── mock-data.ts        # Seed data for NHTSA APIs, diagnostics, and repairs
            └── test-helpers.ts     # Custom viewport, touch-target, and theme checkers
```

### Execution Commands (Node.js)
1.  **Initialization**:
    ```bash
    npm init playwright@latest -- --yes --quiet --lang=TypeScript --tests-dir=tests/e2e/specs
    ```
2.  **Install dependencies**:
    ```bash
    npm install -D typescript @types/node @playwright/test
    ```
3.  **Install browsers**:
    ```bash
    npx playwright install --with-deps
    ```
4.  **Run E2E tests against Mock/Dev Server**:
    ```bash
    npx playwright test
    ```
5.  **Run tests with UI Debugger**:
    ```bash
    npx playwright test --ui
    ```

---

### Alternative: Python Playwright Directory Layout
If the parent orchestrator prefers a pure Python testing suite to match the FastAPI backend:

```
/Users/prathambansal/Dev/RAPP/
├── pytest.ini                      # Pytest configurations (markers, options)
├── requirements-dev.txt            # Dev dependencies including pytest-playwright
└── tests/
    └── e2e/
        ├── conftest.py             # Fixtures for browser setup, custom hooks, port binding
        ├── test_ingestion.py       # Happy/unhappy paths for VIN decoding
        ├── test_diagnostic.py      # Symptoms & tool checklist constraints
        ├── test_safety.py          # Safety banner and dealer-level escalation warnings
        ├── test_paywall.py         # Stripe payload intercept & local storage checks
        ├── pages/                  # Page Object Model
        │   ├── base_page.py
        │   ├── ingestion_page.py
        │   ├── diagnostic_page.py
        │   └── output_page.py
        └── utils/
            ├── mock_data.py
            └── helpers.py
```

### Execution Commands (Python)
1.  **Install dependencies**:
    ```bash
    pip install pytest-playwright
    ```
2.  **Install browsers**:
    ```bash
    playwright install
    ```
3.  **Run tests**:
    ```bash
    pytest tests/e2e
    ```

---

## 4. Test Case Plan (Tiers 1-4)
These opaque-box tests map directly to the requirements in `SCOPE.md`.

### Tier 1: Happy Path & Core Smoke Tests
*Goal: Validate the primary end-to-end user journey under ideal conditions.*

*   **Test 1.1: Single Session E2E Unlock Flow**
    *   *Steps*:
        1. Open root page `/`.
        2. Enter a valid 17-character VIN (e.g. `1FA6P8CF0Hxxxxxxx`) and click "Decode".
        3. Verify vehicle info cards display correct Year, Make, Model, Engine, and Drive type.
        4. In diagnostic symptoms textarea, input `Engine sputtering and shaking at idle`.
        5. Check "Basic Hand Tools" and "Torque Wrench" in the tools checklist, then click "Diagnose".
        6. Verify "Free Diagnosis" section is populated and visible.
        7. Verify "Repair Steps" section is hidden behind the Stripe Paywall CTA banner.
        8. Click "Unlock Repair Steps" (Paywall CTA).
        9. Simulate Stripe checkout page loading, fill test credentials, and submit.
        10. Redirected back to `/` with a success session token.
        11. Verify `localStorage` contains the valid unlock state.
        12. Verify the paywall banner is removed and step-by-step repair instructions are unlocked and visible.
*   **Test 1.2: VIN Barcode Scanner Activation**
    *   *Steps*:
        1. Open root page `/`.
        2. Click "Scan VIN Barcode" button.
        3. Verify camera invocation modal is spawned (or mock successful camera stream feed).
        4. Mock a barcode read event returning a valid VIN.
        5. Verify the VIN input is populated with the read value.

### Tier 2: Validation, Constraints & Edge Cases
*Goal: Ensure boundary limits, invalid inputs, and tool constraints are handled correctly.*

*   **Test 2.1: Invalid VIN Validation**
    *   *Steps*:
        1. Open root page `/`.
        2. Input an invalid VIN (e.g. `SHORT123` or characters containing prohibited letters `I`, `O`, `Q`).
        3. Click "Decode".
        4. Verify a validation error message "Invalid VIN format. Please enter a valid 17-character VIN" is displayed.
        5. Verify the diagnostic step remains disabled/blocked until a valid VIN is decoded.
*   **Test 2.2: Tool Constraints Output Alteration**
    *   *Steps*:
        1. Decode a valid VIN.
        2. Input symptom `Spark plug replacement`.
        3. *Scenario A*: Select ONLY "Basic Hand Tools" (No Torque Wrench).
            *   Submit and verify the output contains a warning: "Warning: Torque Wrench is missing. Proceeding without one may lead to incorrect spark plug tightening."
        4. *Scenario B*: Select both "Basic Hand Tools" and "Torque Wrench".
            *   Submit and verify the output contains explicit torque settings (e.g., "Torque to 18 ft-lbs").
*   **Test 2.3: Missing Symptoms Form Submission**
    *   *Steps*:
        1. Decode a valid VIN.
        2. Keep the symptoms text area empty.
        3. Click "Diagnose".
        4. Verify input validation triggers, showing "Please describe your vehicle's symptoms or input OBD codes."

### Tier 3: Safety & Escalation Protocol
*Goal: Verify safety triggers block dangerous steps, show warnings, recommend dealer tools, and check UI compliance.*

*   **Test 3.1: Airbag/SRS Safety Warning Banner**
    *   *Steps*:
        1. Ingest valid VIN.
        2. Input symptoms: `Airbag light is on, passenger seat SRS fault`.
        3. Select tool profile and click "Diagnose".
        4. Verify that a prominent, high-contrast, non-dismissible warning banner is rendered.
        5. Verify the warning banner has *no* close/dismiss button (`x` or close text).
        6. Verify banner content contains: "DANGER: SRS / Airbag systems are explosive and safety-critical. Professional service is highly recommended."
*   **Test 3.2: High-Voltage EV Battery Safety Warning**
    *   *Steps*:
        1. Decode an electric vehicle VIN (e.g., Tesla Model 3).
        2. Input symptoms: `EV battery coolant low, main battery pack warning`.
        3. Verify the non-dismissible safety warning banner renders: "DANGER: High-voltage systems can cause fatal electrocution. Shut down HV disconnect before proceeding."
*   **Test 3.3: Pressurized Fuel Line Safety Warning**
    *   *Steps*:
        1. Ingest valid VIN.
        2. Input symptoms: `Smell of gas, fuel line leaking near pressure rail`.
        3. Verify the warning banner renders: "DANGER: Fuel lines are highly pressurized. Release pressure system before disconnecting."
*   **Test 3.4: Dealer-Level Tool Escalation**
    *   *Steps*:
        1. Ingest valid VIN.
        2. Input symptoms: `ADAS lane keep assist camera calibration`.
        3. Verify the system outputs: "This procedure requires a dealer-level calibration tool. Professional service is recommended."
        4. Verify that standard DIY steps are hidden/gated with a "Not Capable with Selected Tools" banner.
*   **Test 3.5: Layout & Accessibility (Touch Targets & Dark Mode Contrast)**
    *   *Steps*:
        1. Verify the root element contains `class="dark"` or default styles enforce dark mode (`background-color` is dark/black, `color` is light/white).
        2. Query all interactive elements (buttons, checkboxes, input text fields).
        3. Assert that the bounding box height and width are at least **48px** (e.g. `await expect(button).toHaveCSS('height', /^(4[8-9]|[5-9]\d|\d{3,})px$/)`).
        4. Verify contrast ratio using a playwright-axe accessibility audit tool.

### Tier 4: Payment State Lifecycle, Persistence & Security
*Goal: Validate paywall gates, state preservation in localStorage, and direct endpoint security.*

*   **Test 4.1: DOM Verification of Paywall Gate**
    *   *Steps*:
        1. Run diagnostic flow.
        2. On the Output page, inspect the DOM before payment.
        3. Verify that details, images, and text content for the repair steps are completely absent from the DOM (not just hidden with `display: none` or `visibility: hidden` which can be bypassed via inspector).
*   **Test 4.2: LocalStorage Unlock State Persistence**
    *   *Steps*:
        1. Simulate a successful Stripe payment callback.
        2. Verify that `localStorage.getItem('unlocked_vin_passes')` includes the decoded VIN and a valid signature/token.
        3. Refresh the page.
        4. Verify that the repair steps remain visible immediately without showing the paywall CTA.
*   **Test 4.3: Direct API Gating Security Check**
    *   *Steps*:
        1. Send a direct HTTP POST request to `/api/repair` with a decoded VIN payload but *no* payment session header/cookie.
        2. Verify the server returns a `402 Payment Required` (or `403 Forbidden`) status code.
        3. Verify that the response body does *not* leak any repair instructions.

---

## 5. Mocking & Verification Mechanism

Since the main codebase is not yet implemented, running E2E tests directly would fail due to missing servers. To make the test suite runnable, testable, and capable of failing on bad behavior, we propose a **Mock Application Server** written in Python (using FastAPI and static files).

### Dual-Purpose Mock Server (`mock_app.py`)
This script acts as both:
1.  **A static file server**: Serves a mockup HTML frontend (`index.html`) styling the spec requirements (dark mode default, touch targets >= 48px, interactive input fields, Stripe checkout buttons).
2.  **An API server**: Serves API mocks for `/api/decode-vin`, `/api/diagnose`, and `/api/repair` which gate procedures based on mock payment state.

### Injecting "Faulty Modes" for Verification
To verify that the test suite actually catches violations, the mock server will support configuration via environment variables (toggled before starting the test suite):

```python
# Pseudo-code configuration for mock_app.py
import os

FAULTY_VIN_DECODING = os.getenv("FAULTY_VIN_DECODING", "false").lower() == "true"
MISSING_WARNINGS = os.getenv("MISSING_WARNINGS", "false").lower() == "true"
BYPASS_PAYWALL_GATE = os.getenv("BYPASS_PAYWALL_GATE", "false").lower() == "true"
SMALL_TOUCH_TARGETS = os.getenv("SMALL_TOUCH_TARGETS", "false").lower() == "true"
```

1.  **Test Case**: Invalid VIN format verification.
    *   *Normal Mode*: Mock server validates VIN length and format.
    *   *Faulty Mode (`FAULTY_VIN_DECODING=true`)*: Mock server accepts any input, even empty or 3-character strings.
    *   *Result*: Test 2.1 fails because it expects a validation error which is not displayed.
2.  **Test Case**: Airbag safety warning.
    *   *Normal Mode*: Entering "airbag" triggers a warning banner.
    *   *Faulty Mode (`MISSING_WARNINGS=true`)*: Mock server does not insert the warning HTML block.
    *   *Result*: Test 3.1 fails because the warning banner locator is missing from the DOM.
3.  **Test Case**: Paywall gating.
    *   *Normal Mode*: `/api/repair` checks for authorization headers/tokens and returns `402` without it.
    *   *Faulty Mode (`BYPASS_PAYWALL_GATE=true`)*: `/api/repair` returns the full repair steps to anyone without authorization.
    *   *Result*: Test 4.3 fails because it expects a `402/403` error but receives a `200 OK` with data.
4.  **Test Case**: Touch target size.
    *   *Normal Mode*: Buttons are styled with `min-height: 48px; min-width: 48px;`.
    *   *Faulty Mode (`SMALL_TOUCH_TARGETS=true`)*: Buttons are styled with `height: 30px; width: 30px;` (violating criteria).
    *   *Result*: Test 3.5 fails during CSS/layout verification.

### Running Verification Tests
A helper shell script `run_tests.sh` can automate this validation:

```bash
#!/bin/bash
# run_tests.sh

# 1. Run tests against a Correct Server (All tests should PASS)
echo "=== Running against Correct Mock Server ==="
export FAULTY_VIN_DECODING=false
export MISSING_WARNINGS=false
export BYPASS_PAYWALL_GATE=false
export SMALL_TOUCH_TARGETS=false
python3 mock_app.py & 
MOCK_PID=$!
sleep 2 # wait for server to start

npx playwright test
TEST_EXIT_CODE=$?

kill $MOCK_PID
if [ $TEST_EXIT_CODE -ne 0 ]; then
  echo "❌ Error: E2E tests failed against a healthy mock server!"
  exit 1
fi
echo "✅ Healthy server tests passed."

# 2. Verify that FAULTY_VIN_DECODING causes Test 2.1 to fail
echo "=== Running against Faulty VIN Server (Expected: Fail) ==="
export FAULTY_VIN_DECODING=true
python3 mock_app.py &
MOCK_PID=$!
sleep 2

npx playwright test tests/e2e/specs/ingestion.spec.ts
TEST_EXIT_CODE=$?

kill $MOCK_PID
if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo "❌ Error: Test suite did not catch faulty VIN decoding!"
  exit 1
fi
echo "✅ Test suite successfully caught faulty VIN decoding."

# Repeat for other fault flags...
```

---

## 6. Recommendations & Next Steps

1.  **Implement Node.js Playwright Infrastructure**: Create `package.json`, install Playwright, and write the global configurations in `playwright.config.ts`.
2.  **Create the Mock Server**: Write `mock_app.py` in the `tests/` directory with customizable flags. Write a basic `index.html` mockup that contains dark mode classes, 48px buttons, local storage keys, and forms.
3.  **Draft Page Object Model files**: Write base structures for `ingestion.page.ts`, `diagnostic.page.ts`, and `output.page.ts`.
4.  **Implement Tier 1-4 Spec Files**: Write the test specifications in `tests/e2e/specs/`.
5.  **Verify Test Suite Invalidation**: Run the automated test runner in normal and faulty modes to ensure tests are highly sensitive to regression errors.
