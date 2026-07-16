# Ingestion Incident Log

This file is written to **automatically** by a background watchdog process
monitoring the on-site knowledge-base ingestion batch (see
`docs/onsite_ingestion_runbook.md`). It stays empty/unedited as long as the
batch is healthy — an entry only appears here when the watchdog detects a
crash, a stall, an unexpected error, or normal completion.

**If you are an AI agent picking this up after the fact**: read the most
recent entry below first. It tells you exactly what state the batch was in,
what the watchdog observed, and what it did (or didn't do) about it. Cross-
reference `data/etl_workspace/progress.json` and `ingest_batch.log` (both at
the repo root / `data/etl_workspace/`) for the live/raw state before taking
any action. Do not re-launch the batch without first re-running the §3.1
sanity check in `docs/onsite_ingestion_runbook.md` (SSD mounted, symlinks
resolve, chunk count matches expectations) — a dangling symlink or unplugged
SSD must never result in silently starting a fresh empty store.

---

<!-- Entries appended below by the watchdog. Newest at the bottom. -->
