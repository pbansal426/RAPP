# Google Jules Ingestion Runbook

This is the precise, self-contained task specification for handing NHTSA TSB
ingestion off to Google Jules. Everything it references already exists and
has been tested end-to-end in this session — Jules is executing an already-
proven mechanism, not improvising a new one.

## Why this exists / what problem it solves

The local Mac running this ingestion is memory-constrained (8GB RAM) and the
ingestion workload (PDF parsing + local embedding computation) is CPU-heavy.
Jules runs in its own cloud VM, so offloading the ingestion workload there
frees up the local machine entirely. The catch: Jules can only hand work
back via git (a branch/PR), and the *live* knowledge base
(`data/chroma_db`) lives on an external SSD, symlinked into the repo and
therefore **not git-trackable at all** (git cannot see inside a symlinked
directory). The solution already built and verified this session:

```
Jules (cloud VM)                          This machine (SSD-backed)
─────────────────                          ──────────────────────────
1. Run ingestion for a vehicle list   →
2. etl.export_kb (snapshot to
   kb_export/chroma_db)
3. git commit + push (Git LFS)        →    4. git pull / git lfs pull
                                            5. etl.import_kb (merges the
                                               snapshot into the live SSD
                                               store via upsert -- never
                                               a raw file copy, since
                                               chroma.sqlite3 is a single
                                               metadata file shared across
                                               every vehicle's data)
```

Both directions were tested for real this session: the export→commit→push
path uploaded a genuine 115MB snapshot through Git LFS successfully; the
import/merge path was verified to preserve pre-existing data while adding
new documents, with no loss or duplication, via a small targeted test.

## Prerequisites (already done, listed for completeness)

- `git-lfs` installed and `git lfs install` run in this repo.
- `.gitattributes` tracks `kb_export/**/*.{sqlite3,bin,pickle}` via LFS.
- `etl/export_kb.py` and `etl/import_kb.py` exist, are tested, and are
  committed on `worktree-generic-dancing-blum` (or `main`, once merged).
- `data/` remains gitignored (it's the SSD symlink) — Jules should never
  try to commit anything under `data/` directly, only `kb_export/`.

## The exact task to give Jules

Copy this block as Jules's task description, filling in the vehicle list
in the placeholder section below first (see "Proposed starter batch").

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

For EACH vehicle in the list below, in order:
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
   and their chunk counts. Push to a NEW branch (do not push to main or
   to worktree-generic-dancing-blum directly) and open a PR.
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

## Proposed starter batch (fill in before handing to Jules)

Already ingested, do NOT repeat: 2010 Toyota Corolla, 2015 Toyota
Highlander, 2018 Honda Civic, 2018 Honda Accord, 2018 Toyota Camry, 2018
Ford F-150, 2025 Lexus ES.

A reasonable next batch, chosen for high real-world relevance (top-selling
US models, spread across manufacturers not yet covered) and small enough
to stay comfortably within a single safe iteration:

| Year | Make | Model |
|------|------|-------|
| 2020 | Toyota | RAV4 |
| 2020 | Honda | CR-V |
| 2020 | Ford | Explorer |
| 2020 | Nissan | Rogue |
| 2020 | Nissan | Altima |
| 2020 | Jeep | Grand Cherokee |
| 2020 | Subaru | Outback |
| 2020 | Chevrolet | Equinox |
| 2020 | GMC | Sierra |
| 2020 | Hyundai | Elantra |
| 2020 | Kia | Sorento |
| 2020 | Ram | 1500 |

**Review and edit this list before handing it off** — this is a starting
proposal, not a final decision. Swap years/models as you see fit; the
runbook's per-vehicle NHTSA-naming-retry logic and the 5GB stop condition
apply regardless of what you put here.

## What "national scope" would require instead (not this runbook)

Per this session's research: literally every relevant US vehicle
(~15,000-20,000 Year-Make-Model entries in the modern era, or ~2,700-3,600
if smartly deduplicated to one representative year per ~5.5-year vehicle
generation) projects to roughly 46-61GB for the vector store alone —
beyond what a git/LFS-based workflow should durably hold. This runbook is
scoped to curated batches (a few dozen vehicles at a time, well under 5GB
each) specifically because that fits comfortably within Git LFS's free
tier with room to spare. If/when the goal becomes true exhaustive national
coverage, that's a different, later decision: moving the live knowledge
base to a dedicated cloud storage bucket or managed vector DB service, with
GitHub reserved for code only. Don't scale this runbook's vehicle list into
the thousands without revisiting that architecture first.

## After Jules opens a PR

1. Review the PR: check the vehicle list matches what was actually
   requested, check `docs/ingestion_status.md` was updated correctly,
   check no `data/` or `backend/`/`frontend/` changes snuck in
   unexpectedly.
2. `git checkout` Jules's branch (or merge it first, your call).
3. `git lfs pull` to fetch the actual snapshot data (LFS pointers don't
   auto-download on a normal checkout in all git configurations --
   confirm the files under `kb_export/chroma_db/` are real binary content,
   not tiny LFS pointer text files, before proceeding).
4. `uv run python -m etl.import_kb` — merges the new vehicles into your
   live SSD-hosted store. Confirm the printed "Imported N/N" count matches
   what the PR claims.
5. Spot-check: hit `/api/repair` for one of the newly-added vehicles with
   a real symptom query and confirm it returns grounded, cited content
   (not the generic template fallback) — this is the actual proof the new
   data is live and working, not just "present in a file."
