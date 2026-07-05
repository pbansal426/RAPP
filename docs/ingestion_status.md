# NHTSA TSB Ingestion Status

Tracks progress of `python -m etl --all --load` runs into the local ChromaDB
store (`data/chroma_db`, gitignored — this file is the durable record of
what's been ingested). Vehicle list is the 8 make/model combos the app
actually supports today (`tests/mock_app.py`'s YMM cascade / synthetic-VIN
map); Corolla and the 2014–16 Highlander XLE are the two the E2E suite
exercises directly (see CLAUDE.md), so those are top priority.

| Year | Make | Model | Status | Records Found | PDFs Ingested | PDFs Skipped (no text) | PDFs Failed | Chunks Loaded | Last Updated |
|------|------|-------|--------|---------------:|---------------:|------------------------:|------------:|---------------:|--------------|
| 2010 | Toyota | Corolla | ✅ Done | 396 | 299 | 87 | 0 | 2433 | 2026-07-05 |
| 2015 | Toyota | Highlander | ✅ Done (re-ingested with manifest fix) | 318 | 255 | 52 | 0 | 2122 | 2026-07-05 |
| 2018 | Honda | Civic | ⏳ In progress | — | — | — | — | — | 2026-07-05 |
| — | Honda | Accord | ⬜ Queued | — | — | — | — | — | — |
| — | Toyota | Camry | ⬜ Queued | — | — | — | — | — | — |
| — | Ford | F-150 | ⬜ Queued | — | — | — | — | — | — |
| — | Lexus | RX350 | ⬜ Queued | — | — | — | — | — | — |
| — | Chevrolet | Silverado | ⬜ Queued | — | — | — | — | — | — |
| — | Toyota | RAV4 | ⬜ Queued (added 2026-07-05) | — | — | — | — | — | — |
| — | Honda | CR-V | ⬜ Queued (added 2026-07-05) | — | — | — | — | — | — |
| — | Ford | Explorer | ⬜ Queued (added 2026-07-05) | — | — | — | — | — | — |
| — | Ram | 1500 | ⬜ Queued (added 2026-07-05) | — | — | — | — | — | — |

## Live progress

Watch the current ingestion run update live, from your own terminal, no need to check in with Claude:

```bash
watch -n 2 'cd /Users/prathambansal/Dev/RAPP/.claude/worktrees/generic-dancing-blum && uv run python -m etl.progress_view'
```

## Notes

- "Records Found" = distinct NHTSA manufacturer-communication records for that vehicle; not every record has an attached PDF (some are recalls/other communication types with no document, which are skipped in the audit rather than counted as failures).
- Year picked for still-queued vehicles will follow the same logic as Highlander: match whatever model year range the frontend/E2E suite actually cares about, defaulting to a recent common year otherwise.
- **2026-07-05 fix:** the manifest used to dedupe already-ingested PDFs was keyed globally (`nhtsa_id/file_name`), not per-vehicle. Since NHTSA bulletins are frequently shared across models, this meant a shared TSB got tagged with whichever vehicle's run processed it first, and every subsequent vehicle silently skipped ingesting it (so it never got that vehicle's own make/model metadata tag, and could never be retrieved for it). Fixed in `etl/load/manifest.py` — keys are now scoped per-vehicle. Corolla ran first against an empty manifest so it was unaffected; Highlander's original run was potentially under-ingested and was reset + re-run after the fix (manifest keys from before this fix are incompatible with the new scheme, so the whole manifest was cleared).
- Re-running ingestion for a vehicle already marked Done: use `--reset-vehicle` (clears just that vehicle's manifest entries, e.g. `python -m etl --year 2010 --make Toyota --model Corolla --reset-vehicle --all --load`) rather than deleting the whole manifest file.
- Two `--all --load` runs must never target the same `data/chroma_db`/workspace concurrently — `run_full_ingest` now takes an advisory file lock and will raise `PipelineLockedError` instead of corrupting state if you try.
