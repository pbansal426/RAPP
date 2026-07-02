# Handoff Report: Milestone 2 - Home Page & Navigation Evolution

## 1. Observation
- **`frontend/package.json`**: Checked lines 11-15:
  ```json
    "dependencies": {
      "react": "^18",
      "react-dom": "^18",
      "next": "14.2.35"
    }
  ```
  `tesseract.js` is not present in dependencies.
- **`frontend/src/app/page.tsx`**: Understood current submit logic (lines 22-40) and layout structure. It is currently a single card for VIN identification that calls `api.get` and saves results to `localStorage.setItem('rapp_vin_data', ...)`.
- **`frontend/src/app/diagnose/page.tsx`**: Read layout structure. It displays VIN details from local storage but lacks any back button or link to route to `/` (lines 31-47).
- **`backend/main.py`**: Inspected `decode_vin_internal` (lines 156-224). It validates the alphanumeric format of the string, performs an asynchronous get request to settings.nhtsa_base_url, and cleans/maps the output dictionary.
- **`tests/unit/test_api.py`**: Checked unit test assertions. It tests successful NHTSA decoding and invalid formats, but does not cover synthetic VINs.
- **`tests/e2e-mvp-flow.spec.ts`**: Checked Playwright tests, confirming they assert path transitions `/ -> /diagnose -> /results`.

---

## 2. Logic Chain
1. To compile client-side OCR, the implementer must add `"tesseract.js": "^5.1.0"` to dependencies in `frontend/package.json` (supported by the missing dependency observation in `frontend/package.json`).
2. Tesseract runs completely client-side in the browser, but it can trigger compilation or SSR errors in Next.js. Dynamic import (`const Tesseract = await import('tesseract.js')`) inside the file picker change handler avoids SSR crashes.
3. The cascading dropdown needs state selectors: `selectedYear`, `selectedMake`, and `selectedModel`. Making options dependent (Make options unlock when Year is set; Model options unlock when Make is set) enforces the cascading flow requirements.
4. Constructing the synthetic VIN using the pattern `SYN` + `YY` + `MAKE_CODE` (5 chars) + `MODEL_CODE` (7 chars) produces a valid 17-character identifier. Storing `rapp_vin` and `rapp_vin_data` inside `localStorage` on dropdown submission replicates the state structure of a successful standard VIN decode.
5. In `backend/main.py:decode_vin_internal`, intercepts for `vin.upper().startswith("SYN")` before the NHTSA API call prevent communication failures and return matching mock payloads directly.
6. A standard React/Next.js button calling `router.push('/')` inside `frontend/src/app/diagnose/page.tsx` satisfies the back navigation requirements.

---

## 3. Caveats
- **Local OCR Worker / Offline mode**: In pure airgapped environments, Tesseract.js may attempt to download `.wasm` binaries or trained languages data from unpkg.com or similar CDNs. If tests run in a sandbox without internet access, the mock app or mock responses should be used, or Tesseract's config must load language files from local assets.
- **Cascading mappings**: Mappings are hardcoded on both client and server side. Future vehicle additions require maintaining synchronization between the list of models in `frontend/src/app/page.tsx` and `backend/main.py`.

---

## 4. Conclusion
The codebase is fully prepared for Milestone 2 implementation. The proposed implementation strategy details the changes required for `package.json`, `page.tsx` (frontend and backend), and `diagnose/page.tsx`, as well as how to extend the unit and E2E test suites to guarantee coverage.

---

## 5. Verification Method
- **Local Unit Tests**: Run `poetry run pytest tests/unit/ -v` to check backend synthetic VIN handling.
- **Local Frontend Build & Linters**: Validate using:
  - `cd frontend && pnpm build`
  - `poetry run ruff check backend/`
- **End-to-End Tests**: Run `npx playwright test` to execute the Playwright MVP flow and the new test cases.

---

## Remaining Work
1. Install `tesseract.js` in `frontend/`.
2. Apply modifications to `backend/main.py`, adding the synthetic VIN branch in `decode_vin_internal`.
3. Apply modifications to `frontend/src/app/page.tsx` to insert the file/photo OCR handler and the cascading Manual Selection card.
4. Apply modifications to `frontend/src/app/diagnose/page.tsx` to add the back button.
5. Add unit and playwright E2E tests for the new features.
6. Verify locally.
