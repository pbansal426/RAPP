# Complete Jules Instructions — Start to Finish

Everything you need, in order, from starting the Jules task right now
through to the new knowledge base being live on your SSD. Nothing here
depends on anything outside this file.

---

## PHASE 1 — Start the Jules task (do this now)

### 1. Go to Jules and sign in
Go to `jules.google.com` (or the Jules app if you have it installed) and
sign in with the same Google account tied to your AI Pro subscription.

### 2. Connect your GitHub repository (if not already connected)
Jules needs permission to access your GitHub account. Look for a
"Connect GitHub" or repository-selection step during first-time setup —
authorize it for your `pbansal426/RAPP` repo specifically (or all repos,
your call).

### 3. Start a new task
Look for "New Task" (or similar). Select:
- **Repository**: `pbansal426/RAPP`
- **Branch**: `main` (current, merged, up to date — everything Jules
  needs is already there: `etl/export_kb.py`, `etl/import_kb.py`,
  `.gitattributes`, this file, and `docs/jules_ingestion_runbook.md`)

### 4. Paste this exact task description

```
Context: RAPP is an automotive repair app. Its knowledge base is built by
running an ETL pipeline (etl/ package) that pulls NHTSA Technical Service
Bulletins and loads them into a local ChromaDB vector store. Your job is
to run this ingestion for a specific list of vehicles and publish the
result -- you are NOT deciding which vehicles to ingest (that list is
given to you exactly) and you are NOT modifying application code unless a
genuine bug in the ETL pipeline itself blocks ingestion.

Setup:
1. `uv sync --all-groups` (installs the etl dependency group too).
2. Confirm `git lfs install` has been run (`git lfs version` should not error).

Vehicle list (process in this order):
1. 2021 Chevrolet Silverado 1500
2. 2021 Ram 1500
3. 2021 Chevrolet Equinox
4. 2021 Nissan Rogue
5. 2021 Ford Explorer
6. 2021 Chevrolet Malibu
7. 2021 Toyota Tacoma
8. 2021 Toyota RAV4
9. 2021 GMC Sierra 1500
10. 2021 Nissan Altima
11. 2021 Honda CR-V
12. 2021 Jeep Grand Cherokee
13. 2021 Hyundai Tucson
14. 2021 Ford Escape
15. 2021 Ford Edge
16. 2021 Chevrolet Traverse
17. 2021 Chevrolet Trax
18. 2021 Chevrolet Tahoe
19. 2021 Kia Sportage
20. 2021 Mazda CX-5

For EACH vehicle above, in order:
1. Run: `uv run --group etl python -m etl --year <YEAR> --make <MAKE> --model <MODEL> --all --load`
2. If it fails with "NHTSA vehicle search found no match", NHTSA's model
   naming may differ from the common name (e.g. a "300h" trim doesn't
   exist as a model name in NHTSA's system -- it's just "ES"). Try ONE
   simplified variant of the model name (drop trim suffixes, try the base
   nameplate). If it still fails, skip that vehicle, log it clearly in
   your final report, and move to the next one -- do not guess further or
   substitute a different vehicle.
3. After EVERY vehicle (success or skip), check the total size of
   kb_export/ so far would stay under 5GB after export (see step 4) --
   if a single vehicle's data would push the total over that limit, stop
   immediately, do not export or commit, and report this in your summary
   instead. This is a hard stop, not a warning to note and continue past.

After the entire list is processed (or you hit the 5GB stop condition):
1. Run: `uv run python -m etl.export_kb`
   - If this refuses to run because "another etl ingest currently holds
     the workspace lock," something is still running -- wait and retry,
     do not force past this.
2. Run `git add kb_export/` -- verify with `git status` that ONLY
   kb_export/ files (plus, if you touched it, docs/ingestion_status.md)
   are staged. Do NOT `git add -A` or `git add .`.
3. Update docs/ingestion_status.md: add a row per vehicle you processed
   (Year | Make | Model | Status | Records Found | PDFs Ingested | PDFs
   Skipped | PDFs Failed | Chunks Loaded | today's date), matching the
   existing table's format exactly. Mark any skipped vehicle clearly as
   skipped with the reason (e.g. "NHTSA has no match under this name").
4. Commit with a clear message listing exactly which vehicles were added
   and their chunk counts. Push to a NEW branch (do not push to main
   directly) and open a PR.
5. In the PR description, include: the full list of vehicles processed,
   their individual chunk counts, any skipped vehicles and why, and the
   total kb_export/ size after this batch.

Hard rules -- do not deviate from these:
- Never modify anything under backend/ or frontend/ unless the ETL
  pipeline itself is broken and blocking ingestion -- and if you do,
  explain exactly why in the PR description, run
  `uv run ruff check backend/ && uv run black --check backend/ &&
  uv run mypy backend/ && uv run pytest tests/unit/ -q` before
  committing, and keep that change in a clearly separate commit from the
  data commit.
- Never touch data/, data.bak_*, or anything matching those gitignore
  patterns -- these are machine-specific and/or contain real user data
  backups that must never be committed or deleted.
- Never use --reset-vehicle on a vehicle you didn't just ingest yourself
  in this task -- it clears that vehicle's manifest history.
- Never force-push, never rewrite history, never delete branches other
  than your own working branch.
- If anything is ambiguous or a check fails in a way this runbook didn't
  anticipate, stop and describe the problem in the PR description (or as
  a comment/note) rather than guessing at a fix.
```

### 5. Submit it and let it run
Jules works asynchronously in its own cloud VM — you don't need to
babysit it. Based on how long ingestion took locally (each vehicle took
a few minutes on your Mac), 20 vehicles could reasonably take anywhere
from 1-3+ hours in Jules' environment; there's no way to give you an
exact number since Jules' actual compute speed isn't something visible
from here.

### 6. Wait for Jules to open a PR
Jules will notify you (or you'll see it in its task list) once it's done
and has pushed a branch + opened a PR on GitHub.

**Honest caveat**: steps 1-4 above are based on how Jules is documented
to work, not a screenshot-verified walkthrough of its current UI. If any
button names or the exact flow don't match what you see, look for the
closest equivalent — the substance (connect repo → new task → paste
description → submit) should hold regardless of exact wording.

---

## PHASE 2 — After Jules opens a PR

### Step 1: Review the PR before touching anything
Open the PR on GitHub and check:
- The vehicle list in the PR description matches what was given (or has
  a good explanation for any skipped ones).
- `docs/ingestion_status.md` was updated with new rows.
- **Nothing under `backend/`, `frontend/`, or `data/` was touched** —
  only `kb_export/` and the status doc should show as changed. If you
  see anything else, stop and ask Claude before merging.

### Step 2: Merge the PR
Use GitHub's normal merge button — same as before.

### Step 3: Pull it down to your machine
```bash
cd /Users/prathambansal/Dev/RAPP
git pull
```

### Step 4: Actually fetch the real LFS content (don't skip this)
A normal `git pull` only downloads small pointer files for LFS-tracked
content, not the actual data. This step pulls the real thing:
```bash
git lfs pull
```

### Step 5: Confirm you got real data, not pointer files
```bash
ls -la kb_export/chroma_db/chroma.sqlite3
```
You want to see a size in the tens of megabytes or more. If it shows
something tiny (under 1KB), the LFS pull didn't work — stop here rather
than continuing.

### Step 6: Merge Jules's data into your live SSD-hosted store
```bash
uv run python -m etl.import_kb
```
Watch the output — it prints `Imported X/Y` as it goes, then ends with
`Done: merged Y documents from kb_export/chroma_db into the live store.`
Let it finish; for ~20 vehicles this can take several minutes (it's
re-computing embeddings locally, which is CPU-bound) — don't interrupt it.

### Step 7: Confirm the numbers actually add up
```bash
uv run python -c "
import chromadb
from chromadb.config import Settings
client = chromadb.PersistentClient(path='data/chroma_db', settings=Settings(anonymized_telemetry=False))
coll = client.get_or_create_collection('repair_manuals')
print('total documents now in your live SSD store:', coll.count())
"
```
This should be noticeably higher than the count before this batch
(9,590 as of this writing), roughly matching the chunk totals Jules
reported in its PR, added on top.

### Step 8: The real proof — confirm the app can actually use it
File presence alone doesn't prove it works. Pick one of the
newly-ingested vehicles and hit the real endpoint:
```bash
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8123 &
curl -s -X POST http://127.0.0.1:8123/api/repair \
  -H "Content-Type: application/json" \
  -d '{"vin":"test","symptoms":"<a real symptom for one of the new vehicles>","stripe_session_id":"test","vehicle":{"year":2021,"make":"<make>","model":"<model>"}}' \
  | python3 -m json.tool
```
Look at the `citations` field in the response:
- If it says something like `"NHTSA TSB T-SB-..."` — the new data is
  live and retrievable. Done.
- If it says `"no vehicle-specific NHTSA TSB or OEM documentation was
  found"` — either that specific query didn't match, or something in
  steps 4-7 didn't fully take. Try a different symptom/vehicle from the
  batch before assuming a problem.

**Once step 8 shows a real citation, the knowledge base has fully made
it from Jules → GitHub → your Mac → the SSD.** Repeat Phase 1 with a new
vehicle list for the next batch, then Phase 2 again after that PR too.
