# Block 4.5 — Results-Page Fabricated Claims & Pre-Passed Safety Checklist

**Parent plan**: [`../imp_part_2.md`](../imp_part_2.md) Section 5 Stage 4 Block 4.5
**Model specced**: Sonnet 5 | **Thinking specced**: Medium
**Status**: ⬜ Not started
**Verified against codebase**: 2026-07-16 (after Blocks 1.1, 1.2, 1.3, 3.2 landed)

---

## 1. Goal

Blocks 1.1 and 1.3 already fixed the stale price fallbacks and the "Verified"/"Genuine"/"Exact fit" overclaim language on `/results`. This block catches four items that survived those passes — three because they don't match the exact string patterns those blocks' verification `grep`s checked for, one (the pre-passed checklist) because it's a state-default bug, not a copy string. All four actively undermine the "authentic, trustable authority" feel the app should have: an invented dollar figure, a safety checklist that's green before the user does anything, a leftover "verified"/"85%" overclaim, and a fabricated specific-brand endorsement.

---

## 2. Exactly what to change

### Item 1: Fabricated "$1,200+" collateral-damage figure

**File**: `frontend/src/app/results/page.tsx`, line 460 (inside the high-risk alert block, itself inside the "Free diagnosis summary" card)

Current code:
```tsx
<div><strong>High-Risk Alert:</strong> Delaying this repair or modification risks secondary cascading component damage. Estimated potential collateral cost if ignored: <strong>$1,200+</strong>.</div>
```

This number is a flat hardcoded constant — it is not derived from `diagnosis.cost_breakdown` or any other real value on the page, and it displays identically for every vehicle, every symptom, every high-risk diagnosis. Presenting an unfounded specific dollar figure as if it were a real estimate is exactly the kind of thing that breaks trust once a user notices it doesn't change no matter what they enter.

Replace with:
```tsx
<div><strong>High-Risk Alert:</strong> Delaying this repair or modification risks secondary cascading component damage — the longer a safety-critical or high-risk issue goes unaddressed, the more likely it is to affect other components.</div>
```

Do not invent a computed replacement number (e.g. deriving a percentage of `dealership_cost_range`) — that would just be a different fabricated figure with extra steps. The qualitative statement is the honest fix here.

---

### Item 2: Pre-passed safety readiness checklist

**File**: `frontend/src/app/results/page.tsx`, lines 72-73

Current code:
```tsx
const [toolsReady, setToolsReady] = useState<boolean>(true);
const [timeReady, setTimeReady] = useState<boolean>(true);
```

These two booleans back the "Pre-Job Readiness & Competence Quiz" card further down the page (search for `data-testid="prejob-readiness-quiz"`). That card's own footer computes:
```tsx
{toolsReady && timeReady ? 'Readiness Score: 100% — Verified Ready for DIY Execution' : 'Action Required: Complete pre-job checks before unlocking procedure'}
```
Because both start `true`, **every single visitor sees the green "100% — Verified Ready" state on first page load**, before reading or checking either box. A safety-verification gate that's pre-passed is worse than no gate at all — it actively signals false confidence.

Replace with:
```tsx
const [toolsReady, setToolsReady] = useState<boolean>(false);
const [timeReady, setTimeReady] = useState<boolean>(false);
```

No other change needed in this file for this item — the existing checkbox `onChange` handlers and the readiness-score render logic already work correctly once the defaults are honest; they just needed to start `false`.

---

### Item 3: Leftover "verified"/"85%" overclaim (survived Block 1.3's grep)

**File**: `frontend/src/app/results/page.tsx`, line 609 (inside the "Why DIY With RAPP?" price-comparison table's RAPP row, "Value & Details" cell)

Current code:
```tsx
<span className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.85)', fontSize: '0.8rem' }}>
  Save up to 85% today with exact step-by-step guidance & verified parts (includes {diagnosis?.cost_breakdown ? `$${diagnosis.cost_breakdown.guide_fee.toFixed(2)}` : '—'} guide fee)
</span>
```

Block 1.3's verification check was `grep -rn "Genuine Dealer\|Exact factory fit\|Verified Parts\|Verified AI Analysis\|lowest verified price"` — a case-sensitive search for the capitalized phrase `"Verified Parts"`. This line uses the lowercase in-sentence phrase `"verified parts"`, so it was never caught, even though it has the identical problem: there is no fitment/inventory verification anywhere in the codebase (all parts links are keyword-search URLs, per `backend/pricing.py::_search_url`). It also carries an unrelated flat "85%" savings claim that never varies with the real numbers the page already computes (see the "Save ~$X vs Dealership" hero badge earlier on this same page, built from real `cost_breakdown` data) and an "exact" claim that overstates the precision of AI-generated steps.

Replace with:
```tsx
<span className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.85)', fontSize: '0.8rem' }}>
  Save significantly vs. a dealership with step-by-step guidance and sourced parts (includes {diagnosis?.cost_breakdown ? `$${diagnosis.cost_breakdown.guide_fee.toFixed(2)}` : '—'} guide fee)
</span>
```

(This edit is scoped to the text only — the `color: 'rgba(255, 255, 255, 0.85)'` inline style on this `<span>` is Block 4.6's concern (theme-token pass), not this block's. Leave it as-is here; do not fix it in this block.)

---

### Item 4: Fabricated specific-brand endorsement for oil/fluid/filter parts

**File**: `frontend/src/app/results/PartsPurchasePlan.tsx`, inside `buildDisplayOptions` (near the top of the file)

Current code:
```tsx
const opt1Brand = isOilFluidFilter && opt1?.brand === 'OEM-Spec Part' ? 'Mobil 1 / Castrol' : (opt1?.brand || 'OEM Factory');
const opt2Brand = isOilFluidFilter && opt2?.brand === 'Duralast / equivalent aftermarket' ? 'Valvoline / Pennzoil' : (opt2?.brand || 'Premium Aftermarket');
```

This hardcodes two specific real consumer brand pairs ("Mobil 1 / Castrol", "Valvoline / Pennzoil") for **any** oil/fluid/filter-type part, regardless of the vehicle or what the backend actually recommended — there is no product-matching, pricing, or availability logic behind these names; it's a keyword-triggered string swap presented as a confident purchase recommendation. If a user ever cross-checks this against a real parts catalog and finds no basis for the specific brands named, it reads as made up — because it is.

Note that the `title` relabeling a few lines below this (`'Premium Synthetic Oil'` / `'Standard Conventional Oil'`) is a legitimate, honest category description (it just renames what "OEM"/"Aftermarket" mean for a fluid, which is genuinely confusing language for oil) — **that part is fine and should not change.** Only the specific-brand-name substitution is the problem.

Replace the two lines above with:
```tsx
const opt1Brand = opt1?.brand || 'OEM Factory';
const opt2Brand = opt2?.brand || 'Premium Aftermarket';
```

This drops the fabricated brand-name override entirely and falls back to the real backend-supplied `brand` field (the same fallback already used for every non-oil part category), rather than inventing a specific endorsement with no data behind it.

**Do not** also change the `isOilFluidFilter` variable itself — it's still used a few lines below for the `title` and `rationale` swaps, which are staying.

---

## 3. Verification

```bash
grep -n "1,200\|Save up to 85%" frontend/src/app/results/page.tsx
# Expect: no output

grep -n "useState<boolean>(true)" frontend/src/app/results/page.tsx
# Expect: no output (both toolsReady/timeReady now read (false))

grep -n "Mobil 1\|Castrol\|Valvoline\|Pennzoil" frontend/src/app/results/PartsPurchasePlan.tsx
# Expect: no output

cd frontend && ./node_modules/.bin/next build
```
**Expected**: `✓ Compiled successfully`, zero TS/ESLint errors.

**Manual check**: load `/results` fresh (clear `rapp_skill_level`/no prior interaction) with a populated diagnosis — the "Pre-Job Readiness & Competence Quiz" card must show the yellow **"Action Required: Complete pre-job checks before unlocking procedure"** state, not the green "100%" state, until both checkboxes are manually checked. Confirm an oil-change-category repair (e.g. symptoms mentioning "oil change") still shows the "Premium Synthetic Oil" / "Standard Conventional Oil" titles in the parts plan (the title relabeling must still fire) but no longer names "Mobil 1", "Castrol", "Valvoline", or "Pennzoil" anywhere.
