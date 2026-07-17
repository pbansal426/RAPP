# Block 4.2 — UX Interaction Polish & State Preservation

**Parent plan**: [`../imp_part_2.md`](../imp_part_2.md) Section 5 Stage 4 Block 4.2
**Model specced**: Sonnet 5 | **Thinking specced**: Medium
**Status**: ⬜ Not started

---

## 1. Goal

Eliminate user friction, false error alerts, and destructive state wipes across the core vehicle identification, checkout, and repair flows:
1. Prevent Year/Make/Model cascading state resets when clicking/re-selecting the same Make or Year (`app/page.tsx`).
2. Fix the 402 Network Error loop triggered by `pregenerateRepairGuide()` on `/results` (`app/results/page.tsx`).
3. Lock interactive drag/close actions during Tesseract OCR cropping (`app/VinCropModal.tsx`).
4. Add a "Copy Diagnostic Summary" button to the AI overview card on `/results` (`app/results/page.tsx`).
5. Replace native browser `window.confirm()` during "Start Over" with an inline confirmation banner (`app/repair/page.tsx`).
6. Dynamically interpolate the user's actual vehicle tools when AI chat quota is exhausted (`app/repair/ChatPanel.tsx`).

---

## 2. Exactly what to change

### Step 1: Prevent cascading state resets in `frontend/src/app/page.tsx`

In `handleYearChange` and `handleMakeChange` (lines 110-125), check if the value actually changed before wiping sub-selections:

```diff
   const handleYearChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
+    const val = e.target.value;
+    if (val === selectedYear) return;
-    setSelectedYear(e.target.value);
+    setSelectedYear(val);
     setSelectedMake('');
     setSelectedModel('');
     setSelectedTrim('');
     setSelectedDriveType('');
     setYmmError(null);
   };

   const handleMakeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
+    const val = e.target.value;
+    if (val === selectedMake) return;
-    setSelectedMake(e.target.value);
+    setSelectedMake(val);
     setSelectedModel('');
     setSelectedTrim('');
     setSelectedDriveType('');
     setYmmError(null);
   };
```

### Step 2: Fix 402 Network Error loop in `frontend/src/app/results/page.tsx`

In `pregenerateRepairGuide` (lines 218-233), check if the user is an active subscriber (`authUser?.subscriptionStatus === 'active'`) OR if an existing valid paid `sessionId` (`rapp_unlocked_${vin}`) already exists before sending `POST /api/repair`. Otherwise, do not call `/api/repair` with `'pregenerate-on-intent'` (which is guaranteed to return `HTTP 402 Payment Required` server-side):

```diff
   const pregenerateRepairGuide = () => {
     if (!vin || localStorage.getItem(`rapp_repair_${vin}`)) return;
+    const existingUnlock = localStorage.getItem(`rapp_unlocked_${vin}`);
+    const isSubscriber = authUser?.subscriptionStatus === 'active';
+    if (!existingUnlock && !isSubscriber) {
+      // Do not hit /api/repair without a valid unlock proof or active sub,
+      // or the backend will raise HTTP 402 and pollute console error logs.
+      return;
+    }
     const tools = JSON.parse(localStorage.getItem('rapp_tools') ?? '[]') as string[];
     const obdCodes = JSON.parse(localStorage.getItem('rapp_obd_codes') ?? '[]') as string[];
     api.post<{ repair_steps: string[]; citations: string[] }>('/api/repair', {
       vin,
       symptoms,
       obd_codes: obdCodes,
       tools,
-      stripe_session_id: 'pregenerate-on-intent',
+      stripe_session_id: existingUnlock || 'pregenerate-on-intent',
       vehicle: vinData,
       skill_level: skillLevel,
     })
```

### Step 3: Add "Copy Diagnostic Summary" button in `frontend/src/app/results/page.tsx`

1. Import `useState` (if not already present) and `CheckIcon` from `@/app/sharedIcons`.
2. Inside `ResultsPage`, add state `const [copied, setCopied] = useState(false);`.
3. Add a helper:
   ```typescript
   const handleCopyDiagnosis = () => {
     if (!diagnosis) return;
     const text = [
       `RAPP Free Diagnosis for VIN: ${vin}`,
       `Category: ${diagnosis.cost_breakdown?.category ?? 'General'}`,
       `Summary: ${diagnosis.symptoms_summary}`,
       diagnosis.root_causes ? `Root Causes:\n${diagnosis.root_causes.join('\n')}` : '',
     ].filter(Boolean).join('\n\n');
     navigator.clipboard.writeText(text);
     setCopied(true);
     setTimeout(() => setCopied(false), 2000);
   };
   ```
4. In the JSX header of `<div className="card" data-testid="free-diagnosis-summary">` (around line 430), right above the `<p style={{ fontWeight: 600... }}>` summary:
   ```tsx
   <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
     <h2 style={{ fontSize: '1.25rem', margin: 0 }}>Free Diagnosis & Mod Overview</h2>
     {diagnosis && (
       <button
         type="button"
         className="btn btn-secondary"
         onClick={handleCopyDiagnosis}
         style={{ padding: '4px 10px', fontSize: '0.8rem', display: 'inline-flex', alignItems: 'center', gap: 6 }}
       >
         {copied ? <><CheckCircleIcon size={14} style={{ color: '#4ade80' }} /> Copied!</> : 'Copy Summary'}
       </button>
     )}
   </div>
   ```

### Step 4: Lock canvas drag & close actions during `ocrLoading` (`VinCropModal.tsx`)

In `frontend/src/app/VinCropModal.tsx`, update the modal close button and canvas wrapper:

1. Disable the top-right close `×` button when `processing` is true:
   ```tsx
   <button
     type="button"
     onClick={onCancel}
     disabled={processing}
     style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: processing ? 'not-allowed' : 'pointer', opacity: processing ? 0.4 : 1 }}
     aria-label="Close modal"
   >
     ×
   </button>
   ```
2. Add `pointerEvents: processing ? 'none' : 'auto'` and `opacity: processing ? 0.7 : 1` to the canvas container `<div style={{ position: 'relative', overflow: 'hidden'... }}>`.

### Step 5: Replace `window.confirm()` in `frontend/src/app/repair/page.tsx`

1. Add state: `const [confirmingStartOver, setConfirmingStartOver] = useState(false);`
2. Change `startOver()` to only execute directly when triggered by the confirmation click:
   ```typescript
   const executeStartOver = () => {
     if (!vin) return;
     localStorage.removeItem(`rapp_repair_${vin}`);
     localStorage.removeItem(`rapp_repair_checked_${vin}`);
     setCheckedSteps({});
     setRepair(null);
     setError(null);
     setConfirmingStartOver(false);
     const sessionId = localStorage.getItem(`rapp_unlocked_${vin}`) ?? '';
     const tools = safeGetJson<string[]>('rapp_tools', []);
     generateAndCache(vin, symptoms, tools, sessionId, vinData);
   };
   ```
3. In JSX, where the `"Start Over"` button renders (or top of the repair guide header):
   ```tsx
   {confirmingStartOver ? (
     <div className="alert alert-warning" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, margin: '12px 0', padding: '10px 14px', borderRadius: 8 }}>
       <span>Start over and clear all checked-off progress?</span>
       <div style={{ display: 'flex', gap: 8 }}>
         <button type="button" className="btn btn-primary" style={{ padding: '4px 10px', fontSize: '0.85rem', background: '#ef4444' }} onClick={executeStartOver}>Yes, Reset</button>
         <button type="button" className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '0.85rem' }} onClick={() => setConfirmingStartOver(false)}>Cancel</button>
       </div>
     </div>
   ) : (
     <button type="button" className="btn btn-secondary text-sm" onClick={() => setConfirmingStartOver(true)}>↻ Start Over</button>
   )}
   ```

### Step 6: Dynamic tool fallbacks in `frontend/src/app/repair/ChatPanel.tsx`

Update `cannedReply(userMsg: string)` (around line 53) to accept a second parameter `tools: string[] = []` or read directly from safe browser storage:

```typescript
function cannedReply(userMsg: string): string {
  const lower = userMsg.toLowerCase();
  if (lower.includes('torque') || lower.includes('tighten') || lower.includes('lbs') || lower.includes('ft-lbs')) {
    return 'OEM Specification: Coil pack mounting bolts torque to 7.5 ft-lbs (10 Nm). Spark plugs torque to 15 ft-lbs (20 Nm) on aluminum heads.';
  }
  if (lower.includes('socket') || lower.includes('tool') || lower.includes('wrench') || lower.includes('size')) {
    let cachedTools: string[] = [];
    if (typeof window !== 'undefined') {
      try { cachedTools = JSON.parse(localStorage.getItem('rapp_tools') ?? '[]'); } catch {}
    }
    const toolCallout = cachedTools.length > 0 ? `Your selected job tools include: ${cachedTools.join(', ')}.` : 'Required tools: 10mm deep socket, 3-inch extension, 3/8-inch drive ratchet.';
    return `${toolCallout} Always check bolt head clearances before applying torque.`;
  }
  if (lower.includes('corro') || lower.includes('connector')) {
    return 'If you see corrosion on a connector, clean it with electrical contact cleaner and a small brass brush before reconnecting — don’t force a corroded plug.';
  }
  if (lower.includes('safety') || lower.includes('disconnect') || lower.includes('battery')) {
    return 'Safety protocol: isolate the negative 12V battery terminal first. Let the engine cool at least 45 minutes before working near it to avoid thermal burns.';
  }
  return 'To help you best: follow the safety guidelines in Phase 1, torque all components to OEM spec, and inspect plugs/wiring for contamination.';
}
```

---

## 3. Verification

Run the exact check below from repository root before committing:

```bash
cd frontend && ./node_modules/.bin/next build
```

**Expected output**:
- `✓ Compiled successfully`
- Zero TypeScript (`TS2304` / `TS2322`) errors and zero ESLint errors.
