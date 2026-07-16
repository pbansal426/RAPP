# RAPP — App Improvement Opportunities (Full-Codebase Audit)

**Audit date**: 2026-07-16
**Auditor**: Claude (Opus 4.8), full read of `backend/`, `frontend/src/`, `docs/`, tests
**Purpose**: Machine-referenceable backlog of genuine improvements found by scanning the
codebase *after* all 15 `imp.md` Phase 2 items shipped. Each finding has an ID, evidence
(file:line verified at audit time), impact, and a concrete implementation sketch so a
future AI agent can pick one up without re-deriving context.

**How to use this doc (AI agents)**: Treat each `RAPP-XX` as a candidate task. Verify the
evidence lines still hold (code moves), check `docs/implementation/imp.md` for the active
block, and follow the CLAUDE.md 4-step protocol. Findings are ordered by severity within
each section, not globally.

---

## Section A — Revenue-Critical Defects (things silently losing money today)

### RAPP-01 · Purchased repair guides exist only in browser localStorage
- **Category**: durability / revenue protection
- **Evidence**: `frontend/src/app/repair/page.tsx:123` caches the generated guide in
  `localStorage['rapp_repair_{vin}']`; `DbSavedRepair` (`backend/core/models.py:76-96`)
  persists `symptoms` and `citations` but **not `repair_steps`**; `backend/routers/repair.py`
  regenerates via `generate_repair_procedure()` on every uncached fetch.
- **Impact**: A customer who pays $4.99–$14.99, then clears their browser / switches devices /
  opens the link on their phone in the garage, loses the product they bought. Re-viewing a
  saved Garage repair triggers a *fresh Gemini generation* — costs money, adds latency, and can
  return *different steps* than the guide they paid for (non-deterministic product). If Gemini
  quota is exhausted, a paying customer cannot see their purchase at all.
- **Fix sketch**: Add `repair_steps: JSON` column to `DbSavedRepair` and a
  `DbGeneratedGuide` table keyed by `DbGuideUnlock.session_id` (steps + citations + generated_at).
  `POST /api/repair` writes it on first generation and returns the stored copy on subsequent
  calls with the same session_id. Frontend keeps localStorage as an offline cache only.
  This also cuts Gemini spend per purchase to exactly one generation call.
- **Effort**: S–M (one table, one write path, one read-before-generate check).

### RAPP-02 · Annual subscribers' AI chat cap never resets (5 messages per VIN, forever)
- **Category**: product defect / subscription value
- **Evidence**: `backend/routers/repair.py:234-236` — when a subscriber has no checkout
  session, chat usage is keyed as `sub_{user.id}_{vin}`; `DbChatUsage` rows are never expired
  or reset (`backend/core/models.py:113-124`), and `MAX_CHAT_REPLIES = 5` is absolute.
- **Impact**: The Annual Pass ($19.99/yr) — positioned in `imp.md` as the **primary SKU** —
  gives a subscriber 5 lifetime chat messages per vehicle. A subscriber doing a second repair
  on the same car months later gets "limit exceeded" immediately. This directly undermines the
  subscription's renewal value proposition.
- **Fix sketch**: Key subscriber usage per job/month, e.g. `sub_{user.id}_{vin}_{YYYY-MM}` or
  reset `message_count` when `last_message_at` is older than N days. Decide the intended
  entitlement (e.g. 5/repair-session or 25/month for subscribers) and document it in the
  pricing copy.
- **Effort**: XS (key-format change + one policy decision).

### RAPP-03 · Safety block fires *after* payment, returning an empty guide with no refund path
- **Category**: revenue integrity / trust
- **Evidence**: `backend/routers/repair.py:166-192` — `/api/repair` (post-402, i.e. already
  paid) runs `check_high_risk()` **plus** a second TSB-text scan (`check_text_high_risk`) that
  `/api/diagnose` never runs. A repair can pass the free diagnosis un-flagged, get purchased,
  then return `repair_steps: []` + `is_blocked_safety: true`.
- **Impact**: Customer pays, receives nothing, and there is no automated refund or credit.
  Chargeback and trust risk on exactly the transactions where the user is most anxious.
- **Fix sketch**: (a) Run the same RAG-text safety scan during `/api/diagnose` so the block is
  known *before* the paywall CTA renders (results page already handles `is_high_risk` — extend
  it to suppress/replace the purchase CTA); (b) if the post-payment path still blocks, grant a
  `referral_credits`-style guide credit or trigger a Polar refund automatically and say so in
  the response.
- **Effort**: S (the scan function already exists; move/duplicate the call).

### RAPP-04 · Mock checkout unlock path has no environment gate
- **Category**: security / revenue protection
- **Evidence**: `backend/routers/payments.py:92-115` — `/api/payments/success-stub` writes a
  real `DbGuideUnlock` for any caller-supplied `session_id`+`vin`, unauthenticated. It exists
  for dev/mock mode, but the route is registered unconditionally; if it ships to prod alongside
  a configured Polar account, anyone who reads the JS bundle can mint free unlocks with one GET.
- **Fix sketch**: 404/410 the stub when `polar_is_configured()` is true (or gate on an
  `ENVIRONMENT != "production"` setting in `backend/core/config.py`). One `if` statement.
- **Effort**: XS.

### RAPP-05 · Parts purchase links carry no affiliate tags — free money left on the table
- **Category**: monetization (new revenue stream, zero UX change)
- **Evidence**: `backend/pricing.py` builds `purchase_url` as plain Amazon/AutoZone/RockAuto
  search links (per CLAUDE.md contract, `PartOption.purchase_url`).
- **Impact**: Every diagnosis renders 3-tier parts lists with outbound links pre-paywall — this
  is exactly the traffic affiliate programs pay for. Amazon Associates (~1-4% auto parts),
  eBay Motors, Advance Auto/CJ. At even modest traffic this monetizes the ~free tier users who
  never pay for a guide.
- **Fix sketch**: Add `AFFILIATE_TAG_AMAZON` etc. to `Settings`; append `&tag=` (Amazon) /
  program params in the single place `purchase_url` is constructed in `backend/pricing.py`.
  No frontend change (contract shape unchanged).
- **Effort**: XS–S (plus signing up for the programs).

---

## Section B — Structural / Reliability Gaps

### RAPP-06 · No database migration system — schema drift is a time bomb
- **Category**: structural
- **Evidence**: `backend/app.py` lifespan runs `Base.metadata.create_all` on every startup;
  no `alembic` anywhere in `pyproject.toml` or `backend/`. CLAUDE.md itself documents the
  symptom ("a stale server process… needs a restart (not a migration)").
- **Impact**: `create_all` only creates *missing tables* — it never adds columns to existing
  ones. The schema has grown fast (referral columns, subscription columns, skill columns all
  added to `users`). On the current SQLite file each addition has presumably worked only
  because the DB was recreated or columns were hand-added; on the documented prod path
  (Postgres via `DATABASE_URL`) the first deploy after a column addition will 500 on query.
- **Fix sketch**: Introduce Alembic; autogenerate the initial revision from current models;
  replace `create_all` with `alembic upgrade head` in the lifespan (or a release step). Keep
  `create_all` only for the test suite.
- **Effort**: M (one-time setup; small ongoing discipline).

### RAPP-07 · Zero rate limiting on free, unauthenticated Gemini-backed endpoints
- **Category**: security / cost control
- **Evidence**: `POST /api/diagnose` (`backend/routers/diagnose.py:71`) and
  `POST /api/diagnose/verify-external` (`:157`) each make a Gemini call per request with no
  auth, no rate limit, no CAPTCHA, no per-IP throttle. The only 429s are *passthroughs of
  Gemini's own quota*. `POST /api/vin/ocr` likewise. `DbChatUsage` protects only paid chat.
- **Impact**: Today (free tier, 20 req/day) one curious visitor exhausts the whole product's
  LLM quota for every user. On a paid Gemini tier this inverts into a denial-by-wallet vector —
  a script hitting `/api/diagnose` in a loop bills the owner directly.
- **Fix sketch**: Add `slowapi` (or a small in-house token bucket keyed on IP, mirroring the
  TTL-cache pattern already in `backend/services/nhtsa_safety.py`) on the three Gemini-backed
  free endpoints, e.g. 10/hour/IP for diagnose, 5/hour/IP for verify-external and OCR. Return
  the existing 429 shape so frontends already handle it.
- **Effort**: S.

### RAPP-08 · No LLM response caching — identical questions pay for identical generations
- **Category**: cost / latency
- **Evidence**: no `cache` usage in `backend/services/llm.py` or `backend/routers/repair.py`;
  `generate_diagnosis_summary` and `generate_repair_procedure` call Gemini every time.
- **Impact**: "2015 Highlander + squealing brakes" produces essentially the same diagnosis for
  every user who asks, but each ask is a fresh billable, slow (~seconds) Gemini call. Diagnosis
  is the *free* step, so cache hits here are pure cost savings; they also make the free step
  feel instant, which helps conversion.
- **Fix sketch**: A `DbLlmCache` table (or the in-memory TTL pattern from `nhtsa_safety.py`)
  keyed on `sha256(kind + normalized(year|make|model|engine) + normalized(symptoms) + sorted(obd_codes))`
  with a 30–90 day TTL. Check before Gemini in `generate_diagnosis_summary`; guide generation
  gets per-session persistence via RAPP-01 instead (skill-level personalization makes cross-user
  guide caching less safe).
- **Effort**: S–M.

### RAPP-09 · Zero product analytics — the conversion funnel is invisible
- **Category**: structural / growth
- **Evidence**: no posthog/plausible/gtag/umami/mixpanel anywhere in `frontend/src` or
  `backend/`; no event logging beyond structlog server logs.
- **Impact**: The business model is a funnel (visit → VIN → diagnose → results/paywall view →
  checkout start → purchase), and none of its stages are measured. Pricing-tier experiments
  (the $4.99/$9.99/$14.99 split), the ChatGPT-check funnel, and the referral program shipped
  with no way to know if they work. Every future product decision is currently a guess.
- **Fix sketch**: Self-hostable/privacy-friendly default: PostHog (free tier) or Plausible +
  custom events. Instrument ~8 events through one tiny `frontend/src/lib/analytics.ts` helper
  (respecting the api.ts single-wrapper convention): `vin_decoded` (method: text/ymm/photo/scan),
  `diagnose_submitted`, `results_viewed`, `paywall_cta_clicked`, `checkout_started` (tier),
  `purchase_completed` (webhook-side, server event), `chat_message_sent`, `outcome_submitted`.
- **Effort**: S–M. **This should arguably be done before any further growth feature.**

### RAPP-10 · Anonymous purchases are unrecoverable — no receipt/restore path
- **Category**: durability / support load
- **Evidence**: unlock proof is `DbGuideUnlock` keyed by checkout session id; the client's only
  copy is `localStorage['rapp_unlocked_{vin}']`. Anonymous buyers (explicitly supported —
  `user_id` nullable, `backend/routers/payments.py:26-35`) have no way to restore access after
  clearing storage; nothing is emailed at purchase time.
- **Fix sketch**: Polar checkouts capture the buyer's email. On `order.created` webhook, send a
  receipt email (Resend is already wired: `backend/services/email.py`) containing a restore
  link: `/repair/restore?session={id}&vin={vin}` which re-seeds localStorage after the backend
  confirms the pair against `DbGuideUnlock`. Pairs naturally with RAPP-01.
- **Effort**: S.

### RAPP-11 · `results/page.tsx` and `repair/page.tsx` are ~1,000-line monoliths
- **Category**: maintainability
- **Evidence**: `frontend/src/app/results/page.tsx` (1,000 lines), `repair/page.tsx` (987),
  `check-ai/page.tsx` (631) — each mixing data fetching, localStorage orchestration, and many
  visual sections in one client component.
- **Impact**: The Claude/Gemini ownership split (CLAUDE.md pinned contract) gets riskier as
  these grow — presentational edits and data-layer logic collide in the same file; merge
  conflicts and accidental contract breaks become likely.
- **Fix sketch**: Extract per-section components (PartsDashboard, CostComparison, SocialProofBadge,
  RecallPanel, PhaseList, OutcomeSurveyModal…) and move localStorage orchestration into
  `frontend/src/lib/` hooks (e.g. `useRepairSession()`), which also puts that logic on Claude's
  side of the ownership line where it belongs. Keep every frozen `data-testid` intact.
- **Effort**: M (mechanical, but must be done carefully against the frozen E2E selectors).

### RAPP-12 · RAG retrieval quality is unmeasured — no hit/miss telemetry, no demand signal
- **Category**: structural / data moat
- **Evidence**: `backend/rag/retriever.py` returns results or `[]`; nothing records whether a
  diagnose/repair request found relevant TSBs, and nothing records which vehicles users ask
  about. KB coverage is 7 vehicles (see `docs/ingestion_status.md`); the 15-generation batch
  (`scripts/seed_vehicles.json`) was hand-curated, not demand-driven.
- **Impact**: "RAG-verified" is the product's core claim, but there is no number for what % of
  paid guides actually had grounding docs. Ingestion priority (the single biggest KB investment)
  is being set without knowing what users drive.
- **Fix sketch**: Add a `DbQueryLog` (year, make, model, matched_chunk_count, top_distance,
  endpoint, created_at) written from `backend/services/rag.py`. A tiny
  `GET /api/admin/rag-stats` or a notebook over the table answers both questions. Feed the
  vehicle-frequency ranking back into `seed_vehicles.json` ordering.
- **Effort**: S.

### RAPP-13 · Safety classification is naive keyword matching (false positives and negatives)
- **Category**: safety / quality
- **Evidence**: `check_high_risk` (`backend/routers/diagnose.py:22-68`) and
  `check_text_high_risk` (`backend/routers/repair.py:74-118`) do substring matching. "My fuel
  economy dropped" does not match, but "smells like a fuel leak near the back" hard-blocks; a
  TSB that *mentions* "airbag warning lamp may illuminate" in passing blocks an unrelated paid
  guide (compounding RAPP-03).
- **Fix sketch**: Keep keywords as a fast pre-filter, but confirm borderline hits with one cheap
  structured Gemini call (`SafetyAssessment{is_high_risk, system, rationale}` — the structured-
  output pattern already exists in `backend/services/gemini.py`). Log every block so false-
  positive rate becomes measurable (ties into RAPP-09/12).
- **Effort**: M.

---

## Section C — High-Leverage New Features

### RAPP-14 · "Am I being overcharged?" shop-quote checker (photo → verdict)
- **Category**: acquisition / viral feature
- **Why it fits**: RAPP already has every ingredient: the vision-upload pipeline
  (`_normalize_image_for_vision` in `backend/routers/vin.py`, reused by photo checkpoints),
  structured Gemini extraction (`backend/services/gemini.py`), fair-cost data
  (`backend/pricing.py` dealer/indy/DIY ranges), and real-outcome averages (`DbRepairOutcome`).
- **Feature**: User photographs a repair-shop estimate → Gemini extracts line items →
  compare against `estimate_pricing()` + outcome stats → "This quote is ~$310 above the typical
  independent-shop range for a 2016 RAV4 alternator. Here's the DIY option for $89." This is the
  single most shareable moment the product can generate, and it funnels directly into the
  existing paywall ("do it yourself for $9.99").
- **Sketch**: `POST /api/quote/check` (multipart) → `QuoteExtraction` Pydantic schema →
  match line items to `repair_templates.py` categories → respond with per-line verdicts.
  Free tier with the RAPP-07 rate limit; gate full line-by-line detail behind the paywall.
- **Effort**: M.

### RAPP-15 · Live OBD-II reading via Web Bluetooth (ELM327)
- **Category**: differentiation / UX
- **Why it fits**: `/diagnose` currently asks users to *type* OBD codes, which assumes they
  already own a scanner app. Cheap ELM327 BLE dongles ($10-20) speak a simple serial protocol;
  Chrome/Edge on Android + desktop support Web Bluetooth (iOS Safari does not — feature-detect
  and hide, same pattern as the torch toggle in `useCameraStream.ts`).
- **Feature**: "Connect scanner" button on `/diagnose` → reads DTCs directly into
  `rapp_symptoms`/`obd_codes` → zero-typing diagnosis. Also enables a post-repair "codes
  cleared ✓" verification step in `ConclusionPhase.tsx`, closing the loop the static conclusion
  phase currently fakes.
- **Sketch**: `frontend/src/lib/obdBluetooth.ts` (Claude-side lib code) implementing the ELM327
  AT-command init + mode 03 (read DTCs) / mode 04 (clear); presentational button is Gemini-side.
  No backend change.
- **Effort**: M–L (device testing is the long pole).

### RAPP-16 · PWA / offline mode — the garage has no Wi-Fi
- **Category**: UX / retention
- **Why it fits**: The core usage moment (hands greasy, under the car, phone propped on the
  engine bay) is exactly where connectivity is worst. The guide is already cached in
  localStorage (`rapp_repair_{vin}`); the app just can't *boot* offline.
- **Sketch**: Add `manifest.json` + a service worker (Next.js `app/` supports this via
  `next-pwa` or a hand-rolled `public/sw.js`) precaching the app shell and the `/repair` route.
  "Install RAPP" prompt after first purchase. Checked-step state already persists.
- **Effort**: S–M.

### RAPP-17 · Programmatic SEO from the outcome/pricing data moat
- **Category**: growth / SEO
- **Evidence of gap**: no `sitemap.ts`, no `robots.ts`, no per-article `generateMetadata`, no
  OpenGraph images anywhere in `frontend/src/app/`; the Knowledge Hub (`hub/page.tsx`) is a
  single client-rendered list page with articles in a TS array (`hub/articles.ts`) — no per-
  article URLs means no per-article rankings.
- **Feature**: (a) Baseline hygiene: `sitemap.ts`, `robots.ts`, per-page metadata, OG images,
  `/hub/[slug]` routes with `generateStaticParams` + Article JSON-LD. (b) The compounding play:
  static pages like `/costs/{make}-{model}-{category}` ("What a 2015 Highlander brake job
  actually costs — dealer vs shop vs DIY") generated from `backend/pricing.py` ranges and,
  as volume grows, real `DbRepairOutcome` averages — data competitors don't have. Each page's
  CTA is the existing diagnose flow.
- **Effort**: S for hygiene; M for the cost pages. High compounding return.

### RAPP-18 · Maintenance schedule + mileage tracking turns Garage into a retention loop
- **Category**: retention / subscription value
- **Why it fits**: The Annual Pass needs a reason to exist between breakdowns. Recall-watch
  cron (`backend/scripts/recall_watch_cron.py` + `DbRecallAlertSent`) already established the
  "we watch your car and email you" pattern — extend it from recalls to routine maintenance.
- **Feature**: User enters current mileage (+ rough miles/month) per saved vehicle → backend
  schedules "oil change due ~March", "brake fluid at 60k" from a per-powertrain interval table
  → email nudges deep-link into the existing maintenance guides (Block 7 content). Each nudge
  is a purchase/engagement opportunity and a reason to renew.
- **Sketch**: `mileage`,`miles_per_month` on `DbSavedRepair` (or a new `DbVehicle` table —
  cleaner, since Garage currently models repairs, not vehicles), an interval table in backend,
  and a second cron mirroring the recall-watch structure.
- **Effort**: M.

### RAPP-19 · Spanish localization
- **Category**: market expansion
- **Why it fits**: US DIY auto repair skews heavily Spanish-bilingual; competitors (forums,
  YouTube) serve this audience badly for *vehicle-specific* content. All user-facing strings
  are currently hardcoded English in TSX; Gemini prompts can emit either language for free
  (`Respond in {locale}` + the structured schemas are language-agnostic).
- **Sketch**: `next-intl` (App Router native) + `es` message catalog; add `locale` to
  `DiagnoseRequest`/`RepairRequest` (contract change — update CLAUDE.md pinned contract per
  protocol) and thread it into the prompt builders in `backend/services/llm.py`.
- **Effort**: L (mostly translation surface area, not architecture).

---

## Suggested sequencing (if asked "what first?")

1. **RAPP-04** (env-gate mock unlock) + **RAPP-02** (chat-cap key) — two tiny fixes to real defects.
2. **RAPP-01 + RAPP-10** (persist purchased guides + receipt/restore email) — protect the thing people pay for.
3. **RAPP-09** (analytics) — nothing else can be evaluated without it.
4. **RAPP-07 + RAPP-08** (rate limits + LLM cache) — required before any real traffic.
5. **RAPP-03 + RAPP-06** (pre-paywall safety check, Alembic) — before prod Postgres.
6. **RAPP-05 + RAPP-17** (affiliate tags, SEO hygiene) — cheap compounding revenue/growth.
7. Then the feature bets: **RAPP-14** (quote checker) first — highest viral ceiling, lowest new
   infrastructure — followed by RAPP-16/18, with RAPP-15/19 as larger swings.
