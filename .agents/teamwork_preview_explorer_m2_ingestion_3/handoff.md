# Soft Handoff Report: Milestone 2 (Home Page & Navigation Evolution)

This document provides observations, logic, conclusions, and remaining steps for implementing the home page and navigation improvements under Milestone 2.

---

## 1. Observation
We observed the following files and configurations in the codebase:
1. **`frontend/package.json`**:
   * Dependencies currently include:
     ```json
     "dependencies": {
       "react": "^18",
       "react-dom": "^18",
       "next": "14.2.35"
     }
     ```
2. **`frontend/src/app/page.tsx`**:
   * Line 17-40 contains the submit handler for the VIN:
     ```typescript
     const handleSubmit = async () => {
       const trimmed = vin.trim().toUpperCase();
       if (trimmed.length !== 17) {
         setError('VIN must be exactly 17 characters.');
         return;
       }
       setError(null);
       setLoading(true);
       try {
         const data = await api.get<VinData>(`/api/vin/${trimmed}`);
         localStorage.setItem('rapp_vin', trimmed);
         localStorage.setItem('rapp_vin_data', JSON.stringify(data));
         router.push('/diagnose');
       } catch (err) {
         setError(err instanceof ApiError ? err.message : 'Could not decode VIN. Please try again.');
       } finally {
         setLoading(false);
       }
     };
     ```
   * Lines 87-95 contain the barcode button which is stubbed:
     ```tsx
     <button
       id="scan-barcode-btn"
       data-testid="scan-barcode-btn"
       className="btn btn-secondary"
       type="button"
       onClick={() => alert('Barcode scanner coming soon — enter VIN manually for now.')}
     >
       📷 Scan Barcode / QR
     </button>
     ```
3. **`frontend/src/app/diagnose/page.tsx`**:
   * Begins layout on line 31, currently starts with:
     ```tsx
     return (
       <main className="page">
         <header className="page-header">
           <p className="logo">⚙ RAPP</p>
           <h1 className="page-title">Diagnostic Input</h1>
     ```
   * No back navigation exists.
4. **`backend/main.py`**:
   * The `decode_vin_internal` function is defined starting on line 156:
     ```python
     async def decode_vin_internal(vin: str) -> dict[str, Any]:
         # Validate VIN format: exactly 17 alphanumeric characters
         if len(vin) != 17 or not vin.isalnum():
             raise HTTPException(
                 status_code=status.HTTP_400_BAD_REQUEST,
                 detail="Invalid VIN format. Must be exactly 17 alphanumeric characters."
             )

         url = f"{settings.nhtsa_base_url}/DecodeVin/{vin}?format=json"
     ```
5. **Testing suite**:
   * `poetry run pytest` (mapped to `./.venv/bin/pytest`) successfully executes 36 test cases in `tests/unit/test_api.py`, `tests/unit/test_challenge.py`, and `tests/unit/test_rag.py`.
   * The verification script `tests/verify_tests.sh` runs Playwright E2E tests against `tests/mock_app.py` for multiple cases (including injected failures).

---

## 2. Logic Chain
1. To introduce client-side OCR, we must first add `tesseract.js` to `frontend/package.json` so that Next.js can bundle and load it in the browser (Observation 1).
2. The manual barcode button in `frontend/src/app/page.tsx` needs to be linked to a file input trigger that reads images and invokes `tesseract.js` (Observation 2). Once the OCR scans the text, the code should extract the 17-character VIN sequence, populate the VIN input field, and let the user edit or click "Decode VIN" (Observation 2).
3. The cascading dropdowns will be modeled as a parallel ingestion path. Upon completion of cascading selection (Year -> Make -> Model), the submit action will construct a 17-character synthetic VIN starting with `SYN` matching the mapping specification. It will then populate `localStorage` with synthetic metadata and perform client-side routing to `/diagnose` (Observation 2).
4. Since the backend `decode_vin_internal` forwards all requests to the external NHTSA API (Observation 4), a synthetic VIN prefix check (`vin.startswith("SYN")`) is required at the entry of `decode_vin_internal` to parse locally mapped make/model values, bypass the NHTSA HTTP request entirely, and return the decoded specs directly.
5. In `/diagnose` page, adding a button that runs `router.push('/')` will resolve the missing back navigation issue (Observation 3).

---

## 3. Caveats
* **OCR Quality and CDNs**: Tesseract.js normally fetches worker files and language trained data from remote CDNs at runtime. If the user's browser lacks internet connectivity or blocks CDNs, the worker initialization might fail. A fallback mechanism or local hosting instructions for Tesseract workers should be considered.
* **Lowercase input**: The backend should normalize all VIN input to uppercase using `.upper()` before checking if it starts with `"SYN"`.
* **Playwright Mock App**: The script `tests/verify_tests.sh` runs Playwright tests against `tests/mock_app.py`, which is a python mock file. Changes made to real files (`backend/main.py` and `frontend/...`) won't be fully tested by the mock server unless the mock app is also kept in sync or a real-app E2E pipeline is run.

---

## 4. Conclusion
The implementation strategy is solid and fully supported by the codebase architecture. Adding `tesseract.js` to the package.json, coding the dropdown UI in `page.tsx`, updating the backend parser in `backend/main.py`, and integrating the back button in `/diagnose/page.tsx` will satisfy the requirements.

---

## 5. Remaining Work
1. Add `"tesseract.js": "^5.1.0"` to `frontend/package.json` and run `pnpm install` in `frontend/`.
2. Add Year/Make/Model cascading state and selects to `frontend/src/app/page.tsx`.
3. Add photo capture hidden input and Tesseract.js scan logic to `frontend/src/app/page.tsx`.
4. Update `decode_vin_internal` in `backend/main.py` with the `SYN` prefix parser.
5. Add the "Back" button to `frontend/src/app/diagnose/page.tsx`.
6. Verify unit tests via `./.venv/bin/pytest` and write a new unit test for synthetic VINs.
7. Verify E2E via `npx playwright test`.

---

## 6. Verification Method
* **Unit Tests**:
  Run `./.venv/bin/pytest` to verify python backend tests pass.
* **Frontend Compilation**:
  Run `pnpm build` in the `frontend` directory to ensure compilation succeeds with zero TypeScript/lint errors.
* **E2E verification**:
  Run `npx playwright test` to run the E2E flow.
