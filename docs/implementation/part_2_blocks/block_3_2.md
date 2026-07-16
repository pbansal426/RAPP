# Block 3.2 — NHTSA ingestion noise filter (future batches only)

> **Model**: Sonnet 5 · **Thinking**: Medium · **Stage**: 3 (Docs & Content Polish) · **Status**: ⬜ Not started
> **Parent**: [`../imp_part_2.md`](../imp_part_2.md) §3.2

---

## TL;DR

A large share of NHTSA "manufacturer communications" for some vehicles are pure dealer-process admin bulletins (e.g. *"how to upload a GDS2 session log to a Technical Assistance Case"*) with zero repair relevance. They get downloaded, chunked, and embedded like real TSBs, wasting ingestion time and diluting retrieval. Add a **conservative** keyword pre-filter to the ETL pipeline that skips only unambiguously-administrative records, then validate it with a dry-run before trusting it on a real batch.

**Applies to FUTURE ingestion batches only.** Do **not** touch or clean up already-ingested chunks — that's a separate, riskier operation out of scope here.

---

## ⚠️ Corrections vs. `imp_part_2.md` — IMPORTANT BUG FIX

The parent plan's `_is_administrative_record` helper calls `record.summary.lower()`. But **`TsbRecord.summary` is typed `str | None`** (`etl/models.py:53`) — a record with a null summary would raise `AttributeError` and crash the whole ingest. **Guard against None**: use `(record.summary or "").lower()`. The corrected helper is in the code below — use it, not the parent plan's version.

---

## Context you need

- The pipeline is `etl/pipeline.py`. The relevant function is `run_full_ingest`, whose per-record loop begins at line 200: `for record in records:`, immediately followed by `try: documents = client.resolve_documents(record)`.
- `TsbRecord` (imported from `etl.models`, line 23) has fields `nhtsa_id: int`, `summary: str | None`, `communication_number`, `communication_date`, `components`, `document_count`.
- `log = logging.getLogger(__name__)` is already defined at module level (line 34).
- A false-positive filter (dropping a real repair TSB) is **worse** than a little noise — so the blocklist must be narrow and every skip must be human-reviewed before this runs on a real batch.

---

## Change 1 — Module-level constant + helper (`etl/pipeline.py`)

Add near the top of the module, **after the imports and `log = logging.getLogger(__name__)` (line 34), before `class PipelineError`** (line 37). Note the `(record.summary or "")` None-guard:
```python
# Conservative blocklist: these phrase patterns only ever appear on pure
# dealer-process/tooling bulletins (verified against real NHTSA samples
# during the 2026-07-16 on-site batch), never on genuine repair/failure
# TSBs. Deliberately narrow -- a false-positive skip here silently loses
# real repair content, which is worse than a little ingestion noise.
_ADMINISTRATIVE_SUMMARY_PATTERNS = (
    "session log",
    "gds2",
    "cx connect",
    "technical assistance case",
    "how to email",
)


def _is_administrative_record(record: TsbRecord) -> bool:
    # record.summary is Optional[str]; guard against None or it AttributeErrors.
    summary_lower = (record.summary or "").lower()
    return any(pattern in summary_lower for pattern in _ADMINISTRATIVE_SUMMARY_PATTERNS)
```
> `TsbRecord` is already imported at line 23 — no new import needed.

---

## Change 2 — Apply the filter in the loop (`etl/pipeline.py::run_full_ingest`)

**Current** (lines 200-203):
```python
            for record in records:
                try:
                    documents = client.resolve_documents(record)
                    time.sleep(0.5)  # Polite pacing for NHTSA API
```
**Change** — insert the skip check as the first thing in the loop body, before the `try`:
```python
            for record in records:
                if _is_administrative_record(record):
                    log.info(
                        f"Skipping administrative bulletin (NHTSA ID {record.nhtsa_id}): "
                        f"{(record.summary or '')[:80]}"
                    )
                    continue
                try:
                    documents = client.resolve_documents(record)
                    time.sleep(0.5)  # Polite pacing for NHTSA API
```

---

## Change 3 — Dry-run validation script (one-off, NOT part of the permanent CLI)

Before trusting the filter on a real batch, write a small throwaway script (put it under `scripts/` or run it inline) that calls `list_communications` for a few already-ingested vehicles and reports, for each, how many records the new filter *would* skip — printing each skipped record's **full** summary for manual eyeball review. Sketch:
```python
# scripts/dryrun_admin_filter.py  (one-off; delete after review)
from etl.config import EtlConfig
from etl.clients.nhtsa_communications import NhtsaManufacturerCommunicationsClient
from etl.models import VehicleKey
from etl.pipeline import _is_administrative_record

config = EtlConfig()  # or however the repo constructs it in other etl scripts
vehicles = [VehicleKey(...), VehicleKey(...)]  # 2+ already-ingested vehicles
for vehicle in vehicles:
    with NhtsaManufacturerCommunicationsClient(config) as client:
        records = client.list_communications(vehicle)
    skipped = [r for r in records if _is_administrative_record(r)]
    print(f"\n=== {vehicle}: {len(skipped)}/{len(records)} would be skipped ===")
    for r in skipped:
        print(f"  NHTSA {r.nhtsa_id}: {r.summary}")
```
> Match the repo's actual `EtlConfig`/`VehicleKey` construction used by other etl scripts (e.g. `scripts/ingest_seed_vehicles.py`) — don't guess the constructor args.

---

## Do NOT touch

- Any already-ingested chunk or the live vector store — this is a pipeline change for **future** runs only.
- `run_vertical_slice` — the filter goes only in `run_full_ingest`.
- Do not widen the blocklist speculatively. If the dry-run shows any borderline-repair summary would be skipped, **tighten** the patterns instead of proceeding.

---

## Verification

1. **Dry-run review is the real gate.** Run the Change-3 script against **at least 2** already-ingested vehicles. Read **every** summary the filter would skip. If any looks even slightly repair-relevant (not purely administrative dealer-process/tooling), tighten the patterns and re-run. Only proceed once every would-skip summary is clearly administrative.
2. **Lint/type pass** (ETL uses the same toolchain):
   ```bash
   uv run ruff check etl/ && uv run black --check etl/ && uv run mypy etl/
   ```
   (If the repo scopes mypy to `backend/` only, at least run ruff/black on `etl/`.)
3. **No crash on null summary** — the `(record.summary or "")` guard means a record with `summary=None` is simply not skipped and processes normally; confirm the dry-run doesn't raise on any vehicle.
4. Only **after** the dry-run review passes should this filter be used on a real `scripts/ingest_seed_vehicles.py` run.

---

## Definition of Done

- [ ] `_ADMINISTRATIVE_SUMMARY_PATTERNS` + `_is_administrative_record` added at module level (with `(record.summary or "")` None-guard)
- [ ] Skip check inserted at the top of the `for record in records:` loop in `run_full_ingest`
- [ ] Dry-run script written and run against ≥2 already-ingested vehicles; every would-skip summary manually confirmed administrative
- [ ] `ruff`/`black` (and `mypy` if scoped) clean on `etl/`
- [ ] Committed: `feat(etl): Block 3.2 skip administrative NHTSA bulletins on ingest`
- [ ] `imp_part_2.md` §1 tracker row 3.2 → `✅ Done`; session logged in §5 (note the None-guard bug fix)
