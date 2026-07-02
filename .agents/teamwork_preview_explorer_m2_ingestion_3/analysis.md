# Milestone 2 Investigation & Implementation Strategy Report

This report outlines the findings and detailed strategy for the implementation of the Home Page & Navigation Evolution (Milestone 2) in the RAPP codebase.

---

## 1. Overview of Key Findings
* **Frontend Setup**: The frontend uses Next.js 14 (App Router) and `pnpm`. There is currently no `tesseract.js` dependency in `frontend/package.json`.
* **Home Page UI (`frontend/src/app/page.tsx`)**: Displays a dark-themed card containing a single text input for VIN manual entry, a submit button, and a mock barcode scanner button. Transitions straight to `/diagnose` upon successfully querying the backend API.
* **Diagnose Page UI (`frontend/src/app/diagnose/page.tsx`)**: Displays vehicle metadata read from `localStorage` (`rapp_vin`, `rapp_vin_data`), has a textarea for symptoms, checkboxes for available garage tools, and a button to submit. It does not currently contain a back navigation button.
* **Backend VIN Decoding (`backend/main.py`)**: The `decode_vin_internal` function currently performs validation on input string length and characters, then forwards the VIN to the NHTSA vPIC API. It has no local override for synthetic (mock) VINs.

---

## 2. Codebase Investigation Summary

### 2.1 Dependency Configuration (`frontend/package.json`)
The dependencies are configured under standard NPM fields. Currently:
* `react`: `^18`
* `next`: `14.2.35`
We must append `"tesseract.js": "^5.1.0"` to the `"dependencies"` block.

### 2.2 Home Page Structure (`frontend/src/app/page.tsx`)
* **State Management**: Uses `vin`, `loading`, and `error` state.
* **Navigation Logic**: Submits to `/api/vin/${trimmed}` via custom API library (`src/lib/api.ts`). Upon receiving data, it saves:
  * `localStorage.setItem('rapp_vin', trimmed)`
  * `localStorage.setItem('rapp_vin_data', JSON.stringify(data))`
  * `router.push('/diagnose')`
* **Layout**: Uses CSS classes `page`, `page-header`, `card`, `input`, `btn`, `btn-primary`, and `btn-secondary`.

### 2.3 Diagnose Page Structure (`frontend/src/app/diagnose/page.tsx`)
* **Layout**: Displays a `.vin-strip` containing year, make, and model information.
* **Navigation Logic**: Validates symptoms, saves them to `localStorage`, and routes to `/results`.
* **Missing Navigation**: No back button. We need to import `useRouter` and add a back button.

### 2.4 Backend VIN Decoding (`backend/main.py`)
* The entry point is `/api/vin/{vin}` which calls `decode_vin_internal(vin)`.
* It expects a 17-character alphanumeric string. If it fails this check, it returns HTTP 400.
* It performs a real HTTP call to `https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/...` which fails/stubs out for fake synthetic VINs.

---

## 3. Implementation Strategy

### 3.1 Cascading 3-Step Dropdown (R1)
To allow selection without a real VIN, we will add a tabbed toggle or form section to the home page:
1. **Toggle Switch**: User can choose between "Manually Enter / Scan VIN" and "Select Year/Make/Model".
2. **Options definitions**:
   * **Years**: `2015` to `2026`.
   * **Makes**: `HONDA`, `TOYOTA`, `FORD`, `LEXUS`, `CHEVROLET`.
   * **Models per Make**:
     * `HONDA` -> `CIVIC`, `ACCORD`
     * `TOYOTA` -> `CAMRY`, `COROLLA`
     * `FORD` -> `F-150`
     * `LEXUS` -> `RX350`
     * `CHEVROLET` -> `SILVERADO`
3. **Dropdown Controls**:
   * Dropdowns will use the `select` element styled with the standard `.input` class.
   * "Make" dropdown is disabled until "Year" is chosen.
   * "Model" dropdown is disabled until "Make" is chosen.
   * Selecting a parent level resets the child level selections.

### 3.2 Synthetic VIN Generation & LocalStorage Persistence
Upon clicking the submit button for the Year/Make/Model flow:
1. **Extract Year Prefix**: Convert year to 2-digit format (`yy = String(selectedYear).slice(-2)`).
2. **Retrieve Make & Model Codes**:
   * **Makes**: `HONDA` -> `HONDA`, `TOYOTA` -> `TOYOT`, `FORD` -> `FORDX`, `LEXUS` -> `LEXUS`, `CHEVROLET` -> `CHEVR`
   * **Models**: `CIVIC` -> `CIVICXX`, `ACCORD` -> `ACCORDX`, `F-150` -> `F150XXX`, `CAMRY` -> `CAMRYXX`, `COROLLA` -> `COROLLA`, `RX350` -> `RX350XX`, `SILVERADO` -> `SILVERA`
3. **Construct 17-character Synthetic VIN**:
   * Pattern: `SYN` (3 chars) + `yy` (2 chars) + `MAKE_CODE` (5 chars) + `MODEL_CODE` (7 chars).
   * Example: `SYN22HONDACIVICXX` for 2022 Honda Civic.
4. **Decoded Data Mappings**:
   * Honda: Engine: "1.5L 4-Cylinder", Drive: "FWD"
   * Toyota: Engine: "2.5L 4-Cylinder", Drive: "FWD"
   * Ford: Engine: "3.5L V6", Drive: "AWD"
   * Lexus: Engine: "3.5L V6", Drive: "AWD"
   * Chevrolet: Engine: "5.3L V8", Drive: "AWD"
5. **Persistence**: Store `rapp_vin` and `rapp_vin_data` in `localStorage` exactly like standard VIN decoding:
   ```json
   {
     "vin": "SYN22HONDACIVICXX",
     "year": 2022,
     "make": "HONDA",
     "model": "CIVIC",
     "engine": "1.5L 4-Cylinder",
     "drive_type": "FWD"
   }
   ```
6. **Navigation**: Perform `router.push('/diagnose')`.

### 3.3 Client-Side OCR via Tesseract.js (R1)
1. **File Input element**: Add a hidden `<input type="file" accept="image/*" ref={fileInputRef} onChange={handleFileChange} />`.
2. **Trigger Button**: Replace/update the `scan-barcode-btn` action to trigger `fileInputRef.current.click()`.
3. **Tesseract.js OCR execution**:
   * In the change handler, extract the selected image file.
   * Call `Tesseract.recognize(file, 'eng')`.
   * Extract the resulting text, strip whitespaces and newlines, and check for the first sequence of 17 alphanumeric characters.
   * Populate the VIN text input field with the detected string to allow user confirmation/editing.
   * Display appropriate error messages if OCR fails or if no 17-character alphanumeric string is found.

### 3.4 Backend Synthetic VIN Support (`backend/main.py`)
Update `decode_vin_internal` to inspect the prefix:
```python
# In backend/main.py:decode_vin_internal
vin_upper = vin.upper()
if vin_upper.startswith("SYN"):
    # 1. Extract YY and build Year
    yy_str = vin_upper[3:5]
    try:
        year = 2000 + int(yy_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid synthetic VIN year digits")
    
    # 2. Decode Make Code
    make_code = vin_upper[5:10]
    make_mapping = {
        "HONDA": "HONDA",
        "TOYOT": "TOYOTA",
        "FORDX": "FORD",
        "LEXUS": "LEXUS",
        "CHEVR": "CHEVROLET"
    }
    make = make_mapping.get(make_code)
    if not make:
        raise HTTPException(status_code=400, detail="Invalid synthetic VIN make code")
        
    # 3. Decode Model Code
    model_code = vin_upper[10:17]
    model_mapping = {
        "CIVICXX": "CIVIC",
        "ACCORDX": "ACCORD",
        "F150XXX": "F-150",
        "CAMRYXX": "CAMRY",
        "COROLLA": "COROLLA",
        "RX350XX": "RX350",
        "SILVERA": "SILVERADO"
    }
    model = model_mapping.get(model_code)
    if not model:
        raise HTTPException(status_code=400, detail="Invalid synthetic VIN model code")
        
    # 4. Map spec dictionary (Bypass NHTSA call)
    spec_mapping = {
        "HONDA": {"engine": "1.5L 4-Cylinder", "drive_type": "FWD"},
        "TOYOTA": {"engine": "2.5L 4-Cylinder", "drive_type": "FWD"},
        "FORD": {"engine": "3.5L V6", "drive_type": "AWD"},
        "LEXUS": {"engine": "3.5L V6", "drive_type": "AWD"},
        "CHEVROLET": {"engine": "5.3L V8", "drive_type": "AWD"}
    }
    specs = spec_mapping[make]
    
    return {
        "year": year,
        "make": make,
        "model": model,
        "engine": specs["engine"],
        "drive_type": specs["drive_type"]
    }
```

### 3.5 Back Button Navigation in `/diagnose` (R6)
Add a back button styled at the top-left of the diagnose screen layout:
```tsx
// Inside frontend/src/app/diagnose/page.tsx
<button
  onClick={() => router.push('/')}
  className="btn btn-secondary"
  style={{ width: 'auto', alignSelf: 'flex-start', marginBottom: '20px' }}
>
  ← Back
</button>
```

---

## 4. Verification Methods

### 4.1 Unit Testing Strategy
* Create new unit tests in `tests/unit/test_api.py` targeting the `/api/vin/{vin}` endpoint with synthetic inputs (e.g. `SYN22HONDACIVICXX`).
* Assert that:
  1. Status code is 200.
  2. Output dictionary contains correct year (`2022`), make (`HONDA`), model (`CIVIC`), engine (`1.5L 4-Cylinder`), and drive type (`FWD`).
  3. Real NHTSA call is bypassed (not called/mocked).
  4. Invalid synthetic VIN components (e.g. invalid make or model code) result in a 400 Bad Request error.

### 4.2 End-to-End Verification Strategy
* Run E2E tests using Playwright: `npx playwright test`.
* Create a new E2E test case in `tests/e2e-mvp-flow.spec.ts` that:
  1. Interacts with the home page.
  2. Selects 2022 -> Honda -> Civic.
  3. Triggers submission.
  4. Asserts that the page transitions to `/diagnose`.
  5. Verifies that the correct VIN (`SYN22HONDACIVICXX`), Year (`2022`), Make (`HONDA`), and Model (`CIVIC`) are shown in the diagnostic info strip.
  6. Clicks the "Back" button and verifies that the page transitions back to `/`.
