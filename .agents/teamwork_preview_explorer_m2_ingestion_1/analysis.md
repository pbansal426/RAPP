# Milestone 2 (Home Page & Navigation Evolution) Ingestion Analysis

This report presents findings from the investigation of the RAPP codebase regarding the integration of a Year/Make/Model cascading selector, client-side OCR for VIN extraction, backend synthetic VIN decoding, and navigation back from the diagnosis page.

---

## 1. Detailed Findings & File Structure

### 1.1 Dependency Configuration (`frontend/package.json`)
The frontend uses standard React 18 / Next.js 14 setup.
- **Path**: `frontend/package.json`
- **Dependencies**: React `^18`, React-DOM `^18`, Next `14.2.35`.
- **Requirements**: `tesseract.js` needs to be added under `dependencies` as `"tesseract.js": "^5.1.0"`.

### 1.2 Home Page Layout & Logic (`frontend/src/app/page.tsx`)
- **Path**: `frontend/src/app/page.tsx`
- **Current State**:
  - Contains a single dark mode layout (`main.page` class) with a card holding a `vin-input` and buttons `submit-vin-btn` and `scan-barcode-btn`.
  - The `scan-barcode-btn` has an alert stub: `"Barcode scanner coming soon..."`.
- **Target Changes**:
  - Integrate `tesseract.js` for OCR scanning on image uploads.
  - Implement a method toggle at the card top: "Use VIN" vs "Select Vehicle".
  - Build a cascading 3-step dropdown: Year -> Make -> Model, which dynamically filters the next selector based on the previous selection.
  - Support synthetic VIN generation using the pattern `SYN` + `YY` (last 2 digits of year) + `MAKE_CODE` (5 chars) + `MODEL_CODE` (7 chars) on selector form submission.

### 1.3 Diagnosis Page Layout & Logic (`frontend/src/app/diagnose/page.tsx`)
- **Path**: `frontend/src/app/diagnose/page.tsx`
- **Current State**:
  - Displays step 2 card with symptoms text area and garage tools check list.
  - Navigates to `/results` on submit.
  - Currently has NO back button.
- **Target Changes**:
  - Add a "← Back" button at the top-left of the page that routes back to `/`.

### 1.4 Backend API & VIN Decoding (`backend/main.py`)
- **Path**: `backend/main.py`
- **Current State**:
  - `decode_vin_internal(vin: str)` validates that length is 17 and `vin.isalnum()`.
  - Communicates directly with NHTSA API using `https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json`.
- **Target Changes**:
  - Update `decode_vin_internal` to check if `vin.startswith("SYN")`.
  - If `vin` starts with `SYN`, bypass NHTSA call, parse `YY` (indices 3-5), `MAKE_CODE` (indices 5-10), and `MODEL_CODE` (indices 10-17).
  - Reverse map codes to full text names and specific specs:
    - HONDA: Engine: "1.5L 4-Cylinder", Drive: "FWD"
    - TOYOTA: Engine: "2.5L 4-Cylinder", Drive: "FWD"
    - FORD: Engine: "3.5L V6", Drive: "AWD"
    - LEXUS: Engine: "3.5L V6", Drive: "AWD"
    - CHEVROLET: Engine: "5.3L V8", Drive: "AWD"
  - Return the parsed dictionary structure immediately.

---

## 2. Detailed Implementation Strategy

### 2.1 Proposed `frontend/package.json` Modification
Add `"tesseract.js": "^5.1.0"` to the dependencies dictionary:
```json
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "next": "14.2.35",
    "tesseract.js": "^5.1.0"
  },
```

### 2.2 Proposed `frontend/src/app/page.tsx` Implementation
Rewrite `page.tsx` to handle method toggles, OCR processing via Tesseract, cascading selectors, and synthetic VIN formulation.
Below is the precise before/after logic structure:

#### Before (Lines 1-40):
```typescript
'use client';

import { useState } from 'react';
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

export default function HomePage() {
  const router = useRouter();
  const [vin, setVin] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

#### After Proposal:
```typescript
'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';
import Tesseract from 'tesseract.js';

interface VinData {
  vin: string;
  year: number | string | null;
  make: string;
  model: string;
  engine: string;
  drive_type: string;
}

const YEARS = Array.from({ length: 2026 - 2015 + 1 }, (_, i) => String(2026 - i));
const MAKES = ['HONDA', 'TOYOTA', 'FORD', 'LEXUS', 'CHEVROLET'];
const MODELS_BY_MAKE: Record<string, string[]> = {
  HONDA: ['CIVIC', 'ACCORD'],
  TOYOTA: ['CAMRY', 'COROLLA'],
  FORD: ['F-150'],
  LEXUS: ['RX350'],
  CHEVROLET: ['SILVERADO'],
};

const MAKE_CODES: Record<string, string> = {
  HONDA: 'HONDA',
  TOYOTA: 'TOYOT',
  FORD: 'FORDX',
  LEXUS: 'LEXUS',
  CHEVROLET: 'CHEVR',
};

const MODEL_CODES: Record<string, string> = {
  CIVIC: 'CIVICXX',
  ACCORD: 'ACCORDX',
  'F-150': 'F150XXX',
  CAMRY: 'CAMRYXX',
  COROLLA: 'COROLLA',
  RX350: 'RX350XX',
  SILVERADO: 'SILVERA',
};

export default function HomePage() {
  const router = useRouter();
  const [vin, setVin] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Selector states
  const [method, setMethod] = useState<'vin' | 'dropdown'>('vin');
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedMake, setSelectedMake] = useState('');
  const [selectedModel, setSelectedModel] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleOcr = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const { data: { text } } = await Tesseract.recognize(file, 'eng');
      const words = text.split(/\s+/);
      let foundVin = '';
      for (const word of words) {
        const cleanWord = word.replace(/[^A-Za-z0-9]/g, '').toUpperCase();
        if (cleanWord.length === 17) {
          foundVin = cleanWord;
          break;
        }
      }
      if (!foundVin) {
        const allCleaned = text.replace(/[^A-Za-z0-9]/g, '').toUpperCase();
        const match = allCleaned.match(/[A-Z0-9]{17}/);
        if (match) {
          foundVin = match[0];
        }
      }
      if (foundVin) {
        setVin(foundVin);
      } else {
        setError('No 17-character alphanumeric VIN found in image. Please try again or enter it manually.');
      }
    } catch (err) {
      setError('OCR recognition failed. Please try again or enter it manually.');
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDropdownSubmit = async () => {
    if (!selectedYear || !selectedMake || !selectedModel) {
      setError('Please select Year, Make, and Model.');
      return;
    }
    setError(null);
    setLoading(true);

    const yy = selectedYear.slice(-2);
    const makeCode = MAKE_CODES[selectedMake];
    const modelCode = MODEL_CODES[selectedModel];
    const syntheticVin = `SYN${yy}${makeCode}${modelCode}`;

    try {
      const data = await api.get<VinData>(`/api/vin/${syntheticVin}`);
      localStorage.setItem('rapp_vin', syntheticVin);
      localStorage.setItem('rapp_vin_data', JSON.stringify(data));
      router.push('/diagnose');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not decode synthetic VIN. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Rendering conditional DOM (using Playwright ids 'vin-input', 'scan-barcode-btn', 'submit-vin-btn' in default 'vin' state to ensure backwards compatibility)
```

### 2.3 Proposed `/diagnose` Back Button
In `frontend/src/app/diagnose/page.tsx`, import standard Next Router, and insert the back button component at the top of the main container:
```typescript
      <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 20 }}>
        <button
          id="back-to-home-btn"
          data-testid="back-to-home-btn"
          className="btn btn-secondary"
          style={{ width: 'auto', height: 40, minHeight: 40, padding: '0 16px', fontSize: '0.9rem' }}
          onClick={() => router.push('/')}
        >
          ← Back to Home
        </button>
      </div>
```

### 2.4 Proposed `backend/main.py` Update
Rewrite `decode_vin_internal` starting at line 156 of `backend/main.py`:
```python
async def decode_vin_internal(vin: str) -> dict[str, Any]:
    # Validate VIN format: exactly 17 alphanumeric characters
    if len(vin) != 17 or not vin.isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid VIN format. Must be exactly 17 alphanumeric characters."
        )

    if vin.startswith("SYN"):
        yy_str = vin[3:5]
        make_code = vin[5:10]
        model_code = vin[10:17]
        
        try:
            year = 2000 + int(yy_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid year in synthetic VIN."
            )
            
        SYN_MAKE_MAP = {
            "HONDA": "HONDA",
            "TOYOT": "TOYOTA",
            "FORDX": "FORD",
            "LEXUS": "LEXUS",
            "CHEVR": "CHEVROLET",
        }
        
        SYN_MODEL_MAP = {
            "CIVICXX": "CIVIC",
            "ACCORDX": "ACCORD",
            "F150XXX": "F-150",
            "CAMRYXX": "CAMRY",
            "COROLLA": "COROLLA",
            "RX350XX": "RX350",
            "SILVERA": "SILVERADO",
        }
        
        if make_code not in SYN_MAKE_MAP or model_code not in SYN_MODEL_MAP:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid make or model code in synthetic VIN."
            )
            
        make = SYN_MAKE_MAP[make_code]
        model = SYN_MODEL_MAP[model_code]
        
        SYN_SPECS_MAP = {
            "HONDA": {"engine": "1.5L 4-Cylinder", "drive_type": "FWD"},
            "TOYOTA": {"engine": "2.5L 4-Cylinder", "drive_type": "FWD"},
            "FORD": {"engine": "3.5L V6", "drive_type": "AWD"},
            "LEXUS": {"engine": "3.5L V6", "drive_type": "AWD"},
            "CHEVROLET": {"engine": "5.3L V8", "drive_type": "AWD"},
        }
        
        specs = SYN_SPECS_MAP[make]
        
        return {
            "year": year,
            "make": make,
            "model": model,
            "engine": specs["engine"],
            "drive_type": specs["drive_type"]
        }

    # Rest of standard NHTSA decoding logic...
```

---

## 3. Verification Method

### 3.1 Unit Testing Strategy
Add tests targeting the new synthetic VIN parser in `tests/unit/test_api.py`:
```python
def test_synthetic_vin_decoding_success(client):
    # Honda civic 2026 synthetic
    response = client.get("/api/vin/SYN26HONDACIVICXX")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2026
    assert data["make"] == "HONDA"
    assert data["model"] == "CIVIC"
    assert data["engine"] == "1.5L 4-Cylinder"
    assert data["drive_type"] == "FWD"
    
    # Chevrolet silverado 2015 synthetic
    response = client.get("/api/vin/SYN15CHEVRSILVERA")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2015
    assert data["make"] == "CHEVROLET"
    assert data["model"] == "SILVERADO"
    assert data["engine"] == "5.3L V8"
    assert data["drive_type"] == "AWD"

def test_synthetic_vin_decoding_invalid_code(client):
    response = client.get("/api/vin/SYN26INVALIDMODEL")
    assert response.status_code == 404
    assert "Invalid make or model code" in response.json()["error"]
```

Run test via:
```bash
.venv/bin/pytest tests/unit/ -v
```

### 3.2 E2E/Integration Testing Strategy
After making the implementation, run the verify test suite to confirm compile, lint, and mock checks:
```bash
cd frontend && pnpm run lint && pnpm run build
cd .. && ./tests/verify_tests.sh
```
All of these must compile with zero errors.
