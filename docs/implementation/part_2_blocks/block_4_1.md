# Block 4.1 — Frontend Runtime Safety (`safeGetJson` & `localStorage` crash guards)

**Parent plan**: [`../imp_part_2.md`](../imp_part_2.md) Section 5 Stage 4 Block 4.1
**Model specced**: Sonnet 5 | **Thinking specced**: Medium
**Status**: ⬜ Not started

---

## 1. Goal

Eliminate client-side white screens of death (`SyntaxError: Unexpected end of JSON input` or `Unexpected token`) caused by bare `JSON.parse(localStorage.getItem(...))` calls when local storage contains truncated, malformed, or missing JSON strings. Add a bulletproof utility `safeGetJson<T>(key: string, fallback: T): T` and migrate every bare parse call in `diagnose/page.tsx`, `results/page.tsx`, and `repair/page.tsx` to use it.

---

## 2. Exactly what to change

### Step 1: Create or expand `frontend/src/lib/storage.ts`

Check if `frontend/src/lib/storage.ts` exists. If not, create it with the following exact implementation:

```typescript
/**
 * Safely parses a JSON string from localStorage.
 * If localStorage is inaccessible (e.g. SSR or strict privacy mode), key is missing,
 * or the stored value is malformed JSON, returns `fallback` without throwing an exception.
 */
export function safeGetJson<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback;
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch (err) {
    if (process.env.NODE_ENV !== 'production') {
      console.warn(`[safeGetJson] Failed to parse localStorage key "${key}":`, err);
    }
    return fallback;
  }
}
```

### Step 2: Migrate `frontend/src/app/diagnose/page.tsx`

1. Import `safeGetJson` at the top:
   ```typescript
   import { safeGetJson } from '@/lib/storage';
   ```
2. Replace line 27-28 (`useEffect` mount):
   ```diff
   -    const stored = localStorage.getItem('rapp_vin_data');
   -    if (stored) setVinData(JSON.parse(stored));
   +    const storedData = safeGetJson<Record<string, unknown> | null>('rapp_vin_data', null);
   +    if (storedData) setVinData(storedData);
   ```

### Step 3: Migrate `frontend/src/app/results/page.tsx`

1. Import `safeGetJson` at the top:
   ```typescript
   import { safeGetJson } from '@/lib/storage';
   ```
2. Replace line 148 (`useEffect` check):
   ```diff
   -    const tools = JSON.parse(localStorage.getItem('rapp_tools') ?? '[]') as string[];
   +    const tools = safeGetJson<string[]>('rapp_tools', []);
   ```
3. Replace line 181 (`useEffect` API payload):
   ```diff
   -    const obdCodes = JSON.parse(localStorage.getItem('rapp_obd_codes') ?? '[]') as string[];
   +    const obdCodes = safeGetJson<string[]>('rapp_obd_codes', []);
   ```
4. Replace line 220-221 inside `pregenerateRepairGuide`:
   ```diff
   -    const tools = JSON.parse(localStorage.getItem('rapp_tools') ?? '[]') as string[];
   -    const obdCodes = JSON.parse(localStorage.getItem('rapp_obd_codes') ?? '[]') as string[];
   +    const tools = safeGetJson<string[]>('rapp_tools', []);
   +    const obdCodes = safeGetJson<string[]>('rapp_obd_codes', []);
   ```

### Step 4: Migrate `frontend/src/app/repair/page.tsx`

1. Import `safeGetJson` at the top:
   ```typescript
   import { safeGetJson } from '@/lib/storage';
   ```
2. Replace line 149 inside `completePendingSave`:
   ```diff
   -      const tools = JSON.parse(localStorage.getItem('rapp_tools') ?? '[]') as string[];
   +      const tools = safeGetJson<string[]>('rapp_tools', []);
   ```
3. Replace line 166-168 inside main `useEffect`:
   ```diff
   -    const storedVinData = localStorage.getItem('rapp_vin_data');
   -    const parsedVinData = storedVinData ? JSON.parse(storedVinData) : null;
   -    if (parsedVinData) setVinData(parsedVinData);
   +    const parsedVinData = safeGetJson<Record<string, unknown> | null>('rapp_vin_data', null);
   +    if (parsedVinData) setVinData(parsedVinData);
   ```
4. Replace line 172:
   ```diff
   -    const tools = JSON.parse(localStorage.getItem('rapp_tools') ?? '[]') as string[];
   +    const tools = safeGetJson<string[]>('rapp_tools', []);
   ```
5. Replace line 178-181 (`rapp_parts_${storedVin}`):
   ```diff
   -    const storedParts = localStorage.getItem(`rapp_parts_${storedVin}`);
   -    if (storedParts) {
   -      try { setParts(JSON.parse(storedParts)); } catch { /* malformed cache, ignore */ }
   -    }
   +    const storedParts = safeGetJson<RecommendedPart[] | null>(`rapp_parts_${storedVin}`, null);
   +    if (storedParts) setParts(storedParts);
   ```
6. Replace line 189-200 (`rapp_repair_${storedVin}` and `rapp_repair_checked_${storedVin}`):
   ```diff
   -    const cachedRepair = localStorage.getItem(`rapp_repair_${storedVin}`);
   -    if (cachedRepair) {
   -      try {
   -        setRepair(JSON.parse(cachedRepair));
   -        const cachedChecked = localStorage.getItem(`rapp_repair_checked_${storedVin}`);
   -        if (cachedChecked) setCheckedSteps(JSON.parse(cachedChecked));
   -        setLoading(false);
   -        return;
   -      } catch {
   -        // fall through to a fresh generation if the cached value is malformed
   -      }
   -    }
   +    const cachedRepair = safeGetJson<RepairResponse | null>(`rapp_repair_${storedVin}`, null);
   +    if (cachedRepair) {
   +      setRepair(cachedRepair);
   +      const cachedChecked = safeGetJson<Record<string, boolean>>(`rapp_repair_checked_${storedVin}`, {});
   +      setCheckedSteps(cachedChecked);
   +      setLoading(false);
   +      return;
   +    }
   ```
7. Replace line 217 inside `startOver()`:
   ```diff
   -    const tools = JSON.parse(localStorage.getItem('rapp_tools') ?? '[]') as string[];
   +    const tools = safeGetJson<string[]>('rapp_tools', []);
   ```

---

## 3. Verification

Run the exact checks below from repository root before committing:

```bash
cd frontend && ./node_modules/.bin/next build
```

**Expected output**:
- `✓ Compiled successfully`
- `✓ Generating static pages (24/24)`
- Zero TypeScript (`TS2304` / `TS2322`) errors and zero ESLint errors.

To manually verify in browser devtools console on `http://localhost:3000/diagnose`:
```javascript
localStorage.setItem('rapp_tools', '["10mm socket"'); // deliberately malformed JSON without closing bracket
// Refresh page -> verifies page loads cleanly without throwing SyntaxError.
```
