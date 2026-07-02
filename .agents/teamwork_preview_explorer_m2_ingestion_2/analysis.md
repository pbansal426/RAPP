# Analysis: Milestone 2 - Home Page & Navigation Evolution (R1, R6)

## Summary of Findings
Milestone 2 targets enhancements in vehicle identification and navigation:
1. **Year/Make/Model Cascading Dropdowns**: To allow manual vehicle profiling, bypassing API-based VIN lookups. When Year is selected, Make options become available. When Make is selected, Model options become available. Submission constructs a synthetic 17-character VIN (`SYN` + `YY` + `MAKE_CODE` + `MODEL_CODE`), saves it and its properties in `localStorage`, and routes to `/diagnose`.
2. **Client-side OCR via Tesseract.js**: To extract a 17-character VIN from a file picker or photo capture. The extracted text populates the input box to allow editing and confirmation.
3. **Backend Support for Synthetic VINs**: To bypass the NHTSA API check for any VIN prefixed with `SYN`, parse the parameters using reverse mapping, and directly return the corresponding static mock details (`year`, `make`, `model`, `engine`, `drive_type`).
4. **Navigation**: Addition of a back navigation button in `/diagnose` that routes the user back to the home page `/`.

---

## 1. File Modification Blueprints

### A. `frontend/package.json`
Add `tesseract.js` (recommended version `^5.1.0`) to the dependencies.

```json
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "next": "14.2.35",
    "tesseract.js": "^5.1.0"
  }
```

### B. `frontend/src/app/page.tsx`
We will rewrite `frontend/src/app/page.tsx` to add:
- Dynamic import of `tesseract.js` (to safeguard against server-side rendering/compilation errors).
- Ref for hidden file input to trigger image selection.
- Handlers for File Input change, running OCR, filtering a 17-character alphanumeric string, and displaying it in the text field.
- Dual options/cards: "VIN Ingestion (Manual or Scan)" and "Manual Selection (Cascading Dropdowns)".
- The cascading state-handlers for Year, Make, and Model.

#### Proposed Implementation Code

```tsx
'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';

interface VinData {
  vin: string;
  year: number | string | null;
  make: string;
  model: string;
  engine: string;
  drive_type: string;
}

const YEARS = Array.from({ length: 2026 - 2015 + 1 }, (_, i) => String(2015 + i));

const MAKE_DATA: Record<string, { code: string; models: string[]; engine: string; drive_type: string }> = {
  HONDA: { code: 'HONDA', models: ['CIVIC', 'ACCORD'], engine: '1.5L 4-Cylinder', drive_type: 'FWD' },
  TOYOTA: { code: 'TOYOT', models: ['CAMRY', 'COROLLA'], engine: '2.5L 4-Cylinder', drive_type: 'FWD' },
  FORD: { code: 'FORDX', models: ['F-150'], engine: '3.5L V6', drive_type: 'AWD' },
  LEXUS: { code: 'LEXUS', models: ['RX350'], engine: '3.5L V6', drive_type: 'AWD' },
  CHEVROLET: { code: 'CHEVR', models: ['SILVERADO'], engine: '5.3L V8', drive_type: 'AWD' },
};

const MODEL_CODES: Record<string, string> = {
  CIVIC: 'CIVICXX',
  ACCORD: 'ACCORDX',
  CAMRY: 'CAMRYXX',
  COROLLA: 'COROLLA',
  'F-150': 'F150XXX',
  RX350: 'RX350XX',
  SILVERADO: 'SILVERA',
};

export default function HomePage() {
  const router = useRouter();
  
  // VIN state
  const [vin, setVin] = useState('');
  const [loading, setLoading] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Dropdown state
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedMake, setSelectedMake] = useState('');
  const [selectedModel, setSelectedModel] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Handle standard/OCR VIN submission
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

  // OCR Processing
  const handleOcrClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setOcrLoading(true);
    setError(null);
    try {
      const Tesseract = await import('tesseract.js');
      const { data: { text } } = await Tesseract.recognize(file, 'eng');
      
      // Clean string by removing whitespace, underscores, and hyphens
      const cleaned = text.replace(/[\s\-_]/g, '').toUpperCase();
      const match = cleaned.match(/[A-Z0-9]{17}/);
      
      if (match) {
        setVin(match[0]);
        setError(null);
      } else {
        setError('Could not find a 17-character VIN in the image. Please enter manually.');
      }
    } catch (err) {
      setError('OCR failed to parse the image.');
    } finally {
      setOcrLoading(false);
    }
  };

  // Handle Manual Dropdown Selection Submission
  const handleDropdownSubmit = () => {
    if (!selectedYear || !selectedMake || !selectedModel) {
      setError('Please select all fields.');
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const yy = selectedYear.slice(-2);
      const makeCode = MAKE_DATA[selectedMake].code;
      const modelCode = MODEL_CODES[selectedModel];
      const syntheticVin = `SYN${yy}${makeCode}${modelCode}`;

      const decodedData = {
        year: Number(selectedYear),
        make: selectedMake,
        model: selectedModel,
        engine: MAKE_DATA[selectedMake].engine,
        drive_type: MAKE_DATA[selectedMake].drive_type,
      };

      localStorage.setItem('rapp_vin', syntheticVin);
      localStorage.setItem('rapp_vin_data', JSON.stringify(decodedData));
      router.push('/diagnose');
    } catch (err) {
      setError('Failed to save vehicle details.');
    } finally {
      setLoading(false);
    }
  };

  const makes = Object.keys(MAKE_DATA);
  const models = selectedMake ? MAKE_DATA[selectedMake].models : [];

  return (
    <main className="page">
      <header className="page-header">
        <p className="logo">⚙ RAPP</p>
        <h1 className="page-title">Vehicle Repair &amp;<br />Modification AI Engine</h1>
        <p className="page-subtitle">Identify your vehicle using one of the methods below.</p>
      </header>

      {error && (
        <div role="alert" style={{ color: 'var(--accent-red)', fontSize: '0.9rem', marginBottom: 16, textAlign: 'center', fontWeight: 'bold' }}>
          {error}
        </div>
      )}

      {/* Option 1: VIN Identification */}
      <div className="card">
        <p className="card-label">Option A — Identification via VIN</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <label htmlFor="vin-input" className="sr-only">Vehicle Identification Number (VIN)</label>
          <input
            id="vin-input"
            data-testid="vin-input"
            className="input"
            type="text"
            placeholder="Enter 17-character VIN"
            value={vin}
            maxLength={17}
            autoCapitalize="characters"
            spellCheck={false}
            onChange={(e) => setVin(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            aria-describedby={error ? 'vin-error' : undefined}
          />

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 4 }}>
            <button
              id="submit-vin-btn"
              data-testid="submit-vin-btn"
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={loading || ocrLoading}
              aria-busy={loading}
            >
              {loading ? <><span className="loading-spinner" aria-hidden="true" /> Decoding VIN…</> : '→ Decode VIN'}
            </button>

            <button
              id="scan-barcode-btn"
              data-testid="scan-barcode-btn"
              className="btn btn-secondary"
              type="button"
              onClick={handleOcrClick}
              disabled={loading || ocrLoading}
            >
              {ocrLoading ? <><span className="loading-spinner" aria-hidden="true" /> Scanning...</> : '📷 Scan VIN from Photo'}
            </button>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept="image/*"
              style={{ display: 'none' }}
              data-testid="ocr-file-input"
            />
          </div>
        </div>
      </div>

      {/* Option 2: Cascading Dropdowns */}
      <div className="card">
        <p className="card-label">Option B — Identification via Dropdowns</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          
          {/* Year Dropdown */}
          <div>
            <select
              id="year-select"
              data-testid="year-select"
              className="input"
              value={selectedYear}
              onChange={(e) => {
                setSelectedYear(e.target.value);
                setSelectedMake('');
                setSelectedModel('');
              }}
            >
              <option value="">Select Year</option>
              {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>

          {/* Make Dropdown */}
          <div>
            <select
              id="make-select"
              data-testid="make-select"
              className="input"
              value={selectedMake}
              onChange={(e) => {
                setSelectedMake(e.target.value);
                setSelectedModel('');
              }}
              disabled={!selectedYear}
            >
              <option value="">Select Make</option>
              {makes.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>

          {/* Model Dropdown */}
          <div>
            <select
              id="model-select"
              data-testid="model-select"
              className="input"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={!selectedMake}
            >
              <option value="">Select Model</option>
              {models.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>

          <button
            id="submit-dropdown-btn"
            data-testid="submit-dropdown-btn"
            className="btn btn-primary"
            onClick={handleDropdownSubmit}
            disabled={loading || ocrLoading || !selectedYear || !selectedMake || !selectedModel}
            style={{ marginTop: 4 }}
          >
            → Confirm Vehicle Selection
          </button>
        </div>
      </div>

      <p className="text-muted text-sm" style={{ textAlign: 'center', marginTop: 16 }}>
        Your VIN is on your dashboard (driver side), door sticker, or registration.
      </p>
    </main>
  );
}
```

---

### C. `frontend/src/app/diagnose/page.tsx`
Add a back button at the top-left of `/diagnose`. We will position it nicely above the title.

```tsx
// Inside DiagnosePage return before the header or inside the header:
  return (
    <main className="page">
      <div style={{ marginBottom: 16 }}>
        <button
          onClick={() => router.push('/')}
          className="btn btn-secondary"
          style={{ width: 'auto', minHeight: 40, height: 40, padding: '0 16px' }}
          data-testid="back-btn"
        >
          ← Back to Vehicle Identification
        </button>
      </div>

      <header className="page-header">
        <p className="logo">⚙ RAPP</p>
        <h1 className="page-title">Diagnostic Input</h1>
        <p className="page-subtitle">Tell us what&apos;s wrong and what tools you have.</p>
      </header>
...
```

---

### D. `backend/main.py`
Update `decode_vin_internal` to check if `vin` starts with `SYN` (case-insensitive). If it does:
1. Extract `YY` year, `MAKE_CODE` (5 chars), and `MODEL_CODE` (7 chars) from the string.
2. Resolve `YY` -> `year = 2000 + int(yy)` (handling ValueError gracefully).
3. Resolve `MAKE_CODE` using a reverse-mapping dictionary:
   - `HONDA` -> `HONDA`
   - `TOYOT` -> `TOYOTA`
   - `FORDX` -> `FORD`
   - `LEXUS` -> `LEXUS`
   - `CHEVR` -> `CHEVROLET`
4. Resolve `MODEL_CODE` using a reverse-mapping dictionary:
   - `CIVICXX` -> `CIVIC`
   - `ACCORDX` -> `ACCORD`
   - `CAMRYXX` -> `CAMRY`
   - `COROLLA` -> `COROLLA`
   - `F150XXX` -> `F-150`
   - `RX350XX` -> `RX350`
   - `SILVERA` -> `SILVERADO`
5. Assign engine and drive types directly:
   - HONDA: Engine: `"1.5L 4-Cylinder"`, Drive: `"FWD"`
   - TOYOTA: Engine: `"2.5L 4-Cylinder"`, Drive: `"FWD"`
   - FORD: Engine: `"3.5L V6"`, Drive: `"AWD"`
   - LEXUS: Engine: `"3.5L V6"`, Drive: `"AWD"`
   - CHEVROLET: Engine: `"5.3L V8"`, Drive: `"AWD"`
6. Bypass the HTTP requests to NHTSA API.

#### Proposed Code

```python
async def decode_vin_internal(vin: str) -> dict[str, Any]:
    # Validate VIN format: exactly 17 alphanumeric characters
    if len(vin) != 17 or not vin.isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid VIN format. Must be exactly 17 alphanumeric characters."
        )

    vin_upper = vin.upper()
    if vin_upper.startswith("SYN"):
        # Synthetic VIN structure: SYN + YY (2 chars) + MAKE_CODE (5 chars) + MODEL_CODE (7 chars)
        yy = vin_upper[3:5]
        make_code = vin_upper[5:10]
        model_code = vin_upper[10:17]

        try:
            year = 2000 + int(yy)
        except ValueError:
            year = f"20{yy}"

        make_map = {
            "HONDA": "HONDA",
            "TOYOT": "TOYOTA",
            "FORDX": "FORD",
            "LEXUS": "LEXUS",
            "CHEVR": "CHEVROLET"
        }

        model_map = {
            "CIVICXX": "CIVIC",
            "ACCORDX": "ACCORD",
            "CAMRYXX": "CAMRY",
            "COROLLA": "COROLLA",
            "F150XXX": "F-150",
            "RX350XX": "RX350",
            "SILVERA": "SILVERADO"
        }

        make = make_map.get(make_code)
        model = model_map.get(model_code)

        if not make or not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Synthetic VIN codes not recognized."
            )

        engines = {
            "HONDA": "1.5L 4-Cylinder",
            "TOYOTA": "2.5L 4-Cylinder",
            "FORD": "3.5L V6",
            "LEXUS": "3.5L V6",
            "CHEVROLET": "5.3L V8"
        }

        drives = {
            "HONDA": "FWD",
            "TOYOTA": "FWD",
            "FORD": "AWD",
            "LEXUS": "AWD",
            "CHEVROLET": "AWD"
        }

        return {
            "year": year,
            "make": make,
            "model": model,
            "engine": engines.get(make, "Unknown"),
            "drive_type": drives.get(make, "Unknown")
        }

    # Standard NHTSA API resolution path
    url = f"{settings.nhtsa_base_url}/DecodeVin/{vin}?format=json"
    ...
```

---

## 2. Test Integration Strategies

### Unit Tests (`tests/unit/test_api.py`)
Add direct assertions verifying synthetic VIN decoding bypasses external endpoints and produces exact payload dictionaries:

```python
def test_synthetic_vin_decoding_success(client):
    # Test Toyota synthetic decoding
    response = client.get("/api/vin/SYN24TOYOTCAMRYXX")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2024
    assert data["make"] == "TOYOTA"
    assert data["model"] == "CAMRY"
    assert data["engine"] == "2.5L 4-Cylinder"
    assert data["drive_type"] == "FWD"

    # Test Honda synthetic decoding
    response = client.get("/api/vin/SYN15HONDACIVICXX")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2015
    assert data["make"] == "HONDA"
    assert data["model"] == "CIVIC"
    assert data["engine"] == "1.5L 4-Cylinder"
    assert data["drive_type"] == "FWD"

def test_synthetic_vin_decoding_invalid_codes(client):
    # Invalid Model Code
    response = client.get("/api/vin/SYN24TOYOTWRONGGG")
    assert response.status_code == 404
```

### End-to-End Tests (`tests/e2e-mvp-flow.spec.ts`)
We will add new Playwright test cases checking the Year/Make/Model selectors, OCR, and the Back Button:

```typescript
  test('Step 1 (Manual): Cascading Dropdowns Identification', async ({ page }) => {
    await page.goto('/');

    const yearSelect = page.locator('[data-testid="year-select"]');
    const makeSelect = page.locator('[data-testid="make-select"]');
    const modelSelect = page.locator('[data-testid="model-select"]');
    const submitDropdownBtn = page.locator('[data-testid="submit-dropdown-btn"]');

    // Initially Make and Model and Submit button must be disabled or empty options
    await expect(makeSelect).toBeDisabled();
    await expect(modelSelect).toBeDisabled();
    await expect(submitDropdownBtn).toBeDisabled();

    // Select Year
    await yearSelect.selectOption('2024');
    await expect(makeSelect).toBeEnabled();

    // Select Make
    await makeSelect.selectOption('TOYOTA');
    await expect(modelSelect).toBeEnabled();

    // Select Model
    await modelSelect.selectOption('CAMRY');
    await expect(submitDropdownBtn).toBeEnabled();

    // Submit selection
    await submitDropdownBtn.click();

    // Transition to /diagnose and verify state
    await expect(page).toHaveURL(/\/diagnose/);
    const vinText = await page.evaluate(() => localStorage.getItem('rapp_vin'));
    expect(vinText).toBe('SYN24TOYOTCAMRYXX');
  });

  test('Step 2 (Navigation): Back Button from /diagnose to /', async ({ page }) => {
    // Navigate directly to diagnose with a preset vin
    await page.goto('/');
    await page.evaluate(() => localStorage.setItem('rapp_vin', 'SYN24TOYOTCAMRYXX'));
    await page.goto('/diagnose');

    const backBtn = page.locator('[data-testid="back-btn"]');
    await expect(backBtn).toBeVisible();
    await backBtn.click();

    await expect(page).toHaveURL(/\/$/); // Back to root homepage
  });
```

---

## 3. Compliance and Clean Build Checks
- **No external network queries**: Ensure no network requests run during test suite verification except local loopbacks. Tesseract OCR runs fully local/client-side using static WASM wrappers or locally downloaded resources. Note: To prevent dynamic downloading of Tesseract langfiles/WASM at test execution time in CODE_ONLY network mode, the implementer can configure Tesseract to use local worker paths or mock OCR responses during CI/CD.
- **Strict Linting**: Build the typescript target (`pnpm build` in `frontend/`) and lint the Python files using `make lint` before finalizing.
- **Directory structures**: Maintain all source files inside `/frontend` and `/backend` strictly, avoiding creation of runtime files inside `/tests` or `.agents`.
