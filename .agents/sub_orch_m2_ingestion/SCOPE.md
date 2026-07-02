# Scope: Milestone 2 - Home Page & Navigation Evolution (R1, R6)

## Objective
Implement Year/Make/Model cascading selector, OCR-based VIN scanner, update home page layout, and add back navigation from `/diagnose` to `/`.

## Files to Read/Modify
- `frontend/package.json` (add `tesseract.js` to dependencies)
- `frontend/src/app/page.tsx` (rewrite to include Year/Make/Model dropdown, photo capture with Tesseract.js OCR, and update layout)
- `frontend/src/app/diagnose/page.tsx` (add back navigation button to `/`)
- `backend/main.py` (modify `decode_vin_internal` to support parsing synthetic VINs starting with `SYN`)

## Detailed Requirements

### 1. Year/Make/Model Selector (R1)
- Add a cascading 3-step dropdown: Year (2015-2026) -> Make (HONDA, TOYOTA, FORD, LEXUS, CHEVROLET) -> Model (CIVIC, ACCORD, CAMRY, COROLLA, F-150, RX350, SILVERADO).
- On final selection, construct a synthetic 17-character alphanumeric VIN using the pattern:
  `SYN` + `YY` (2-digit year) + `MAKE_CODE` (5 chars) + `MODEL_CODE` (7 chars)
- Synthetic code mapping:
  - Makes: `HONDA` -> `HONDA`, `TOYOTA` -> `TOYOT`, `FORD` -> `FORDX`, `LEXUS` -> `LEXUS`, `CHEVROLET` -> `CHEVR`
  - Models: `CIVIC` -> `CIVICXX`, `ACCORD` -> `ACCORDX`, `F-150` -> `F150XXX`, `CAMRY` -> `CAMRYXX`, `COROLLA` -> `COROLLA`, `RX350` -> `RX350XX`, `SILVERADO` -> `SILVERA`
- Store `rapp_vin` (synthetic VIN) and `rapp_vin_data` (decoded JSON object with `year`, `make`, `model`, `engine`, `drive_type`) in `localStorage` on submit, then navigate to `/diagnose`.
  - Honda: Engine: "1.5L 4-Cylinder", Drive: "FWD"
  - Toyota: Engine: "2.5L 4-Cylinder", Drive: "FWD"
  - Ford: Engine: "3.5L V6", Drive: "AWD"
  - Lexus: Engine: "3.5L V6", Drive: "AWD"
  - Chevrolet: Engine: "5.3L V8", Drive: "AWD"

### 2. VIN Photo Capture via OCR (R1)
- Add a photo capture/file picker button.
- Integrate `tesseract.js` client-side to run OCR on the selected image, extract the first 17-character alphanumeric string that looks like a VIN, and populate the input field.
- Ensure the user can edit/confirm the text before submission.

### 3. Backend Synthetic VIN Support
- Update `decode_vin_internal` in `backend/main.py`:
  - If `vin` starts with `SYN`, parse the `YY` year, `MAKE_CODE`, and `MODEL_CODE` using reverse mapping.
  - Return the decoded dictionary directly, skipping the NHTSA API call.

### 4. Back Navigation (R6)
- Add a back button in `/diagnose` (top-left) that routes to `/`.

## Completion Criteria
1. Standard VIN entry works and navigates to `/diagnose`.
2. Y/M/M selector works and navigates to `/diagnose`.
3. Photo selector extracts VIN and populates input.
4. Back button on `/diagnose` returns to `/`.
5. Frontend compiles successfully with zero TypeScript or lint errors.
