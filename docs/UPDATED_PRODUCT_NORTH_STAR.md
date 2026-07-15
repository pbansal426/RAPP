# RAPP — Product North Star

**Purpose**: business/product AND execution-workflow companion to `CLAUDE.md` (technical architecture). Paste or upload this into any AI conversation (Claude, Gemini, ChatGPT) for product/strategy help, and load it permanently into the Planning Agent's project knowledge — it captures decisions already made and how work actually gets executed, so neither needs to be re-derived.

---

## 1. What RAPP actually is

Not a DIY repair-guide app. A **fraud-shield / leverage tool** for any car owner who feels they're overpaying — not DIY mechanics specifically. The free diagnosis is the hook (the "you were about to get ripped off" reveal); the paid unlock sells confidence and negotiating ammunition, with the step-by-step guide as a bonus underneath for the DIY-willing minority.

**Primary competitor: ChatGPT/Gemini**, not RepairPal/YourMechanic. We don't out-cover it, we out-verify it — vehicle-exact fitment, real regional pricing, safety-flagged refusal to guess on high-risk systems, persistent per-vehicle state a stateless chatbot can't have.

**Core brand promise**: make the user feel *enlightened* — more knowledgeable and proactive about their car — not just sold a guide.

## 2. Trust architecture (non-negotiable)

Two visibly separate tiers in the UI, never blended:
- **Verified OEM Procedure** — repairs + real maintenance, grounded in NHTSA TSBs, the existing RAG moat. High trust bar.
- **Community Guide** — mods, detailing, cosmetic work. Clearly labeled as non-factory-sourced, lower safety-critical bar (nobody dies from a mis-torqued CarPlay unit).

Never let mod/detail content borrow the trust signal built for safety-critical repair content.

## 3. Monetization stack, in priority order

1. **Annual pass subscription (~$15-20/yr)** — primary product. Fixes the low-frequency-usage problem, avoids per-transaction fee drag, removes the "is this $4 worth it" friction on cheap jobs.
2. **Single-incident purchase (Value-Anchored Tiered Pricing: `$4.99` / `$9.99` / `$14.99`)** — low-commitment on-ramp for first-time visitors not ready to subscribe.
   - **Tier 1 (`$4.99`)**: Quick Maintenance / Minor Fix (Dealer Quote `< $150` | `Category A`). Low-friction access for basic bulb swaps, wipers, and simple OBD sensors.
   - **Tier 2 (`$9.99`)**: Standard DIY Diagnostic & Repair (Dealer Quote `$150–$600` | `Category B`). Customer saves `$200–$400+` vs. shop quote; unlock fee is `< 5%` of money saved.
   - **Tier 3 (`$14.99`)**: Major Complex Repair & High-Value Diagnosis (Dealer Quote `> $600` | `Category C`). Customer saves `$500–$1,800+`. Revealing exact labor times and preventing dealership overcharging delivers massive financial and psychological value.
3. **Parts affiliate, sold as kits** — one-click bundle (part + tool + consumable) sized to exact VIN, not a list of separate links. Larger basket size than link-only affiliate.
4. **Phase 1.5: vetted shop lead-gen** — sell qualified, AI-verified leads to a fair-price shop network. Matches the only proven model in this category (RepairPal/YourMechanic monetize the shop side, not the consumer).
5. **Phase-later: VSC/repair-cost-protection affiliate** — touches the "insurance" ambition without becoming a licensed insurer.

**Rejected**: flat all-in-one bundle price (`$3.99` single unlock or flat bundle). Doesn't map to value delivered — overpriced for a bulb, underpriced for a $600 job. Kills the "fair price" brand story and suffers from severe payment processor fee drag on cheap flat transactions (`~17.5%` lost to MoR fees at `$3.99`).

**Payment processor**: merchant-of-record (Lemon Squeezy or Polar), not raw Stripe — as a solo founder, sales-tax nexus compliance across 40+ states is a real, unbudgeted burden Stripe doesn't solve for you.

## 4. Beating ChatGPT — the actual wedge list

Not breadth. Verified accuracy + personalization + confidence-building, specifically:
- **Readiness Check** — pre-job quiz (skill/tools/time) → green/yellow/red recommendation
- **Photo checkpoints** — user photographs part mid-repair, app confirms before unlocking next step (reuses existing VIN-OCR pipeline)
- **Skill leveling** — persistent competence tracking across jobs; ChatGPT has no memory across sessions
- **Bail-out plans built into every guide** — explicit point-of-no-return + fallback, not an afterthought
- **Social proof from real outcome data** — "214 Corolla owners completed this, avg 45 min" — requires the outcome-capture data moat (below)
- **"Check my ChatGPT answer"** — paste what ChatGPT said, get it verified against real fitment/OEM data. Turns the biggest competitive threat into an acquisition funnel.
- **Recall/TSB watch** — proactive alerts on saved vehicles using data already ingested for RAG. Zero marginal cost, structurally impossible for a stateless chatbot to replicate.

## 5. The moat (beyond RAG grounding, which is copyable)

NHTSA TSB data is free and public — no defensibility there alone. Real moat: **capture actual post-repair outcomes** (what did the user actually pay?) via a simple follow-up. Builds a proprietary, geographically-specific fair-price dataset that improves with scale — a real network effect, unlike a static-manual competitor.

**Sequencing note**: the outcome-capture follow-up mechanism should be built into the Stage 2 Results-screen work (Section 11) now, while that screen is already being touched — cheap to add now, expensive to retrofit post-launch.

## 6. Entry point / funnel design

- **"Paste your quote" as the primary hook** — higher purchase intent than cold symptom search (user already has a number stinging them), stronger SEO angle ("is my mechanic quote fair"), more shareable.
- Symptom/VIN search remains the secondary path for pre-quote users.
- **Universal rule: value before signup**, for every user type. No forked "browsers get signup-first" logic — that inverts actual conversion psychology (low-intent visitors have the *least* tolerance for friction, not the most). Landing page uses two self-selecting CTAs ("I have a problem now" / "See how it works") rather than an explicit intent question.
- Guest sessions must persist through the eventual signup conversion — never make someone re-enter what they already told the app.

## 7. Phase 1 scope (build now)

- Stripe → merchant-of-record swap
- Real email delivery (kills the dev-mode reset-link-in-response security hole)
- Server-side chat rate limiting (currently client-side/localStorage, trivially bypassed)
- Liability disclaimer / ToS pass
- Safety-flagged categories (airbag/SRS, HV battery, pressurized fuel line): diagnosis stays, step-by-step guide explicitly redirects to "professional required"
- Results screen redesign around the price-gap reveal as the hero moment
- Maintenance content (oil changes, wipers, bulbs, tire pressure) — reuses the existing verified engine, fixes usage-frequency problem
- Readiness Check + bail-out framing
- Recall/TSB watch
- Referral program
- Knowledge Hub, text articles only (curated video embeds, not hosted)
- Finish the committed ~20-vehicle Jules ingestion pilot before any GTM push

## 8. Explicitly shelved (phase 1.5+, not now)

Mods/detailing content vertical · tool-rental marketplace (aggregate existing retailer loaner programs instead — do not build owned inventory, liability/logistics too heavy) · leaderboard (when built: rank by $ saved, not job count — opt-in, private by default) · self-hosted video · shop lead-gen marketplace · VSC affiliate · live mechanic calls · national vehicle coverage beyond the curated pilot batch

## 9. Shelved indefinitely — do not reference until RAPP has real revenue

The full OBD2 hardware ecosystem (always-on dongle, security/tracking, teen monitoring, fleet/B2B, proprietary insurance underwriting). This is a vision document for a *different, later, differently-capitalized company* — six separate businesses bundled into one hardware SKU, each with its own GTM, trust model, and regulatory exposure. Revisit only after RAPP has paying users and real capital.

---

## 10. Execution workflow — tools, roles, and setup

**The Planning Agent** (this project, a Claude Project) is where all conceptual/strategic conversation happens — new feature ideas, scope questions, anything that might touch a decision already made above — *before* anything becomes a coding task. It holds this entire document plus `CLAUDE.md` and `ARCHITECTURE_BLUEPRINT.md` as permanent project knowledge, so it reasons with full context on what's already been decided and won't contradict it.

For genuinely new ideas (not just extensions of existing scope), stress-test with the Gemini "Strategic Auditor" gem (four-pillar Reality Check: Viability / Sustainability / Competitive Moat / Go-to-Market) before it enters this document.

**Execution tools, by task nature — not arbitrary rotation:**
- **Claude Code (Sonnet 5 default, Opus for the highest-stakes work)** — anything security-critical, correctness-critical, or touching money/liability. Non-negotiable for payment processing, safety-flagged logic, and auth/security fixes.
- **Antigravity (Gemini 3.1 Pro)** — architecture-adjacent but not liability-critical work; medium complexity; benefits from large context or browser-based visual verification (UI/UX work).
- **Antigravity (Gemini 3 Flash)** — fast, well-defined, low-stakes UI/content work where speed matters more than depth.
- **Jules (Gemini 3.1 Pro backend)** — well-scoped, async, parallelizable tasks with clear acceptance criteria. Currently running the ~20-vehicle ingestion pilot continuously; add new well-scoped tasks (see Section 11) alongside it.
- **Gemini 3.1 Pro (Gemini app, occasional use)** — reserved specifically for full-codebase-scale reads once the repo outgrows what's practical to reason about in Claude's context — not a default tool, an occasional-use one.

**Repo setup — git worktrees, one per active agent:**
- One shared Python venv lives *outside* all worktrees (`~/venvs/rapp`), installed once, activated in each terminal before launching any tool — this ensures Claude Code / Antigravity CLI both inherit the correct environment without depending on the agent remembering to activate it itself.
- Each active task gets its own worktree off `main` (e.g., `../rapp-claude` on branch `claude/stripe-swap`, `../rapp-antigravity` on branch `antigravity/results-redesign`), each in its own terminal tab — so agents never edit the same files simultaneously.
- `CLAUDE.md` and `AGENTS.md` are tracked files, so every worktree checkout includes them automatically.
- Coordination happens through git, not real-time communication: work independently in each worktree, merge to `main` from the primary repo folder after reviewing the diff, then have other active worktrees `git merge main` to pick up finished work. One agent can be asked to review another's finished branch before merge.

**CLAUDE.md hygiene**: keep `CLAUDE.md` strictly technical and lean — this document (business/product/workflow) is NOT loaded into Claude Code's default context. If a specific Claude Code task genuinely needs product-context (e.g., "implement Readiness Check exactly per spec"), `@`-mention this file for that one session rather than paying the token cost of loading it every session.

## 11. Current execution plan (plan of record — update as stages complete)

**Stage 1 — Security & compliance (blocks everything else, do first):**
1. Server-side chat rate limiting — Claude Code, Sonnet
2. Real email delivery — Claude Code, Sonnet
3. Stripe → merchant-of-record swap — Claude Code, Opus, Plan Mode first (real money, real compliance risk)
4. Safety-flagged categories (airbag/SRS, HV battery, fuel line) — Claude Code, Opus (highest-care task in the backlog — real-world safety surface, not just a bug surface)
5. Liability disclaimer / ToS pass — draft in Planning Agent first (must reflect Section 2's trust architecture), then Claude Code, Sonnet for implementation

**Stage 2 — Core trust features (the actual product differentiation):**
6. Results screen redesign (price-gap reveal as hero) — Antigravity, Gemini 3.1 Pro, active browser-verification. **Build the outcome-capture follow-up (Section 5) into this work now.**
7. Readiness Check + bail-out framing — scoring logic (what makes something green/yellow/red) spec'd in Planning Agent first; UI build in Antigravity, Gemini 3.1 Pro
8. Photo checkpoints — Claude Code, Sonnet (extends existing verified VIN-OCR infrastructure, not greenfield)

**Stage 3 — Content & growth (parallelizable):**
9. Maintenance content (oil/wipers/bulbs/tire pressure) — Jules, several parallel well-scoped tasks, one per category
10. Knowledge Hub (text articles, curated video embeds) — Antigravity, Gemini 3 Flash
11. Referral program — Jules
12. Recall/TSB watch — Jules, recurring background job

**Stage 4 — Gating item, runs throughout Stages 1–3:**
- ~20-vehicle Jules ingestion pilot must complete before any GTM push — this is the actual "done" criterion for Phase 1, not the feature list alone.

**Sequencing rule**: Stage 1 ships before anything else, regardless of how tempting visible features are. Stages 2 and 3 run in parallel across worktrees once Stage 1 is clear.

## 12. Decision-logging process

Every Planning Agent conversation that reaches a real decision — a new feature approved, a scope change, a monetization tweak, anything that would otherwise need to be re-derived next time — ends with a doc update, not just a decision left in chat.

**Process**: 
1. Decision reached in the Planning Agent conversation.
2. Planning Agent states plainly which section of which doc it affects (this document for product/business/workflow decisions, `CLAUDE.md` for technical architecture/build-state decisions) and drafts the exact addition.
3. In Claude Code, run `/log-decision` (a project custom slash command at `.claude/commands/log-decision.md`) with that drafted addition — it appends it to the correct file, in the right section, matching the existing terse, decision-focused style.
4. Every execution tool's next session automatically inherits the update with zero re-explaining, since it's now part of the tracked repo files.

**Standing rule for the Planning Agent**: if a conversation reaches a decision and I haven't mentioned logging it, prompt me — "should this go into North Star / CLAUDE.md?" — rather than letting a real decision live only in chat history.

### Tracked Architectural & Product Decisions

| Date | Section | Decision | Rationale & Tradeoffs |
|:---|:---|:---|:---|
| **2026-07-15** | §3 Monetization & §7 Stage 1 | **Value-Anchored Tiered Single-Incident Pricing (`$4.99` / `$9.99` / `$14.99`) replaces Flat `$3.99`** | **Why**: Flat `$3.99` contradicted our core "fair price" brand story by overpricing simple bulb swaps (killing conversion) while massively underpricing complex `$1,000` repairs where our RAG diagnosis delivers hundreds in savings. Furthermore, flat `$3.99` suffered severe MoR fee drag (`~17.5%` lost to payment processor fees).<br>**Unit Economics Verification**: At `$4.99`, `$9.99`, and `$14.99`, net contribution margins after MoR fees (`~5% + $0.50`) and direct AI COGS (`~$0.03`) rise to **`84.4%` (`$4.21 net`)**, **`89.7%` (`$8.96 net`)**, and **`91.5%` (`$13.71 net`)** respectively.<br>**Known Open Question #1 (To Monitor Post-Launch)**: *Subscription Cannibalization vs. Decoy Anchor Effect.* At `$14.99` (or two `$9.99` jobs), single unlocks approach our **`$19.99/yr` Annual Pass**. While this serves as a powerful "decoy/anchor" conversion driver nudging high-value users into the annual subscription right away, high purchase frequency without subscribing could cannibalize ARR. Monitored via post-launch cohort telemetry.<br>**Payment-Path Routing Note**: Modifying shipped code (`backend/services/stripe.py` `_GUIDE_PRICE_USD_CENTS = 399`) right before MoR migration (`Stage 1.3`) creates throwaway work. Therefore, this change is routed as a combined **Task Block 1 (Payment & Monetization Overhaul — Stages 1.3 & 1.4 Combined)** where the MoR swap (`Polar/Lemon Squeezy`), Tiered Single Pricing (`$4.99/$9.99/$14.99`), and Annual Pass (`$19.99/yr`) are deployed in one unified payment-path overhaul. |
| **2026-07-15** | CLAUDE.md — Architecture (payments/auth) | **Server-side guide-unlock proof lives in a new `DbGuideUnlock` table, not literally inside `DbSavedRepair`** as `imp.md` 1.3/1.4's "webhook must save the unlocked VIN... to `DbSavedRepair`" bullet said verbatim. | **Why**: `DbSavedRepair` requires a non-null `user_id` and `symptoms` — invariants that make sense for the user-facing "saved to garage" feature, but a checkout can complete while the customer is logged out and before any guide has even been generated to save (so there's no `symptoms`/guide content yet to attach). Loosening those columns to accommodate an anonymous, pre-guide unlock record would weaken the garage feature's own guarantees. `DbGuideUnlock` is a minimal `session_id -> vin` proof table instead, written by the Polar webhook (on `order.created` / a confirmed `checkout.updated` — deliberately **not** `checkout.created`, which only means checkout was started, not paid) and by the mock `success-stub` (since mock/dev checkouts never fire a real webhook). `POST /api/repair` / `/api/repair/chat` now check this table instead of trusting any non-empty client-supplied `stripe_session_id`, which is the actual architectural fix the bullet was after — the exact table name was incidental to that goal. |
| **2026-07-15** | CLAUDE.md — Architecture (outcomes/social proof) | **New `DbRepairOutcome` table (Task Block 3 / Stage 2.1-2.2) derives `category` server-side via `select_template()` instead of accepting a client-supplied category, and allows `user_id`/`saved_repair_id` to be null.** | **Why**: Trusting a client-supplied category would let the outcome-stats aggregation (and the "214 Corolla owners... avg 45 min" social-proof badge built on top of it) drift from the categories `/api/repair` itself uses, or be spoofed to inflate a category's count. Reusing `backend/repair_templates.py::select_template(symptoms, obd_codes)` — the same classifier `/api/repair` calls — keeps outcome categories and repair-template categories a single source of truth. Nullable `user_id`/`saved_repair_id` matter because the outcome-capture goal (real completion-time/cost data feeding social proof) applies just as much to anonymous single-incident purchasers as to logged-in Garage users; requiring an account here would silently exclude most of the guide-unlock volume from the stats it's meant to power. |

---

*Companion doc: `CLAUDE.md` (technical architecture, current build state, tech debt). Update both when a decision touches product and implementation.*
