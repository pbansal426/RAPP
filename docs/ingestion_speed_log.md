# Ingestion Speed Log

Tracks real per-vehicle ingestion throughput across ingestion sessions and
machines, so different laptops running the same `etl/` pipeline and the same
`scripts/seed_vehicles.json` can be compared directly. This is a
**measurement log, not a status log** — see `docs/ingestion_status.md` for
final per-batch results and `docs/ingestion_incident_log.md` for
crashes/stalls.

## Tracking protocol

- **One row per vehicle**, appended the moment the running batch moves on to
  the *next* vehicle (i.e. `progress.json`'s `"vehicle"` field changes) —
  this is when a vehicle's final `records_found`/`pdfs_ingested`/
  `chunks_loaded` numbers are known. The background watchdog
  (`docs/onsite_ingestion_runbook.md` process) does this automatically
  during an active session; do it manually if you're watching a session
  without that automation running.
- **Always record the machine identifier** (`hostname`, chip, RAM — via
  `hostname && sysctl -n machdep.cpu.brand_string && sysctl -n hw.memsize`)
  once per session at the top of that session's section, not per row —
  it doesn't change mid-session.
- **Duration is wall-clock time**, not CPU time — this pipeline is
  network/pacing-bound (NHTSA API + a deliberate 0.5s politeness delay per
  call), so wall-clock is what's actually comparable across machines; CPU
  time would mostly measure network latency variance, not real throughput
  differences.
- **Rate** = `pdfs_ingested / duration_minutes`. This is the single number
  most comparable across machines/sessions, since `records_found` varies
  enormously by vehicle (population/documentation-volume driven, not a
  hardware factor — see the Silverado noise-vs-signal finding in
  `docs/implementation/imp_part_2.md` §4/3.2) while the underlying
  per-PDF cost (network round-trip + 0.5s pacing sleep + parse + embed) is
  roughly constant per machine.
- If a vehicle's start/end boundary is inferred after the fact (not caught
  live by the watchdog) rather than observed directly, mark it
  **(approximate)** in the Notes column rather than presenting reconstructed
  timestamps as precise.

## Session 1 — 2026-07-16, on-site laptop

**Machine**: `Ankurs-MacBook-Pro.local` — Apple M5, 16 GB RAM, macOS (Darwin 25.5.0)
**Batch started**: 2026-07-16T05:32:27Z

| # | Vehicle | Records found | PDFs ingested | Chunks loaded | Start (UTC) | End (UTC) | Duration (min) | Rate (pdfs/min) | Notes |
|--:|---|--:|--:|--:|---|---|--:|--:|---|
| 1 | 2015 Ram 1500 | 591 | 579 | 1,295 | 05:32:27 | ~05:37 | ~4.6 | ~126 | (approximate — bundled window) |
| 2 | 2015 Chevrolet Silverado 1500 | 1,488 | 1,488 | ~6,300 | ~05:37 | ~06:20 | ~43 | ~35 | (approximate — bundled window; this vehicle's PDF volume is a documented outlier, see imp_part_2.md §4/3.2 on administrative-bulletin noise) |
| 3 | 2016 Toyota RAV4 | — | — | — | ~06:20 | ~06:33 | ~13 | — | (approximate — bundled window, exact records_found not captured live) |
| 4 | 2017 Honda CR-V | 281 | 281 | — | ~06:33 | ~06:46 | ~13 | ~22 | (approximate — bundled window) |

<!-- From here on, the watchdog appends rows automatically on each vehicle-boundary transition, with precise (not approximate) start/end times. -->
| 5 | 2016 Nissan Rogue | 322 | 306 | 2482 | 2026-07-16T06:50:24Z | 2026-07-16T06:54:24Z | 4.0 | 76 | live-tracked |
| 6 | 2015 Ford Escape | 128 | 98 | 443 | 2026-07-16T06:54:24Z | 2026-07-16T06:58:24Z | 4.0 | 24 | live-tracked |
| 7 | 2016 Mazda CX-5 | 704 | 607 | 3995 | 2026-07-16T06:58:24Z | 2026-07-16T07:20:24Z | 22.0 | 28 | live-tracked |
| 8 | 2013 Chevrolet Equinox | 1943 | 1920 | 6913 | 2026-07-16T07:20:24Z | 2026-07-16T08:22:26Z | 62.0 | 31 | live-tracked |
| 9 | 2016 Ford Explorer | 197 | 150 | 811 | 2026-07-16T08:22:26Z | 2026-07-16T08:28:26Z | 6.0 | 25 | live-tracked |
| 10 | 2015 Jeep Grand Cherokee | 511 | 474 | 1208 | 2026-07-16T08:28:26Z | 2026-07-16T08:42:26Z | 14.0 | 34 | live-tracked |
| 11 | 2015 Jeep Wrangler | 225 | 199 | 409 | 2026-07-16T08:42:26Z | 2026-07-16T08:48:27Z | 6.0 | 33 | live-tracked |
| 12 | 2015 Nissan Altima | 331 | 278 | 3404 | 2026-07-16T08:48:27Z | 2026-07-16T09:00:27Z | 12.0 | 23 | live-tracked |
| 13 | 2015 Hyundai Sonata | 250 | 198 | 2291 | 2026-07-16T09:00:27Z | 2026-07-16T09:10:27Z | 10.0 | 20 | live-tracked |
| 14 | 2017 Subaru Outback | 384 | 339 | 2894 | 2026-07-16T09:10:27Z | 2026-07-16T09:24:28Z | 14.0 | 24 | live-tracked |
| ? | 2015 Ram 1500 | 591 | 493 | 0 | 2026-07-16T10:10:14Z | 2026-07-16T12:06:20Z | 116.1 | 4 | live-tracked |
| ? | 2015 Chevrolet Silverado 1500 | 1488 | 1353 | 0 | 2026-07-16T12:06:20Z | 2026-07-16T14:14:08Z | 127.8 | 11 | live-tracked |
| ? | 2016 Toyota RAV4 | 257 | 147 | 0 | 2026-07-16T14:14:08Z | 2026-07-16T14:18:08Z | 4.0 | 37 | live-tracked |
| ? | 2017 Honda CR-V | 281 | 201 | 0 | 2026-07-16T14:18:08Z | 2026-07-16T14:22:08Z | 4.0 | 50 | live-tracked |
| ? | 2016 Nissan Rogue | 322 | 245 | 0 | 2026-07-16T14:22:08Z | 2026-07-16T14:26:09Z | 4.0 | 61 | live-tracked |
| ? | 2015 Ford Escape | 128 | 78 | 0 | 2026-07-16T14:26:09Z | 2026-07-16T14:28:09Z | 2.0 | 39 | live-tracked |
