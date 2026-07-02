# Original User Request

## Initial Request — 2026-06-30T21:36:20Z

You are the Project Orchestrator for the Phase 1 MVP of the Automotive AI Repair Engine.
Your metadata directory is: /Users/prathambansal/Dev/RAPP/.agents/orchestrator
The project root is: /Users/prathambansal/Dev/RAPP
The verbatim user request is located at: /Users/prathambansal/Dev/RAPP/ORIGINAL_REQUEST.md
The reference specification is at: /Users/prathambansal/Dev/RAPP/PHASE_1_SPEC.md

Your responsibilities:
1. Decompose the project requirements into logical milestones and record them in your `plan.md` in your metadata directory.
2. Maintain `progress.md` in your metadata directory detailing completed milestones, current activities, and next steps.
3. Spawn and manage specialist subagents to execute the technical tasks (RAG setup, Backend API implementation, Frontend Next.js integration, clean grease-monkey UI, safety paywall logic, and integration testing).
4. Run integration tests or verify the build to ensure everything works and satisfies the Acceptance Criteria.
5. Report completion back to the Sentinel parent (conversation ID: 4014231e-dcda-49bb-81c0-d82f5fbd5904) once all milestones are achieved.

Rules:
- Never place project code, tests, or data files under `.agents/`.
- No chromadb imports may exist outside the backend `rag/` module.
- No `auth.py`, login route, or `/login` page may exist in the codebase.
- Maintain premium grease-monkey UI contrast, large typography (read from 3 feet on cracked phone screen), and 48px tap targets.
- Ensure all frontend fetches are routed through `src/lib/api.ts`.

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

## Resume Request — 2026-07-02T09:20:24Z

You are the Project Orchestrator. The previous orchestrator (a6392d7e-78d9-4fac-a164-415e9d22ae0f) stopped due to a transient RESOURCE_EXHAUSTED quota error, which has now cleared.
The workspace contains existing implementations for several components (e.g., ObdCodePicker, VehicleHeroCard, ChatPanel, SaveGuidePrompt, garage page).
Your task is to resume the evolution:
1. Audit the existing codebase to verify what has been implemented so far.
2. Update plan.md, progress.md, and PROJECT.md in your folder (.agents/orchestrator/) to align with the actual current state.
3. Continue executing the product evolution requirements specified under the header '## Follow-up — 2026-07-02T04:49:30Z' in /Users/prathambansal/Dev/RAPP/ORIGINAL_REQUEST.md.
4. Run all validation tests and checks.
5. Notify me immediately when you claim victory or require human input.
