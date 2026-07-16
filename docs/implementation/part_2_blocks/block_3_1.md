# Block 3.1 — Doc consistency pass

> **Model**: Haiku 5 · **Thinking**: Low · **Stage**: 3 (Docs & Content Polish) · **Status**: ⬜ Not started
> **Parent**: [`../imp_part_2.md`](../imp_part_2.md) §3.1

---

## TL;DR

Two doc contradictions that AI agents treat as ground truth:
1. RAPP's acronym is expanded two different ways: `CLAUDE.md` says "Automotive AI Repair Engine"; `imp.md:18` says "(Repair AI-Powered Procedure)".
2. `imp.md`'s citation-check section claims `docs/PRODUCT_NORTH_STAR.md` "exists in the repository" and is "100% verified", while `imp.md`'s own later session log records that same file being **deleted as obsolete** (and it is in fact gone).

Fix both — pure doc edits, no code.

---

## ⚠️ Corrections vs. `imp_part_2.md`

Minor line-number drift only: the parent plan calls the citation entry "line 57-58"; the actual entry spans **lines 56-58** of `imp.md`. Match on the quoted text below, not the line number. `docs/PRODUCT_NORTH_STAR.md` is confirmed deleted (not present in `docs/`; removal logged at `imp.md:332`).

---

## Change 1 — Standardize the tagline (`docs/implementation/imp.md`, line 18)

**Current**:
```md
This document outlines the gap analysis and step-by-step implementation plan for RAPP (Repair AI-Powered Procedure), comparing the current codebase state against the requirements in the **Updated Product North Star** (`docs/UPDATED_PRODUCT_NORTH_STAR.md`).
```
**Change** the parenthetical `(Repair AI-Powered Procedure)` → `— Automotive AI Repair Engine` (standardizing on `CLAUDE.md`'s version, since that's the doc every agent reads first):
```md
This document outlines the gap analysis and step-by-step implementation plan for RAPP — Automotive AI Repair Engine, comparing the current codebase state against the requirements in the **Updated Product North Star** (`docs/UPDATED_PRODUCT_NORTH_STAR.md`).
```

Then confirm no other occurrence exists anywhere in `docs/` or `CLAUDE.md`:
```bash
grep -rn "Repair AI-Powered Procedure" docs/ CLAUDE.md
```
Update any other hit the same way. (As of 2026-07-16 the only occurrences outside `imp_part_2.md` itself are `imp.md:18` and the references *inside* `imp_part_2.md`/this doc that quote the old string — **do not** edit the quoted references inside the plan docs; they're describing the problem, not asserting the tagline.)

---

## Change 2 — Fix the deleted-file contradiction (`docs/implementation/imp.md`, lines 56-58)

**Current**:
```md
6. **Doc Citation Check (`docs/UPDATED_PRODUCT_NORTH_STAR.md`)**:
   - *Codebase Verification*: Verified via directory listing on `docs/` — BOTH `docs/PRODUCT_NORTH_STAR.md` (83 lines, up to Section 9) and `docs/UPDATED_PRODUCT_NORTH_STAR.md` (145 lines, including Sections 10-12 and the full execution plan) exist in the repository.
   - *Resolution*: The citation `docs/UPDATED_PRODUCT_NORTH_STAR.md` in this document is **100% accurate and verified**. It points directly to the authoritative 145-line product specification.
```
**Change** — annotate that `PRODUCT_NORTH_STAR.md` was subsequently removed, so the doc no longer contradicts its own later session log:
```md
6. **Doc Citation Check (`docs/UPDATED_PRODUCT_NORTH_STAR.md`)**:
   - *Codebase Verification*: Verified via directory listing on `docs/`. `docs/UPDATED_PRODUCT_NORTH_STAR.md` (145 lines, including Sections 10-12 and the full execution plan) is the authoritative product spec. (The older `docs/PRODUCT_NORTH_STAR.md` was present at the time of this check but has since been removed as obsolete — see the session-log entry below.)
   - *Resolution*: The citation `docs/UPDATED_PRODUCT_NORTH_STAR.md` in this document is accurate and points directly to the authoritative 145-line product specification.
```

---

## Do NOT touch

- `CLAUDE.md`'s tagline line (~7) — it's already the canonical version we're standardizing *to*.
- The session-log entry in `imp.md` (~line 332) that records the removal — it's correct; Change 2 makes the earlier section agree with it, not the other way around.
- Any occurrence of "Repair AI-Powered Procedure" **inside** `imp_part_2.md` or this `part_2_blocks/` folder — those quote the old string to describe the bug; editing them would erase the problem statement.

---

## Verification

1. **Tagline standardized**:
   ```bash
   grep -rn "Repair AI-Powered Procedure" docs/ CLAUDE.md
   ```
   Should return **only** lines inside `imp_part_2.md` / `part_2_blocks/` that *quote* the old string as part of describing this very fix — no live tagline usage in `imp.md` or elsewhere.
2. **No self-contradiction**: `imp.md` no longer asserts `PRODUCT_NORTH_STAR.md` currently exists while its session log says it was deleted.
3. **File really is gone** (sanity): `ls docs/PRODUCT_NORTH_STAR.md` → "No such file".

---

## Definition of Done

- [ ] `imp.md:18` tagline changed to "— Automotive AI Repair Engine"
- [ ] `imp.md:56-58` citation entry annotated with the "since removed" note
- [ ] `grep` shows no live "Repair AI-Powered Procedure" tagline usage (only problem-describing quotes in plan docs)
- [ ] Committed: `docs: Block 3.1 standardize RAPP tagline + fix deleted-file contradiction`
- [ ] `imp_part_2.md` §1 tracker row 3.1 → `✅ Done`; session logged in §5
