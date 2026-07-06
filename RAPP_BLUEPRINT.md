# RAPP — Architecture Blueprint & Context Snapshot

**Purpose of this document**: exhaustive, high-density context injection for AI models unfamiliar with this repository. Every claim below was verified against the actual codebase as of the date this was written (2026-07-05), not inferred from naming conventions or assumed from convention. Where something is a plan/aspiration rather than shipped fact, it is explicitly labeled as such.

---

## 1. What This App Does

**RAPP (Repair AI... Pinpoint Precision)** is an automotive diagnostic and repair-guide web application. A user enters their vehicle's VIN (or selects Year/Make/Model), describes a symptom or OBD-II trouble code, and the app:

1. Decodes the VIN into vehicle specs (year, make, model, engine, drivetrain, powertrain type) via the NHTSA vPIC API.
2. Produces a **free diagnosis**: a plain-language root-cause summary, a safety risk flag (with hard-coded triggers for airbag/SRS, high-voltage EV battery, and pressurized fuel line hazards), a parts shopping list (three price tiers per part: OEM, aftermarket/budget, performance/upgrade, each with a real retailer search link), and a cost comparison (dealership vs. independent shop vs. DIY).
3. Behind a **$4.00 paywall** (Stripe checkout), unlocks a **detailed, phase-structured repair guide**: step-by-step instructions with inline torque-spec and tool callouts, inline wiring/layout diagrams where relevant, and a live AI chat assistant grounded in the same procedure the user is looking at.
4. Lets registered users save unlocked guides to a personal "Garage" for later reference.

### Core value proposition
Existing repair-info sources are either (a) generic marketing copy with no real procedural detail, (b) paywalled OEM factory manuals costing hundreds of dollars for a single manual, or (c) unstructured forum posts of unknown reliability. RAPP's differentiator is **grounding real repair steps in actual manufacturer Technical Service Bulletins (TSBs)** pulled from NHTSA's public API — free, government-sourced, vehicle-specific data — formatted into an actionable guide by an LLM that is contractually forbidden from inventing content beyond what was actually retrieved.

### Full functional feature list (as shipped)
- VIN entry via manual 17-character text, Year/Make/Model cascade (synthetic VIN generation client-side), photo OCR (Gemini vision + Tesseract.js fallback), and live camera scanning (windshield OCR loop or door-jamb barcode scan via `@zxing/browser`).
- Free diagnosis: AI-generated (Gemini) or template-based root-cause summary, high-risk safety warnings, three-tier parts shopping list, dealership/independent/DIY cost comparison.
- Stripe-based paywall unlock ($4.00 flat fee per repair guide).
- Detailed repair guide: RAG-grounded step-by-step instructions bucketed into 5 phases (Safety/Prep, Access, Component Replacement/Torque, Reassembly, Conclusion/Verification — the last is templated, not RAG-derived), inline diagrams (layout diagrams for torque-related steps, wiring diagrams for connector/harness steps), citations to the specific NHTSA TSB(s) used.
- **Live AI chat assistant** on the repair-guide page, grounded in the exact procedure shown (not a fresh, possibly-inconsistent query), capped at 5 real AI replies per vehicle to protect Gemini's free-tier quota, with a client-side keyword-matched fallback for unlimited free follow-up.
- User accounts: signup/login/password-reset/email-verification (dev-mode: reset/verify links are returned directly in the API response, not emailed — no email provider is wired up yet), settings page, JWT bearer-token auth.
- "My Garage": save unlocked repair guides (including their citations) to a personal account, view saved-repair history.

---

## 2. Technical Stack

### Backend
- **Language**: Python 3.11 (pinned, `>=3.11,<3.12`)
- **Framework**: FastAPI `0.111.x`, served by Uvicorn (dev) / Gunicorn + Uvicorn workers (production, 2 workers)
- **Dependency management**: `uv` (Astral) — **not** Poetry, **not** pip directly. `uv.lock` is the lockfile; `uv sync --all-groups` installs everything including the `etl` and `dev` dependency groups.
- **ORM / DB**: SQLAlchemy 2.0 (`Mapped`/`mapped_column` typed style), SQLite for local dev (`sqlite:///./data/rapp.db`), swappable to Postgres via `DATABASE_URL` in production. No migration tool (Alembic etc.) — schema changes rely on `Base.metadata.create_all()` at every startup, which **only creates missing tables, never alters existing ones**; a schema change to an existing table requires manually resetting the local dev DB file.
- **LLM**: `google-genai` SDK `2.10.x`, model `gemini-3.5-flash` (used for repair-step generation, diagnosis summaries, VIN-photo OCR vision, and repair-guide chat — never for embeddings by default).
- **Vector store**: ChromaDB `0.5.3.x`, `PersistentClient`. **Default embeddings are ChromaDB's own local `all-MiniLM-L6-v2` (384-dim, free, CPU-bound)** — Gemini's `text-embedding-004` is opt-in only via `USE_GEMINI_EMBEDDINGS=true`, a deliberate cost-control decision made this session (previously Gemini embeddings were the default).
- **Password hashing**: `hashlib.scrypt` (stdlib, no extra native dependency) — not bcrypt/argon2.
- **Auth tokens**: PyJWT, HS256, three distinct token types (`access`/`reset`/`verify`) sharing one secret but scoped by a `type` claim so a leaked short-lived reset/verify token can't be replayed as a session token.
- **Structured logging**: `structlog`.
- **Retry logic**: `tenacity` (used for NHTSA API calls and — as of this session — Gemini embedding calls, with a predicate that does *not* retry on 400/401/403 client errors).
- **Image handling**: Pillow + `pillow-heif` (VIN photo normalization/downscaling before sending to Gemini vision).
- **Testing**: `pytest` + `pytest-asyncio`. Lint: `ruff` (rules: E, F, I, N, W, UP, B). Format: `black`. Types: `mypy` strict mode, but **only against `backend/`** — `tests/`, `etl/`, and `frontend/` are excluded from the strict CI gate (though `etl/` is kept mypy-clean in practice by convention, not enforcement).

### Frontend
- **Framework**: Next.js `14.2.35`, App Router (not Pages Router), React `^18`.
- **Language**: TypeScript `^5`.
- **Package manager**: pnpm (note: `npm run dev`/`pnpm build` triggers an `ERR_PNPM_IGNORED_BUILDS` dependency-approval error in this environment; invoking `./node_modules/.bin/next dev`/`build` directly bypasses it).
- **Styling**: hand-written vanilla CSS (`globals.css`, CSS custom properties for design tokens) — explicitly **not** Tailwind, despite some Tailwind-*looking* class names (`.bg-slate-900`, `.text-orange-500`, etc.) which are hand-written hooks Playwright asserts against, not a Tailwind build.
- **State**: no Redux/Zustand/Context-based global store — **localStorage is the session layer** for the entire VIN→diagnose→results→repair flow (see §4).
- **OCR/scanning**: Tesseract.js (client-side fallback OCR), `@zxing/browser`/`@zxing/library` (barcode scanning for door-jamb VIN plates), `heic2any` (iPhone photo format conversion).
- **E2E testing**: Playwright. Two independent suites: (a) `tests/e2e-mvp-flow.spec.ts` runs against `tests/mock_app.py` (a self-contained fake backend+frontend on one port, used to validate the E2E suite itself, run via `tests/verify_tests.sh`); (b) `tests/e2e-real-backend-smoke.spec.ts` (added this session) runs a focused smoke test against the **real** FastAPI backend + real Next.js frontend in `ENVIRONMENT=test` mode (mocked vector store, no live Gemini calls).

### Infra / Deployment
- Docker: separate multi-stage Dockerfiles for `backend/` (python:3.11-slim, non-root user, Gunicorn) and `frontend/` (node:20-alpine, non-root user). `docker-compose.yml` / `docker-compose.dev.yml` at repo root.
- CI: GitHub Actions (`.github/workflows/ci.yml`) — three jobs: `backend-quality` (ruff/black/mypy/pytest), `e2e-tests` (Playwright against mock_app.py), `e2e-real-backend` (added this session — Playwright against the real backend/frontend in test mode), `frontend-build` (TypeScript/ESLint via `pnpm build`).
- Payments: Stripe (`stripe` Python SDK `9.12.x`). Currently mock/stubbed checkout-URL helpers in `backend/services/stripe.py` — the seam exists for a real Stripe SDK call but isn't fully wired to live Stripe Checkout sessions yet (needs verification against current code before assuming either way — this file describes the seam's existence, not a claim about its exact completeness).

### External data sources
- **NHTSA vPIC API** (`vpic.nhtsa.dot.gov`) — VIN decoding.
- **NHTSA Manufacturer Communications / TSB API** (`api.nhtsa.gov`) — the actual knowledge-base content ingested by the `etl/` pipeline. Public, free, US government data — no licensing concern.

---

## 3. Directory Structure

```
RAPP/
├── backend/                      # FastAPI application
│   ├── app.py                    # Real bootstrap: FastAPI instance, CORS, lifespan, router registration, /health
│   ├── main.py                   # Thin backward-compat shim: re-exports app/settings/internals for `uvicorn backend.main:app`
│   ├── schemas.py                # Every Pydantic request/response model, single source of truth
│   ├── pricing.py                # Parts-pricing tier generation + cost-breakdown math (pure functions, no FastAPI dep)
│   ├── repair_templates.py       # Curated deterministic repair-procedure library (13 templates), zero-cost fallback
│   ├── vin_fallback.py           # Offline WMI-based VIN decode fallback (make + year only) when live NHTSA is down
│   ├── core/
│   │   ├── config.py             # pydantic-settings Settings singleton; settings.is_test_mode forces mocks in CI
│   │   ├── database.py           # SQLAlchemy engine/session, DATABASE_URL
│   │   ├── models.py             # DbUser, DbSavedRepair ORM models (SQLAlchemy 2.0 Mapped style)
│   │   ├── security.py           # scrypt password hashing, JWT create/decode (access/reset/verify token types)
│   │   ├── exceptions.py         # Centralized exception handlers; manually attaches CORS headers to the
│   │   │                         #   catch-all 500 handler (Starlette's ServerErrorMiddleware wraps outside
│   │   │                         #   CORSMiddleware, so it wouldn't otherwise get CORS headers -- fixed this session)
│   │   └── logging.py            # structlog configuration
│   ├── routers/
│   │   ├── vin.py                # GET /api/vin/{vin}, POST /api/vin/ocr, decode_vin_internal (shared helper)
│   │   ├── diagnose.py           # POST /api/diagnose
│   │   ├── repair.py             # POST /api/repair, POST /api/repair/chat (chat added this session)
│   │   ├── payments.py           # POST /api/payments/* (Stripe checkout)
│   │   ├── auth.py               # POST /api/auth/{signup,login,forgot-password,reset-password,send-verification,verify-email}, GET/PATCH /api/auth/me
│   │   └── repairs.py            # POST/GET /api/repairs (Garage save/list)
│   ├── services/
│   │   ├── gemini.py             # THE ONLY module that touches google-genai directly: client construction,
│   │   │                         #   call_gemini_text, call_gemini_repair_steps, extract_vin_via_gemini
│   │   ├── llm.py                # RAG-grounded generation orchestration (added/expanded this session):
│   │   │                         #   generate_repair_procedure, generate_diagnosis_summary, generate_chat_reply,
│   │   │                         #   refine_brake_category
│   │   ├── rag.py                # Thin pass-through to backend/rag/ (routers must not import backend.rag directly)
│   │   └── stripe.py             # Mock checkout-URL helpers (seam for real Stripe integration)
│   └── rag/                      # THE ONLY package allowed to import chromadb (enforced by
│       ├── __init__.py           #   tests/unit/test_rag.py::test_import_hygiene, which scans backend/** only)
│       ├── retriever.py          #   retrieve(query, vin_meta, k) -- builds the metadata filter, normalizes types
│       └── vector_store.py       #   ChromaVectorStore (local MiniLM default embeddings) + MockVectorStore
├── etl/                           # NHTSA TSB ingestion pipeline (separate from backend/, its own `uv` dep group)
│   ├── __main__.py               # CLI: python -m etl --year Y --make M --model Model [--all] [--load] [--reset-vehicle]
│   ├── config.py                 # EtlConfig (NHTSA API base, chunking targets, workspace_dir)
│   ├── models.py                 # VehicleKey (+ .slug property), TsbRecord, TsbDocument, TextChunk, TableChunk
│   ├── pipeline.py                # run_vertical_slice (1-doc smoke test), run_full_ingest (the real ingest loop),
│   │                              #   _workspace_lock (advisory flock, added this session), _write_progress (live
│   │                              #   progress.json for `etl.progress_view`, added this session)
│   ├── progress_view.py          # Pretty-prints progress.json for `watch`-ing a live ingest
│   ├── export_kb.py               # Snapshot data/chroma_db -> kb_export/chroma_db for a Git LFS commit (added
│   │                              #   this session, for the Jules hand-off workflow)
│   ├── import_kb.py               # Merge a pulled kb_export/chroma_db snapshot into the live store via upsert,
│   │                              #   never a raw file copy (added this session)
│   ├── clients/nhtsa_communications.py  # NHTSA manufacturer-communications API client
│   ├── transform/
│   │   ├── pdf_layout.py         # Layout-aware PDF parser (prose vs. tables)
│   │   └── chunking.py           # RecursiveCharacterSplitter (~1000 token chunks, ~200 overlap)
│   └── load/
│       ├── manifest.py           # IngestManifest -- tracks per-(vehicle-slug, nhtsa_id, file_name) ingest status,
│       │                         #   scoped per-vehicle since this session's fix (previously global, silently
│       │                         #   caused shared TSBs to be tagged only for whichever vehicle processed them first)
│       ├── vector_loader.py      # chunks_to_documents (enhanced metadata incl. source_authority, bulletin_number),
│       │                         #   load_into_vector_store
│       └── audit.py              # Vertical-slice audit log printer
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js App Router pages -- "Gemini"-owned territory per the project's
│   │   │                         #   internal Claude/Gemini work-split convention (see §5)
│   │   │   ├── page.tsx          # / -- VIN entry (4 paths: manual text, YMM cascade, photo upload, camera scan)
│   │   │   ├── diagnose/page.tsx # /diagnose -- symptoms + OBD codes + owned-tools input
│   │   │   ├── results/page.tsx  # /results -- free diagnosis + parts/cost breakdown + paywall CTA
│   │   │   ├── repair/page.tsx   # /repair -- unlocked detailed guide + ChatPanel + SaveGuidePrompt
│   │   │   ├── repair/success/page.tsx  # Stripe redirect handler
│   │   │   ├── garage/page.tsx   # /garage -- saved repairs list (does NOT yet display citations in the UI,
│   │   │   │                     #   even though the backend has supported it since this session)
│   │   │   ├── signin, signup, forgot-password, reset-password, verify-email, settings -- auth pages
│   │   │   └── (scan modals, diagrams, icons, etc.)
│   │   └── lib/                  # Typed API/data layer -- Claude-owned territory per the same convention
│   │       ├── api.ts            # THE single typed fetch wrapper -- no raw fetch calls elsewhere
│   │       ├── types.ts          # Every request/response TS interface, mirrors backend/schemas.py exactly
│   │       ├── auth.ts, repairs.ts, nhtsa.ts, obdCodes.ts, logos.ts, vehicleSpecs.ts, barcodeVin.ts,
│   │       │   vinCheckDigit.ts, useCameraStream.ts, firebase.ts (dead stub, kept only so
│   │       │   isFirebaseConfigured() returns true -- no real Firebase project exists)
│   ├── Dockerfile
│   └── package.json
├── tests/
│   ├── unit/                     # Backend pytest suite (112 tests as of this session)
│   ├── e2e-mvp-flow.spec.ts      # Frozen-contract Playwright suite against mock_app.py
│   ├── e2e-real-backend-smoke.spec.ts  # Playwright smoke test against the real backend (added this session)
│   ├── mock_app.py               # Self-contained fake frontend+backend on one port, validates the E2E suite itself
│   └── verify_tests.sh           # Runs the mock-app E2E suite 5x (1 healthy + 4 fault-injection scenarios)
├── docs/
│   ├── ingestion_status.md       # Live-updated table of which vehicles have been ingested (added this session)
│   ├── ARCHITECTURE_BLUEPRINT.md # This document
│   └── (data_sources_strategy.md, embedding_strategy.md, knowledge_base_metadata_schema.md, etc. -- Phase 0-6
│        knowledge-base scaling roadmap docs, pre-existing)
├── data/                          # GITIGNORED. Real internal-disk dir, split by role (see §6): chroma_db and
│   │                              #   etl_workspace are symlinks to the external SSD (large, re-buildable);
│   │                              #   rapp.db is a real internal file (tiny, irreplaceable accounts DB)
├── kb_export/                     # Git-LFS-tracked snapshot destination (added this session) -- NOT the live
│   │                              #   store, just the Jules/GitHub hand-off transit point (see §6)
├── .gitattributes                 # Git LFS tracking rules for kb_export/**/*.{sqlite3,bin,pickle} (added this session)
├── CLAUDE.md                      # Primary AI-agent-facing architecture doc (maintained continuously; this
│                                   #   blueprint is a distinct, denser, cross-model-portable snapshot of the same reality)
├── pyproject.toml / uv.lock        # Backend deps (uv)
├── package.json / frontend/package.json  # Root Playwright deps / frontend Next.js deps
└── .github/workflows/ci.yml       # 4-job CI pipeline
```

---

## 4. Data Flow

### 4.1 Request/response schemas (pinned contract)

All shapes are defined once in `backend/schemas.py` (Pydantic) and mirrored exactly in `frontend/src/lib/types.ts` (TypeScript interfaces). Per project convention, changing either side without updating the other — and without updating the pinned-contract section of `CLAUDE.md` — is treated as a bug.

- **`VehicleInfo`**: `year, make, model, trim, engine, drive_type, body_class, vehicle_type, fuel_type, powertrain` — all optional. Triple role: (a) the `vehicle` field on `DiagnoseRequest`/`RepairRequest`/`RepairChatRequest`, (b) the shape of a decoded `GET /api/vin/{vin}` response, (c) the shape of `rapp_vin_data` in localStorage.
- **`DiagnoseRequest`** → **`DiagnoseResponse`**: `{summary, is_high_risk, high_risk_system, warning_message, recommended_parts: RecommendedPart[], cost_breakdown: CostBreakdown | null}`. `RecommendedPart` = `{part_name, options: PartOption[3]}` (always exactly OEM/Aftermarket/Upgrade tiers). `CostBreakdown` = `{dealership_cost_range: [lo,hi], independent_shop_range: [lo,hi], parts_total, diy_total, estimated_labor_hours}`.
- **`RepairRequest`** (`DiagnoseRequest` + `stripe_session_id`) → **`RepairResponse`**: `{repair_steps: string[], citations: string[]}`. Torque-callout steps are guaranteed to start with the literal word `"Torque "` (frontend regex dependency).
- **`RepairChatRequest`** (added this session): `{vin, vehicle?, symptoms, repair_steps: string[], message, stripe_session_id}` → **`RepairChatResponse`**: `{reply: string | null}` (`null` = Gemini unavailable/failed, client falls back to a local canned reply).
- **`SavedRepairCreate`/`SavedRepairResponse`**: vehicle identity fields + `symptoms` + `payment_session_id` + **`citations: string[] | null`** (added this session — captured at save time since a later re-fetch of `/api/repair` could return different citations after new TSB ingestion; **not yet surfaced in the `/garage` UI**, see §5 tech debt).

### 4.2 The RAG-grounding data flow (the core technical mechanism)

```
User query (symptoms + OBD codes)
        │
        ▼
backend/services/rag.py::retrieve(query, vin_meta, k)
        │  (thin pass-through, never imports chromadb itself)
        ▼
backend/rag/retriever.py::retrieve()
        │  builds metadata filter: make/model/engine/drive_type (list, uppercased)
        │  + year (coerced to int -- a real bug fixed this session: the vehicle-
        │    object request path stringified year, silently zeroing every match
        │    against the int-typed year in Chroma's stored metadata)
        ▼
backend/rag/vector_store.py::ChromaVectorStore.search()
        │  local MiniLM embedding (or Gemini text-embedding-004 if opted in)
        │  k-nearest-neighbor query against the persistent ChromaDB collection
        ▼
   results: list[{id, text, metadata, distance}]
        │
        ├── if EMPTY: fall back to backend/repair_templates.py::select_template()
        │             (keyword/OBD-code matching) → deterministic canned steps,
        │             citation = honest "no vehicle-specific source found" message
        │             (NEVER a specific manual name -- fixed this session after
        │             finding hardcoded citations like "Honda Civic ESM..." were
        │             returned even for e.g. a Toyota query)
        │             Gemini is NOT called in this branch at all.
        │
        └── if NON-EMPTY: build a strict prompt containing ONLY the retrieved
            OEM text + user's declared tools, call Gemini with a system prompt
            that forbids inventing content beyond that text, cross-references
            required tools against what the user has and explicitly flags
            missing ones. Citations are built from real metadata
            (bulletin_number + source_url when present, prefixed
            "[Unverified/community-sourced]" if source_authority isn't
            "official" -- forward-looking, since every source today IS official).
```

This exact flow powers `generate_repair_procedure` (repair steps), `generate_diagnosis_summary` (free-diagnosis summary — looser fallback: still calls Gemini ungrounded if RAG misses, since a diagnosis is inherently a best-guess triage step, unlike a repair procedure), `generate_chat_reply` (chat, grounded in the `repair_steps` already shown rather than a fresh query), and `refine_brake_category` (disambiguates the diagnose parts list between disc and drum brake templates using real retrieved text, since keyword-only symptom matching can't tell them apart — added this session after finding a real mismatch during manual testing).

### 4.3 State management

**No client-side global store.** localStorage is the entire session layer, keyed by:
`rapp_vin`, `rapp_vin_data`, `rapp_symptoms`, `rapp_tools`, `rapp_unlocked_{vin}` (Stripe session id, set post-payment, checked by `/repair`), `rapp_garage_dismissed_{vin}`, `rapp_chat_count_{vin}` (added this session — the chat-cap counter), `rapp_token` (JWT bearer token).

**Server-side state**: two SQLite tables (`users`, `saved_repairs`) for auth/garage; the ChromaDB persistent store for the knowledge base; no server-side session store (JWT is fully stateless).

### 4.4 Authentication flow

Signup/login issue an `access` JWT (HS256, `settings.jwt_secret_key`). Password-reset and email-verification issue separately-typed `reset`/`verify` JWTs off the *same* secret, distinguished by a `type` claim checked at decode time — this scoping is load-bearing: without it, a leaked short-lived reset token could be replayed as a full session token. `frontend/src/lib/auth.ts` stores the access token in `localStorage['rapp_token']`; `frontend/src/lib/api.ts::authHeader()` attaches it as a Bearer header to every request automatically.

---

## 5. Why Built This Way

### Active design patterns
- **Strict RAG grounding as a liability/accuracy control, not just a quality one.** The entire architecture is built around one non-negotiable rule: an AI-generated repair step must never assert something the retrieved OEM text doesn't support. This shows up as: skipping Gemini entirely on a RAG miss (repair steps), honest "no source found" citations instead of a plausible-sounding fake one, and the disc/drum brake disambiguation fix.
- **Layered fallback, not a single point of failure.** Repair-step generation degrades: real RAG+Gemini → curated deterministic templates → generic hardcoded placeholder steps. VIN decode degrades: live NHTSA API → offline WMI-prefix fallback (make+year only). Chat degrades: real Gemini → client-side keyword-matched canned replies.
- **Ownership split by file territory, not by feature.** An internal convention (not enforced by tooling, just documented in `CLAUDE.md`) assigns `backend/` and `frontend/src/lib/*.ts` (the typed data layer) to one contributor persona ("Claude") and `frontend/src/app/**/*.tsx` + `globals.css` (presentational UI) to another ("Gemini"). Neither side is supposed to change the pinned request/response shapes without updating the shared contract doc.
- **RAG isolation as an enforced architectural boundary.** Exactly one package (`backend/rag/`) is allowed to import `chromadb`; a unit test (`test_import_hygiene`) greps the entire `backend/` tree to guarantee it. Everything else goes through `backend/services/rag.py`'s pass-through.
- **Cost-consciousness as a first-class architectural constraint**, not an afterthought: local embeddings by default (Gemini embeddings cost money and aren't needed for this), a hard per-vehicle cap on real AI chat replies (Gemini's free tier is a shared 20-requests/day budget across the *entire app* — VIN OCR, repair generation, diagnosis, chat all draw from the same pool), and `settings.is_test_mode` forcing mocked Gemini/vector-store clients in CI regardless of what secrets happen to be present.

### Key architectural choices and their rationale
- **`uv` over Poetry**: faster, simpler lockfile-based resolution; explicit project convention, not something this document can independently verify the original reasoning for beyond current usage.
- **SQLite for local dev, Postgres-ready for prod**: zero local setup friction; `DATABASE_URL` is the only thing that needs to change.
- **Backend-owned auth instead of the originally-specced client-side Firebase Auth**: the app already runs a FastAPI server continuously, so a second (Firebase) identity system alongside it was judged pure duplication with its own quota/vendor surface — this superseded the original spec (`ORIGINAL_REQUEST.md`) after the Firebase version was built once and then replaced.
- **ChromaDB (local, file-based) over a hosted vector DB**: appropriate for the current curated-vehicle-count scale; explicitly **not** appropriate at true "every vehicle in the US" scale (see §6) — this is a known, deliberate, scale-bounded choice, not an oversight.
- **`data/` split by role — SSD-safe-to-unplug** (revised this session; supersedes the earlier whole-directory-symlink approach): the ingested knowledge base outgrew comfortable internal-disk headroom, so the *large, re-buildable* data — `chroma_db` (vector store) and `etl_workspace` (raw TSB PDFs) — lives on an external SSD, reached via per-item symlinks (`data/chroma_db`, `data/etl_workspace`). But `data/` itself is now a **real internal-disk directory**, and `data/rapp.db` (the ~1 MB, *irreplaceable* accounts/saved-repairs DB) is a **real internal file**, not on the SSD. This means the SSD is never the single copy of anything you can't regenerate, and it can be unplugged without breaking the app: startup only touches `rapp.db`, and RAG **fails open** when `chroma_db` is unreachable (`backend/rag/__init__.py` `get_vector_store()` returns a transient uncached `MockVectorStore` on construction failure; `backend/rag/retriever.py` `retrieve()` try/excepts to `[]`), auto-recovering on replug with no restart. Still zero config/env changes — every path (`./data/chroma_db`, `sqlite:///./data/rapp.db`, `data/etl_workspace`) is unchanged; only what's behind each one moved. Durability of `rapp.db` is handled by `backend/core/backup.py` (SQLite online-backup API → `<ssd>/backups/`, keep-last-20, no-op when SSD absent), run automatically on server startup and on demand via `make backup-db` / `scripts/backup_rapp_db.command` (Finder double-click) / `scripts/backup_rapp_db.sh`. `chroma_db` is intentionally *not* auto-mirrored to the Mac (it's re-buildable and would eat the free space the split protects) — the existing `etl/export_kb.py` + `kb_export` Git-LFS path is the off-SSD KB snapshot mechanism.

### Known technical debt (explicitly identified, not exhaustive)
1. **`diagnose.py`'s free-text summary generation is intentionally less strict than repair-step generation** — it still calls Gemini ungrounded (ungrounded = ordinary LLM knowledge, no retrieved-text constraint) when RAG finds nothing, whereas repair-step generation refuses outright in the same situation. This is a deliberate, documented inconsistency (diagnosis is framed as best-guess triage, repair steps are framed as authoritative instructions), flagged explicitly as "worth a conscious call, not a unilateral fix" during this session's code audit, and not yet revisited by the user.
2. **The chat-reply cap (5 per vehicle) is enforced client-side only** (a `localStorage` counter), not server-side — a motivated user could clear localStorage and bypass it. Accepted as proportionate for the current single-operator/MVP stage; flagged as a tamper-resistance tradeoff, not silently assumed safe.
3. **`/garage`'s frontend does not yet display the `citations` field** on saved repairs, even though the backend/schema/DB column and typed API layer have supported it since this session's changes — this is backend-complete, frontend-pending, explicitly deferred as presentational (`.tsx`) work outside the backend-owned scope of this session.
4. **`frontend/src/lib/firebase.ts` is a dead stub** kept only so `isFirebaseConfigured()` returns `true` for a couple of presentational call sites (one such dead-code branch was found and removed from `results/page.tsx` during this session's audit; others may remain).
5. **No migration tool** — schema changes to existing SQLite tables require manually deleting/resetting the local dev DB file (`Base.metadata.create_all()` only creates missing tables). Encountered directly this session when adding the `citations` column to `saved_repairs`.
6. **Password reset / email verification are dev-mode only** — no real email provider is wired up; the reset/verify links are returned directly in the API JSON response for the frontend to render, rather than emailed. Explicitly must be replaced before any real user ever needs it.
7. **The ETL ingest manifest was globally keyed until this session** (a real, now-fixed bug): since NHTSA TSBs are frequently shared across multiple vehicle models/years, a global `nhtsa_id/file_name` key meant a shared bulletin only ever got tagged with whichever vehicle's ingest run processed it first — every subsequent vehicle silently skipped re-ingesting it, missing that vehicle's own metadata tag entirely, and could never retrieve it. Fixed by scoping manifest keys per-vehicle; Highlander's original ingest run had to be reset and redone after the fix (chunk count went from 995 to 2122 on the redo, confirming real data had been missed).
8. **A real accuracy bug in the free-diagnosis parts list** (found and fixed this session): the parts/cost estimate was chosen purely by symptom-keyword matching, independent of whatever the actual RAG-grounded repair procedure later determined — confirmed concretely with a 2010 Corolla brake query that returned a front disc pad/rotor parts list while the real grounded procedure (genuine NHTSA TSB content) was a rear drum-brake shoe job. Fixed via `refine_brake_category`, which checks real retrieved OEM text for drum-specific terminology before finalizing the parts template. This class of bug (symptom-keyword-matched parts list disagreeing with RAG-grounded actual procedure) may exist for other ambiguous categories beyond brakes; not audited exhaustively.

---

## 6. Roadmap, In-Flight Plans, and Explicit TODOs

**No inline `TODO`/`FIXME` comments exist in the codebase** (verified via repo-wide grep) — all forward-looking plans live in conversation/documentation, not code annotations. As of this session:

### Actively in progress
- **Google Jules ingestion hand-off**: Jules (Google's async cloud coding agent) will run the heavy NHTSA-TSB ingestion workload in its own cloud VM -- offloading CPU/RAM load from the local development machine -- then hand the resulting vector-store data back via a Git LFS commit (`kb_export/chroma_db`, `.gitattributes`-tracked), which the local machine merges into its live SSD-hosted store via `etl/import_kb.py` (upsert-based merge, not a raw file overwrite, since ChromaDB's metadata file is shared across all collections). **The export/import mechanism is built and verified end-to-end (a real 115MB Git LFS push, and a correctness-verified merge)**, and a full precise Jules task runbook exists at `docs/jules_ingestion_runbook.md`, including a sourced 20-vehicle starter batch (cross-checked against iSeeCars' on-road commonality study and full-year-2025 sales rankings). Status as of this document: the runbook is ready to hand to Jules; Jules has not yet run against it (see the timeline below for exact status).
- **National-scale vehicle coverage is explicitly out of scope for the current git/LFS-based architecture.** Research this session (independently verified, not just accepted from a pasted estimate) found: ~15,000-20,000 distinct Year-Make-Model combinations exist for the "modern era" (1992-2026) US market; NHTSA TSBs are scoped per vehicle *generation* (typically 5-6 years) rather than per individual year, so a smart per-generation ingestion strategy needs roughly 2,700-3,600 distinct ingestion targets rather than 15-20K. Even so, that projects to ~46-61GB for the vector store alone (measured ~17MB/vehicle rate) — beyond what Git LFS's free tier comfortably supports for a permanent, ever-growing store. **Explicit recommendation on record**: true exhaustive national coverage should live in a dedicated cloud storage bucket or managed vector DB service, with GitHub/git reserved for code and a curated subset (the current pilot, or the top 50-150 most common vehicles) rather than everything.
- **Ingestion queue as of this document**: Corolla, Highlander, Civic, Accord, Camry, F-150, and Lexus ES (300h) are ingested (~9,590 vector-store chunks total). This was a deliberately curated pilot set, explicitly stopped short of the full national-scope plan above pending the Jules/cloud-storage transition. The next batch (20 more vehicles, ~340MB projected) is specified and ready in `docs/jules_ingestion_runbook.md`, pending Jules actually running it.

### Identified but not yet built
- Extending the disc/drum-style RAG disambiguation pattern to other potentially-ambiguous repair categories beyond brakes (not audited).
- A CI job exercising the *real* backend end-to-end existed as a gap identified and closed this session (`e2e-real-backend` in `ci.yml`) — but it's scoped to a single smoke-test spec, not full parity with the mock-app suite's frozen-contract coverage.
- Garage UI surfacing of the now-backend-supported `citations` field (see tech debt #3).
- A real Stripe Checkout integration to replace the current mock/stub checkout-URL helper (status of exact completeness not independently re-verified for this document — treat `backend/services/stripe.py` as the authoritative current-state source, not this summary).
- Real email delivery to replace the dev-mode direct-link-in-response pattern for password reset/email verification.

---

## 7. Chronological Development Timeline

This section is a factual, chronologically-ordered record of every development step taken in the working sessions that produced the changes described above, for full traceability.

1. **Wired RAG-grounded repair-step generation** (`backend/services/llm.py` new module): consolidated previously-inline retrieval/generation/fallback logic from `backend/routers/repair.py`. Flipped ChromaDB's default embeddings from Gemini (`text-embedding-004`, paid) to local MiniLM (free). Fixed Gemini-embedding retry logic to stop retrying on 400/401/403 client errors. Added `settings.is_test_mode` to force mocked Gemini/vector-store clients in CI/test regardless of ambient secrets. Found and fixed a real bug where the vehicle-object request path stringified `year` before passing it to the RAG metadata filter, silently zeroing every match against the int-typed year in Chroma's stored metadata.
2. **Fixed a suite of ETL ingestion caveats**: manifest keys scoped per-vehicle instead of globally (fixing silent data loss for shared TSBs across vehicles — Highlander had to be reset and re-ingested, recovering more than double the original chunk count); added an advisory file lock (`_workspace_lock`) preventing two ingest runs from corrupting the same ChromaDB store concurrently; silenced third-party (`pdfminer`) debug-log spam that was drowning out actual ingest progress; added a live `progress.json` (written after every single PDF processed) plus `etl/progress_view.py`, a pretty-printer for watching ingestion progress in real time without polling an agent.
3. **Fixed hardcoded, vehicle-mismatched fallback citations**: both the curated template library and the generic zero-match fallback previously returned specific, often-wrong OEM manual names (e.g., citing a Honda manual for a Toyota query) regardless of the actual vehicle queried — replaced with an honest, dynamically vehicle-aware "no vehicle-specific source found, verify against official documentation" message. Also added forward-looking `source_authority` provenance flagging in citations, ahead of any non-official (community/UGC) data source ever being added.
4. **Ran a manual ingestion pilot**: Corolla, Highlander, Civic, Accord, Camry, F-150, Lexus ES (300h) — the last required discovering that NHTSA's model taxonomy calls it just "ES" (300h is a trim, not a distinct model name in their system) after an initial ingest attempt failed to find any match.
5. **Added a CI job exercising the real backend end-to-end** (`e2e-real-backend` in `.github/workflows/ci.yml`) plus a dedicated Playwright spec/config, distinct from the existing mock-app-only suite — verified locally to run clean in `ENVIRONMENT=test` mode with zero live Gemini/Chroma calls.
6. **Fixed a real CORS bug** found during a broader codebase audit: the catch-all exception handler ran inside Starlette's `ServerErrorMiddleware`, which wraps *outside* `CORSMiddleware`, so any genuine unhandled 500 never got CORS headers and surfaced to the browser as a network failure rather than a real error — fixed by attaching CORS headers manually in that handler. Also removed one confirmed-dead `isFirebaseConfigured()` UI branch.
7. **Extended RAG grounding to the free-diagnosis summary** (`generate_diagnosis_summary`), with a deliberately looser fallback than repair-step generation (diagnosis is best-guess triage, not authoritative instruction) — built without adding any new VIN-decode network dependency to a step that never had one.
8. **Added citation persistence to saved repairs** (`DbSavedRepair.citations`, `SavedRepairCreate`/`Response` schema fields, `frontend/src/lib/repairs.ts` typed layer) — backend-complete; garage UI display explicitly left as out-of-scope presentational work.
9. **Built and wired a real Gemini-backed repair-guide chat feature**, replacing pure client-side keyword matching: new `POST /api/repair/chat` endpoint grounded strictly in the exact `repair_steps` already shown to the user, same paywall gate as `/api/repair`, capped at 5 real AI replies per vehicle (localStorage-tracked) with a graceful fallback to the pre-existing canned responses. Verified via a real, user-driven, single-message GUI test (not just mocked unit tests) — confirmed correct tool-part-number extraction grounded in real retrieved OEM text.
10. **Fixed a confirmed real accuracy bug**: the free-diagnosis parts list disagreed with the actual RAG-grounded repair procedure for the same query (disc-brake parts recommended against a real drum-brake procedure) — added a `brakes_drum` template and `refine_brake_category`, which checks retrieved OEM text for drum-specific terminology before finalizing the diagnose parts list.
11. **Migrated the knowledge-base data directory to external SSD storage**: verified the SSD's actual filesystem (ExFAT, no native Unix symlink support at the target, though the symlink itself lives on the source APFS volume so this doesn't matter), copied and integrity-verified the full ingested dataset (byte-for-byte apparent-size match, exact ChromaDB document-count match), then symlinked `data/` to the SSD location in both the working worktree and the user's separate main checkout — preserving a pre-existing, non-empty main-checkout `data/` (which held 3 real user accounts) as an explicitly-protected, gitignored backup folder rather than deleting it.
12. **Researched and corrected GitHub/Git LFS storage-limit assumptions twice**, converging on an accurate picture: GitHub's own docs cite a 10GB *recommended* (not hard-blocking) on-disk size guideline for the main repository, entirely separate from Git LFS's own 10GB storage + 10GB/month bandwidth free-tier allowance (an earlier, outdated 1GB LFS figure was corrected mid-session). Independently verified Google Jules' actual sandbox capabilities (real Ubuntu VM with genuine internet access, supports environment variables/secrets and a setup script; hand-off mechanism is git-only, no documented arbitrary-file-export path) rather than assuming.
13. **Built the actual Git LFS hand-off mechanism**: installed `git-lfs`, added `.gitattributes` scoping LFS tracking to `kb_export/**/*.{sqlite3,bin,pickle}`, and wrote `etl/export_kb.py` (snapshots the live SSD-hosted `data/chroma_db` into the git-trackable `kb_export/chroma_db`, refusing to run if any ingest currently holds the workspace lock) and `etl/import_kb.py` (merges a pulled snapshot into the live store via document-level upsert, never a raw file copy, since ChromaDB's metadata file is shared across every collection and a blind copy would silently delete whatever the live side has that the snapshot doesn't). **Caught and fixed a real bug in the export script's own safety check** (it was checking the wrong file path for the ingest lock — the lock lives per-vehicle, not at the top-level workspace directory) by testing it directly rather than assuming it worked, and separately caught and cleaned up a self-inflicted double-process race condition during manual testing of the import script.
14. **Independently researched the true scope of "every relevant vehicle in the US"**: verified a user-supplied ~15,000-20,000 modern-era Year-Make-Model estimate against an independent source (Kelley Blue Book's ~275-models-available-at-any-time figure, extrapolated), and computed both naive (per-year) and smart (per-generation) storage projections, concluding that even the optimized approach (~46-61GB for the vector store alone) exceeds what a git/LFS-based architecture should durably hold — informing the explicit recommendation to keep git/Jules scoped to a curated subset and move to dedicated cloud storage for true exhaustive coverage.
15. **This document**: written as a standalone, cross-model-portable architecture snapshot, distinct from the continuously-maintained `CLAUDE.md`.
16. **Reconciled a local git divergence** after the PR merged: the user's separate main checkout had one small local commit (a `.gitignore` tweak duplicating content already fixed on the PR branch, plus a note file pointing at the ingestion-status doc) made before pulling the merge, causing a 1-ahead/16-behind divergence. Resolved with an explicit `git pull --no-rebase` (no global git config changed) and one trivial `.gitignore` conflict resolution; verified afterward that the SSD symlink, the live vector store (9,590 documents), and the user's note file all survived intact, and that the full test suite (112/112) still passed on the reconciled main checkout.
17. **Finalized the Jules runbook's starter batch**: replaced the original 12-vehicle placeholder proposal with a cross-checked, sourced 20-vehicle list (iSeeCars' 2020-2025 on-road-commonality study + full-year-2025 US sales rankings), each entry annotated with its source ranking, sized at ~340MB projected total -- far inside Git LFS's 10GB free tier. Documented an explicit, honest caveat that the representative "2021" model year per vehicle is a reasonable default, not an individually-verified generation-boundary determination per model.
18. **Wrote step-by-step, non-technical instructions** for the user to safely carry a Jules-produced PR all the way from GitHub through to a live, queryable local knowledge base: review checklist, `git pull` + `git lfs pull` (explicitly flagging that a plain `git pull` only fetches LFS pointer files, not real content), a real-vs-pointer-file sanity check, running `etl.import_kb`, a document-count confirmation, and a live `/api/repair` curl spot-check whose `citations` field is the actual proof the new data is retrievable -- not just present in a file. Saved as `JULES_PR_MERGE_INSTRUCTIONS.md` at the repo root for easy offline access.
