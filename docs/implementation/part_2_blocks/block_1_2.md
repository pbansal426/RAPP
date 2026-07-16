# Block 1.2 — Resolve "100% Satisfaction Guarantee" vs. Terms-of-Service contradiction

> **Model**: Fable 5 · **Thinking**: Low · **Stage**: 1 (Trust & Correctness) · **Status**: ⬜ Not started
> **Parent**: [`../imp_part_2.md`](../imp_part_2.md) §1.2

---

## TL;DR

**One-line copy change.** The paywall footer promises a "100% Satisfaction Guarantee" directly above the payment buttons — on the same screen where the user must agree to Terms that say everything is "as-is" with no warranties and that they "assume 100% of the … risks." No refund system exists anywhere in the code. Replace the false guarantee with an accurate trust signal.

**Do not build a refund system.** That is explicitly out of scope — a refund policy is a business decision, not a copy fix.

---

## Context you need

- The false claim lives on the `/results` paywall, `frontend/src/app/results/page.tsx`, line 995 — the muted footer line beneath the two payment cards (Annual Pass / Single Job Unlock).
- The contradicting contract is `frontend/src/app/terms/page.tsx`, which the user opens via the "Terms of Service" checkbox on the same paywall. For reference, that file states (line 29): *"you explicitly assume 100% of the physical, financial, and mechanical risks"* and (line 36): all procedures are *"as-is" and "as-available" without warranties of any kind.* **These lines are correct and stay untouched** — the fix is to stop the paywall from contradicting them, not to soften the Terms.
- The app has real, non-contradictory trust signals to lean on instead: every repair step is cited to a RAG-grounded source, and recalls/complaints come from live NHTSA data.

---

## ⚠️ Corrections vs. `imp_part_2.md`

None. Line 995 and the exact current string are accurate as of 2026-07-16.

---

## Exact change

### `frontend/src/app/results/page.tsx` — line 995

**Current**:
```tsx
        <p className="text-muted text-sm" style={{ marginTop: 24 }}>
          Secure Checkout • Instant Lifetime Access • 100% Satisfaction Guarantee
        </p>
```

**Change** — replace the text content only (leave the `<p>`, `className`, and `style` exactly as-is):
```tsx
        <p className="text-muted text-sm" style={{ marginTop: 24 }}>
          Secure Checkout • Instant Lifetime Access • Every Step Cited to a Real NHTSA/OEM Source
        </p>
```

Keep the `•` bullet separators and surrounding spacing identical — only the third clause changes.

---

## Do NOT touch

- `frontend/src/app/terms/page.tsx` — no change. The fix is to stop contradicting it, not to edit it.
- The `<p>` element, its `className`, or its `style`.
- Any refund/checkout logic — there is none to add.

---

## Verification

1. **No guarantee claim remains anywhere**:
   ```bash
   grep -rn "Satisfaction Guarantee\|100% Satisfaction" frontend/src
   ```
   Must return nothing.
2. **Terms page untouched**:
   ```bash
   git diff --name-only | grep -q "terms/page.tsx" && echo "ERROR: terms was modified" || echo "OK: terms untouched"
   ```
   Must print `OK: terms untouched`.
3. **Build passes**:
   ```bash
   cd frontend && ./node_modules/.bin/next build
   ```

---

## Definition of Done

- [ ] Line 995 text replaced; `<p>`/style unchanged
- [ ] `grep` for "Satisfaction Guarantee" returns nothing
- [ ] `terms/page.tsx` shows no diff
- [ ] `next build` passes clean
- [ ] Committed: `fix(results): Block 1.2 replace false satisfaction guarantee with accurate trust signal`
- [ ] `imp_part_2.md` §1 tracker row 1.2 → `✅ Done`; session logged in §5
