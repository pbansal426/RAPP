# Block 1.1 — Fix stale/wrong price displays + `RAPP_GUIDE_FEE` calc bug + remove leaked jargon badge

> **Model**: Sonnet 5 · **Thinking**: Medium · **Stage**: 1 (Trust & Correctness) · **Status**: ⬜ Not started
> **Parent**: [`../imp_part_2.md`](../imp_part_2.md) §1.1

---

## TL;DR

Five edits across two frontend files. Four are cosmetic string/fallback fixes (stop showing fabricated dollar amounts and an internal roadmap label to users). The fifth is a **real calculation bug**: `PartsPurchasePlan.tsx` hardcodes a flat `$4.00` RAPP guide fee that no longer matches the tiered ($4.99/$9.99/$14.99) fee the backend actually charges — the component must receive and use the real `guide_fee` from the diagnosis response instead.

**All edits are in the frontend only. No backend change.**

---

## Context you need

- **Real pricing is computed server-side** in `backend/pricing.py::build_cost_breakdown` → returns a `cost_breakdown` object that includes `guide_fee` (a tiered value: `4.99` / `9.99` / `14.99`, chosen by `estimate_pricing()` based on the *dealership cost*, not the category name) and `diy_total` (`guide_fee + parts_total`).
- The frontend receives this as `diagnosis.cost_breakdown` on `/results`. The type `CostBreakdown` in `frontend/src/lib/types.ts` (line 68) **already includes `guide_fee: number`**, so reading `diagnosis.cost_breakdown.guide_fee` compiles with no type change needed.
- `PartsPurchasePlan.tsx` currently has *no* way to receive the real fee — it hardcodes `const RAPP_GUIDE_FEE = 4.0;`. This block wires the real value in as a prop.

---

## ⚠️ Corrections vs. `imp_part_2.md`

1. **`RAPP_GUIDE_FEE` is used TWICE in `PartsPurchasePlan.tsx`, not once.** The parent plan says to replace "its one usage (`const diyTotal = RAPP_GUIDE_FEE + partsTotal;`)". There is a **second** usage in the budget-footer copy at line 237:
   ```tsx
   Selected parts ${partsTotal.toFixed(2)} + ${RAPP_GUIDE_FEE.toFixed(2)} RAPP guide fee
   ```
   If you delete the `const RAPP_GUIDE_FEE = 4.0;` line and only fix line 80, **`next build` will fail** with `RAPP_GUIDE_FEE is not defined`. You must update **both** usages to the new `guideFee` variable. This doc's edits below cover both.
2. The parent plan's verification says "a `brakes` category repair should show `guide_fee: 9.99` … per tier thresholds." Minor nuance: `estimate_pricing()` picks the tier from the computed **dealership high cost**, not from the category string directly. Brakes happens to land in the `9.99` tier, so the example is correct, but if you're spot-checking a different category, compute `dealership_high` first — don't assume the tier maps 1:1 to a category name.

---

## Exact changes

### File 1 of 2 — `frontend/src/app/results/page.tsx`

#### Edit 1 — line 583: dealership-comparison DIY total fallback

**Current** (inside the "RAPP Guided DIY" price-table row):
```tsx
                {diagnosis?.cost_breakdown
                  ? `$${diagnosis.cost_breakdown.diy_total.toFixed(2)}`
                  : '$39.00'}
```
**Change** the fallback `'$39.00'` → `'—'` (a plain em dash, no dollar sign):
```tsx
                {diagnosis?.cost_breakdown
                  ? `$${diagnosis.cost_breakdown.diy_total.toFixed(2)}`
                  : '—'}
```

#### Edit 2 — line 593: "Save up to 85%" guide-fee fallback

**Current**:
```tsx
                    Save up to 85% today with exact step-by-step guidance & verified parts (includes {diagnosis?.cost_breakdown ? `$${diagnosis.cost_breakdown.guide_fee.toFixed(2)}` : '$4.00'} guide fee)
```
**Change** the fallback `'$4.00'` → `'—'`:
```tsx
                    Save up to 85% today with exact step-by-step guidance & verified parts (includes {diagnosis?.cost_breakdown ? `$${diagnosis.cost_breakdown.guide_fee.toFixed(2)}` : '—'} guide fee)
```
> Note: the word "verified" in this line is de-overclaimed separately in **Block 1.3** — do **not** touch it here, only the `'$4.00'` fallback.

#### Edit 3 — line 973: single-unlock price fallback

**Current** (inside the "Single Job Unlock" paywall card):
```tsx
                {diagnosis?.cost_breakdown ? `$${diagnosis.cost_breakdown.guide_fee.toFixed(2)}` : '$4.00'}
```
**Change** the fallback `'$4.00'` → `'—'`:
```tsx
                {diagnosis?.cost_breakdown ? `$${diagnosis.cost_breakdown.guide_fee.toFixed(2)}` : '—'}
```

#### Edit 4 — line 692: leaked internal roadmap label

**Current** (badge in the "Pre-Job Readiness Quiz" card):
```tsx
          <span className="badge" style={{ background: 'rgba(249, 115, 22, 0.15)', color: 'var(--accent-yellow)', fontSize: '0.75rem', fontWeight: 700 }}>
            Stage 2.3 &amp; 2.5 Verified
          </span>
```
**Change** only the badge text `Stage 2.3 &amp; 2.5 Verified` → `Personalized Guidance`. Leave the `<span>`, `className`, and `style` exactly as-is:
```tsx
          <span className="badge" style={{ background: 'rgba(249, 115, 22, 0.15)', color: 'var(--accent-yellow)', fontSize: '0.75rem', fontWeight: 700 }}>
            Personalized Guidance
          </span>
```

#### Edit 5 — lines 515-518: pass the real guide fee into `<PartsPurchasePlan>`

**Current**:
```tsx
      <PartsPurchasePlan
        parts={diagnosis?.recommended_parts ?? []}
        vehicleTitle={`${vinData?.year ?? ''} ${vinData?.make ?? ''} ${vinData?.model ?? ''}`.trim() || 'your vehicle'}
      />
```
**Change** — add the `guideFee` prop:
```tsx
      <PartsPurchasePlan
        parts={diagnosis?.recommended_parts ?? []}
        vehicleTitle={`${vinData?.year ?? ''} ${vinData?.make ?? ''} ${vinData?.model ?? ''}`.trim() || 'your vehicle'}
        guideFee={diagnosis?.cost_breakdown?.guide_fee}
      />
```

---

### File 2 of 2 — `frontend/src/app/results/PartsPurchasePlan.tsx` (the calc bug)

#### Edit 6 — add `guideFee` to the props interface (currently lines 6-9)

**Current**:
```tsx
interface PartsPurchasePlanProps {
  parts: RecommendedPart[];
  vehicleTitle?: string;
}
```
**Change**:
```tsx
interface PartsPurchasePlanProps {
  parts: RecommendedPart[];
  vehicleTitle?: string;
  guideFee?: number;
}
```

#### Edit 7 — delete the hardcoded constant (currently lines 11-12)

**Current**:
```tsx
// Matches backend/pricing.py's RAPP guide fee used in cost_breakdown.diy_total.
const RAPP_GUIDE_FEE = 4.0;
```
**Change** — **delete both lines entirely** (the comment and the const). Nothing replaces them at module scope.

#### Edit 8 — destructure the new prop with a safe default (currently line 67)

**Current**:
```tsx
export default function PartsPurchasePlan({ parts, vehicleTitle }: PartsPurchasePlanProps) {
```
**Change** — add `guideFee = 4.99` (the tier-1 floor; a defensive fallback that only fires if `cost_breakdown` somehow hasn't loaded, which in practice it always has by the time parts render):
```tsx
export default function PartsPurchasePlan({ parts, vehicleTitle, guideFee = 4.99 }: PartsPurchasePlanProps) {
```

#### Edit 9 — usage #1: the `diyTotal` calculation (currently line 80)

**Current**:
```tsx
  const diyTotal = RAPP_GUIDE_FEE + partsTotal;
```
**Change**:
```tsx
  const diyTotal = guideFee + partsTotal;
```

#### Edit 10 — usage #2: the budget-footer copy (currently line 237) — **THE ONE THE PARENT PLAN MISSES**

**Current**:
```tsx
          <p className="text-muted text-sm" style={{ margin: '4px 0 0' }}>
            Selected parts ${partsTotal.toFixed(2)} + ${RAPP_GUIDE_FEE.toFixed(2)} RAPP guide fee
          </p>
```
**Change**:
```tsx
          <p className="text-muted text-sm" style={{ margin: '4px 0 0' }}>
            Selected parts ${partsTotal.toFixed(2)} + ${guideFee.toFixed(2)} RAPP guide fee
          </p>
```

---

## Do NOT touch

- The `data-testid="parts-plan-total"` element (line ~222 of `PartsPurchasePlan.tsx`) — it is a **frozen contract** per `CLAUDE.md`. Only the *number* it renders changes; the element, its testid, and structure stay identical.
- The word "verified"/"Verified" anywhere — those are **Block 1.3's** job, not this block's.
- Any `style`, `className`, or wrapper element — every edit above changes only text content, a fallback literal, a prop, or a variable name.

---

## Verification

1. **Build passes** (this is the gate that catches the two-usage bug):
   ```bash
   cd frontend && ./node_modules/.bin/next build
   ```
   Must complete with zero TS/ESLint errors. A failure mentioning `RAPP_GUIDE_FEE is not defined` means you missed Edit 10.
2. **No fabricated strings remain**:
   ```bash
   grep -n "39.00\|\$4.00\|Stage 2\." frontend/src/app/results/page.tsx
   ```
   Must return nothing.
   ```bash
   grep -n "RAPP_GUIDE_FEE" frontend/src/app/results/PartsPurchasePlan.tsx
   ```
   Must return nothing (the const and both usages are gone).
3. **Manual trace** (optional but recommended): run the app, diagnose a brakes symptom (e.g. VIN + "grinding noise when braking"), and confirm on `/results`:
   - The parts-plan footer total = `selected parts + 9.99` (the brakes tier), not `+ 4.00`.
   - The single-unlock card and the "Save up to 85%" line show the same `9.99`, not `4.00`.
   - No "Stage 2.3 & 2.5" text appears anywhere; the quiz badge reads "Personalized Guidance".

---

## Definition of Done

- [ ] Edits 1-5 applied in `results/page.tsx`
- [ ] Edits 6-10 applied in `PartsPurchasePlan.tsx` (including the second `RAPP_GUIDE_FEE` usage at line 237)
- [ ] `cd frontend && ./node_modules/.bin/next build` passes clean
- [ ] Both `grep` checks return nothing
- [ ] Committed: `fix(results): Block 1.1 correct guide-fee display + calc, drop leaked jargon`
- [ ] `imp_part_2.md` §1 tracker row 1.1 → `✅ Done`; session logged in §5
