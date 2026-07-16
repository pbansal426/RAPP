# RAPP — Implementation Plan Part 2: Trust, Correctness & Growth-Loop Closure

**Reference Docs**: `CLAUDE.md` · `docs/implementation/imp.md` (Part 1 — feature roadmap, 15/15 complete) · `docs/UPDATED_PRODUCT_NORTH_STAR.md`
**Created**: 2026-07-16
**Origin**: A full-app audit (structural + copy/trust/correctness) run across two parallel sub-agents plus direct code inspection, requested explicitly to find "smaller flaws with huge impact" before considering any production launch. This is NOT a new-feature roadmap — every block below is a fix to something that already exists and is already wired into the live app.

> [!IMPORTANT]
> ## ⬅ THIS IS THE ACTIVE IMPLEMENTATION PLAN
> When you are told **"execute 1.1"**, **"do block 2.3"**, or **any bare/two-level block number** (`1.1`–`3.2`), it refers to a block **in this document**. Part 1 ([`imp.md`](imp.md)) is 100% complete and is no longer executed — its `"Stage X.Y"` / single-number `"Block N"` labels are historical. If you're ever unsure which plan a bare number means, see the disambiguation table in `CLAUDE.md` → Step 1.
>
> **To execute a block you MUST open its field manual [`part_2_blocks/block_<N>_<M>.md`](part_2_blocks/) FIRST** (see §0 below) — it overrides this file on any conflict.
>
> **MANDATORY FOR ALL AI AGENTS**: Follow the same 5-step operational protocol as `imp.md` (see `CLAUDE.md`): read this file's active block (and its field manual) before touching code, never silently alter scope, lint/typecheck before committing, log your session in **Section 5** below — and **leave git clean & merged, before and after** (CLAUDE.md **Step 5**: no stray worktrees, no unmerged branches, no uncommitted changes, no open PRs when you finish).

---

## 0. How to use this document

Each block below is written so that an agent can be told **"execute block 1.1"** (or any block number) with no other context and know exactly what to do — the judgment calls (what the replacement copy should say, what the event names should be, what the exact diff looks like) have already been made in this document, not left for the executing agent to invent. This is a deliberate design choice: it lets every block run on a smaller/cheaper model than the task would otherwise need, without any loss of quality, because the "thinking" already happened when this doc was written.

> [!IMPORTANT]
> **⭐ Each block has a dedicated, code-verified execution spec in [`part_2_blocks/`](part_2_blocks/).** When you are told to execute a block, **open [`part_2_blocks/block_<N>_<M>.md`](part_2_blocks/) first** (e.g. block 1.1 → [`part_2_blocks/block_1_1.md`](part_2_blocks/block_1_1.md); index in [`part_2_blocks/README.md`](part_2_blocks/README.md)). Those files re-verify every line number and current-code snippet against the actual codebase, spell out the exact edits, and **flag/correct places where the summary in *this* document is stale or buggy** (e.g. Block 1.1's second `RAPP_GUIDE_FEE` usage, Block 2.1's Stripe→Polar move, Block 2.2's magic-link auth, Block 3.2's `str | None` crash). On any conflict, the `part_2_blocks/` file wins — it is the field manual; this file is the plan of record.

**Model/thinking recommendations below assume sequential execution** — one block finishes before the next starts. They deliberately do not follow `CLAUDE.md`'s Claude-owns-backend/Gemini-owns-frontend split, because that split exists to prevent two agents from colliding on the same files *concurrently*; it doesn't apply when blocks run one at a time. Pick whichever model/thinking level is listed unless you have a specific reason to deviate — if you do deviate, note why in the session log (Section 5).

**Verification baseline for every block**: after making the change, run
```bash
cd frontend && ./node_modules/.bin/next build   # must pass with zero TS/ESLint errors, for any frontend block
uv run ruff check backend/ && uv run black --check backend/ && uv run mypy backend/   # for any backend block
uv run pytest tests/unit/ -v   # for any backend block touching logic (not pure copy strings)
```
Do not commit if any of these fail. Fix forward; don't skip the check.

---

## 1. Progress Tracker

| Block | Focus | Model | Thinking | Status |
|---|---|---|---|---|
| 1.1 | Fix stale/wrong price displays + `RAPP_GUIDE_FEE` calc bug + remove leaked jargon badge | Sonnet 5 | Medium | ✅ Done |
| 1.2 | Resolve "100% Satisfaction Guarantee" vs. Terms-of-Service contradiction | Fable 5 | Low | ✅ Done |
| 1.3 | De-overclaim "Verified"/"Genuine"/"Exact fit" language | Haiku 5 | Low | ✅ Done |
| 1.4 | Harden production email deliverability (fail loud, not silent) | Sonnet 5 | Low | ✅ Done |
| 2.1 | Baseline funnel analytics (PostHog) | Sonnet 5 | Medium | ✅ Done |
| 2.2 | Surface the referral program in the UI | Gemini Flash 3.5 | Medium | ⬜ Not started |
| 2.3 | Wire `/hub` and `/check-ai` into real navigation | Gemini Flash 3.5 | Low | ⬜ Not started |
| 2.4 | Operationalize the recall-watch cron for real | Haiku 5 | Medium | ⬜ Not started |
| 3.1 | Doc consistency pass (name/tagline + imp.md self-contradiction) | Haiku 5 | Low | ⬜ Not started |
| 3.2 | NHTSA ingestion noise filter (future batches only) | Sonnet 5 | Medium | ✅ Done |

Update the Status column to `✅ Done` as each block completes, and log the session in Section 5.

---

## 2. Stage 1 — Trust & Correctness (do first; these actively mislead users today)

### 1.1 Fix stale/wrong price displays + calc bug + remove leaked jargon badge
**Model: Sonnet 5, Thinking: Medium**

**Problem**: Four separate spots show a stale or fabricated dollar figure that doesn't match the real pricing (tiered $4.99/$9.99/$14.99 single-incident + $19.99/yr annual, computed server-side in `backend/pricing.py`), plus one spot leaks an internal roadmap label into production UI.

**Exact changes**:

1. **`frontend/src/app/results/page.tsx:583`** — currently:
   ```tsx
   {diagnosis?.cost_breakdown
     ? `$${diagnosis.cost_breakdown.diy_total.toFixed(2)}`
     : '$39.00'}
   ```
   Change the fallback from `'$39.00'` to `'—'` (a plain em dash, no dollar sign — never show a specific-looking number that isn't real).

2. **`frontend/src/app/results/page.tsx:593`** — currently:
   ```tsx
   Save up to 85% today with exact step-by-step guidance & verified parts (includes {diagnosis?.cost_breakdown ? `$${diagnosis.cost_breakdown.guide_fee.toFixed(2)}` : '$4.00'} guide fee)
   ```
   Change the fallback from `'$4.00'` to `'—'`.

3. **`frontend/src/app/results/page.tsx:973`** — currently:
   ```tsx
   {diagnosis?.cost_breakdown ? `$${diagnosis.cost_breakdown.guide_fee.toFixed(2)}` : '$4.00'}
   ```
   Change the fallback from `'$4.00'` to `'—'`.

4. **`frontend/src/app/results/page.tsx:692`** — currently:
   ```tsx
   <span className="badge" style={{ background: 'rgba(249, 115, 22, 0.15)', color: 'var(--accent-yellow)', fontSize: '0.75rem', fontWeight: 700 }}>
     Stage 2.3 &amp; 2.5 Verified
   </span>
   ```
   Change the badge text from `Stage 2.3 & 2.5 Verified` to `Personalized Guidance`. Do not touch the surrounding `style` or the `<span>` wrapper — only the text content.

5. **`frontend/src/app/results/PartsPurchasePlan.tsx` — the actual calculation bug** (this is more than a display fix). Currently:
   ```tsx
   // Matches backend/pricing.py's RAPP guide fee used in cost_breakdown.diy_total.
   const RAPP_GUIDE_FEE = 4.0;
   ```
   is a **hardcoded flat fee that no longer matches reality** — the real guide fee is tiered ($4.99/$9.99/$14.99) and is already computed server-side, available as `diagnosis.cost_breakdown.guide_fee` in the parent page. This component currently has no way to receive that real value. Fix:
   - Add a `guideFee?: number` prop to the `PartsPurchasePlanProps` interface (top of the file, alongside `parts` and `vehicleTitle`).
   - In the component function signature, destructure it with a safe default: `{ parts, vehicleTitle, guideFee = 4.99 }` (4.99 is the tier-1 floor — a defensible fallback since this component only ever renders once `diagnosis.recommended_parts` is non-empty, meaning `cost_breakdown` has already loaded in practice; the default is defensive, not expected to fire).
   - Delete the module-level `const RAPP_GUIDE_FEE = 4.0;` line entirely and replace its one usage (`const diyTotal = RAPP_GUIDE_FEE + partsTotal;`) with `const diyTotal = guideFee + partsTotal;`.
   - In `frontend/src/app/results/page.tsx`, update the `<PartsPurchasePlan>` invocation (currently lines 515-518) to also pass `guideFee={diagnosis?.cost_breakdown?.guide_fee}`.
   - **Do not** rename or remove the `data-testid="parts-plan-total"` element (line ~222 of `PartsPurchasePlan.tsx`) — it is a frozen contract per `CLAUDE.md`. Only the underlying number it displays changes.

**Verification**: After the fix, manually trace one example — a `brakes` category repair should show `guide_fee: 9.99` from the backend (per `backend/pricing.py`'s tier thresholds), and the parts-plan total footer should reflect `9.99 + partsTotal`, not `4.0 + partsTotal`. Confirm no `'$39.00'`, `'$4.00'`, or `'Stage 2.3'` strings remain anywhere in `results/page.tsx` (`grep -n "39.00\|\\$4.00\|Stage 2\." frontend/src/app/results/page.tsx` should return nothing).

---

### 1.2 Resolve "100% Satisfaction Guarantee" vs. Terms-of-Service contradiction
**Model: Fable 5, Thinking: Low**

**Problem**: `frontend/src/app/results/page.tsx:995` currently reads:
```tsx
<p className="text-muted text-sm" style={{ marginTop: 24 }}>
  Secure Checkout • Instant Lifetime Access • 100% Satisfaction Guarantee
</p>
```
This sits directly above the payment buttons on the same screen where the user must check a Terms-of-Service box (`frontend/src/app/terms/page.tsx`) stating everything is provided "as-is"/"as-available" with no warranties, and that the user "explicitly assume[s] 100% of the physical, financial, and mechanical risks." No refund policy exists anywhere in the codebase (backend has no refund endpoint, no refund logic, Terms mentions none). The word "Guarantee" directly contradicts the contract the user is forced to agree to on the same screen.

**The decision (already made — just apply it)**: Do not build a real refund system (out of scope for this block; a genuine refund policy is a business decision, not a copy fix). Instead, replace the false claim with an accurate one that's still trust-building, since the app already has real, non-contradictory trust signals to lean on (RAG-grounded citations, real NHTSA source data).

**Exact change** — `frontend/src/app/results/page.tsx:995`, replace:
```tsx
Secure Checkout • Instant Lifetime Access • 100% Satisfaction Guarantee
```
with:
```tsx
Secure Checkout • Instant Lifetime Access • Every Step Cited to a Real NHTSA/OEM Source
```
Do not change the surrounding `<p>` tag, className, or style — only the text content.

**Verification**: `grep -rn "Satisfaction Guarantee\|100% Satisfaction" frontend/src` should return nothing. Confirm `frontend/src/app/terms/page.tsx` is untouched by this block (no change needed there — the fix is to stop contradicting it, not to soften it).

---

### 1.3 De-overclaim "Verified"/"Genuine"/"Exact fit" language
**Model: Haiku 5, Thinking: Low**

**Problem**: Several places claim more certainty than the underlying mechanism actually provides. All parts links are Amazon/AutoZone/RockAuto keyword-search URLs (`backend/pricing.py::_search_url`) — there is no fitment verification, no inventory check, no live price lookup anywhere in the code. Calling these "Verified" or "Genuine" or claiming "Exact factory fit" overclaims what the product does and could reasonably make a user think RAPP guaranteed compatibility.

**Exact changes** (five spots, all pure string replacement — no logic changes except where noted):

1. **`backend/pricing.py`** — in `build_part_options`, the OEM tier's `rationale` string currently reads:
   ```python
   "rationale": "Exact factory fit and spec — the safest choice for warranty and long-term reliability.",
   ```
   Change to:
   ```python
   "rationale": "Matches OEM spec — a safe choice for warranty and long-term reliability.",
   ```

2. **`backend/pricing.py`** — the Aftermarket/Budget tier's `rationale` string currently reads:
   ```python
   "rationale": "Reliable daily-driver replacement at the lowest verified price point.",
   ```
   Change to:
   ```python
   "rationale": "Reliable daily-driver replacement at a low estimated price point.",
   ```
   (The word "verified" is wrong here — `estimated_price` comes from `parse_part_price`, a regex parse of template text, not a live price check.)

3. **`backend/pricing.py`** — the OEM tier's `"brand"` field currently reads `"OEM / Genuine Dealer Part"`. Change to `"OEM-Spec Part"`.

   **⚠️ Coupled change — do this in the same pass or you will introduce a new bug**: `frontend/src/app/results/PartsPurchasePlan.tsx`'s `buildDisplayOptions` function does an exact string match against this same brand label:
   ```tsx
   const opt1Brand = isOilFluidFilter && opt1?.brand === 'OEM / Genuine Dealer Part' ? 'Mobil 1 / Castrol' : (opt1?.brand || 'OEM Factory');
   ```
   and
   ```tsx
   const opt1Rationale = isOilFluidFilter && opt1?.rationale.includes('factory fit')
     ? '...'
     : (opt1?.rationale || 'Exact factory spec and fitment.');
   ```
   Update the string literal `'OEM / Genuine Dealer Part'` in this file to `'OEM-Spec Part'` to match the new backend value — if you change the backend string without this, the oil/fluid/filter branch (which relabels parts as "Mobil 1 / Castrol" for oil-type items) silently stops matching and breaks. Also update the fallback rationale `'Exact factory spec and fitment.'` (same overclaiming pattern) to `'Matches OEM spec and fitment.'`, and the `.includes('factory fit')` check to `.includes('OEM spec')` to match the new rationale wording from change #1 above. Leave the Aftermarket/Budget brand string (`'Duralast / equivalent aftermarket'`) untouched — that one is fine, it names a real aftermarket brand without an accuracy claim.

4. **`frontend/src/app/results/PartsPurchasePlan.tsx`** — the section header currently reads:
   ```tsx
   <h2 className="section-title" style={{ margin: 0 }}>Verified Parts &amp; Tool Purchase Recommendations</h2>
   ```
   Change to:
   ```tsx
   <h2 className="section-title" style={{ margin: 0 }}>Recommended Parts &amp; Tool Purchase Options</h2>
   ```

5. **`frontend/src/app/results/page.tsx:433`** — the badge currently reads:
   ```tsx
   <span className="badge badge-free">Verified AI Analysis</span>
   ```
   Change to:
   ```tsx
   <span className="badge badge-free">AI-Generated, RAG-Grounded Analysis</span>
   ```

**Do not touch**: `frontend/src/app/results/page.tsx:417`'s complaints-summary copy ("Based on {N} unverified NHTSA consumer complaints... not confirmed defects") — this is already correctly hedged and is the model to match, not a thing to fix.

**Verification**: `grep -rn "Genuine Dealer\|Exact factory fit\|Verified Parts\|Verified AI Analysis\|lowest verified price" backend/pricing.py frontend/src/app/results/` should return nothing. Manually confirm the oil/fluid/filter relabeling branch in `PartsPurchasePlan.tsx` still fires correctly for an oil-change repair (the "Premium Synthetic Oil" / "Standard Conventional Oil" titles should still appear, not the generic "OEM Factory Part" / "Premium Aftermarket" titles) — this is the concrete regression this block could introduce if the coupled string change in #3 is missed.

---

### 1.4 Harden production email deliverability
**Model: Sonnet 5, Thinking: Low**

**Problem**: `backend/core/config.py:56` defaults `email_from` to `"RAPP <onboarding@resend.dev>"` — Resend's sandbox address, which **only delivers to the account owner's own inbox** until a custom domain is verified with Resend. `backend/routers/auth.py` already fails closed correctly in every way code can control (never leaks the magic link outside dev, never lets callers distinguish a real account from a fake one) — but nothing currently stops a staging/production deploy from silently running with the sandbox `email_from` address, meaning **every real user's sign-in email would 4xx and never arrive**, logged only as a `structlog` warning (`magic_link_send_failed`) that nobody is actively watching.

**This block has two parts — one is code, one is NOT code (flag it, don't attempt it)**:

1. **Code fix**: `backend/core/config.py` already has a `model_validator` that fails startup if `RESEND_API_KEY` is missing in staging/production (lines 91-99):
   ```python
   @model_validator(mode="after")
   def _require_resend_key_outside_dev(self) -> "Settings":
       if self.environment in EMAIL_REQUIRED_ENVIRONMENTS and not self.resend_api_key:
           raise ValueError(
               f"RESEND_API_KEY must be set when ENVIRONMENT={self.environment!r} -- "
               "magic-link auth is not allowed to fall back to leaking the sign-in "
               "link in the API response outside development/test."
           )
       return self
   ```
   Extend this same validator (don't add a second one — keep the fail-fast check in one place) to also raise if `email_from` still contains the sandbox domain in a required-email environment:
   ```python
   @model_validator(mode="after")
   def _require_resend_key_outside_dev(self) -> "Settings":
       if self.environment in EMAIL_REQUIRED_ENVIRONMENTS:
           if not self.resend_api_key:
               raise ValueError(
                   f"RESEND_API_KEY must be set when ENVIRONMENT={self.environment!r} -- "
                   "magic-link auth is not allowed to fall back to leaking the sign-in "
                   "link in the API response outside development/test."
               )
           if "resend.dev" in self.email_from:
               raise ValueError(
                   f"email_from is still Resend's sandbox address ({self.email_from!r}) "
                   f"in ENVIRONMENT={self.environment!r} -- Resend's sandbox sender only "
                   "delivers to the account owner's own inbox, so every real user's "
                   "magic-link email would silently fail. Verify a custom domain with "
                   "Resend and set EMAIL_FROM to an address on that domain before deploying."
               )
       return self
   ```

2. **Not code — flag this clearly in your session log and do not attempt it**: a human must actually verify a real domain with Resend (DNS TXT/CNAME records, done in Resend's dashboard) and set `EMAIL_FROM` to an address on that domain in the deployed environment's actual env vars. No AI agent can complete this — it requires DNS access to a real owned domain. This block's code fix exists specifically so a deploy **fails loudly at startup** instead of silently shipping broken auth, which is the part actually fixable in code.

**Verification**: `uv run pytest tests/unit/ -v` still passes (the new check only fires when `environment` is `staging`/`production`, which local test runs never set). Manually confirm: setting `ENVIRONMENT=production` and `RESEND_API_KEY=some-key` with `EMAIL_FROM` left at its default now raises a clear `ValueError` on startup instead of starting silently.

---

## 3. Stage 2 — Measurement & Growth-Loop Closure

### 2.1 Baseline funnel analytics
**Model: Sonnet 5, Thinking: Medium**

**Problem**: Zero analytics/telemetry exists anywhere in the codebase (confirmed: no PostHog, GA, Amplitude, Mixpanel, or Segment references in `backend/` or `frontend/src/`), despite `docs/UPDATED_PRODUCT_NORTH_STAR.md`'s own pricing-strategy section assuming "post-launch cohort telemetry" exists to monitor whether the $14.99 single-tier price cannibalizes the $19.99/yr annual pass. You cannot optimize a funnel you can't see.

**This block requires a human-provided key first — flag this, don't block on it**: a PostHog account (free tier) must be created and its Project API Key obtained before this is wired live. The code below should be written to **no-op safely** if the key isn't configured (matching the existing pattern for `RESEND_API_KEY`/`GEMINI_API_KEY`/`STRIPE_SECRET_KEY` elsewhere in this codebase — never crash or block core functionality on a missing third-party key).

**Event taxonomy (already decided — implement exactly this, do not invent additional events)**:

| Event name | Fired where | Key properties |
|---|---|---|
| `vin_submitted` | `frontend/src/app/page.tsx`, at the point each of the 4 VIN-entry paths (manual/YMM/photo/scan) successfully resolves a VIN | `method: "manual" \| "ymm" \| "photo" \| "scan"` |
| `diagnose_completed` | `frontend/src/app/diagnose/page.tsx` or wherever `POST /api/diagnose` resolves successfully | `is_high_risk: boolean`, `has_recommended_parts: boolean` |
| `results_viewed` | `frontend/src/app/results/page.tsx`, on mount once `diagnosis` has loaded | `guide_fee: number`, `has_recalls: boolean` |
| `checkout_started` | `frontend/src/app/results/page.tsx`, inside `handlePay`, right before the API call | `price_type: "single" \| "annual"` |
| `checkout_completed` | backend, `backend/routers/payments.py`'s webhook handler, on confirmed payment (`payment_confirmed` branch already in the code) | `price_type`, `vin` (do not send symptoms/PII) |

**Implementation**:
- **Frontend**: add `posthog-js` to `frontend/package.json`. Initialize once in `frontend/src/app/layout.tsx` behind a check for `process.env.NEXT_PUBLIC_POSTHOG_KEY` (no-op if unset — do not throw). Add a small `frontend/src/lib/analytics.ts` exporting a single `track(event: string, properties?: Record<string, unknown>)` helper that wraps `posthog.capture` and no-ops if PostHog was never initialized — this matches the existing single-wrapper pattern already used for API calls (`lib/api.ts`) and auth (`lib/auth.ts`), so don't add raw `posthog.capture()` calls scattered through page components.
- **Backend**: add the `posthog` Python package (note: it is already a transitive dependency per `uv.lock`, but not currently imported anywhere — add it as a direct dependency in `pyproject.toml` since relying on an unlisted transitive package is fragile). Add a `backend/services/analytics.py` with a single `track(event: str, properties: dict | None = None)` function reading `POSTHOG_API_KEY` from `backend/core/config.py`'s `Settings` (add this field, default `None`), no-op if unset.
- Call `track(...)` at exactly the 5 points in the table above — nowhere else in this block.

**Verification**: With no `POSTHOG_API_KEY`/`NEXT_PUBLIC_POSTHOG_KEY` set (the default), confirm the app behaves identically to before this block (no errors, no network calls to PostHog). With a real free-tier key set, manually walk through VIN entry → diagnose → results → checkout-start and confirm all 4 frontend events appear in the PostHog project's live event stream.

---

### 2.2 Surface the referral program in the UI
**Model: Gemini Flash 3.5, Thinking: Medium**

**Problem**: The referral program is fully real on the backend — `backend/routers/auth.py` accepts a `referral_code` on signup, credits both the referrer and the new signup, and exposes `referral_code`/`referral_credits` via `GET /api/auth/me` (`backend/schemas.py:203-204`). But `grep`ing the entire frontend for "referral" returns zero results — there is no page, no settings display, no share link, nothing. A user cannot discover their own referral code exists.

**Exact changes**:

1. **`frontend/src/lib/auth.ts`** — the `AuthUser` interface (line 8) and `UserResponse` interface (line 18) are both missing `referral_code`/`referral_credits` entirely, even though the backend already returns them on `/api/auth/me`. Add to both interfaces:
   ```ts
   referralCode: string;
   referralCredits: number;
   ```
   (on `AuthUser`, camelCase per this file's existing convention — see how `display_name` maps to `displayName` at line 37) and
   ```ts
   referral_code: string;
   referral_credits: number;
   ```
   (on `UserResponse`, matching the raw API's snake_case). Update the mapping function (near line 37) to translate `referral_code` → `referralCode`, `referral_credits` → `referralCredits`.

2. **`frontend/src/app/settings/page.tsx`** — add a new card (matching the existing card pattern at lines 71 and 98) titled "Invite Friends, Earn Credit" showing:
   - The user's referral code/link in a read-only input: `${window.location.origin}/signup?ref=${user.referralCode}`
   - A "Copy Link" button using `navigator.clipboard.writeText(...)`
   - The current credit balance: `You've earned {user.referralCredits} credit(s) so far.`

3. **`frontend/src/app/signup/page.tsx`** — read a `?ref=` query param on mount (matching the existing `<Suspense>`-wrapped search-param pattern already used by `repair/success/page.tsx` and `verify-email/page.tsx`) and pre-fill/pass it as `referral_code` in the signup request body — check `backend/schemas.py:179` for the exact field name the signup endpoint already accepts (`referral_code: str | None = None`).

4. **`frontend/src/app/repair/success/page.tsx`** (the post-purchase landing page) — add a single-line, dismissible callout below the existing success content: `"Know someone who'd find this useful? Share your referral link and you'll both get credit."` linking to `/settings` (do not build a separate share modal here — route to the existing settings card from #2 to avoid duplicating the copy-link UI in two places).

**Verification**: Sign up a fresh test account using a `?ref=<existing-user-code>` URL and confirm (via `GET /api/auth/me` for both accounts) that both the referrer and the new signup show increased `referral_credits`. Confirm the settings-page card renders the correct code/link and the copy button actually copies the full URL (not just the bare code).

---

### 2.3 Wire `/hub` and `/check-ai` into real navigation
**Model: Gemini Flash 3.5, Thinking: Low**

**Problem**: Both `/hub` (Knowledge Hub content) and `/check-ai` ("Check My ChatGPT Answer" acquisition funnel) are fully built pages with zero inbound links anywhere in the app. `frontend/src/app/HeaderAuthLink.tsx` — the only persistent global UI element across pages (a fixed top-right corner widget; note its own comment says it's "Temporary home... until the Phase B navbar replaces this whole corner widget") — currently only links to `/garage`, `/settings`, `/signin`. Neither `/hub/[slug]` nor `/check-ai` link back to anything either.

**Exact changes**:

1. **`frontend/src/app/HeaderAuthLink.tsx`** — add two links inside the existing fixed-position `<div>`, visible regardless of auth state (unlike the existing Garage/Settings links, which are gated behind `user &&`):
   ```tsx
   <a href="/hub" style={{ ...linkStyle, color: 'var(--text-secondary)' }}>Guides</a>
   <a href="/check-ai" style={{ ...linkStyle, color: 'var(--text-secondary)' }}>Check My AI Answer</a>
   ```
   Place these before the `{configured && !loading && (...)}` auth-gated block so they always show, matching the existing `linkStyle` object already defined in this file.

2. **`frontend/src/app/results/page.tsx`** — add one contextual link near the free diagnosis summary (the "Free Diagnosis & Mod Overview" card, around line 430): a small text link reading `"Already asked ChatGPT about this? Verify its answer against real OEM data →"` linking to `/check-ai`. This is the actual acquisition-funnel intercept point per the original design intent (`imp.md` 2.6) — a user skeptical of/comparing against another AI is exactly who should see this, at exactly the moment they're evaluating RAPP's diagnosis.

**Verification**: From a fresh page load of `/`, confirm both `/hub` and `/check-ai` are reachable via a visible click, not just a typed URL. Confirm the existing E2E suite (`tests/e2e-mvp-flow.spec.ts`) still passes — these are additive links, not changes to any frozen `data-testid`.

---

### 2.4 Operationalize the recall-watch cron
**Model: Haiku 5, Thinking: Medium**

**Problem**: `backend/scripts/recall_watch_cron.py` is fully implemented — it walks every saved vehicle, checks NHTSA for open recalls, and emails the owner. But nothing in this repo actually schedules it; its own docstring says "run manually" or "schedule via cron/launchd." **Do not use GitHub Actions for this** — the accounts database (`data/rapp.db`) lives on local disk on whichever Mac runs the backend, not anywhere a GitHub-hosted runner could reach. The correct mechanism, given the current architecture (a locally-run FastAPI server), is `launchd` (macOS's native scheduler) or a plain user crontab entry on that same host.

**Exact changes**:

1. Create `scripts/com.rapp.recall-watch.plist`:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
       <key>Label</key>
       <string>com.rapp.recall-watch</string>
       <key>ProgramArguments</key>
       <array>
           <string>/bin/bash</string>
           <string>-lc</string>
           <string>cd /path/to/RAPP &amp;&amp; uv run python -m backend.scripts.recall_watch_cron</string>
       </array>
       <key>StartCalendarInterval</key>
       <dict>
           <key>Hour</key>
           <integer>8</integer>
           <key>Minute</key>
           <integer>0</integer>
       </dict>
       <key>StandardOutPath</key>
       <string>/tmp/rapp-recall-watch.log</string>
       <key>StandardErrorPath</key>
       <string>/tmp/rapp-recall-watch.log</string>
   </dict>
   </plist>
   ```
   Note the literal `/path/to/RAPP` placeholder — this must be replaced with the real absolute path of whichever machine this gets installed on; it cannot be hardcoded to this dev machine's path since that would break portability. Document this substitution step clearly in the Makefile target below rather than hardcoding a path that only works here.

2. Add a `Makefile` target (alongside the existing `backup-db` target mentioned in `CLAUDE.md`):
   ```makefile
   recall-watch-install:
   	@echo "Installing recall-watch daily cron (8am) via launchd..."
   	sed "s|/path/to/RAPP|$(shell pwd)|g" scripts/com.rapp.recall-watch.plist > ~/Library/LaunchAgents/com.rapp.recall-watch.plist
   	launchctl load ~/Library/LaunchAgents/com.rapp.recall-watch.plist
   	@echo "Installed. Logs at /tmp/rapp-recall-watch.log"

   recall-watch-uninstall:
   	launchctl unload ~/Library/LaunchAgents/com.rapp.recall-watch.plist || true
   	rm -f ~/Library/LaunchAgents/com.rapp.recall-watch.plist

   recall-watch-once:
   	uv run python -m backend.scripts.recall_watch_cron
   ```

3. Document this in `docs/onsite_ingestion_runbook.md`'s sibling ops doc, or add a short section to `CLAUDE.md`'s Commands section: `make recall-watch-install` to schedule, `make recall-watch-once` to test a single run immediately.

**Verification**: Run `make recall-watch-once` against a test account with a saved repair for a vehicle with a known open recall (pick any real VIN with a currently-open NHTSA recall for testing) and confirm an email attempt is logged. Run `make recall-watch-install` and confirm `launchctl list | grep rapp` shows the job registered.

---

## 4. Stage 3 — Docs & Content Efficiency Polish

### 3.1 Doc consistency pass
**Model: Haiku 5, Thinking: Low**

**Problem**: Two contradictions in the docs AI agents are told to treat as ground truth:
1. RAPP's tagline is given two different meanings for the same acronym: `CLAUDE.md` line ~7 says "RAPP — Automotive AI Repair Engine"; `docs/implementation/imp.md` line 18 says "RAPP (Repair AI-Powered Procedure)."
2. `imp.md` line 57 says `docs/PRODUCT_NORTH_STAR.md` "exists in the repository" as part of a citation-accuracy verification; `imp.md`'s own session log (same file, same date, later section) says that exact file was deleted as obsolete. The file is in fact gone.

**Exact changes**:
1. Standardize on **"RAPP — Automotive AI Repair Engine"** (the version in `CLAUDE.md`, since that's the doc every agent reads first and treats as overriding default behavior per its own header). Update `docs/implementation/imp.md` line 18's parenthetical from `(Repair AI-Powered Procedure)` to `— Automotive AI Repair Engine`. Grep the rest of `docs/` for any other occurrence of "Repair AI-Powered Procedure" and update those too.
2. In `imp.md`, edit the line 57-58 citation-verification entry to note the file was subsequently removed as obsolete (add a parenthetical: "since removed — see the session log entry below"), rather than leaving a flat contradiction between two sections of the same document.

**Verification**: `grep -rn "Repair AI-Powered Procedure" docs/` returns nothing. `imp.md` no longer asserts a file exists in one section while its own later section says it was deleted.

---

### 3.2 NHTSA ingestion noise filter
**Model: Sonnet 5, Thinking: Medium**

**Problem**: A live sample of NHTSA records for the 2015 Chevrolet Silverado 1500 (pulled directly via `etl/clients/nhtsa_communications.py`'s `list_communications`, during the on-site ingestion batch) showed a large share of the 1,488 "manufacturer communications" are pure dealer-process administrative bulletins with zero repair relevance — e.g. *"how to save a GDS2 session log and upload to a Technical Assistance Case,"* *"how to email GDS2 session logs into Technical Assistance."* These get downloaded, parsed, chunked, and embedded into the RAG store identically to genuine repair TSBs, costing ingestion time and diluting future retrieval with chunks that could never be relevant to a user's symptom-based query.

**This block applies to future ingestion batches only — do not touch the currently-running or already-completed batch's data.** This is a pipeline improvement, not a cleanup of existing chunks (removing already-ingested noise from the live store is a separate, riskier operation not in scope here).

**Exact change** — `etl/pipeline.py`, inside the per-record loop in `run_full_ingest` (around the `for record in records:` loop, before `client.resolve_documents(record)` is called): add a pre-filter check against `record.summary` using a conservative keyword blocklist. Only skip records that are **unambiguously** administrative — err heavily toward keeping anything ambiguous, since a false-positive filter (losing a genuine repair TSB) is worse than a little noise:

```python
# Conservative blocklist: these phrase patterns only ever appear on pure
# dealer-process/tooling bulletins (verified against real NHTSA samples
# during the 2026-07-16 on-site batch), never on genuine repair/failure
# TSBs. Deliberately narrow -- a false-positive skip here silently loses
# real repair content, which is worse than a little ingestion noise.
_ADMINISTRATIVE_SUMMARY_PATTERNS = (
    "session log",
    "gds2",
    "cx connect",
    "technical assistance case",
    "how to email",
)

def _is_administrative_record(record: TsbRecord) -> bool:
    summary_lower = record.summary.lower()
    return any(pattern in summary_lower for pattern in _ADMINISTRATIVE_SUMMARY_PATTERNS)
```

In the loop, right after `for record in records:` and before the existing `try: documents = client.resolve_documents(record)` call, add:
```python
if _is_administrative_record(record):
    log.info(f"Skipping administrative bulletin (NHTSA ID {record.nhtsa_id}): {record.summary[:80]}")
    continue
```

Add a `dry_run` mode before trusting this on a real batch: write a small one-off script (not part of the permanent CLI) that calls `list_communications` for 3-4 already-ingested vehicles and reports how many records the new filter *would* have skipped, printing each skipped record's full summary for manual eyeball review — confirm none of them look like genuine repair content before relying on this filter for a real ingestion run.

**Verification**: Run the dry-run check described above against at least 2 vehicles already in the KB. Manually read every summary the filter would skip — if any look even slightly like they could be repair-relevant (not purely administrative), tighten the blocklist patterns rather than proceeding. Only after that manual review passes should this filter be used on a real `ingest_seed_vehicles.py` run.

---

## 5. Active Execution Log & AI Session Audit Trail

<!-- Append one entry per session here: date, agent/model used, blocks completed, files changed, tests run, handoff notes for the next session. -->

### 2026-07-16 — Claude (Opus 4.8) — Block 2.1 complete

- **Block**: 2.1 — Baseline funnel analytics (PostHog). Status → ✅ Done.
- **Followed `part_2_blocks/block_2_1.md` verbatim**, including its 3 corrections vs. this parent plan: `diagnose_completed` fired in `results/page.tsx` (not `diagnose/page.tsx`); `checkout_completed` fired in the Polar webhook (not a Stripe handler); PostHog init done via a client component since `layout.tsx` is a server component.
- **Files changed**: NEW `frontend/src/lib/analytics.ts` (single wrapper, no-op when `NEXT_PUBLIC_POSTHOG_KEY` unset), NEW `frontend/src/app/PostHogInit.tsx` (client init component), NEW `backend/services/analytics.py` (server wrapper, no-op when `POSTHOG_API_KEY` unset). Edited `frontend/package.json` (+`posthog-js`), `pyproject.toml` (+`posthog`), `backend/core/config.py` (`posthog_api_key`/`posthog_host` settings), `frontend/src/app/layout.tsx` (render `<PostHogInit/>`), `frontend/src/app/page.tsx` (`vin_submitted` at all 4 VIN paths via a `method` param on `decodeAndGo` + explicit calls for ymm/photo/scan), `frontend/src/app/results/page.tsx` (`diagnose_completed`, `results_viewed` effect, `checkout_started`), `backend/routers/payments.py` (`checkout_completed` after `_record_guide_unlock`, vin+price_type only, no PII). Exactly the 5 specced events — no others.
- **Tests**: `cd frontend && ./node_modules/.bin/next build` → 24/24 pages, zero TS/ESLint errors. `uv run pytest tests/unit/` → 199 passed. `uv run ruff check backend/`, `uv run black --check backend/`, `uv run mypy backend/` all pass. App is no-op-safe with no key set (default) — verification ran entirely on build/lint/type/unit paths, **no live Gemini or PostHog network calls**.
- **⚠️ OUTSTANDING HUMAN-ONLY TASK (handoff, not a blocker)**: create a free-tier PostHog account + project and set `NEXT_PUBLIC_POSTHOG_KEY` / `POSTHOG_API_KEY` (+ optional `*_HOST`) in the deployed env before events flow. Logged in the new repo-level checklist `docs/DEFERRED_HUMAN_TASKS.md` (item 2).
- **Handoff**: next block per tracker: 2.2 (surface referral program in UI).

### 2026-07-16 — Claude (Opus 4.8) — Block 1.4 complete

- **Block**: 1.4 — Harden production email deliverability (fail loud, not silent). Status → ✅ Done.
- **Files changed**: `backend/core/config.py` (extended the existing `_require_resend_key_outside_dev` `model_validator` — kept it a single validator, added a sandbox-sender check that raises `ValueError` when `email_from` still contains `resend.dev` in `staging`/`production`). `tests/unit/test_config.py` (updated `test_settings_allows_configured_resend_key_outside_dev` to pass a real `email_from`; added `test_settings_rejects_sandbox_sender_outside_dev` and `test_settings_allows_sandbox_sender_in_development`). `docs/implementation/imp_part_2.md` (this tracker + log).
- **Followed `part_2_blocks/block_1_4.md` verbatim** (no corrections vs. parent plan; validator was at 91-99 and `email_from` at 56 as documented). The sandbox default on line 56 was left unchanged — it's correct for local dev; the validator only rejects it in staging/production.
- **Tests**: `uv run pytest tests/unit/` → 196 passed (2 pre-existing config tests updated to supply a real sender since the new guard correctly rejects the sandbox default). `uv run ruff check backend/`, `uv run black --check backend/`, `uv run mypy backend/` all pass. Guard verified via one-liners: `ENVIRONMENT=production RESEND_API_KEY=test-key` raises `ValueError` mentioning the sandbox address; adding `EMAIL_FROM="RAPP <hello@example.com>"` prints `OK`.
- **⚠️ OUTSTANDING HUMAN-ONLY OPS TASK (handoff, not a blocker)**: a human must verify a real owned domain with Resend (DNS TXT/CNAME records in Resend's dashboard) and set `EMAIL_FROM` to an address on that verified domain in each deployed (staging/production) environment's actual env vars. **No AI agent can complete this** — it requires DNS control over a real domain. Until it's done, a staging/production deploy will now **refuse to boot** (by design) rather than silently ship broken magic-link auth. The code fix is the deliverable and is complete; this note is the remaining human action.
- **Handoff**: backend-only change; no frontend/runtime API surface touched. Next block per tracker: 2.1.

### 2026-07-16 — Claude (Opus 4.8) — Block 3.2 complete

- **Block**: 3.2 — NHTSA ingestion noise filter (future batches only). Status → ✅ Done.
- **Files changed**: `etl/pipeline.py` (added `_ADMINISTRATIVE_SUMMARY_PATTERNS` + `_is_administrative_record` helper at module level with the `(record.summary or "")` None-guard; inserted the skip check at the top of `run_full_ingest`'s `for record in records:` loop). `docs/implementation/imp_part_2.md` (this tracker + log).
- **Bug fix vs. parent plan**: used the `part_2_blocks/block_3_2.md` None-guard (`TsbRecord.summary` is `str | None`) — the parent plan's bare `record.summary.lower()` would `AttributeError` on any null-summary record.
- **Deviation (blocklist tightened after dry-run — logged per §2 zero-silent-drift rule)**: the plan's blocklist included a bare `"gds2"` pattern. The mandatory dry-run (Silverado 1500, Equinox, Altima via live `list_communications`) showed `"gds2"` caught **genuine repair bulletins** — notably NHTSA 10190387 ("recover the TCM before declaring it a bad part and replacing") and 10138054 (SPS module-programming error). Every *truly* administrative record also matched `"session log"` or `"technical assistance case"`, so **`"gds2"` was removed**: zero loss of real admin coverage, both false positives eliminated. Final blocklist: `("session log", "cx connect", "technical assistance case", "how to email")`. Post-tightening dry-run: Silverado 13/1488, Equinox 26/1943, Altima 0/331 — all remaining skips manually confirmed purely administrative (GM TAC-contact / session-log-upload bulletins).
- **Tests**: `ruff check etl/`, `black --check etl/`, `mypy etl/` all pass (17 files). Dry-run script was throwaway (deleted, not committed).
- **Handoff**: filter applies to **future** `run_full_ingest` batches only; already-ingested chunks untouched. Merge this before launching any new/continued ingestion batch so the filter takes effect. No app/runtime surface changed (ETL-only).

### 2026-07-16 — Claude (Sonnet 5) — Block 1.1 complete

- **Block**: 1.1 — Fix stale/wrong price displays + `RAPP_GUIDE_FEE` calc bug + remove leaked jargon badge. Status → ✅ Done.
- **Files changed**: `frontend/src/app/results/page.tsx` (5 edits: `'$39.00'`→`'—'` diy_total fallback, `'$4.00'`→`'—'` guide-fee fallback ×2, `Stage 2.3 &amp; 2.5 Verified`→`Personalized Guidance` badge text, added `guideFee={diagnosis?.cost_breakdown?.guide_fee}` prop to `<PartsPurchasePlan>`); `frontend/src/app/results/PartsPurchasePlan.tsx` (deleted hardcoded `const RAPP_GUIDE_FEE = 4.0`, added `guideFee?: number` prop with `= 4.99` default, switched both usages — the `diyTotal` calc and the budget-footer copy string — to the real prop value). `docs/implementation/imp_part_2.md` (this tracker + log).
- **Followed `part_2_blocks/block_1_1.md` verbatim**, including its correction over the parent plan (the second `RAPP_GUIDE_FEE` usage at the budget-footer line that the parent plan's summary missed).
- **Tests**: `cd frontend && ./node_modules/.bin/next build` — compiled successfully, zero TS/ESLint errors (two pre-existing unrelated `react-hooks/exhaustive-deps` warnings on `repair/page.tsx`/`results/page.tsx` line 197, untouched by this block). `grep -n "RAPP_GUIDE_FEE" PartsPurchasePlan.tsx` → empty (both usages removed). `grep -n "39.00\|\$4.00\|Stage 2\."page.tsx` → only pre-existing internal JSX *comments* referencing "Stage 2.1/2.2/2.3/2.5" remain (lines 310/675/704/778) — not user-visible text and out of this block's specced scope (only the rendered badge at line 692 was in scope); left untouched per "Do NOT touch" guidance to avoid drift beyond the specced edits.
- **Handoff**: no backend change, no other block touched. Next block per tracker: 1.2 (Satisfaction Guarantee vs. ToS contradiction).

### 2026-07-16 — Antigravity — Block 1.2 complete

- **Block**: 1.2 — Resolve "100% Satisfaction Guarantee" vs. Terms-of-Service contradiction. Status → ✅ Done.
- **Files changed**: `frontend/src/app/results/page.tsx` (line 995: replaced `100% Satisfaction Guarantee` with `Every Step Cited to a Real NHTSA/OEM Source`). `docs/implementation/imp_part_2.md` (this tracker + log).
- **Followed `part_2_blocks/block_1_2.md` verbatim**, leaving `terms/page.tsx` and all `<p>` tags/styles untouched.
- **Tests**: `next build` — compiled successfully with zero TS/ESLint errors. `grep -rn "Satisfaction Guarantee\|100% Satisfaction" frontend/src` → empty. `terms/page.tsx` diff check → `OK: terms untouched`.
- **Handoff**: no backend change, no other block touched. Next block per tracker: 1.3 (De-overclaim "Verified"/"Genuine"/"Exact fit" language).

### 2026-07-16 — Antigravity — Block 1.3 complete

- **Block**: 1.3 — De-overclaim "Verified"/"Genuine"/"Exact fit" language. Status → ✅ Done.
- **Files changed**: `backend/pricing.py` (Edits 1-3: de-overclaimed Aftermarket rationale, OEM brand `"OEM-Spec Part"`, OEM rationale `"Matches OEM spec — ..."`). `frontend/src/app/results/PartsPurchasePlan.tsx` (Edits 4-6: updated coupled oil/fluid/filter exact matchers to `'OEM-Spec Part'` and `'OEM spec'`, and de-overclaimed section header). `frontend/src/app/results/page.tsx` (Edit 7: changed badge to `AI-Generated, RAG-Grounded Analysis`). `docs/implementation/imp_part_2.md` (this tracker + log).
- **Followed `part_2_blocks/block_1_3.md` verbatim**, preserving the em-dash `—` and keeping the coupled matchers exact so oil/fluid/filter relabeling stays functional.
- **Tests**: `grep` check across `backend/pricing.py` and `frontend/src/app/results/` returned empty (`OK: no overclaiming strings found`). `uv run ruff check backend/`, `uv run black --check backend/`, `uv run mypy backend/` all passed. `uv run pytest tests/unit/ -v` passed (196 passed). `next build` compiled successfully with zero TS/ESLint errors.
- **Handoff**: no other block touched. Next block per tracker: 1.4 (Harden production email deliverability).
