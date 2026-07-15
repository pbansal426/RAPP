# 📗 RAPP Master Execution Blocks & Model Selection Guide

This guide is tailored for **you**—the project owner. We have organized the entire remaining implementation roadmap (`Stage 1.3 through Stage 4`) into **9 Cohesive Task Blocks**. 

Why Blocks? Whenever multiple tasks touch the exact same core files (`models.py`, `payments.py`, `results/page.tsx`, `gemini.py`), assigning them separately causes conflicting code diffs, double work, and broken state machines. By executing them as **Task Blocks**, your assigned model completes tightly coupled features together cleanly in one session.

---

## 🪙 Our 4 Token & Cost Tiers Explained

- 🔴 **Heavyweight Geniuses (`Claude Opus 5`, `Gemini 3.1 Pro`)**: Spend premium tokens here **only** where errors could cost real money or break core data (`Block 1 Payment Overhaul`, `Block 6 Check AI Vector Search`).
- 🟡 **All-Round Workhorses (`Claude Sonnet 5`)**: Your daily driver. Fast, surgical, type-safe, and avoids over-engineering (`Block 2 Safety & Legal`, `Block 3 Outcome Moat`, `Block 5 Photo OCR`).
- 🟢 **Speed & Savings Champions (`Gemini 3.5 Flash`, `Claude Haiku`, `Fable / GPT OSS`)**: Cost fractions of a cent and run instantly. Assigned to static text, legal checklists, and volume dictionary/markdown generation (`Block 7 Content Hub`).
- 🟣 **Background Specialist (`Jules - Google Async Agent`)**: Meant for long-running batch ingestion tasks (`Block 9 Vector Database Scale`) so your interactive terminal sessions never lock up or time out.

---

## 🚀 Master Cheat Sheet: The 9 Future Task Blocks & Assigned Models

| Block # | Task Block Name & Included Roadmap Stages | 🏆 Top Pick (Pick This First) | 🔄 Backup Pick (If #1 Unavailable) | 💰 Token Verdict |
|:---|:---|:---|:---|:---|
| **Block 1** ✅ **COMPLETED** | **Payment & Monetization Overhaul**<br>• `1.3 MoR Payment Swap (Polar/Lemon Squeezy)`<br>• `1.4 Annual Pass ($19.99/yr Primary SKU)`<br>• `Tiered Single Pricing ($4.99 / $9.99 / $14.99)` | **Claude Opus 5** | Gemini 3.1 Pro | 🔴 Spend Premium<br>*(Core Revenue Stack)* |
| **Block 2** ✅ **COMPLETED** | **Pre-Job Liability & High-Risk Safety Gate**<br>• `1.5 High-Risk Safety Redirects (Airbag/EV/Fuel)`<br>• `1.6 Terms of Service & Checkout Checkbox UI` | **Claude Sonnet 5** | Gemini 3.5 Flash | 🟡 Smart Balance<br>*(Boolean Gate & UI)* |
| **Block 3** ✅ **COMPLETED** | **Social Proof & Outcome Capture Moat**<br>• `2.1 Results Hero Redesign & Survey Modal`<br>• `2.2 Social Proof Aggregation Query & Stats Badge` | **Claude Sonnet 5** | Gemini 3.1 Pro | 🟡 Smart Balance<br>*(DB Stats & Hero Cards)* |
| **Block 4** ✅ **COMPLETED** | **In-Guide Safety & Competence Tracking**<br>• `2.3 Pre-Job Readiness Quiz & Bailout Warnings`<br>• `2.5 Skill Leveling & User Competence Memory` | **Gemini 3.1 Pro** | Claude Sonnet 5 | 🟡 Smart Balance<br>*(Runtime Prompt Tuning)* |
| **Block 5** ✅ **COMPLETED** | **Mid-Repair Photo Checkpoint Pipeline**<br>• `2.4 Mid-Repair Photo OCR ("📸 Verify My Work")` | **Claude Sonnet 5** | Gemini 3.1 Pro | 🟡 Smart Balance<br>*(File Stream & Vision API)* |
| **Block 6** ✅ **COMPLETED** | **"Check My ChatGPT Answer" Viral RAG Funnel**<br>• `2.6 External AI Verification Landing Page (/check-ai)` | **Gemini 3.1 Pro** | Claude Opus 5 | 🔴 Spend Premium<br>*(Vector RAG Engine)* |
| **Block 7** ✅ **COMPLETED** | **High-Velocity Content & SEO Hub**<br>• `3.1 Routine Maintenance Templates (Wipers/Oil)`<br>• `3.2 Knowledge Hub Articles & Guide Library (/hub)` | **Gemini 3.5 Flash** | Claude Haiku / Fable | 🟢 Maximum Savings<br>*(Dict & Markdown Speed)* |
| **Block 8** | **Growth & Proactive Retention Automation**<br>• `3.3 Referral Program Tracking (`referral_code`)`<br>• `3.4 Recall & TSB Watch Automated Email Crons` | **Claude Sonnet 5** | Gemini 3.1 Pro | 🟡 Smart Balance<br>*(Async Python Scripts)* |
| **Block 9** | **Vector Database Scale-Up (GTM Gate)**<br>• `4.1 20-Vehicle Batch Ingestion Pilot (Chroma DB)` | **Jules (Async Agent)** | Gemini 3.1 Pro via CLI | 🟣 Background Task<br>*(Unattended Batch)* |

---

## 🔬 Deep Dive: Why Did We Build These 9 Blocks & Choose These Models?

### Stage 1: Launch Blockers

#### Block 1: Payment & Monetization Overhaul (`Stages 1.3 + 1.4 + Tiered Pricing`)
- 🛠️ **Why grouped together**: Shipped code currently has flat `$3.99` single pricing built directly into raw Stripe (`stripe.py`). Modifying single pricing on Stripe before swapping for a Merchant-of-Record (`Polar` or `Lemon Squeezy`) creates double throwaway work. In one clean block, we swap raw Stripe for MoR, implement **Value-Anchored Tiered Single Pricing (`Tier 1: $4.99`, `Tier 2: $9.99`, `Tier 3: $14.99`)**, AND launch our **`$19.99/yr` Annual Pass**.
- 🏆 **Top Pick: `Claude Opus 5`** (Backup: `Gemini 3.1 Pro`)
- 💡 **Rationale**: Touches `models.py`, checkout routers, webhook HMAC verification, and UI pricing cards simultaneously. Payment webhooks have zero margin for error. Opus 5 handles complex multi-file state machines flawlessly without breaking checkout or throwing exceptions.

#### Block 2: Pre-Job Liability & High-Risk Safety Gate (`Stages 1.5 + 1.6`)
- 🛠️ **Why grouped together**: Both tasks govern pre-job checkout gating on the exact same screens (`repair.py`, `repair/page.tsx`, `terms/page.tsx`). When a user enters a dangerous symptom (`Airbag/SRS`, `High Voltage EV`, `Fuel Lines`), we abort step generation and display a Red Alert modal. Simultaneously, we wrap checkout/guide unlock buttons in our mandatory `[x] I agree to DIY Liability Terms` checkbox. Grouping them ensures total pre-repair legal and safety compliance in one clean pass.
- 🏆 **Top Pick: `Claude Sonnet 5`** (Backup: `Gemini 3.5 Flash`)
- 💡 **Rationale**: Fast, surgical, and disciplined on boolean logic (`if request.is_high_risk:` and `disabled={!agreed}`). Builds crisp glassmorphism UI without wasting expensive Opus tokens.

---

### Stage 2: Core Trust Features & Viral Growth Moats

#### Block 3: Social Proof & Outcome Capture Moat (`Stages 2.1 + 2.2`)
- 🛠️ **Why grouped together**: Both tasks build our core data moat on the top hero section of `frontend/src/app/results/page.tsx`. Stage 2.1 creates the database schema (`DbRepairOutcome`) and post-repair survey modal (`actual_cost_usd`, `actual_duration_minutes`). Stage 2.2 writes the SQL aggregation query (`GET /api/outcomes/stats`) and renders the live community benchmark badge right above the hero card (`"👥 214 Corolla owners completed this job, avg 45 min"`). Grouping them guarantees the survey and stats badge feed into each other perfectly.
- 🏆 **Top Pick: `Claude Sonnet 5`** (Backup: `Gemini 3.1 Pro`)
- 💡 **Rationale**: Perfect synergy between type-safe backend SQLAlchemy aggregation modeling and top-of-viewport Vanilla CSS telemetry card styling.

#### Block 4: In-Guide Safety & Competence Tracking (`Stages 2.3 + 2.5`)
- 🛠️ **Why grouped together**: Both tasks control how our live AI repair engine (`gemini.py`) tunes its system prompts and adapts to the user's profile (`models.py`, `repair.py`). Stage 2.3 runs a pre-job quiz (`Tools? Time? Comfort?`) and injects `[POINT OF NO RETURN]` bailout instructions into Gemini's prompt right before critical steps. Stage 2.5 tracks `DbUser.skill_level` (`Beginner` vs `Advanced`) across jobs to dynamically scale prompt verbosity. Combining them ensures our Gemini prompt builder cleanly handles readiness scoring, skill leveling, and bailout warnings in one cohesive prompt architecture.
- 🏆 **Top Pick: `Gemini 3.1 Pro`** (Backup: `Claude Sonnet 5`)
- 💡 **Rationale**: Because this block tunes the system prompt of our runtime Gemini generator (`backend/services/gemini.py`), Pro understands how to prompt and constrain its `Gemini 3.5 Flash` counterpart better than any other model.

#### Block 5: Mid-Repair Photo Checkpoint Pipeline (`Stage 2.4`)
- 🛠️ **What we are building**: A camera button inside repair steps where users upload photos of their work so Gemini Vision can verify bolt fitment or part orientation (`POST /api/repair/checkpoint/verify`).
- 🏆 **Top Pick: `Claude Sonnet 5`** (Backup: `Gemini 3.1 Pro`)
- 💡 **Rationale**: Sonnet is elite at wiring `python-multipart` image streams, handling image byte conversions cleanly, and building responsive UI camera triggers with active loading shimmer states.

#### Block 6: "Check My ChatGPT Answer" Viral RAG Funnel (`Stage 2.6`)
- 🛠️ **What we are building**: Our highest-converting acquisition tool (`/check-ai`). Users paste advice they got from ChatGPT/Claude, our system searches our verified automotive database (`Chroma DB`), and generates a detailed 0-100 accuracy scorecard spotting where ChatGPT hallucinated.
- 🏆 **Top Pick: `Gemini 3.1 Pro`** (Backup: `Claude Opus 5`)
- 💡 **Rationale**: **Pro is purpose-built for vector RAG alignment.** It navigates Chroma DB metadata filtering (`chromadb`), compares embedding chunks against user text, and formats a viral comparison scorecard without hallucinating TSB numbers.

---

### Stage 3 & Stage 4: Content, Retention & Scale

#### Block 7: High-Velocity Content & SEO Hub (`Stages 3.1 + 3.2`)
- 🛠️ **Why grouped together**: Both tasks expand our static technical content and SEO footprint without touching core transaction engines. Stage 3.1 populates structured Python dictionaries (`repair_templates.py`) for high-frequency maintenance (wipers, oil, bulbs, tire pressure). Stage 3.2 builds our clean article library (`/hub`) filled with troubleshooting guides and car care advice.
- 🏆 **Top Pick: `Gemini 3.5 Flash`** (Backup: `Claude Haiku` / `Fable`)
- 💡 **Rationale**: **Maximum token savings & speed.** Generating structured dictionaries and markdown articles requires volume and speed, not heavy reasoning. Flash does this in seconds for almost zero cost.

#### Block 8: Growth & Proactive Retention Automation (`Stages 3.3 + 3.4`)
- 🛠️ **Why grouped together**: Both tasks build async background processes and email notification loops using Resend API (`email.py`). Stage 3.3 creates referral link tracking (`referral_code`) where users earn free unlocks for inviting friends. Stage 3.4 (`Recall Watch`) builds an automated daily cron script querying government safety databases (`NHTSA`) and emailing users when a safety recall is issued on their saved car.
- 🏆 **Top Pick: `Claude Sonnet 5`** (Backup: `Gemini 3.1 Pro`)
- 💡 **Rationale**: Sonnet writes rock-solid, crash-proof standalone Python scripts (`httpx` + `structlog`) that run unattended in background crons with automatic retries (`tenacity`).

#### Block 9: Vector Database Scale-Up — GTM Gate (`Stage 4.1`)
- 🛠️ **What we are building**: Our gating item before any go-to-market push: batch chunking, embedding, and storing technical manual data across 20 vehicle makes/models into `chroma_db`.
- 🏆 **Top Pick: `Jules` (Google Async Agent)** (Backup: `Gemini 3.1 Pro via CLI script`)
- 💡 **Rationale**: Jules is specifically engineered for long-running, hands-off batch repository tasks. It runs unattended in the background for 20+ minutes ingesting thousands of records without timing out your interactive terminal window.
