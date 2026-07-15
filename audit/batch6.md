# Batch 6 Audit — Tests, CI & Infra

STATUS: complete
SUMMARY: 16/16 units reviewed — 3 HIGH findings (CI e2e-tests job broken on main via chromium-only browser install; rapp.db not volume-mounted in docker-compose; NEXT_PUBLIC_API_URL baked wrong in frontend image), 6 Medium, plus doc-drift and coverage-gap items; full details per unit below.

## Scope (review units)
1. tests/verify_tests.sh
2. tests/e2e-mvp-flow.spec.ts
3. tests/mock_app.py (incl. drift check vs real app)
4. tests/e2e-real-backend-smoke.spec.ts
5. playwright.config.ts
6. playwright.real-backend.config.ts
7. .github/workflows/ci.yml
8. tests/unit/ — part 1 (api/vin/diagnose-repair tests)
9. tests/unit/ — part 2 (auth/security/payments tests)
10. tests/unit/ — part 3 (rag/llm/templates/pricing tests)
11. tests/unit/ — part 4 (remaining: safety/backup/etc.)
12. backend Dockerfile
13. frontend/Dockerfile
14. docker-compose.yml + docker-compose.dev.yml
15. Makefile + scripts/
16. .env.example + acceptance-criteria coverage map (ORIGINAL_REQUEST.md)

## Findings

### 1. tests/verify_tests.sh — reviewed
- **Sound overall**: 5 runs (1 healthy full-suite + 4 fault-injections), exit-code capture is correct (`exit_code=$?` immediately follows the playwright invocation), env flags explicitly reset per case, EXIT trap stops the server.
- **[Low] Fixed `sleep 2` server-start wait, no health poll** — on a slow/loaded machine the first Playwright hit can race the mock server and produce a spurious "normal conditions" failure. A curl-until-200 loop would make this deterministic.
- **[Low] `cleanup_port` does `kill -9` on *whatever* owns the port** — if an unrelated process holds 3699 it gets killed without confirmation it's mock_app. Low likelihood, but a pgrep filter on the command line would be safer.
- **[Info] Port is 3699 here, while playwright.config default/mock docs say 3099** — not a bug (FRONTEND_URL is passed through), but the two "mock ports" in the repo docs (3099 vs 3699) invite confusion.
- **[Info] Writes `mock_app.log` to repo root** — untracked artifact accumulating at root; covered by .claudeignore now, but `$CLAUDE_JOB_DIR`-style tmp or tests/ would be tidier.
- **[Info] Fault coverage is asymmetric by design**: SMALL_TOUCH_TARGETS is only verified via Step 1 (Step 2 also has 48px assertions but isn't run in that case); BYPASS_PAYWALL_GATE only via "Step 3" grep. Acceptable — one failing test per fault is enough to prove the suite catches it.


### 2. tests/e2e-mvp-flow.spec.ts — reviewed
- 9 tests covering: VIN entry + dark mode + 48px targets (Step 1), diagnose inputs/tools (Step 2), free summary + paywall gate + unlock flow (Step 3&4), non-dismissible red safety banner (Safety Protocol), YMM cascade + synthetic VIN (Step 5), back-nav (Step 6), spec auto-lock Corolla/Highlander (Steps 7–8), price table + garage CTA (Milestone 4).
- **[Medium — doc drift] Safety banner color contract: spec asserts RED (`border-red-500|bg-red-950|text-red-500`, lines 145–151) but CLAUDE.md's frozen-contract section still says "safety-warning-banner (orange classes, no dismiss button)".** The design-system merge (#9, "safety-banner red") changed the spec; CLAUDE.md's test-infrastructure paragraph was not updated. Whoever trusts CLAUDE.md will write orange classes and break the suite.
- **[Low] Paywall assertion is UI-visibility only** — asserts `locked-repair-steps` hidden and CTA present; it never asserts the *API* 402 gate (that's covered by unit tests instead, verified later). Combined coverage is fine, but the E2E "paywall gate" name overstates what it proves.
- **[Low] Milestone 4 uses non-testid selectors** (`.price-table`, `text=Save to My Garage & Keep Guide Forever`) — these are de-facto frozen contracts *not listed* in CLAUDE.md's frozen data-testid list. Renaming that class or copy string breaks CI with no documented warning.
- **[Info] Test VIN `1HGBH41JXMN109186` has an invalid check digit** — harmless against mock/synthetic paths, but against the real app it exercises live NHTSA (documented flake source).
- **[Info] Step 7 asserts localStorage `engine` = `"Gasoline · 1.8L I4"`** (powertrain-prefixed) while the visible engine-detail field holds `"1.8L I4"` — a subtle stored-shape contract the real frontend must keep matching (checked against mock_app next).
- Unlock-state key `rapp_unlocked_{vin}` and `/repair/success` redirect are asserted — matches CLAUDE.md contract.

### 3. tests/mock_app.py — reviewed (incl. drift check vs real app)
Purpose recap: mock exists to validate the E2E *suite* (fault injection), not the app. Reviewed for both internal correctness and drift.

**Verified in-sync with the real app (greps against frontend/src):**
- Synthetic VIN scheme: mock's hardcoded `makeCodes`/`modelCodes` (TOYOT/FORDX/…, COROLLA/F150XXX/…) produce exactly what the real `buildSyntheticVin` in `app/page.tsx:28-33` (5-char X-padded make + 7-char X-padded model) generates for every make/model the suite uses. ✓
- Engine localStorage shape: both join `powertrain · engineDetail` (`page.tsx:168` vs mock line 239). ✓
- Safety banner: both use `border-red-500 bg-red-950 text-red-500`, and `globals.css:123-125` defines those hand-written red hooks. Real banner (`results/page.tsx:279`) has no dismiss button. ✓
- `.price-table` class and "Save to My Garage & Keep Guide Forever" heading both exist in real `results/page.tsx` (437, 544). ✓
- specTable (Corolla 2009-19, Highlander XLE 2014-16) mirrors `vehicleSpecs.ts` per CLAUDE.md; both auto-select first trim on model change. ✓
- Default port 3099 matches playwright.config default. ✓

**Drift / issues found:**
- **[Medium — drift] Mock's `rag-citation` is the hardcoded string "Honda Civic ESM 2016-2021 Section 12-4" (line 471)** — this is *exactly* the fabricated-citation pattern that was deliberately purged from the real backend (blueprint fix: "hardcoded citations like 'Honda Civic ESM…' returned even for a Toyota query"). Harmless functionally (test only asserts visibility), but the mock now models behavior the real app is contractually forbidden from having; a future test asserting citation *content* against the mock would enshrine the anti-pattern.
- **[Medium — coverage gap] The mock (and therefore the entire fault-injection E2E suite) has no representation of newer shipped surfaces**: recalls/complaints on /results, three-tier parts list + `parts-plan-total`, chat panel, auth pages, /garage, VIN OCR/scan modals, `/api/*` endpoints (mock is pure HTML pages, no API layer). The frozen suite still tests only the Phase-1 MVP flow. Real-backend smoke may partially cover this (next unit).
- **[Low] Mock's paywall is presentational-only**: BYPASS_PAYWALL_GATE toggles CSS display, so the fault-injection proves the *test* notices a visible-steps regression — it cannot catch a real-app regression where the `/api/repair` 402 gate breaks while the UI still hides steps (that's covered only by unit tests).
- **[Low] Mock hardcodes DIY price $39.00 with "$4.00 guide fee"** while the real app computes `diy_total` from `cost_breakdown`; fine while no E2E asserts numbers, but a trap if one ever does.
- **[Info] Mock never guards missing localStorage keys** (real pages redirect to `/`) — deliberate, tests pre-populate; noted so nobody "fixes" it.
- **[Info] Duplicate `import os` inside `__main__` block (line 492)** — cosmetic.
### 4. tests/e2e-real-backend-smoke.spec.ts — reviewed
- Well-designed and honest about scope: single golden-path flow (YMM → diagnose → results → paywall → repair) against real backend+frontend in `ENVIRONMENT=test`; deliberately avoids NHTSA (synthetic VIN) and Gemini/Chroma (test mode). Comments accurately describe the fallback path exercised (MockVectorStore → template/generic steps).
- **[Low] Asserts the paywall UI gate but never the API gate here either** — it navigates straight to `/repair/success` and confirms steps render; a regression that made `/api/repair` stop 402-ing without a session id would not be caught by any E2E (only by unit tests). Cheap improvement: one `request.post('/api/repair')` without `stripe_session_id` asserting 402.
- **[Info] Only chromium, workers=1, retry 1 on CI — appropriate for a smoke test.**

### 5. playwright.config.ts — reviewed
- Correctly excludes the real-backend spec via `testIgnore`; baseURL defaults to 3099 (mock_app default). `webServer` intentionally commented out (verify_tests.sh owns server lifecycle).
- **[High — root cause of live CI failure, see unit 7] Defines 5 browser projects (chromium, firefox, webkit, Mobile Chrome, Mobile Safari) unconditionally.** CI's `e2e-tests` job installs *only* chromium. Every `npx playwright test` inside verify_tests.sh therefore fails on firefox/webkit ("Executable doesn't exist") in CI.
- **[Low] Both configs write to the same `playwright-report/` dir** — running mock suite then real-backend suite locally silently overwrites the first report.

### 6. playwright.real-backend.config.ts — reviewed
- Clean, single-spec `testMatch`, chromium-only, baseURL 3100, workers=1. Cross-references its CI job accurately. No issues beyond the shared report dir noted above.

### 7. .github/workflows/ci.yml — reviewed
- **[HIGH — CONFIRMED LIVE FAILURE] `e2e-tests` job is broken on main right now.** Verified via `gh run list`/`gh run view --log-failed`: latest main run (2026-07-06) — `backend-quality`, `frontend-build`, `e2e-real-backend` all pass; `e2e-tests` fails in "Run E2E verification harness" with dozens of `browserType.launch: Executable doesn't exist … firefox-1532 / webkit-2311`. Cause: job runs `npx playwright install --with-deps chromium` (ci.yml:67) but verify_tests.sh runs the full 5-project matrix. Every recent run on every branch is red for this reason.
- **[HIGH — soundness consequence] The fault-injection verification is vacuous in CI**: cases 2–5 *expect* a non-zero exit, and missing firefox/webkit guarantees non-zero exit regardless of whether the injected fault is actually detected. So in CI, verify_tests.sh currently proves nothing about the suite's fault-catching ability — only the "Normal Conditions" case fails visibly. Fix options: install all browsers in CI (slow), or run verify_tests with `--project=chromium` in CI (`FRONTEND_URL=… npx playwright test --project=chromium`, e.g. via a `PW_ARGS`/`PLAYWRIGHT_PROJECT` env the script passes through).
- **[Medium] `frontend-build` runs `pnpm build` — the exact invocation CLAUDE.md documents as failing locally with `ERR_PNPM_IGNORED_BUILDS`.** It passes in CI (fresh CI env behaves differently), but the repo now has two divergent canonical build commands (CI: `pnpm build`; local: `./node_modules/.bin/next build`) — worth unifying so local verification actually reproduces CI.
- **[Low] `pnpm install` in `e2e-real-backend`/`frontend-build` is unpinned** (no explicit `--frozen-lockfile`; pnpm does default to frozen when `CI=true`, so this works, but implicitly).
- **[Low] `on: push: branches: ["**"]` + `pull_request: branches: [main]`** double-runs every PR commit; no `concurrency` group to cancel superseded runs — wasted minutes, no correctness issue.
- **[Info] Good practices present**: real-backend job health-polls both servers with logs-on-failure artifacts, pins `DATABASE_URL` outside the repo, leaves `GEMINI_API_KEY` unset by design, kills servers in `if: always()`; `e2e-tests` uploads playwright-report on failure.
- **[Info] Real-backend smoke runs the frontend via `next dev`, not a production build** — acceptable for smoke, but means CI never exercises the production bundle against the real backend (frontend-build compiles it but never serves it).
### 8. tests/unit — part 1: conftest.py, structlog.py, test_api.py, test_rag.py, test_challenge.py — reviewed
- **conftest.py**: correctly forces `ENVIRONMENT=test` before the Settings singleton instantiates, with an accurate comment about .env leakage. Good.
- **[Medium] `tests/unit/structlog.py` is a fake structlog module that shadows the real installed package** for any test run where `tests/unit/` lands on `sys.path` (pytest's rootdir insertion — no `__init__.py` in tests/unit). Its header claims it exists "to allow running unit tests without external package installation," but structlog *is* a real installed dependency (`uv sync`). Consequences: backend logging code paths are silently no-oped during unit tests (a structlog misconfiguration would never be caught), and any future test importing structlog directly gets the stub. It also invites confusion — nothing marks it as a shim except one comment. Either delete it (structlog is installed everywhere tests run) or move it into an explicit mocking fixture.
- **test_api.py (775 lines, the backbone)**: genuinely strong coverage — VIN decode success/retry/invalid/404/offline-fallback/unknown-WMI-502 + powertrain derivation (EV, PHEV) + User-Agent header assertion; synthetic VINs incl. case-insensitivity and 4 error shapes; diagnose low/high-risk (all three hard-coded hazard systems asserted with exact copy), grounded vs ungrounded Gemini, Gemini-failure fallback; parts/cost invariants (3 tiers exactly, `diy_total = 4.00 + parts_total`, empty-not-omitted zero case); drum/disc disambiguation both directions; repair 402 gate, RAG path, honest zero-hit citation (explicitly asserts `"ESM" not in citation` — regression-locks the fabricated-citation fix), structured-output schema, Gemini-failure→template; payments mock mode + 303 stub + webhook 503; OCR content-type/empty/no-key-503/success/422; check-digit helpers; chat 402/grounded/null-reply.
- **[Medium — coverage gap] No test for the OCR 429 path** (`GeminiRateLimitError` → HTTP 429). CLAUDE.md calls this distinction load-bearing (the scan loop must not mistake throttling for "no VIN"); it is the one documented OCR status code with no unit test. Similarly untested: the >20MB upload cap and the Pillow downscale/re-encode normalization (`_normalize_image_for_vision` is only exercised with fake bytes that never hit a real decode path — presumably mocked; a tiny real JPEG fixture would cover it).
- **[Low] `test_diagnose_low_risk` sends `obd_codes` as a bare string** (`"P0101"`) — passes, meaning the backend schema silently tolerates a shape the pinned contract forbids ("always send as an array"). Fine as leniency, but the test enshrines it without saying so.
- **test_rag.py**: covers metadata filtering (full 5-field), case/list normalization, punctuation, empty stores, singleton thread-safety (20 threads), ephemeral Chroma when installed, and the import-hygiene contract. Solid. Two notes: **[Info]** import-hygiene scans `backend/**` only — `etl/` importing chromadb directly would pass unnoticed (blueprint states the rule as backend-scoped, so consistent, just narrower than CLAUDE.md's "nothing outside backend/rag/" phrasing); **[Info]** several tests poke the private `backend.rag._vector_store_instance` directly rather than a reset helper — workable, mildly brittle.
- **test_challenge.py**: robustness edge cases (missing/None obd_codes, RAG returning None/empty/malformed metadata, redirect param preservation, webhook 503 for valid/empty/malformed JSON with an honest comment that this only proves the unconfigured path).
- **[Low] Fabricated-citation tension**: when RAG returns a doc with missing/None metadata, the asserted citation is `"HONDA CIVIC Manual (2018)"` — a synthesized manual name derived from VIN meta, not from any real source. This is the same *class* of invented citation the zero-hit path was purged of; a metadata-less chunk yields a plausible-sounding manual that doesn't exist. Worth a conscious decision in the backend batch.
### 9. tests/unit — part 2: test_auth.py, test_repairs_db.py, test_stripe_payments.py — reviewed
- **test_auth.py** tests **magic-link auth** (`/api/auth/request-link`, `/api/auth/verify-link`) — and the security-critical cases are all present: single-use token (reuse → 401), type-claim scoping in *both* directions (access token rejected as verify token and vice versa), per-email rate limit (429), and the standout `test_request_link_does_not_leak_link_when_send_fails` (a configured-but-failing email provider must NOT fall back to returning the magic link — would let anyone sign in as any address). Missing-header 403 vs invalid-token 401 distinction documented. High quality.
- **[Medium — doc drift] CLAUDE.md and RAPP_BLUEPRINT.md still document the *password* auth stack** (`signup`/`login`/`forgot-password`/`reset-password`/`send-verification`/`verify-email`, scrypt hashing, reset/verify token types), but the tests — and per merge `0f8be24` ("magic-link auth") the code — are magic-link-based. Neither doc mentions `request-link`/`verify-link`. Whichever direction is current truth (tests strongly suggest magic-link), both architecture docs are stale on the auth flow, endpoint list, and token-type taxonomy.
- **test_repairs_db.py**: covers auth-required (403), save/list round-trip incl. `citations`, minimal-fields nulls, **per-user scoping** (user B can't see user A's repairs), most-recent-first ordering. In-memory SQLite via dependency override + StaticPool — correct pattern, no shared state.
- **test_stripe_payments.py**: exemplary — webhook tests build a **real Stripe-format HMAC signature** (`t=...,v1=...`) and exercise actual verification (valid → 200, wrong secret → 400, missing header → 400); checkout covers mock-mode fallback, live-mode URL passthrough, metadata (vin/symptoms/user_id from bearer token, empty when anonymous), and 502 on Stripe failure.
- **[Low] No webhook replay/timestamp-tolerance test** (Stripe signatures embed `t=`; if verification ignores staleness, a captured event could be replayed — depends on `stripe.Webhook.construct_event` defaults, which do enforce tolerance; worth one test to pin it).

### 10. tests/unit — part 3: test_pricing.py, test_templates.py — reviewed
- **test_pricing.py**: price parsing (range/single/default), 3-tier invariants (Budget < OEM < Upgrade), cost-breakdown invariants across *every* template ($4 fee arithmetic, dealership > independent > DIY, sane ranges), and Amazon associate-tag behavior (untagged by default, tagged when configured, non-Amazon URLs never tagged). Thorough for pure functions.
- **test_templates.py**: OBD-code matching (P0301/P0420/C0035), code embedded in free text, keyword fallbacks (brakes/suspension/charging), None-safety, ≥14 steps per template, ≥1 citation & part per template, no emoji, ≥10 templates.
- **[Low — contract wording drift] Torque callout: CLAUDE.md's pinned contract says torque steps "are guaranteed to **start with** the literal word 'Torque '", but `test_every_template_has_a_torque_callout` asserts `"Torque " in step` (anywhere), with a comment saying the frontend regex also matches anywhere.** The test+frontend agree with each other; the pinned-contract doc overstates the guarantee. Align the doc (or tighten the test) so the contract is stated once, correctly.

### 11. tests/unit — part 4: test_vehicle_safety.py, test_vin_fallback.py, test_backup.py, test_etl_loader.py — reviewed
- **test_vehicle_safety.py**: parsing, empty results, graceful degradation on ConnectError/Timeout (never 5xx — matches the documented design), case-insensitive cache hit, multi-component complaint aggregation (comma-split, each counts), endpoint 422 on missing params. Autouse cache-clearing fixture prevents cross-test bleed. Gaps (minor): TTL *expiry* is untested (only cache hits), and the documented "top 5 components" cap is never asserted.
- **test_vin_fallback.py**: both year-decode cycles (numeric pos-7 → 1980s cycle, alpha pos-7 → 2010s cycle), unknown WMI → None, model deliberately blank. Small and exactly right.
- **test_backup.py**: backup produces a valid queryable copy (PRAGMA integrity_check), no-ops when source missing or backup volume absent, prune keeps newest N. Doesn't exercise a live-WAL source (the scenario the online-backup API exists for), but acceptable.
- **test_etl_loader.py**: includes the **regression test for the per-vehicle manifest scoping bug** (shared NHTSA id across two vehicles tracked independently) plus reset_vehicle and chunk→document conversion (ids, uppercased make, table→markdown). Two blemishes: **[Low]** `test_load_into_vector_store` sets `os.environ["VECTOR_STORE"]="mock"` without cleanup (leaks into later tests in the same process — harmless today only because conftest forces test mode) and asserts nothing beyond "didn't crash". **[Info]** ETL coverage stops at the load layer: pipeline.py's workspace lock, progress.json, and export/import (import_kb upsert-merge correctness — a data-loss-critical path per the blueprint) have no unit tests at all; they were verified manually per the blueprint.
### 12. backend/Dockerfile — reviewed
- Good multi-stage build: standalone uv binary, layer-cached dep install (`--frozen --no-install-project` then full sync), dev group excluded, non-root user, gunicorn+uvicorn workers, logs to stdout. No issues with the image itself.
- **[Info] 2 gunicorn workers × process-local state**: the auth per-email rate-limit dict and the NHTSA safety TTL caches are per-process, so limits/caches are effectively halved/duplicated across workers. Known-acceptable at this scale, but worth remembering before raising worker count.

### 13. frontend/Dockerfile — reviewed
- Correct standalone build (`next.config.mjs` has `output: 'standalone'` — verified), frozen lockfile, non-root, static assets copied properly.
- **[HIGH — deploy correctness] `NEXT_PUBLIC_API_URL` is never provided at build time.** Next.js inlines `NEXT_PUBLIC_*` into the client bundle during `pnpm build`; this Dockerfile has no `ARG`/`ENV` for it, so every image bakes the fallback `http://localhost:8000` (`api.ts:1`). docker-compose.yml then sets it as a *runtime* env var (line 32), which does nothing for client-side code. It "works" locally only because the user's browser resolves localhost itself. Any non-localhost deployment of these images will silently point the UI at the wrong backend. Fix: `ARG NEXT_PUBLIC_API_URL` → `ENV` in the builder stage + `build.args` in compose.

### 14. docker-compose.yml + docker-compose.dev.yml — reviewed
- **[HIGH — data durability] `rapp.db` (the "tiny and irreplaceable" accounts DB) is NOT on a volume.** Only `chroma_data:/app/data/chroma_db` is mounted; with default `DATABASE_URL` the accounts DB lands at `/app/data/rapp.db` in the container's writable layer and is destroyed on `docker compose down`/image recreate (`docker-clean` in the Makefile removes volumes too, but rapp.db doesn't even survive an ordinary rebuild). The repo's whole SSD-split design treats rapp.db as the one thing that must never be lost — the compose file inverts that: the re-buildable KB is persisted, the irreplaceable DB is ephemeral. The SSD-based `backup_rapp_db` also can't run inside the container. Add a named volume (or bind mount) for `/app/data` minus chroma, or set `DATABASE_URL` onto a mounted path.
- **[Medium] docker-compose.dev.yml's frontend override is broken as written**: it overrides `command: pnpm dev` but not the build `target`, so the container runs the *runtime* stage image — which contains only the standalone `server.js` output, no `pnpm`, no full source tree, no dev node_modules. It also mounts `./frontend/src:/app/src`, a path the standalone output doesn't read. (Backend dev override correctly targets `builder`.) `make docker-up` therefore can't work for frontend hot reload.
- **[Low] `env_file: .env` is required to exist** or compose errors; fine for this repo (a real `.env` is present) but worth a `required: false` or documented copy step for fresh clones.
- **[Info] Healthchecks on both services are well-formed** (python urllib / node http, sane intervals, `depends_on: service_healthy`); `VECTOR_STORE`/`CHROMA_DB_PATH` env plumbing matches what `backend/rag/__init__.py:47` actually reads. ✓

### 15. Makefile + scripts/ — reviewed
- Makefile targets map cleanly onto CI and CLAUDE.md commands, with two consistency slips: **[Low]** `dev-frontend`/dev-compose use `pnpm dev`, the exact invocation CLAUDE.md documents as broken locally (`ERR_PNPM_IGNORED_BUILDS`) — the documented workaround (`./node_modules/.bin/next dev`) never made it into the Makefile; **[Low]** `test-e2e` runs `npx playwright test` with no server startup, so it fails unless the user separately started mock_app or a dev stack (only `test-verify` is self-contained). **[Info]** `make install` installs *all* Playwright browsers (`--with-deps`, no filter) — consistent with the 5-project config and further evidence the CI-side chromium-only install (unit 7 HIGH) is the outlier.
- `backup-db` + `scripts/backup_rapp_db.sh` + `.command`: single source of truth in `backend/core/backup.py` (has a `__main__` entry — verified), repo-root-resolving wrapper, honest comments. Clean.
- `scripts/check_kb.py` (KB doc-count + retrieval spot check), `ingest_seed_vehicles.py` + `seed_vehicles.json` (pilot batch driver): fine as operator tools.
- **[Low] `scripts/reindex_with_gemini.py` and `.env.example`'s `USE_GEMINI_EMBEDDINGS=true` both contradict the recorded cost-control decision** (local MiniLM embeddings are the default; Gemini embeddings are opt-in *and paid*). A fresh developer copying `.env.example` silently opts into paid embeddings, and the reindex script's docstring ("for improved retrieval quality") reads as a recommendation. Flip the example to `false`/empty and add a cost warning to the script.
- **[Medium] `.env.example` is stale in both directions**: it still lists `PINECONE_API_KEY`/`PINECONE_INDEX` ("when VECTOR_STORE=pinecone" — no pinecone backend exists in `backend/rag/`), while missing variables the code now reads: `RESEND_API_KEY` (magic-link email), `AMAZON_ASSOCIATE_TAG`, `RAPP_BACKUP_DIR`, `ENVIRONMENT`, `ALLOWED_ORIGINS`, `STRIPE_PRICE_*` usage should be re-verified. Also `JWT_SECRET_KEY`'s example value is 25 chars — below the ≥32-byte guidance CLAUDE.md itself gives (PyJWT warns).
### 16. Acceptance-criteria coverage map (ORIGINAL_REQUEST.md → tests/CI) — reviewed
ORIGINAL_REQUEST.md contains four Acceptance Criteria blocks (initial build, follow-up production pass, UI-evolution pass, affiliate/results pass). Mapping each to what actually verifies it today:

**Covered (automated, trustworthy):**
- `/health` 200, VIN decode field population, diagnose/repair/payments routes respond → `test_api.py` (mocked NHTSA; live-NHTSA behavior is deliberately untested in automation — acceptable).
- ruff/mypy/black exit 0 → CI `backend-quality` (the AC's "poetry run" wording is superseded by uv — docs already note this).
- chromadb isolation → `test_rag.py::test_import_hygiene`.
- Frontend builds with zero TS/ESLint errors → CI `frontend-build`.
- 5 routes resolve; VIN input + scan CTA; ≥48px targets; free/locked visual separation; frozen `data-testid`s; unlock flow; YMM cascade + auto-lock; price-table columns; garage sign-up presence → `e2e-mvp-flow.spec.ts` (against the mock) + real-backend smoke for the golden path.
- JWT issue/verify against users table; `/garage` data layer; per-user scoping → `test_auth.py`/`test_repairs_db.py`. `.env.example` has `DATABASE_URL`+`JWT_SECRET_KEY` ✓.
- 3-tier parts + $4.00 DIY math → `test_pricing.py` + `test_api.py` (note: the spec text says "2 structured options" per part; the shipped/pinned contract is 3 tiers — the contract superseded the spec, tests follow the contract).

**Not covered by any automation (gaps, ranked):**
1. **Docker AC ("docker compose up starts both services, health checks pass") — zero coverage.** No CI job ever builds either image. Combined with the three compose/Dockerfile defects above (rapp.db ephemeral, NEXT_PUBLIC_API_URL baked wrong, dev override broken), this AC is currently *failing in substance* and nothing would notice.
2. **"All 4 Playwright E2E tests pass against the real Next.js frontend"** — the frozen suite runs only against mock_app in CI; the real frontend gets one smoke path. The AC as written is only satisfiable manually (`FRONTEND_URL=localhost:3000`).
3. Tesseract.js OCR fallback, camera scan modals, photo previews/HEIC, OBD-II picker search, tool-inventory filtering, chat panel default-visible, inline diagrams, Conclusion/Verification phase, results-page back button, garage page rendering — all presentational-pass ACs with no automated assertions (mock app predates these features entirely; see unit 3 coverage-gap finding).
4. "Safety banner with **orange** classes" (third AC block) vs. the shipped **red** banner asserted by the suite — the AC text and CLAUDE.md are both stale relative to the design-system merge; the tests are internally consistent with the code.
5. "Under 10 seconds" response-time requirement — never measured anywhere (no timing assertion in any suite).

## Summary of key findings (severity-ordered)
1. **[HIGH] CI is red on main**: `e2e-tests` installs only chromium but runs the 5-browser matrix → every run fails on firefox/webkit, and the 4 fault-injection cases pass vacuously (they expect failure, which missing browsers guarantee). Fix: `--project=chromium` in CI or install all browsers. (unit 7)
2. **[HIGH] docker-compose leaves rapp.db (irreplaceable accounts DB) in the container's ephemeral layer** while persisting only the re-buildable chroma volume — inverts the repo's own durability design. (unit 14)
3. **[HIGH] Frontend Docker image bakes `NEXT_PUBLIC_API_URL` fallback at build time**; compose's runtime env var is inert for client code — any non-localhost deploy silently targets the wrong backend. (unit 13)
4. **[Medium] Docker acceptance criteria have zero automated coverage** — the three findings above are invisible to CI. (unit 16)
5. **[Medium] docker-compose.dev.yml frontend hot-reload override cannot work** (runtime-stage image lacks pnpm/source). (unit 14)
6. **[Medium] Doc drift, three instances**: CLAUDE.md says safety banner = orange (code/tests = red); CLAUDE.md+blueprint document password auth (code/tests = magic-link `request-link`/`verify-link`); CLAUDE.md says torque steps "start with" `Torque ` (tests+frontend: "contains"). (units 2, 9, 10)
7. **[Medium] `.env.example` stale**: `USE_GEMINI_EMBEDDINGS=true` contradicts the cost-control default, dead Pinecone vars, missing `RESEND_API_KEY`/`ENVIRONMENT`/`ALLOWED_ORIGINS`/`AMAZON_ASSOCIATE_TAG`/`RAPP_BACKUP_DIR`, weak example JWT key. (unit 15)
8. **[Medium] `tests/unit/structlog.py` shadows the real structlog package** during test runs for no current reason. (unit 8)
9. **[Medium] Coverage gaps**: OCR 429/`GeminiRateLimitError` path untested; mock app (and thus the whole fault-injection suite) covers only the Phase-1 flow — recalls, parts dashboard, chat, auth pages, garage, scan modals have no E2E representation; ETL pipeline lock/progress/import_kb untested. (units 3, 8, 11)
10. **[Low] assorted**: mock's hardcoded "Honda Civic ESM" citation models the purged anti-pattern; synthesized `"HONDA CIVIC Manual (2018)"` citation for metadata-less RAG docs; Milestone-4 selectors not in the frozen-testid registry; verify_tests.sh sleep-based startup + kill -9 by port; Makefile `pnpm dev`/`test-e2e` inconsistencies; shared playwright-report dir. (units 1, 2, 3, 8, 15)

STATUS-DETAIL: all 16 units reviewed; single pass, no re-verification, per instructions.
