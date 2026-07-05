# After Jules Opens a PR — Step-by-Step

Follow these steps in order once Google Jules finishes an ingestion batch
and opens a pull request (per `docs/jules_ingestion_runbook.md`). This gets
its work safely from GitHub onto your Mac and merged into the live,
SSD-hosted knowledge base.

## Step 1: Review the PR before touching anything

Open the PR on GitHub and check:
- The vehicle list in the PR description matches what you asked for (or
  has a good explanation for any skipped ones).
- `docs/ingestion_status.md` was updated with new rows.
- **Nothing under `backend/`, `frontend/`, or `data/` was touched** — only
  `kb_export/` and the status doc should show as changed. If you see
  anything else, stop and ask Claude before merging.

## Step 2: Merge the PR

Use GitHub's normal merge button — same as before.

## Step 3: Pull it down to your machine

```bash
cd /Users/prathambansal/Dev/RAPP
git pull
```

## Step 4: Actually fetch the real LFS content (don't skip this)

A normal `git pull` only downloads small pointer files for LFS-tracked
content, not the actual data. This step pulls the real thing:

```bash
git lfs pull
```

## Step 5: Confirm you got real data, not pointer files

```bash
ls -la kb_export/chroma_db/chroma.sqlite3
```

You want to see a size in the tens of megabytes or more. If it shows
something tiny (under 1KB), the LFS pull didn't work — stop here rather
than continuing.

## Step 6: Merge Jules's data into your live SSD-hosted store

```bash
uv run python -m etl.import_kb
```

Watch the output — it prints `Imported X/Y` as it goes, then ends with
`Done: merged Y documents from kb_export/chroma_db into the live store.`
Let it finish; for ~20 vehicles this can take several minutes (it's
re-computing embeddings locally, which is CPU-bound) — don't interrupt it.

## Step 7: Confirm the numbers actually add up

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
(9,590 as of this document), roughly matching the chunk totals Jules
reported in its PR, added on top.

## Step 8: The real proof — confirm the app can actually use it

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
- If it says something like `"NHTSA TSB T-SB-..."` — the new data is live
  and retrievable. Done.
- If it says `"no vehicle-specific NHTSA TSB or OEM documentation was
  found"` — either that specific query didn't match, or something in
  steps 4-7 didn't fully take. Try a different symptom/vehicle from the
  batch before assuming a problem.

**Once step 8 shows a real citation, the knowledge base has fully made it
from Jules → GitHub → your Mac → the SSD.** Repeat this whole file for
every subsequent Jules batch.
