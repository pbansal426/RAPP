# Block 1.3 — De-overclaim "Verified"/"Genuine"/"Exact fit" language

> **Model**: Haiku 5 · **Thinking**: Low · **Stage**: 1 (Trust & Correctness) · **Status**: ⬜ Not started
> **Parent**: [`../imp_part_2.md`](../imp_part_2.md) §1.3

---

## TL;DR

Five string replacements across two files (`backend/pricing.py`, `frontend/src/app/results/PartsPurchasePlan.tsx`) plus one badge in `results/page.tsx`. The app calls parts "Verified"/"Genuine"/"Exact fit" but there is **no fitment verification, no inventory check, no live price lookup** anywhere — all part links are keyword-search URLs. This block softens those claims to what the product actually does.

**One of these is a coupled change**: the OEM brand string is matched by an exact-equality check in the frontend. If you change the backend string without the matching frontend edit, you silently break the oil/fluid/filter relabeling branch. Both are in this doc — do them together.

---

## Context you need

- `backend/pricing.py::build_part_options` produces the three part tiers (Aftermarket/Budget, OEM, Upgrade) with `brand` and `rationale` strings.
- `frontend/src/app/results/PartsPurchasePlan.tsx::buildDisplayOptions` reshapes those into the OEM-vs-Aftermarket pair shown on `/results`, and — for oil/fluid/filter parts — relabels them with friendlier copy. That relabeling **depends on exact-matching the backend's OEM brand string and rationale substrings.**
- Nothing else reads these strings, so this is a pure copy change with one coupling to keep consistent.

---

## ⚠️ Corrections vs. `imp_part_2.md`

None on facts — all five spots and their current strings verified accurate as of 2026-07-16. The coupling risk in change #3 is real and is spelled out in full below. The em-dash (`—`, U+2014) in the OEM rationale is a literal character in the source; keep using a real em-dash in the replacement.

---

## Exact changes

### File 1 — `backend/pricing.py`

#### Edit 1 — Aftermarket/Budget rationale (line 100)

**Current**:
```python
            "rationale": "Reliable daily-driver replacement at the lowest verified price point.",
```
**Change** ("verified" is wrong — `estimated_price` is a regex parse of template text, not a live price check):
```python
            "rationale": "Reliable daily-driver replacement at a low estimated price point.",
```

#### Edit 2 — OEM tier `brand` (line 104) — **coupled with Edit 4, do both**

**Current**:
```python
            "brand": "OEM / Genuine Dealer Part",
```
**Change**:
```python
            "brand": "OEM-Spec Part",
```

#### Edit 3 — OEM tier rationale (line 109)

**Current**:
```python
            "rationale": "Exact factory fit and spec — the safest choice for warranty and long-term reliability.",
```
**Change** (keep the real em-dash `—`):
```python
            "rationale": "Matches OEM spec — a safe choice for warranty and long-term reliability.",
```

> Leave the Aftermarket/Budget `brand` (`"Duralast / equivalent aftermarket"`) **unchanged** — it names a real aftermarket brand without an accuracy claim.

---

### File 2 — `frontend/src/app/results/PartsPurchasePlan.tsx` (the coupled edits)

The oil/fluid/filter branch in `buildDisplayOptions` (lines 35-43) exact-matches the backend strings you just changed. Update all four matchers so the branch keeps firing.

#### Edit 4 — OEM brand equality check (line 35) — **pairs with Edit 2**

**Current**:
```tsx
  const opt1Brand = isOilFluidFilter && opt1?.brand === 'OEM / Genuine Dealer Part' ? 'Mobil 1 / Castrol' : (opt1?.brand || 'OEM Factory');
```
**Change** the literal `'OEM / Genuine Dealer Part'` → `'OEM-Spec Part'`:
```tsx
  const opt1Brand = isOilFluidFilter && opt1?.brand === 'OEM-Spec Part' ? 'Mobil 1 / Castrol' : (opt1?.brand || 'OEM Factory');
```

#### Edit 5 — OEM rationale substring check + fallback (lines 38-40) — **pairs with Edit 3**

**Current**:
```tsx
  const opt1Rationale = isOilFluidFilter && opt1?.rationale.includes('factory fit')
    ? 'Full synthetic formulation providing superior thermal stability, oxidation resistance, and extended engine protection.'
    : (opt1?.rationale || 'Exact factory spec and fitment.');
```
**Change** — the `.includes('factory fit')` check must match the new rationale wording (`"Matches OEM spec …"`), and the fallback `'Exact factory spec and fitment.'` is itself an overclaim:
```tsx
  const opt1Rationale = isOilFluidFilter && opt1?.rationale.includes('OEM spec')
    ? 'Full synthetic formulation providing superior thermal stability, oxidation resistance, and extended engine protection.'
    : (opt1?.rationale || 'Matches OEM spec and fitment.');
```
> Leave the `opt2` (aftermarket) branch on lines 41-43 unchanged — it checks `.includes('daily-driver')`, and Edit 1 keeps the phrase "daily-driver" in the aftermarket rationale, so that match still works.

#### Edit 6 — section header (line 86)

**Current**:
```tsx
          <h2 className="section-title" style={{ margin: 0 }}>Verified Parts &amp; Tool Purchase Recommendations</h2>
```
**Change**:
```tsx
          <h2 className="section-title" style={{ margin: 0 }}>Recommended Parts &amp; Tool Purchase Options</h2>
```

---

### File 3 — `frontend/src/app/results/page.tsx`

#### Edit 7 — free-analysis badge (line 433)

**Current**:
```tsx
          <span className="badge badge-free">Verified AI Analysis</span>
```
**Change**:
```tsx
          <span className="badge badge-free">AI-Generated, RAG-Grounded Analysis</span>
```

---

## Do NOT touch

- `results/page.tsx` line 417's complaints-summary copy — *"Based on {N} unverified NHTSA consumer complaints … not confirmed defects"*. This is **already correctly hedged** and is the model to match, not a thing to fix.
- The aftermarket `brand` string `"Duralast / equivalent aftermarket"` (pricing.py) and the `opt2` relabel branch (PartsPurchasePlan.tsx lines 36, 41-43).
- The `'$4.00'` guide-fee fallback on line 593 — that's **Block 1.1's** job. (Both blocks touch line 593's text; if 1.1 already ran, "verified parts" there was left for you — change nothing on that line in *this* block unless it still says "verified", which it does not affect the fee fallback.)

---

## Verification

1. **No overclaiming strings remain**:
   ```bash
   grep -rn "Genuine Dealer\|Exact factory fit\|Verified Parts\|Verified AI Analysis\|lowest verified price" backend/pricing.py frontend/src/app/results/
   ```
   Must return nothing.
2. **The coupling didn't break** — this is the concrete regression risk. Run the app, diagnose an **oil-change** symptom (e.g. "oil change" / "5000 mile service"), and confirm on `/results` the parts card shows the friendly titles **"Premium Synthetic Oil" / "Standard Conventional Oil"** with brands "Mobil 1 / Castrol" and "Valvoline / Pennzoil" — **not** the generic "OEM Factory Part" / "Premium Aftermarket". If you see the generic labels, Edit 4/5 didn't match — recheck the exact string equality.
3. **Backend checks pass**:
   ```bash
   uv run ruff check backend/ && uv run black --check backend/ && uv run mypy backend/
   uv run pytest tests/unit/ -v
   ```
4. **Frontend build passes**:
   ```bash
   cd frontend && ./node_modules/.bin/next build
   ```

---

## Definition of Done

- [ ] Edits 1-3 in `backend/pricing.py`
- [ ] Edits 4-6 in `PartsPurchasePlan.tsx` (coupled string matches updated to `'OEM-Spec Part'` and `'OEM spec'`)
- [ ] Edit 7 in `results/page.tsx`
- [ ] Oil-change repair still shows "Premium Synthetic Oil"/"Standard Conventional Oil" (coupling intact)
- [ ] `grep` for overclaiming strings returns nothing
- [ ] Backend lint/type/tests + frontend build all pass
- [ ] Committed: `fix(pricing,results): Block 1.3 de-overclaim parts/analysis language`
- [ ] `imp_part_2.md` §1 tracker row 1.3 → `✅ Done`; session logged in §5
