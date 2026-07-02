## 2026-07-02T05:02:10Z

You are the Worker for Milestone 2 (Home Page & Navigation Evolution).
Your working directory is: /Users/prathambansal/Dev/RAPP/.agents/teamwork_preview_worker_m2_ingestion

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope / Requirements (Milestone 2):
1. Install/add "tesseract.js": "^5.1.0" to frontend/package.json and run pnpm install.
2. In frontend/src/app/page.tsx:
   - Implement Year/Make/Model cascading 3-step dropdown:
     - Select Year (2015-2026) -> Select Make (HONDA, TOYOTA, FORD, LEXUS, CHEVROLET) -> Select Model (CIVIC, ACCORD, CAMRY, COROLLA, F-150, RX350, SILVERADO).
     - Make selection cascades (unlocks after year is selected). Model selection cascades (unlocks/filters after make is selected).
     - Models per Make:
       - HONDA: CIVIC, ACCORD
       - TOYOTA: CAMRY, COROLLA
       - FORD: F-150
       - LEXUS: RX350
       - CHEVROLET: SILVERADO
   - On final selection submit:
     - Construct a 17-character alphanumeric synthetic VIN: "SYN" + YY (2-digit year) + MAKE_CODE (5 chars) + MODEL_CODE (7 chars).
     - Codes:
       - Makes: HONDA -> HONDA, TOYOTA -> TOYOT, FORD -> FORDX, LEXUS -> LEXUS, CHEVROLET -> CHEVR
       - Models: CIVIC -> CIVICXX, ACCORD -> ACCORDX, F-150 -> F150XXX, CAMRY -> CAMRYXX, COROLLA -> COROLLA, RX350 -> RX350XX, SILVERADO -> SILVERA
     - Call `/api/vin/{synthetic_vin}` to decode the VIN.
     - Store the synthetic VIN in localStorage as "rapp_vin" and the decoded JSON object (with year, make, model, engine, drive_type) as "rapp_vin_data" on submit.
     - Navigate to `/diagnose`.
   - Implement client-side OCR via tesseract.js:
     - Add a photo capture/file picker button. Clicking "Scan Barcode / QR" (or a file input triggered by it) should open a file picker.
     - Use tesseract.js client-side to run OCR on the selected image, extract the first 17-character alphanumeric string that looks like a VIN, and populate the input field.
     - Ensure the user can edit/confirm the text before submission.
3. In backend/main.py:
   - Modify decode_vin_internal to support parsing synthetic VINs starting with "SYN" (case insensitive/upper normalized).
   - If the VIN starts with "SYN", parse YY year (e.g. 23 -> 2023), MAKE_CODE, and MODEL_CODE using reverse mapping.
   - Decoded dictionaries must map:
     - HONDA: Engine: "1.5L 4-Cylinder", Drive: "FWD"
     - TOYOT: Engine: "2.5L 4-Cylinder", Drive: "FWD"
     - FORDX: Engine: "3.5L V6", Drive: "AWD"
     - LEXUS: Engine: "3.5L V6", Drive: "AWD"
     - CHEVR: Engine: "5.3L V8", Drive: "AWD"
   - Return the decoded dictionary directly, skipping the NHTSA API call.
4. In frontend/src/app/diagnose/page.tsx:
   - Add a back button in `/diagnose` (top-left) that routes to `/` using `router.push('/')`. Use a test ID: data-testid="back-to-home-btn".
5. Run builds and tests to verify everything compiles and passes:
   - Backend unit tests: .venv/bin/pytest tests/unit/
   - Playwright/E2E: run existing Playwright tests and add coverage if needed.
   - Frontend: pnpm build (or pnpm run build) to verify TypeScript and lint checks.

Refer to these Explorer handoff files for further detail and analysis:
- /Users/prathambansal/Dev/RAPP/.agents/teamwork_preview_explorer_m2_ingestion_1/handoff.md
- /Users/prathambansal/Dev/RAPP/.agents/teamwork_preview_explorer_m2_ingestion_2/handoff.md
- /Users/prathambansal/Dev/RAPP/.agents/teamwork_preview_explorer_m2_ingestion_3/handoff.md

Report back your progress and write handoff.md when complete.
