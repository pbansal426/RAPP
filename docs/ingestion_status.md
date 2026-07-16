# NHTSA TSB Ingestion Status

Tracks progress of `python -m etl --all --load` runs into the ChromaDB
store (`data/chroma_db`, gitignored — this file is the durable record of
what's been ingested). The **baseline** table below is the 7 vehicles
ingested locally on 2026-07-05; the **next-phase** table is the curated
15-generation scale-up batch (`scripts/seed_vehicles.json`), run on-site per
`docs/onsite_ingestion_runbook.md`. Corolla and the 2014–16 Highlander XLE are
the two the E2E suite exercises directly (see CLAUDE.md).

| Year | Make | Model | Status | Records Found | PDFs Ingested | PDFs Skipped (no text) | PDFs Failed | Chunks Loaded | Last Updated |
|------|------|-------|--------|---------------:|---------------:|------------------------:|------------:|---------------:|--------------|
| 2010 | Toyota | Corolla | ✅ Done | 396 | 299 | 87 | 0 | 2433 | 2026-07-05 |
| 2015 | Toyota | Highlander | ✅ Done (re-ingested with manifest fix) | 318 | 255 | 52 | 0 | 2122 | 2026-07-05 |
| 2018 | Honda | Civic | ✅ Done | 231 | 224 | 7 | 0 | 866 | 2026-07-05 |
| 2018 | Honda | Accord | ✅ Done | 297 | 291 | 6 | 0 | 760 | 2026-07-05 |
| 2018 | Toyota | Camry | ✅ Done | 374 | 367 | 7 | 0 | 2679 | 2026-07-05 |
| 2018 | Ford | F-150 | ✅ Done | 389 | 389 | 0 | 0 | 1702 | 2026-07-05 |
| 2025 | Lexus | ES (300h) | ✅ Done — NHTSA models this as just "ES", "300h" is a trim not a model name | 32 | 32 | 0 | 0 | 216 | 2026-07-05 |

**Baseline complete (7 vehicles above).** These were ingested locally on the
primary Mac on 2026-07-05: Corolla, Highlander, Civic, Accord, Camry, F-150, ES.

## Next phase — on-site batch of 15 generations (planned)

The scale-up phase runs **on a more capable laptop**, not Google Jules (which
was found unreliable — see `docs/onsite_ingestion_runbook.md`, the authoritative
runbook, and the decision log in `docs/UPDATED_PRODUCT_NORTH_STAR.md` §12). The
queue lives in `scripts/seed_vehicles.json` and is driven by
`scripts/ingest_seed_vehicles.py`. Fill in the rows below as the batch completes
(the driver prints paste-ready rows):

| Year | Make | Model | Status | Records Found | PDFs Ingested | PDFs Skipped (no text) | PDFs Failed | Chunks Loaded | Last Updated |
|------|------|-------|--------|---------------:|---------------:|------------------------:|------------:|---------------:|--------------|
| 2015 | Ram | 1500 | ⬜ Queued | | | | | | |
| 2015 | Chevrolet | Silverado 1500 | ⬜ Queued | | | | | | |
| 2016 | Toyota | RAV4 | ⬜ Queued | | | | | | |
| 2017 | Honda | CR-V | ⬜ Queued | | | | | | |
| 2016 | Nissan | Rogue | ⬜ Queued | | | | | | |
| 2015 | Ford | Escape | ⬜ Queued | | | | | | |
| 2016 | Mazda | CX-5 | ⬜ Queued | | | | | | |
| 2013 | Chevrolet | Equinox | ⬜ Queued | | | | | | |
| 2016 | Ford | Explorer | ⬜ Queued | | | | | | |
| 2015 | Jeep | Grand Cherokee | ⬜ Queued | | | | | | |
| 2015 | Jeep | Wrangler | ⬜ Queued | | | | | | |
| 2015 | Nissan | Altima | ⬜ Queued | | | | | | |
| 2015 | Hyundai | Sonata | ⬜ Queued | | | | | | |
| 2017 | Subaru | Outback | ⬜ Queued | | | | | | |
| 2016 | Kia | Sorento | ⬜ Queued | | | | | | |

## Live progress

Watch the current ingestion run update live, from your own terminal, no need to check in with Claude (run from the repo root on the ingesting machine):

```bash
watch -n 2 'uv run python -m etl.progress_view'
```

## Notes

- "Records Found" = distinct NHTSA manufacturer-communication records for that vehicle; not every record has an attached PDF (some are recalls/other communication types with no document, which are skipped in the audit rather than counted as failures).
- Year picked for still-queued vehicles will follow the same logic as Highlander: match whatever model year range the frontend/E2E suite actually cares about, defaulting to a recent common year otherwise.
- **2026-07-05 fix:** the manifest used to dedupe already-ingested PDFs was keyed globally (`nhtsa_id/file_name`), not per-vehicle. Since NHTSA bulletins are frequently shared across models, this meant a shared TSB got tagged with whichever vehicle's run processed it first, and every subsequent vehicle silently skipped ingesting it (so it never got that vehicle's own make/model metadata tag, and could never be retrieved for it). Fixed in `etl/load/manifest.py` — keys are now scoped per-vehicle. Corolla ran first against an empty manifest so it was unaffected; Highlander's original run was potentially under-ingested and was reset + re-run after the fix (manifest keys from before this fix are incompatible with the new scheme, so the whole manifest was cleared).
- Re-running ingestion for a vehicle already marked Done: use `--reset-vehicle` (clears just that vehicle's manifest entries, e.g. `python -m etl --year 2010 --make Toyota --model Corolla --reset-vehicle --all --load`) rather than deleting the whole manifest file.
- Two `--all --load` runs must never target the same `data/chroma_db`/workspace concurrently — `run_full_ingest` now takes an advisory file lock and will raise `PipelineLockedError` instead of corrupting state if you try.
