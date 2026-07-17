# Implementation Plan Part 2 — Per-Block Execution Specs

> [!IMPORTANT]
> These `block_<N>_<M>.md` files ARE the blocks referenced by any bare **"execute 1.1"** / **"block 2.3"** instruction — those always mean **Part 2** (this directory's parent, [`../imp_part_2.md`](../imp_part_2.md)), the active plan. Part 1 ([`../imp.md`](../imp.md)) is complete and uses different labels (`"Stage X.Y"`, single-number `"Block N"`). Full disambiguation table: `CLAUDE.md` → Step 1.

**Parent plan**: [`../imp_part_2.md`](../imp_part_2.md)
**Created**: 2026-07-16
**Purpose**: One self-contained, code-verified execution doc per block of `imp_part_2.md`. Each file expands its block into an *exact* set of edits — verified against the real codebase on 2026-07-16 — so an executing agent (often a smaller/cheaper model) can complete the block **without reading anything else and without making a judgment call the plan didn't already make for it.**

---

## How these differ from `imp_part_2.md`

`imp_part_2.md` is the authoritative plan and decision record. These docs are the *field manuals*: every line number, current-code snippet, and string in them was re-read against the actual files on 2026-07-16, and every gotcha that would cause a build break or a wrong edit has been surfaced. **Where `imp_part_2.md` turned out to be stale or contain a bug, these docs correct it and flag the correction in a `⚠️ Corrections vs. imp_part_2.md` section** — the executing agent should trust the block doc over the parent plan on any conflict, and note the deviation in the session log.

Notable corrections captured here (do not skip these):

| Block | What the parent plan gets wrong | Consequence if followed literally |
|---|---|---|
| 1.1 | `RAPP_GUIDE_FEE` is used in **two** places in `PartsPurchasePlan.tsx` (lines 80 **and** 237), not one | Deleting the const while fixing only one usage → `next build` fails (undefined variable) |
| 2.1 | Payments migrated **Stripe → Polar**; the confirmed-payment branch lives in `polar_webhook` (`/api/webhooks/payments`), not a Stripe handler | Wrong file/handler; event never fires |
| 2.1 | `POST /api/diagnose` resolves in `results/page.tsx`, **not** `diagnose/page.tsx` | `diagnose_completed` wired to the wrong page |
| 2.1 | `layout.tsx` is a **server component** (no `'use client'`) | Calling `posthog.init()` in it fails to compile / runs on server |
| 2.2 | `signup/page.tsx` is a **redirect stub** to `/signin` (no form/body); auth is magic-link via `requestMagicLink` | Instruction #3 (`?ref=` in "signup request body") is un-actionable as written |
| 2.2 | `repair/success/page.tsx` is a **transient redirect** (`router.replace('/repair')`) — never seen by a user | A referral callout placed there is invisible |
| 3.2 | `TsbRecord.summary` is typed `str \| None` | `record.summary.lower()` raises `AttributeError` on any record with a null summary |

---

## Execution order

Follow the parent plan's ordering — Stage 1 (trust/correctness) first, then Stage 2 (growth), then Stage 3 (polish). Blocks are independent enough to run one at a time, sequentially, one agent per block.

| Block | Doc | Focus | Model | Thinking |
|---|---|---|---|---|
| 1.1 | [block_1_1.md](block_1_1.md) | Stale/wrong price displays + `RAPP_GUIDE_FEE` calc bug + leaked jargon badge | Sonnet 5 | Medium |
| 1.2 | [block_1_2.md](block_1_2.md) | "100% Satisfaction Guarantee" vs. Terms contradiction | Fable 5 | Low |
| 1.3 | [block_1_3.md](block_1_3.md) | De-overclaim "Verified"/"Genuine"/"Exact fit" language | Haiku 5 | Low |
| 1.4 | [block_1_4.md](block_1_4.md) | Harden production email deliverability (fail loud) | Sonnet 5 | Low |
| 2.1 | [block_2_1.md](block_2_1.md) | Baseline funnel analytics (PostHog) | Sonnet 5 | Medium |
| 2.2 | [block_2_2.md](block_2_2.md) | Surface the referral program in the UI | Gemini Flash 3.5 | Medium |
| 2.3 | [block_2_3.md](block_2_3.md) | Wire `/hub` and `/check-ai` into navigation | Gemini Flash 3.5 | Low |
| 2.4 | [block_2_4.md](block_2_4.md) | Operationalize the recall-watch cron | Haiku 5 | Medium |
| 3.1 | [block_3_1.md](block_3_1.md) | Doc consistency pass | Haiku 5 | Low |
| 3.2 | [block_3_2.md](block_3_2.md) | NHTSA ingestion noise filter | Sonnet 5 | Medium |
| 4.1 | [block_4_1.md](block_4_1.md) | Frontend runtime safety (`safeGetJson` crash guards) | Sonnet 5 | Medium |
| 4.2 | [block_4_2.md](block_4_2.md) | UX interaction polish & state preservation | Sonnet 5 | Medium |
| 4.3 | [block_4_3.md](block_4_3.md) | Accessibility, mobile touch, & `.HEIC` OOM hardening | Sonnet 5 | Medium |
| 4.4 | [block_4_4.md](block_4_4.md) | Backend boundary validation & rate limits | Sonnet 5 | Medium |
| 4.5 | [block_4_5.md](block_4_5.md) | Results-page fabricated claims & pre-passed safety checklist | Sonnet 5 | Medium |
| 4.6 | [block_4_6.md](block_4_6.md) | Theme/design coherence pass — light mode, emoji, native dialogs, jargon | Sonnet 5 | Medium |

---

## Standard operating rules for every block

1. **Read your block doc top-to-bottom before editing.** It contains the full context you need.
2. **Line numbers are as of 2026-07-16.** If a file has shifted, match on the *quoted current code* (always included), not the line number.
3. **Verification baseline** — run the relevant checks before committing; do not commit on a failure:
   ```bash
   # Frontend blocks:
   cd frontend && ./node_modules/.bin/next build     # zero TS/ESLint errors
   # Backend blocks:
   uv run ruff check backend/ && uv run black --check backend/ && uv run mypy backend/
   uv run pytest tests/unit/ -v                        # if backend logic changed
   ```
4. **Commit** with a conventional message referencing the block, e.g. `fix(results): Block 1.1 correct guide-fee display + calc`.
5. **Log your session** in `imp_part_2.md` Section 5 (date, model, block, files changed, tests run, handoff notes) and flip the block's row in the Section 1 progress tracker to `✅ Done`.
6. **Do not expand scope.** If you hit a blocker or think a change is wrong, stop and use `/log-decision` per `CLAUDE.md` — do not silently alter the plan.
