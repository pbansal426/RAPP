# Prompt for the Claude agent running ingestion on the second laptop

Paste this verbatim into Claude Code on the ingesting laptop (e.g. the M4
MacBook Pro), in an empty directory you want the repo cloned into. It is
self-contained and references `docs/onsite_ingestion_runbook.md`, the
authoritative runbook, which it will clone as part of step 1.

```
You are running RAPP's knowledge-base ingestion on this laptop. The full,
authoritative instructions are in docs/onsite_ingestion_runbook.md on the
main branch of https://github.com/pbansal426/RAPP -- clone the repo first,
then read that file in full and follow it exactly. Do NOT improvise a
different mechanism.

Your job:
1. Confirm GitHub auth is already set up (`gh auth status`) -- if not,
   STOP and tell me to run `gh auth login` myself; you cannot complete an
   interactive login. Then install uv/git-lfs if this is a fresh machine,
   clone the repo, checkout main, and run `uv sync --group etl`. Confirm
   at least 15 GB free disk (`df -h .`).
2. Check whether the "Extreme SSD" volume is mounted at
   /Volumes/Extreme SSD -- if so, symlink data/chroma_db and
   data/etl_workspace to it exactly as the runbook's §3.1 shows (Path A).
3. Run the sanity-check command in runbook §3.1 BEFORE touching anything
   else -- it must report a chunk count above 8000. If it doesn't, STOP
   and tell me; do not proceed, you're not pointed at the real data.
4. Make the optional backup copy of chroma_db described in §3.1.
5. NEVER set USE_GEMINI_EMBEDDINGS -- leave it unset. This is the single
   most important rule in the runbook.
6. Smoke-test ONE vehicle (runbook §3.2, the first vehicle in
   scripts/seed_vehicles.json). If it errors, stop and report -- do not
   start the full batch.
7. Launch scripts/ingest_seed_vehicles.py as a BACKGROUND process exactly
   as shown in runbook §3.3 (nohup + caffeinate -i, logged to a file, PID
   saved) -- NEVER run it as a blocking foreground command, it takes
   3-5 hours. Confirm it actually started, then check on it every 15-30
   minutes by tailing the log -- you don't need to stay actively engaged,
   just check in periodically across our conversation.
8. When the log shows "Batch Ingestion Summary", report the full results
   to me: vehicles done/skipped/failed and total chunks loaded.
9. Paste the printed status rows into docs/ingestion_status.md, commit
   ONLY that file (never git add -A), push to a new branch, and open a
   PR summarizing the batch results.
10. If anything is ambiguous or breaks in a way the runbook didn't
    anticipate, STOP and describe the problem to me rather than guessing.

Never touch data/rapp.db, data.bak_*, or the SSD's backups/ folder. Never
force-push or push to main directly. Never edit backend/ or frontend/
unless the ETL pipeline itself is broken.
```
