# On-Site Ingestion Runbook (Second-Laptop / Local)

**This is the authoritative runbook for the ~15-vehicle knowledge-base ingestion.**
It replaces the Google Jules cloud workflow (`docs/jules_ingestion_runbook.md`,
now deprecated) with a local run on a more capable laptop. The mechanism is
identical — the same `etl/` pipeline, the same ChromaDB store, the same
`scripts/ingest_seed_vehicles.py` driver — only the *machine* changes.

> **Why the pivot from Jules?** Jules (cloud VM) proved unreliable in practice,
> and it could only hand work back through a Git-LFS round-trip because it
> could never touch the SSD directly. A laptop you control can plug the SSD in
> and write straight into the live store — simpler, faster, and no LFS size
> ceiling. See the decision-log entry in `docs/UPDATED_PRODUCT_NORTH_STAR.md` §12.

---

## 0. The one decision that changes everything: where is the SSD?

The knowledge base lives on the external **"Extreme SSD"**
(`/Volumes/Extreme SSD/dev/RAPP_data/`). Pick the path that matches your
physical setup for the ingestion session:

| | **Path A — SSD plugged into the ingesting laptop** (RECOMMENDED) | **Path B — SSD stays on the primary Mac** |
|---|---|---|
| How data gets home | Ingest **directly into the live store** on the SSD. Nothing to sync but a docs update. | Ingest into the laptop's **local disk**, publish a snapshot via **Git LFS**, then merge on the Mac. |
| Git's job | Sync code + docs only. | Also ships the vector snapshot through LFS. |
| Pros | Simplest, fastest, no LFS size limit, no merge step. | Works even if the SSD can't travel. |
| Cons | SSD must physically move to the laptop. | Extra export → LFS push → pull → import round-trip. |

**Recommendation: Path A.** The SSD is the durable home of the KB anyway, and
the embeddings are computed locally (no cloud dependency), so there is no
benefit to the LFS round-trip when the drive can simply be present. Use Path B
only if the drive genuinely cannot move to the ingesting laptop.

Both paths are fully specified below. Do §1 and §2 regardless, then jump to §3
(Path A) **or** §4 (Path B).

---

## 1. Prerequisites on the ingesting laptop

0. **GitHub auth (human step, do this first)** — the agent will need to `git
   push` and open a PR at the end. Run `gh auth login` interactively once
   (or confirm `gh auth status` already shows a logged-in account with repo
   write access) before handing off to an AI agent — an agent cannot complete
   an interactive OAuth/browser login itself.
1. **Install `uv` and `git-lfs` if this is a fresh machine:**
   ```bash
   brew install uv git-lfs    # or: curl -LsSf https://astral.sh/uv/install.sh | sh
   git lfs install
   git lfs version            # should print a version, not an error
   uv --version                # should print a version, not "command not found"
   ```
2. **Clone the repo:**
   ```bash
   git clone https://github.com/pbansal426/RAPP.git RAPP && cd RAPP
   git checkout main   # this runbook is merged to main
   ```
3. **Python env with the ETL dependency group:**
   ```bash
   uv sync --group etl
   ```
   `uv.lock` is committed, so this reproduces the exact toolchain (chromadb,
   pdfplumber, etc.) used to build the existing store.
4. **Disk headroom: ~15 GB free.** The downloaded source PDFs
   (`data/etl_workspace/`) run ~600 MB per vehicle — roughly 9–10 GB across all
   15. The vector store itself is tiny (~17 MB/vehicle). PDFs are the heavy,
   gitignored part.
5. **Internet access.** Two calls reach out: NHTSA's public API (no key needed)
   and, on the *first* embedding, a one-time ~80 MB download of ChromaDB's local
   `all-MiniLM-L6-v2` model. After that, embedding is fully offline/local.
   Prefer a stable connection (ethernet or strong Wi-Fi) — this run makes
   several thousand NHTSA requests over hours; a flaky connection means more
   individual document failures (each is retried 3x automatically, but a
   dead connection for a stretch will still show up as failures to review
   afterward, not a hard stop).
6. **No secrets required for ingestion.** `GEMINI_API_KEY` et al. are only for
   the *serving* app (diagnose/repair), not for building the KB. You can ingest
   with an empty `.env`.
7. **Keep the laptop awake and powered.** This is a multi-hour unattended run
   (§3.3 shows how to wrap it in `caffeinate` so normal display/idle sleep
   won't pause it) — but macOS can still suspend background work if the lid
   is closed on battery. Plug in and leave the lid open, or confirm your
   power/sleep settings allow background network activity with the lid
   closed before relying on that.

---

## 2. Hard rules — do not deviate

These are the ways a run silently corrupts the store or the repo. Treat them as
non-negotiable:

- 🚫 **NEVER set `USE_GEMINI_EMBEDDINGS=true`.** The entire existing store is
  built with ChromaDB's local `all-MiniLM-L6-v2` (**384-dim**) embeddings.
  Gemini `text-embedding-004` is **768-dim**. Mixing them poisons retrieval
  (dimension mismatch or, worse, silently nonsensical distances). Leave it
  unset/false on *every* machine — ingesting **and** serving. This is the single
  most important rule in this document.
- 🚫 **Never touch `data/rapp.db`, `data.bak_*`, or the SSD's `backups/`.** Those
  are the irreplaceable user-accounts DB and its snapshots. Ingestion has no
  business writing to them. (`rapp.db` is on the internal disk by design; only
  `chroma_db` and `etl_workspace` are on the SSD.)
- 🚫 **Never `git add -A` / `git add .`.** Stage only the specific paths each step
  names (`docs/…`, or `kb_export/` for Path B). A blanket add can sweep in the
  gitignored `data/` symlink, a stray `.env`, or machine-local junk.
- 🚫 **Never force-push, rewrite history, or push to `main` directly.** Work on a
  branch and open a PR, exactly like every other block in this project.
- ⚠️ **One ingestion at a time against a given store.** The pipeline takes an
  advisory lock (`PipelineLockedError`); don't run two batches at the same
  workspace concurrently, and don't run `etl.export_kb` while a batch is live.
- ⚠️ **Don't edit `backend/` or `frontend/`** unless the ETL pipeline itself is
  genuinely broken and blocking ingestion. If you must, keep it in a separate
  commit and run `uv run ruff check backend/ && uv run black --check backend/ &&
  uv run mypy backend/ && uv run pytest tests/unit/ -q` first.

---

## 3. Path A — SSD plugged into the ingesting laptop (recommended)

### 3.1 Point the repo at the SSD's live store

On a fresh clone, `data/chroma_db` and `data/etl_workspace` don't exist yet
(they're gitignored symlinks on the primary Mac). Recreate them so the pipeline
writes straight into the live store on the SSD:

```bash
# macOS mounts the drive here; adjust if your volume name differs.
SSD="/Volumes/Extreme SSD/dev/RAPP_data"
mkdir -p data
ln -s "$SSD/chroma_db"      data/chroma_db
ln -s "$SSD/etl_workspace"  data/etl_workspace
ls -l data/                 # confirm both resolve (not dangling)
```

> Not on macOS, or the drive mounts elsewhere? Skip the symlinks and instead set
> `CHROMA_DB_PATH="$SSD/chroma_db"` and pass
> `--workspace "$SSD/etl_workspace"` to the ETL commands.

The SSD already carries the manifest from the first 7 vehicles, so those are
auto-skipped — you'll only ingest the new 15.

**Sanity-check you're actually pointed at the real, existing store** before
touching anything — a wrong path/mount would silently start a brand-new empty
store instead of extending the real one:

```bash
uv run python -c "
import chromadb
from chromadb.config import Settings
c = chromadb.PersistentClient(path='data/chroma_db', settings=Settings(anonymized_telemetry=False))
n = c.get_or_create_collection('repair_manuals').count()
print(f'Existing chunk count: {n}')
assert n > 8000, 'Expected the existing 7-vehicle baseline (~9,600 chunks) -- got far fewer. STOP: check the SSD mount/symlink before proceeding.'
"
```

**Optional but recommended: snapshot the live store before a multi-hour
unattended write.** Ingestion upserts by deterministic ID, so this is low-risk,
but a cheap rollback point costs almost nothing given ~1.4 TB free on the SSD:

```bash
cp -R "$SSD/chroma_db" "$SSD/chroma_db.backup_pre_onsite_batch_$(date +%Y%m%d)"
```

### 3.2 Smoke-test ONE vehicle first

Never kick off a multi-hour batch without proving the pipeline runs on this
machine. Pick the first list entry:

```bash
uv run --group etl python -m etl --year 2015 --make Ram --model 1500 --all --load
```

Expect a summary with non-zero "Records found" and "Chunks loaded". If it
errors, stop and fix the environment — do not start the batch.

### 3.3 Run the full batch — as a BACKGROUND process, not foreground

> [!IMPORTANT]
> This step runs for **hours**. If you (or an AI agent) run it as a normal
> foreground command, a shell/SSH disconnect, a terminal tab closing, or an
> agent harness's own tool-call timeout (many agent tools cap a single command
> at ~10 minutes) will **kill the batch partway through**. Always background
> it with `nohup` (survives the launching shell/session exiting) and
> `caffeinate -i` (keeps the Mac from idle-sleeping while it runs), then poll
> a log file instead of blocking on the process.

```bash
nohup caffeinate -i uv run --group etl python scripts/ingest_seed_vehicles.py \
  > ingest_batch.log 2>&1 &
echo $! > ingest_batch.pid
echo "Started as PID $(cat ingest_batch.pid) -- logging to ingest_batch.log"
```

Confirm it actually started before walking away:
```bash
sleep 10 && tail -20 ingest_batch.log
```
You should see `Starting batch ingestion of 15 vehicles` and the first
vehicle's "Processing ..." line. If instead the log is empty or shows a
traceback, the process died immediately — check the error, fix it, and
re-launch (safe to re-run; already-ingested PDFs are skipped via the manifest).

**Check on it periodically** (every 15–30 minutes is plenty — it needs no
interaction):
```bash
tail -30 ingest_batch.log                       # recent activity
ps -p "$(cat ingest_batch.pid)" > /dev/null && echo "still running" || echo "FINISHED or died -- check the log"
```

Or watch the live per-vehicle progress snapshot from another terminal:
```bash
watch -n 5 'uv run python -m etl.progress_view'
```

**It's resumable.** If it dies (crash, disconnect, laptop actually slept
despite `caffeinate`, power loss), just re-launch the same `nohup` command —
the manifest skips everything already ingested, so you only lose the one
in-flight vehicle's partial progress at worst.

**When it's done**, `ps -p "$(cat ingest_batch.pid)"` will report no such
process, and the tail of `ingest_batch.log` will show `Batch Ingestion
Summary` followed by the paste-ready Markdown rows described below.

### 3.4 Record results and publish the docs update

The batch prints a paste-ready Markdown block at the end ("Paste these rows into
docs/ingestion_status.md"). Paste those rows into the table in
`docs/ingestion_status.md`, then:

```bash
git add docs/ingestion_status.md
git commit -m "docs(ingestion): on-site batch — <N> vehicles, <chunks> chunks"
git push
```

That's it for Path A. The SSD now holds the updated live store; when it returns
to the primary Mac there's **nothing to import** — it's already the live copy.
Go to §5 to verify serving.

---

## 4. Path B — SSD stays on the primary Mac (LFS round-trip)

### 4.1 Ingest into the laptop's local disk

Use a real local `data/` directory (NOT a symlink to any SSD):

```bash
mkdir -p data/chroma_db data/etl_workspace
```

Smoke-test one vehicle (§3.2), then run the batch (§3.3). Everything lands in
the laptop's local `./data/chroma_db`.

> Because this is a fresh local store, the manifest is empty, so the driver will
> also (re)ingest the 7 baseline vehicles if they're in your seed list. They're
> **not** in `seed_vehicles.json` (which holds only the new 15), so by default
> you'll produce a snapshot of just the new vehicles — which is exactly what
> `import_kb` needs (it upserts by ID, so overlap is harmless anyway).

### 4.2 Snapshot to `kb_export/` and push via LFS

```bash
uv run python -m etl.export_kb        # copies data/chroma_db -> kb_export/chroma_db
git add kb_export/ docs/ingestion_status.md
git status                            # confirm ONLY kb_export/ + the doc are staged
git commit -m "kb: on-site batch snapshot — <N> vehicles, <chunks> chunks"
git push                              # LFS uploads the .sqlite3/.bin blobs
```

The snapshot for 15 vehicles is only a few hundred MB — far under Git LFS's
10 GB free tier. (The old 5 GB batch cap was about the source PDFs, which never
enter LFS.)

### 4.3 Merge on the primary Mac

Back on the Mac, with the SSD connected:

```bash
git pull
git lfs pull                          # fetch the real blobs, not LFS pointer stubs
# sanity: files under kb_export/chroma_db/ should be MB-sized, not tiny text stubs
uv run python -m etl.import_kb        # upserts the snapshot into the live SSD store
```

`import_kb` re-embeds each document through the Mac's own store
(MiniLM — see the hard rule), so the live store stays internally consistent
regardless of the laptop's setup. Confirm the printed "Imported N/N" matches the
PR's claimed count, then go to §5.

---

## 5. Verify the new data is actually live

Presence in a file isn't proof; grounded retrieval is. With the app running
against the live store (SSD connected, `VECTOR_STORE` unset/`chroma`,
`USE_GEMINI_EMBEDDINGS` unset), hit `/api/repair` for a *newly*-added vehicle
with a real symptom and confirm it returns cited, vehicle-specific content
rather than the generic template fallback:

```bash
curl -s localhost:8000/api/repair \
  -H 'Content-Type: application/json' \
  -d '{"vin":"","symptoms":"CVT shudder and whine when accelerating",
       "obd_codes":[],"tools":[],"stripe_session_id":"<a valid unlock>",
       "vehicle":{"year":2015,"make":"Nissan","model":"Altima"}}' | head -40
```

A non-empty `citations` array pointing at NHTSA bulletins for that vehicle is
the real success signal. (Retrieval also fails *open* to empty results if the
SSD is unplugged — so a blank result usually means "drive not connected," not
"ingestion failed.")

---

## 6. The vehicle list — 15 generations

Defined in `scripts/seed_vehicles.json`. Chosen for RAPP's actual business model
(a fraud-shield for mainstream owners who suspect they're overpaying — see North
Star §1/§3): the **highest on-road populations**, **meaningful repair costs**
where the dealer-vs-DIY gap is widest, and several **notorious known-issue
patterns** (Nissan/Jatco CVT, Hyundai/Kia Theta II engine, Ford EcoBoost coolant
intrusion) where the "here's the verified TSB — you're being overcharged" reveal
is strongest. Representative years are mid-generation (2013–2017) so real TSB
volume has accumulated — a current-year vehicle returns far fewer records.

| # | Year | Make | Model | Generation | Segment |
|--:|-----:|------|-------|-----------|---------|
| 1 | 2015 | Ram | 1500 | 4th gen DS (2011–2018) | Full-size truck |
| 2 | 2015 | Chevrolet | Silverado 1500 | K2XX (2014–2018) | Full-size truck |
| 3 | 2016 | Toyota | RAV4 | XA40 (2013–2018) | Compact SUV |
| 4 | 2017 | Honda | CR-V | 5th gen (2017–2022) | Compact SUV |
| 5 | 2016 | Nissan | Rogue | T32 (2014–2020) | Compact SUV |
| 6 | 2015 | Ford | Escape | 3rd gen (2013–2019) | Compact SUV |
| 7 | 2016 | Mazda | CX-5 | KE (2013–2016) | Compact SUV |
| 8 | 2013 | Chevrolet | Equinox | 2nd gen (2010–2017) | Compact SUV |
| 9 | 2016 | Ford | Explorer | U502 (2011–2019) | Midsize SUV |
| 10 | 2015 | Jeep | Grand Cherokee | WK2 (2011–2021) | Midsize SUV |
| 11 | 2015 | Jeep | Wrangler | JK (2007–2018) | Off-road SUV |
| 12 | 2015 | Nissan | Altima | L33 (2013–2018) | Midsize sedan |
| 13 | 2015 | Hyundai | Sonata | LF (2015–2019) | Midsize sedan |
| 14 | 2017 | Subaru | Outback | BS (2015–2019) | Wagon/SUV |
| 15 | 2016 | Kia | Sorento | UM (2016–2020) | Midsize SUV |

Already ingested (do **not** repeat; they're skipped by the manifest on Path A):
2010 Corolla, 2015 Highlander, 2018 Civic, 2018 Accord, 2018 Camry, 2018 F-150,
2025 Lexus ES.

**Edit the list before you start if the business priorities have shifted** — it's
a well-reasoned proposal, not a locked decision. Any single year that turns out
to sit on the wrong side of a mid-cycle redesign is a cheap one-vehicle re-run
via `--reset-vehicle`, not a disaster.

---

## 7. Copy-paste task block for an AI agent on the ingesting laptop

Paste this verbatim to hand the run to an AI agent on the second laptop. It is
self-contained and references only what's in the repo.

```
You are running RAPP's knowledge-base ingestion on this laptop. The full,
authoritative instructions are in docs/onsite_ingestion_runbook.md (on the
main branch) — read it first and follow it exactly. Do NOT improvise a
different mechanism.

Your job:
1. Confirm GitHub auth is already set up (`gh auth status`) -- if not, STOP
   and ask the human to run `gh auth login` interactively; you cannot do
   this yourself. Then do the rest of the prerequisites (runbook §1):
   install uv/git-lfs if needed, `git clone` + `git checkout main`,
   `uv sync --group etl`. Confirm ~15 GB free disk.
2. Determine the SSD situation and pick Path A or Path B (runbook §0). If the
   "Extreme SSD" is plugged into THIS laptop, use Path A (recommended).
   Otherwise Path B.
3. Obey every hard rule in runbook §2 — especially: NEVER set
   USE_GEMINI_EMBEDDINGS. Leave it unset. The store is 384-dim MiniLM.
4. Path A only: run the sanity-check command in runbook §3.1 BEFORE anything
   else -- it must report a chunk count above 8000. If it doesn't, STOP; you
   are not correctly pointed at the real SSD-hosted store. Also make the
   optional backup copy described there.
5. Smoke-test ONE vehicle before the batch (runbook §3.2). If it errors, stop
   and report — do not start the batch.
6. Launch scripts/ingest_seed_vehicles.py as a BACKGROUND process exactly as
   shown in runbook §3.3 (`nohup caffeinate -i uv run ... &`, log to a file,
   save the PID) — NEVER run it as a blocking foreground command, it takes
   hours and will get killed by a session timeout or disconnect otherwise.
   Confirm it actually started (tail the log after ~10s), then check back
   periodically (every 15-30 min) by tailing the log and checking the PID is
   still alive. It's resumable if it dies -- just relaunch the same command.
7. When the log shows "Batch Ingestion Summary", paste the printed
   paste-ready status rows into docs/ingestion_status.md, commit ONLY the
   paths the runbook names (never `git add -A`), push to a new branch, and
   open a PR summarizing: vehicles done/skipped/failed, total chunks loaded,
   and — for Path B — the kb_export/ size.
8. If anything is ambiguous or a check fails in a way the runbook didn't
   anticipate, STOP and describe it in the PR rather than guessing.

Hard stops: never touch data/rapp.db, data.bak_*, or the SSD's backups/;
never force-push or push to main; never edit backend/ or frontend/ unless the
ETL pipeline itself is broken (and if so, keep it in a separate commit and run
the backend lint/type/test gate first).
```

---

## 8. Git hygiene: don't leave loose ends

Multi-hour unattended sessions are exactly the scenario where work quietly
piles up uncommitted on a laptop and then goes nowhere — especially relevant
here since the machine running ingestion may need to be handed back
mid-session (see `scripts/pause_ingestion_and_eject.sh`) or swapped for a
different laptop entirely. A future agent resuming elsewhere needs
everything already merged, not stranded on a local branch only you can see.

**Protocol, followed at the start and end of every ingestion session (and
any time you're about to hand off a machine)**:

1. `git status` — anything meaningful (docs, scripts, `scripts/seed_vehicles.json`
   changes) that isn't yet committed gets committed now, not left dangling.
   Stage specific paths only, per the hard rule in §2 — never `git add -A`.
2. `git push` the branch. Don't rely on the working tree alone as the only
   copy of the work — a laptop that gets physically handed back is a laptop
   you may not have access to again.
3. If a PR is open for this work, check whether it's mergeable
   (`gh pr checks`, `gh pr view --json mergeable`) and merge it once CI is
   green, rather than leaving it open indefinitely. An open-but-abandoned PR
   is exactly the kind of loose end this section exists to prevent.
4. Exception: the final ingestion-results PR (§3.4) intentionally waits
   until the *whole* batch is done before being opened — that's a scoping
   decision (one clean PR per completed batch), not an excuse to leave
   *other* unrelated work (docs, scripts, config) sitting uncommitted in the
   meantime. Those can and should go out via their own small PR as soon as
   they're ready, independent of whether ingestion itself has finished.

---

## 9. Scaling note (unchanged from the Jules era)

This runbook is scoped to **curated batches of a few dozen vehicles**, which fit
comfortably on the SSD and (for Path B) well within Git LFS's free tier. True
national coverage (~2,700–3,600 deduplicated generation-years → ~46–61 GB for
the vector store alone) is a *different* architecture — a managed vector DB or a
cloud storage bucket, with GitHub reserved for code only. Don't scale this
runbook's list into the thousands without revisiting that decision first.
