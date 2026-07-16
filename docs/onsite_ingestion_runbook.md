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

1. **Clone the repo and check out this branch** (or `main`, once this branch is
   merged):
   ```bash
   git clone <repo-url> RAPP && cd RAPP
   git checkout worktree-onsite-ingestion   # the branch carrying this runbook
   ```
2. **Git LFS** (needed for Path B; harmless to set up either way):
   ```bash
   git lfs install
   git lfs version   # should print a version, not an error
   ```
3. **Python env with the ETL dependency group:**
   ```bash
   uv sync --all-groups      # or: uv sync --group etl
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
6. **No secrets required for ingestion.** `GEMINI_API_KEY` et al. are only for
   the *serving* app (diagnose/repair), not for building the KB. You can ingest
   with an empty `.env`.

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

### 3.2 Smoke-test ONE vehicle first

Never kick off a multi-hour batch without proving the pipeline runs on this
machine. Pick the first list entry:

```bash
uv run --group etl python -m etl --year 2015 --make Ram --model 1500 --all --load
```

Expect a summary with non-zero "Records found" and "Chunks loaded". If it
errors, stop and fix the environment — do not start the batch.

### 3.3 Run the full batch

```bash
uv run --group etl python scripts/ingest_seed_vehicles.py
```

This ingests all 15 vehicles from `scripts/seed_vehicles.json` in order,
skipping anything already in the manifest, continuing past any single-vehicle
failure, and auto-retrying NHTSA naming mismatches once. It's resumable — if the
run is interrupted, just run it again.

Watch progress live from another terminal:
```bash
watch -n 2 'cd /path/to/RAPP && uv run python -m etl.progress_view'
```

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
authoritative instructions are in docs/onsite_ingestion_runbook.md — read it
first and follow it exactly. Do NOT improvise a different mechanism.

Your job:
1. Do the prerequisites (runbook §1): git checkout worktree-onsite-ingestion,
   git lfs install, uv sync --all-groups. Confirm ~15 GB free disk.
2. Determine the SSD situation and pick Path A or Path B (runbook §0). If the
   "Extreme SSD" is plugged into THIS laptop, use Path A. Otherwise Path B.
3. Obey every hard rule in runbook §2 — especially: NEVER set
   USE_GEMINI_EMBEDDINGS. Leave it unset. The store is 384-dim MiniLM.
4. Smoke-test ONE vehicle before the batch (runbook §3.2). If it errors, stop
   and report — do not start the batch.
5. Run scripts/ingest_seed_vehicles.py (runbook §3.3). It ingests the 15
   vehicles in scripts/seed_vehicles.json, is resumable, and continues past
   per-vehicle failures. This takes hours — that's expected.
6. When done, paste the printed status rows into docs/ingestion_status.md,
   commit ONLY the paths the runbook names (never `git add -A`), push to this
   branch (or a new branch), and open a PR summarizing: vehicles done/skipped/
   failed, total chunks loaded, and — for Path B — the kb_export/ size.
7. If anything is ambiguous or a check fails in a way the runbook didn't
   anticipate, STOP and describe it in the PR rather than guessing.

Hard stops: never touch data/rapp.db, data.bak_*, or the SSD's backups/;
never force-push or push to main; never edit backend/ or frontend/ unless the
ETL pipeline itself is broken (and if so, keep it in a separate commit and run
the backend lint/type/test gate first).
```

---

## 8. Scaling note (unchanged from the Jules era)

This runbook is scoped to **curated batches of a few dozen vehicles**, which fit
comfortably on the SSD and (for Path B) well within Git LFS's free tier. True
national coverage (~2,700–3,600 deduplicated generation-years → ~46–61 GB for
the vector store alone) is a *different* architecture — a managed vector DB or a
cloud storage bucket, with GitHub reserved for code only. Don't scale this
runbook's list into the thousands without revisiting that decision first.
