# Original User Request

## Initial Request — 2026-06-30T16:36:07-05:00

Build the **Phase 1 MVP of the Automotive AI Repair Engine** — a web application that converts vehicle diagnostic input (VIN + symptoms/OBD-II codes) into tool-constrained, RAG-verified repair instructions in under 10 seconds. This is a software-only validation build; no hardware integration required. Use any libraries and frameworks that get the job done fastest.

Working directory: /Users/prathambansal/Dev/RAPP

Integrity mode: development

Reference specification: /Users/prathambansal/Dev/RAPP/PHASE_1_SPEC.md — read this file first before writing a single line of code.

## Requirements

### R1. Backend API Server
A FastAPI server must expose a live VIN decoding endpoint using the NHTSA public API (https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json), parsing Year, Make, Model, Engine, and Drive Type from the response. The server must also expose stub endpoints for diagnosis, repair generation, and Stripe checkout/webhook that return HTTP 200. All routes must be flat inside a single `main.py`. CORS must be configured to allow the frontend origin.

### R2. RAG Vector Store Abstraction
Implement a modular abstract vector store interface with a concrete ChromaDB backend, switchable via a `VECTOR_STORE` environment variable. No code outside the `rag/` module may import `chromadb` directly. A `retrieve(query, vin_meta, k=5)` helper function must be exposed through the retriever module.

### R3. Frontend Application
Initialize a Next.js 14 TypeScript application. Implement the full 4-step user flow: VIN input → symptom/tool selection → free diagnosis output → unlocked repair steps. Add a Stripe redirect success handler that stores `{vin, stripeSessionId}` into `localStorage`. All API calls must be routed through a single typed fetch wrapper (`src/lib/api.ts`). There must be no login page, no auth flow, and no session management.

### R4. Grease-Monkey Clean UI
The frontend must have a fully polished dark-mode design: deep dark background, high-contrast sans-serif typography large enough to read from 3 feet on a cracked phone screen, neon orange/yellow highlights for warnings, minimum 48px tap targets on all interactive elements, and smooth micro-animations on page transitions and button interactions. This UI must feel premium and purpose-built for a garage environment — not a generic SaaS dashboard.

### R5. Safety & Paywall Layout
The results page must visually distinguish between the free diagnosis summary (always shown) and the locked detailed repair steps (behind a payment CTA button). High-risk system flags (airbags, EV batteries, fuel lines) must render as non-dismissible prominent warning banners before any procedure content.

## Acceptance Criteria

### Backend
- [ ] `curl http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] `curl http://localhost:8000/api/vin/1HGBH41JXMN109186` returns structured JSON with Year, Make, Model, Engine, and Drive fields populated from a live NHTSA API call
- [ ] Stub routes `/api/diagnose`, `/api/repair`, `/api/payments/create-checkout`, `/api/payments/webhook` all return HTTP 200

### Frontend
- [ ] `npm run build` in the `frontend/` directory completes with zero TypeScript or ESLint errors
- [ ] All five route URLs resolve without 404: `/`, `/diagnose`, `/results`, `/repair`, `/repair/success`
- [ ] The root page renders a prominent VIN input field and a barcode scan CTA
- [ ] All buttons and touch targets are visually oversized (≥ 48px height)
- [ ] The results page shows a clear visual separation between the free section and the locked paywall section

### Architecture
- [ ] No `chromadb` import exists outside `backend/rag/`
- [ ] No `auth.py`, login route, or `/login` page exists anywhere in the codebase
- [ ] All frontend `fetch` calls are routed through `src/lib/api.ts`
- [ ] `backend/services/auth.py` does not exist

## Follow-up — 2026-07-01T04:23:54Z

Build the **Phase 1 MVP of the Automotive AI Repair Engine** — a production-grade web application that converts vehicle diagnostic input (VIN + symptoms/OBD-II codes) into tool-constrained, RAG-verified repair instructions in under 10 seconds. Use industry-standard tooling throughout. Prioritize robustness and real-world deployability over speed of scaffolding.

Working directory: /Users/prathambansal/Dev/RAPP

Integrity mode: development

Reference specification: /Users/prathambansal/Dev/RAPP/PHASE_1_SPEC.md — read this file first before writing a single line of code.

## Existing Work (Preserve As-Is)

The following files already exist and are production-quality. Do NOT modify or delete them:
- `backend/rag/__init__.py` — singleton factory for the vector store
- `backend/rag/vector_store.py` — abstract VectorStore base class + ChromaDB + MockVectorStore implementations
- `backend/rag/retriever.py` — `retrieve(query, vin_meta, k)` helper
- `tests/e2e-mvp-flow.spec.ts` — full Playwright E2E test suite (all `data-testid` selectors are fixed — the app must match them exactly)
- `tests/mock_app.py` — FastAPI mock for test isolation
- `tests/verify_tests.sh` — automated test verification harness
- `tests/unit/test_rag.py` — unit tests for the RAG layer
- `playwright.config.ts` — Playwright multi-browser config
- `package.json` — root Node deps (Playwright)
- `pyproject.toml` — Poetry project file (already created)
- `.env.example` — environment variable template (already created)

Delete `backend/requirements.txt` if it exists — it is replaced by pyproject.toml.

## Critical: data-testid Selectors

The Playwright tests use these exact selectors. Every frontend page MUST implement them:
- `data-testid="vin-input"` — VIN text input on `/`
- `data-testid="submit-vin-btn"` — submit button on `/`
- `data-testid="scan-barcode-btn"` — scan button on `/`
- `data-testid="symptoms-input"` — textarea on `/diagnose`
- `data-testid="tool-hand-tools"` — checkbox on `/diagnose` (id must also be "tool-hand-tools")
- `data-testid="tool-jack-stands"` — checkbox on `/diagnose`
- `data-testid="tool-multimeter"` — checkbox on `/diagnose`
- `data-testid="submit-diagnose-btn"` — submit button on `/diagnose`
- `data-testid="free-diagnosis-summary"` — visible div on `/results`
- `data-testid="locked-repair-steps"` — hidden by default on `/results`
- `data-testid="payment-cta-btn"` — visible button containing text "Unlock" on `/results`
- `data-testid="safety-warning-banner"` — shown on `/results` when symptoms contain "airbag", must have class `border-orange-500` or `bg-orange-950` or `text-orange-500`, must NOT contain a close/dismiss button
- `data-testid="detailed-repair-steps"` — visible on `/repair` when unlocked
- `data-testid="rag-citation"` — visible on `/repair` when unlocked

## Critical: localStorage Keys

The tests rely on these exact localStorage keys:
- `rapp_vin` — the VIN string, set on `/` submit
- `rapp_symptoms` — symptom string, set on `/diagnose` submit
- `rapp_unlocked_{vin}` — set by `/repair/success` page, checked by `/repair` page

The `/repair/success` page reads `vin` and `session_id` from URL query params, writes `localStorage.setItem('rapp_unlocked_' + vin, sessionId)`, then redirects to `/repair`.

The `/repair` page reads `rapp_vin` from localStorage, checks `rapp_unlocked_{vin}`, and shows `detailed-repair-steps` and `rag-citation` only when unlocked.

The body element must have a class matching `/dark|bg-slate-900|bg-zinc-950|bg-black/` (use `className="dark bg-slate-900"` on `<body>`).

## Requirements

### R1. Python Dependency Management (Poetry)
All Python dependencies must be managed via the existing `pyproject.toml`. Running `poetry install` must succeed. A `poetry.lock` must be committed.

### R2. Containerization (Docker + Compose)
Both the backend and frontend must have production-ready multi-stage Dockerfiles. A `docker-compose.yml` must orchestrate both services with health checks and a persistent ChromaDB volume. A `docker-compose.dev.yml` override must enable hot-reload via source volume mounts. Running `docker compose up` must start a fully functional application stack.

### R3. Backend API Server
A FastAPI server must use a lifespan context manager, structlog structured logging, and a centralized exception handler that never leaks stack traces to clients. It must expose: a live NHTSA VIN decoding endpoint (`GET /api/vin/{vin}`), and stub endpoints for diagnosis, repair, and Stripe checkout/webhook that return HTTP 200. Configuration must use pydantic-settings with startup validation. Production runtime must use Gunicorn with uvicorn workers.

### R4. Frontend Application
A Next.js 14 TypeScript application managed with pnpm. TypeScript strict mode enabled. Implement the full 4-step user flow across 5 pages: `/`, `/diagnose`, `/results`, `/repair`, `/repair/success`. Use vanilla CSS (no Tailwind) but class names must match the test expectations above.

### R5. Grease-Monkey Clean UI
Dark mode default (`dark bg-slate-900` on body), high-contrast sans-serif typography readable at arm’s length, neon orange/yellow highlights for warnings and CTAs, minimum 48px height on all buttons and interactive touch targets, smooth micro-animations. The safety warning banner must be non-dismissible (no close button) with orange styling.

### R6. CI Pipeline
A GitHub Actions workflow (`.github/workflows/ci.yml`) must run on push: `poetry run ruff check`, `poetry run black --check`, `poetry run mypy backend/`, `poetry run pytest tests/unit/`, and the Playwright E2E suite against the mock app.

### R7. Developer Experience
A `Makefile` must expose: `make install`, `make dev`, `make test`, `make lint`, `make type-check`, `make docker-up`, `make docker-down`. A `README.md` must document both the Poetry local path and the Docker path.

## Verification Resources

- E2E tests: `tests/e2e-mvp-flow.spec.ts`
- Fault injection harness: `tests/verify_tests.sh`
- Unit tests: `tests/unit/test_rag.py`
- Mock reference implementation: `tests/mock_app.py` — study this to understand exact expected HTML structure and localStorage behaviour

## Acceptance Criteria

### Backend
- [ ] `curl http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] `curl http://localhost:8000/api/vin/1HGBH41JXMN109186` returns JSON with Year, Make, Model, Engine, Drive fields from a live NHTSA API call
- [ ] All stub routes return HTTP 200
- [ ] `poetry run ruff check backend/` exits 0
- [ ] `poetry run mypy backend/` exits 0
- [ ] No `chromadb` import exists outside `backend/rag/`

### Frontend
- [ ] `pnpm build` in `frontend/` completes with zero TypeScript or ESLint errors
- [ ] All 5 routes resolve without 404
- [ ] All `data-testid` attributes present and correctly named

### Docker
- [ ] `docker compose up` starts both services with zero errors
- [ ] Both container health checks pass

### Tests
- [ ] All 4 Playwright E2E tests pass against the real Next.js frontend
- [ ] `./tests/verify_tests.sh` exits 0
- [ ] `poetry run pytest tests/unit/ -v` exits 0

### CI
- [ ] `.github/workflows/ci.yml` is a valid, runnable GitHub Actions workflow

## Follow-up — 2026-07-02T04:49:30Z

Evolve the existing RAPP Automotive AI Repair Engine (Next.js 14 + FastAPI) from a stateless, single-use prototype into a polished, professional application. The changes span every page of the app, adding real Firebase user accounts, a dramatically improved vehicle entry flow, a premium repair experience with a side-panel AI chatbot, and a leaner, more scannable UI throughout.

Working directory: /Users/prathambansal/Dev/RAPP

Integrity mode: development

---

## Existing Codebase Context

The project already has a working frontend (Next.js 14 TypeScript, pnpm, vanilla CSS in `frontend/`) and backend (FastAPI, Python, in `backend/`). All existing API routes, localStorage keys (`rapp_vin`, `rapp_symptoms`, `rapp_tools`, `rapp_unlocked_{vin}`), and the core 4-page user flow must continue to function. The existing `data-testid` selectors on critical paywall and safety elements (`payment-cta-btn`, `safety-warning-banner`, `free-diagnosis-summary`) must not be removed. Other selectors may be updated if the component is redesigned.

Reference existing files before writing new code. Do not delete or overwrite backend RAG or unit test files.

---

## Requirements

### R1. Home Page: Multiple Vehicle Entry Methods

The home page (`/`) must offer three ways to identify a vehicle — all leading to the same `/diagnose` flow:

1. **VIN Text Entry** (existing) — 17-character input with live NHTSA decode on submit.
2. **Year / Make / Model Selector** — a cascading 3-step dropdown. Year → Make → Model. On final selection, construct a synthetic VIN lookup or store the selected values directly in localStorage as `rapp_vin_data` so the rest of the flow works without a real VIN.
3. **VIN Photo Capture** — a button that invokes the device camera or file picker, passes the image through an OCR library (Tesseract.js) to extract the VIN string, and auto-populates the text field for user confirmation before submission.

All three paths must end with the user navigating to `/diagnose` with the vehicle data stored in localStorage.

### R2. Diagnose Page: Smarter Input + Professional UI

Redesign `/diagnose` with these specific changes:

- **Vehicle Hero Card**: Replace the small text strip at the top with a prominent hero section. Show the manufacturer's official logo (fetched via a reliable CDN or logo API like `logo.clearbit.com/{domain}` or a similar free source), display it stylishly, and render the Year + Make + Model in a large, title-level font. The message must clearly communicate "your car has been found."
- **OBD-II Code Picker**: Add a dedicated, searchable dropdown/combobox field above the symptoms textarea. It must include a comprehensive, curated list of OBD-II codes covering P (powertrain), B (body), C (chassis), and U (network) categories — enough that a user with any real scanner will always find their code. Codes must be searchable by both code (P0301) and description (cylinder misfire). Selecting a code auto-append it to the symptoms field.
- **Photo / Image Input**: Add a camera capture and file upload button that lets users attach a photo of their dashboard warning lights or engine bay. The image is stored and displayed as a preview (actual image analysis is a bonus — displaying the image is required).
- **Professional Tool Icons**: Replace all emoji in the tool checkbox list with clean SVG icons (inline or via a free icon set like Heroicons or Lucide). No emoji in the tool section.
- **Symptom Textarea**: Update the placeholder text to be concise and professional, guiding the user to describe specific symptoms rather than anything vague.
- **Text Reduction**: Cut verbose instructional text throughout the page by at least 40%. Keep the same information density in fewer words.

### R3. Results Page: Leaner Copy + Back Navigation

- Reduce all body copy and descriptions by ~40%. Every sentence must earn its place.
- Add a back button (top-left) that returns to `/diagnose`.
- The paywall card copy must be punchy and conversion-focused — no paragraphs.

### R4. Premium Repair Page: Inline Diagrams + Side Chatbot + Real Steps

This is the highest-priority page. The user paid for this content — it must be visibly more valuable than anything they could find on YouTube or a forum.

**Inline Diagrams**: Remove the standalone diagram card at the top. Instead, embed relevant SVG schematics directly within the repair steps at the points where they are contextually needed (e.g., a bolt tightening sequence diagram appears inside the step that instructs the user to torque the bolts). Each phase should have at least one inline visual where appropriate.

**Real, Structured Steps**: The repair steps must be structured as a proper, phase-by-phase procedure with a genuine conclusion:
- Phase 1: Safety & Preparation (battery disconnect, cool-down, lift points)
- Phase 2: Disassembly & Access (what to remove to reach the target component)
- Phase 3: Component Inspection & Replacement (exact component swap with part specs)
- Phase 4: Reassembly & Torque Verification (torque specs, crisscross patterns, clearances)
- **Conclusion / Verification Phase**: OBD-II code clearing instructions, test drive protocol, what to watch for in the next 50–100 miles, and a "you're done" confirmation message.

Use varied typography — different font weights, sizes, and accent colors — for torque specs, warnings, tool callouts, and standard prose. Every step should include at least one tip or contextual question embedded inline (e.g., "Tip: If the bolt won't break free, apply penetrating oil and wait 10 minutes" or "Is your engine still warm? Wait 30 minutes before proceeding.").

**Side-Panel AI Chatbot**: Replace the floating bottom-right chatbot with a persistent side panel (right side on desktop, collapsible drawer on mobile). The chatbot must:
- Be visible by default when the repair page loads, not hidden behind a button.
- Proactively send a contextual opening message based on the specific repair being viewed (not a generic greeting).
- Ask the user questions to better understand their situation (e.g., "Have you already disconnected the battery?" or "Do you see any corrosion on the connector?").
- Use mock/hardcoded responses that are contextually relevant to the repair type shown.

### R5. Post-Repair Firebase Authentication & Account Saving

After the user reaches the end of the `/repair` page (scrolls past the conclusion or a trigger point), display an optional "Save Your Repair Guide" sign-up prompt — a card or modal that is dismissible.

**Firebase Setup**:
- Initialize Firebase in the project using the Firebase CLI (`npx -y firebase-tools@latest`).
- Use Firebase Authentication (email/password) for sign-up and login.
- Use Cloud Firestore to store each user's saved repairs (VIN, car info, symptoms, repair timestamp) and profile (display name, saved payment method flag).
- Add Firebase config env vars to `.env.example` (prefixed `NEXT_PUBLIC_FIREBASE_*`).
- The Firebase SDK must only be initialized client-side in Next.js (`src/lib/firebase.ts`).

**Account Features**:
- After sign-up/login, the user can see a "My Garage" page (`/garage`) listing all their saved repairs.
- The repair guide they just unlocked is automatically saved to Firestore on account creation.
- A "Log In" link appears in the top-right of the header on all pages once Firebase is initialized.

**Non-blocking**: Sign-up must be entirely optional. Users who dismiss the prompt can still view and scroll the repair guide without any restriction.

### R6. Back Navigation Throughout App

Add back buttons on `/diagnose`, `/results`, and `/repair`. Each must navigate to the logically previous page in the flow. Use the browser's `router.back()` or an explicit route, whichever is more reliable for the flow.

---

## Verification Resources

- Existing Playwright E2E tests: `tests/e2e-mvp-flow.spec.ts`
- Fault-injection harness: `tests/verify_tests.sh`
- Backend unit tests: `tests/unit/` (must not regress)
- Mock app reference: `tests/mock_app.py`
- Existing frontend pages: `frontend/src/app/` — study these before rewriting
- Existing CSS system: `frontend/src/app/globals.css` — extend, do not replace

---

## Acceptance Criteria

### Home Page
- [ ] Year/Make/Model selector cascades correctly and navigates to `/diagnose` with vehicle data in localStorage
- [ ] Camera/file-picker button launches image selection, runs OCR via Tesseract.js, and populates the VIN field with extracted text
- [ ] All three entry methods reach `/diagnose` successfully

### Diagnose Page
- [ ] Vehicle hero section displays the manufacturer logo and car name in large title font
- [ ] OBD-II code picker is searchable by code and description; selecting a code updates the symptoms field
- [ ] Photo upload shows a preview image
- [ ] Tool checkboxes use SVG icons — no emoji visible in the tools list
- [ ] Page visible text word count is reduced vs. the current version

### Results Page
- [ ] Back button navigates to `/diagnose`
- [ ] `data-testid="free-diagnosis-summary"`, `data-testid="payment-cta-btn"` (containing "Unlock"), and `data-testid="safety-warning-banner"` (with orange classes) are all present and pass the existing E2E assertions

### Repair Page
- [ ] No standalone diagram card at the top — diagrams appear inline within steps
- [ ] Steps include a Conclusion / Verification phase with OBD clearing and test drive instructions
- [ ] Side chatbot panel is visible by default on page load (not hidden behind a button)
- [ ] Back button navigates to `/results`

### Firebase & Account
- [ ] `src/lib/firebase.ts` initializes Firebase with env-var config
- [ ] Sign-up modal/card appears at the end of the repair page and is dismissible
- [ ] `/garage` route renders without a 404 and shows saved repairs for a logged-in user
- [ ] `.env.example` contains all required `NEXT_PUBLIC_FIREBASE_*` keys

### Tests
- [ ] `./tests/verify_tests.sh` exits 0 (all 5 verification scenarios pass)
- [ ] `./.venv/bin/pytest tests/unit/ -v` exits 0
- [ ] `pnpm build` in `frontend/` completes with zero TypeScript errors

## Follow-up — 2026-07-03T06:54:03Z

Execute Phase 2 of the RAPP (Real Automotive Professional Platform) redesign, transforming the web application frontend into a trustworthy, professional automotive engineering platform with a Deep Industrial Navy aesthetic, cascading vehicle selector, isolated OBD-II diagnostic tooling, and affiliate garage vault.

Working directory: /Users/prathambansal/Dev/RAPP
Integrity mode: development

## Requirements

### R1. Deep Industrial Navy Design System
Transform the application visual design across `frontend/src/app/globals.css` and all layouts from hypermodern/immature to a trustworthy, high-contrast automotive engineering aesthetic using Deep Slate Navy (`#0F172A`) backgrounds, charcoal cards with subtle 1px borders (`rgba(255, 255, 255, 0.08)`), crisp engineered typography, and safety orange/amber (`#F97316`) accents.

### R2. Cascading 4-Step Vehicle Selector & Auto-Lock Specs
Upgrade the homepage vehicle identification flow (`frontend/src/app/page.tsx`) to a 4-step cascading selector (Year → Make → Model → Trim). When selecting a model/trim with a single valid powertrain (such as 2010 Toyota Corolla S or 2015 Highlander XLE), automatically populate and lock the Powertrain (Gasoline), Engine Layout, and Drive Type without requiring manual user selection.

### R3. Automotive Diagnostic Panel (Diagnose Page)
Enhance `frontend/src/app/diagnose/*` with:
- **Brand Logo Badge (`VehicleHeroCard.tsx`)**: Display a prominent, clean vehicle brand vector/SVG badge next to large bold model identification text.
- **OBD-II Picker Isolation (`ObdCodePicker.tsx` & `page.tsx`)**: Selecting OBD-II codes must populate distinct, removable diagnostic tags/chips above/below the textarea rather than inserting text into the user problem input field.
- **HEIC Photo Previews (`page.tsx`)**: Render attached dashboard/engine photo previews reliably (supporting HEIC/HEIF formatting or fallback previews), showing up to 3 thumbnails and collapsing additional photos behind a toggle.
- **Searchable Tool Inventory (`ToolSelector.tsx`)**: Remove childish icons, add a functional search bar, and implement category filters for Tool Brands (Snap-on, Milwaukee, DeWalt, Harbor Freight) and specific mechanical/electrical capabilities.

### R4. Affiliate Parts Dashboard & Garage Sign-Up Vault (Results Page)
Enhance `frontend/src/app/results/*` with:
- **Curated Affiliate Cards (`PartsPurchasePlan.tsx`)**: Render each required part/tool with 2 structured options (e.g., OEM Factory Part vs Premium Aftermarket / Synthetic vs Conventional Oil) featuring clear technical rationales and affiliate search links.
- **3-Column Price Comparison**: Accurately display Dealership vs Independent Shop vs RAPP Guided DIY costs (Guide Fee $4.00 + verified parts total).
- **Post-Repair Garage Vault Sign-Up**: Add a prominent "Save to My Garage & Keep Guide Forever" registration section/modal allowing users to archive their vehicle profile, diagnostic guide, and payment preferences.

## Acceptance Criteria

### Verification & Build Integrity
- [ ] Running `cd frontend && npm run build` (or `npx next build`) succeeds without TypeScript compilation errors or broken imports.
- [ ] All interactive UI flows (4-step selector, OBD-II tag addition/removal, tool inventory filtering, and sign-up modal trigger) function smoothly without client-side console runtime errors.

