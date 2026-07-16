# Fix Plan: Vehicle-Level Skip for Already-Completed Ingestion Vehicles

**Status as of writing**: not yet implemented. Written so a fresh AI agent with no prior context on this session can execute it end-to-end. Read this whole document before touching anything.

**Reference docs**: `docs/onsite_ingestion_runbook.md` (the overall ingestion process this fix speeds up), `docs/ingestion_incident_log.md` (crash/stall log), `docs/ingestion_speed_log.md` (per-vehicle throughput history — this is where the numbers below come from).

---

## 1. Context: why this fix exists

The on-site ingestion batch (`scripts/ingest_seed_vehicles.py` driving `etl/pipeline.py::run_full_ingest`) is resumable at the **per-PDF** level via `IngestManifest` (`etl/load/manifest.py`) — if the process crashes or is restarted, already-ingested PDFs are correctly skipped and not re-downloaded/re-parsed/re-embedded.

**But there is no equivalent short-circuit at the vehicle level.** Confirmed live during the ingestion session that produced this doc: re-running the batch script against a vehicle that was already **100% completed** in a prior run still makes a real NHTSA network call (`resolve_documents`) plus a mandatory 0.5s "polite pacing" sleep for **every single record** in that vehicle (`etl/pipeline.py:202-203`) — even though every resulting PDF then correctly gets skipped a few lines later by the existing per-PDF check (`etl/pipeline.py:219`). That per-PDF check only avoids re-downloading/re-parsing/re-embedding; it does nothing to avoid the network+sleep cost of even reaching that check.

**Measured real cost of this gap** (see `docs/ingestion_speed_log.md` for the full history): re-scanning 2015 Ram 1500 (591 records, already fully done) took **116 minutes**. Re-scanning 2015 Chevrolet Silverado 1500 (1,488 records, already fully done) took **~128 minutes**. Both produced **zero new data** — pure waste. A 30-vehicle batch (15 originally seeded + 15 added mid-session to `scripts/seed_vehicles.json`) was mid-run re-scanning the *original* 15 (already fully completed in an earlier successful pass) before it could ever reach the 15 genuinely new vehicles. At the observed pace, that re-scan alone would cost 10+ more hours before any new work happened.

**Scope note**: this is a narrow, surgical fix for eliminating redundant network waste against vehicles that are already fully done. It is explicitly **not** a broader concurrency/rate-limiting/GPU speedup — that was a separate idea considered and explicitly declined earlier in this project's history. Do not conflate the two or expand scope beyond what's below.

---

## 2. Current code (confirmed exact, read before editing)

### `etl/load/manifest.py` (74 lines total, quoted in full for context)

```python
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

Status = Literal["ingested", "skipped_no_text", "failed"]


class IngestManifest:
    """Tracks the state of ingested PDFs to allow resuming pipelines."""

    def __init__(self, manifest_path: str = "data/etl_workspace/ingest_manifest.json"):
        self.manifest_path = Path(manifest_path)
        self.manifest: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, encoding="utf-8") as f:
                    self.manifest = json.load(f)
            except json.JSONDecodeError:
                self.manifest = {}

    def save(self) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2)

    def _get_key(self, vehicle_slug: str, nhtsa_id: str, file_name: str) -> str:
        # Scoped per-vehicle: the same NHTSA bulletin ID is frequently shared
        # across multiple models/years (e.g. a shared driveline TSB). A global
        # key would mark it "ingested" the first time any vehicle processes
        # it, silently skipping the metadata tagging (make/model/year) every
        # other vehicle needs for its own RAG filter to ever find that chunk.
        return f"{vehicle_slug}/{nhtsa_id}/{file_name}"

    def mark_status(
        self,
        vehicle_slug: str,
        nhtsa_id: str,
        file_name: str,
        status: Status,
        chunks_count: int = 0,
    ) -> None:
        key = self._get_key(vehicle_slug, nhtsa_id, file_name)
        self.manifest[key] = {
            "status": status,
            "chunks_count": chunks_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.save()

    def get_status(
        self, vehicle_slug: str, nhtsa_id: str, file_name: str
    ) -> Status | None:
        key = self._get_key(vehicle_slug, nhtsa_id, file_name)
        entry = self.manifest.get(key)
        return entry.get("status") if entry else None

    def is_ingested(self, vehicle_slug: str, nhtsa_id: str, file_name: str) -> bool:
        return self.get_status(vehicle_slug, nhtsa_id, file_name) == "ingested"

    def reset_vehicle(self, vehicle_slug: str) -> int:
        """Clear all manifest entries for one vehicle so it can be
        re-ingested from scratch (e.g. after wiping the vector store).
        Returns the number of entries removed."""
        prefix = f"{vehicle_slug}/"
        keys_to_remove = [k for k in self.manifest if k.startswith(prefix)]
        for key in keys_to_remove:
            del self.manifest[key]
        if keys_to_remove:
            self.save()
        return len(keys_to_remove)
```

### `etl/pipeline.py` — relevant sections

`IngestSummary` dataclass (lines 96-102):
```python
class IngestSummary:
    vehicle: VehicleKey
    records_found: int = 0
    pdfs_ingested: int = 0
    pdfs_skipped_no_text: int = 0
    pdfs_failed: int = 0
    chunks_loaded: int = 0
```

`run_full_ingest` (lines 160-327), the relevant part of the main loop (lines 195-210):
```python
        with NhtsaManufacturerCommunicationsClient(config) as client:
            records = client.list_communications(vehicle)
            summary.records_found = len(records)
            progress(None)

            for record in records:
                try:
                    documents = client.resolve_documents(record)
                    time.sleep(0.5)  # Polite pacing for NHTSA API
                except NhtsaApiError as exc:
                    log.warning(
                        "failed to resolve documents for NHTSA id %s: %s",
                        record.nhtsa_id,
                        exc,
                    )
                    continue

                for document in documents:
                    if not document.is_pdf:
                        continue

                    nhtsa_id_str = str(record.nhtsa_id)
                    progress(document.file_name)

                    if manifest.is_ingested(
                        vehicle.slug, nhtsa_id_str, document.file_name
                    ):
                        log.info(
                            f"Skipping already ingested PDF: {document.file_name} (NHTSA ID {nhtsa_id_str})"
                        )
                        summary.pdfs_ingested += 1
                        continue
                    ...
```
(the rest of the loop — download/parse/chunk/load/mark_status — is unchanged by this fix)

End of function (line 325-327):
```python
        progress(None, status="done")

    return summary
```

`VehicleKey.slug` (`etl/models.py` lines 41-44):
```python
@property
def slug(self) -> str:
    """Filesystem/manifest-safe identifier, e.g. "2010_toyota_corolla"."""
    return f"{self.year}_{self.make}_{self.model}".lower().replace(" ", "_")
```

**Existing tests to keep passing**: `tests/unit/test_etl_loader.py` has `test_manifest`, `test_manifest_is_scoped_per_vehicle`, `test_manifest_reset_vehicle`. No test currently exercises `run_full_ingest` directly.

---

## 3. The fix

### 3a. `etl/load/manifest.py` — add a vehicle-level completion marker

Add these three additions to the `IngestManifest` class (a new class constant, two new methods):

```python
_COMPLETE_MARKER = "__complete__"
```
(as a class attribute, alongside the existing methods)

```python
def mark_vehicle_complete(self, vehicle_slug: str, records_found: int) -> None:
    """Record that a full run_full_ingest pass over this vehicle finished
    cleanly and every record's documents were resolved and accounted for.
    Lets a future run skip straight past the NHTSA resolve_documents() call
    and its 0.5s pacing sleep for every record -- the per-PDF skip check
    further down already avoided re-downloading/re-parsing, but did
    nothing to avoid the network+sleep cost of even reaching that check
    for a vehicle that's already fully done."""
    key = f"{vehicle_slug}/{self._COMPLETE_MARKER}"
    self.manifest[key] = {
        "status": "complete",
        "records_found": records_found,
        "timestamp": datetime.utcnow().isoformat(),
    }
    self.save()

def is_vehicle_complete(self, vehicle_slug: str) -> bool:
    entry = self.manifest.get(f"{vehicle_slug}/{self._COMPLETE_MARKER}")
    return bool(entry) and entry.get("status") == "complete"

def vehicle_status_counts(self, vehicle_slug: str) -> dict[str, int]:
    """Count per-PDF manifest entries for this vehicle by status (excludes
    the __complete__ marker itself). Shared by run_full_ingest's skip path
    and the backfill script (§3c) so the counting logic isn't duplicated."""
    prefix = f"{vehicle_slug}/"
    counts: dict[str, int] = {}
    for key, entry in self.manifest.items():
        if key.startswith(prefix) and not key.endswith(f"/{self._COMPLETE_MARKER}"):
            counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    return counts
```

**Why this key format is safe**: every real per-PDF key is always 3 path segments (`slug/nhtsa_id/file_name`) per `_get_key`. The marker key is always 2 segments (`slug/__complete__`). No real `nhtsa_id` can literally be the string `"__complete__"`, so there is zero collision risk — `mark_status`/`get_status`/`is_ingested` need **no changes at all**. `reset_vehicle`'s existing prefix-delete (`k.startswith(f"{vehicle_slug}/")`) automatically matches and clears the marker key too — this is desired: resetting a vehicle should force a full re-check next time, and this happens for free with no code change to `reset_vehicle`.

### 3b. `etl/pipeline.py` — the short-circuit

**Add a new field to `IngestSummary`** (alongside the existing `pdfs_failed`):
```python
class IngestSummary:
    vehicle: VehicleKey
    records_found: int = 0
    pdfs_ingested: int = 0
    pdfs_skipped_no_text: int = 0
    pdfs_failed: int = 0
    records_failed: int = 0  # NEW -- see reasoning below
    chunks_loaded: int = 0
```

**Add the skip check** immediately after `summary.records_found = len(records)` / `progress(None)` (currently lines 197-198), before `for record in records:` (line 200):
```python
        with NhtsaManufacturerCommunicationsClient(config) as client:
            records = client.list_communications(vehicle)
            summary.records_found = len(records)
            progress(None)

            if manifest.is_vehicle_complete(vehicle.slug):
                log.info(f"{vehicle} already fully ingested per manifest; skipping resolve/download pass.")
                counts = manifest.vehicle_status_counts(vehicle.slug)
                summary.pdfs_ingested = counts.get("ingested", 0)
                summary.pdfs_skipped_no_text = counts.get("skipped_no_text", 0)
                progress(None, status="done")
                return summary

            for record in records:
                try:
                    documents = client.resolve_documents(record)
                    time.sleep(0.5)  # Polite pacing for NHTSA API
                except NhtsaApiError as exc:
                    log.warning(
                        "failed to resolve documents for NHTSA id %s: %s",
                        record.nhtsa_id,
                        exc,
                    )
                    summary.records_failed += 1  # NEW
                    continue
                ...
```

**Set the marker at the end of the function**, replacing the current final block (lines 325-327):
```python
        if summary.pdfs_failed == 0 and summary.records_failed == 0:
            manifest.mark_vehicle_complete(vehicle.slug, summary.records_found)
        progress(None, status="done")

    return summary
```

**Why `records_failed` is required, not optional**: without it, a vehicle where NHTSA transiently failed to resolve even one record's documents (hits the existing `except NhtsaApiError` branch, which just logs a warning and `continue`s past — silently skipping that record forever, since no PDF-level manifest entry is ever created for a record whose documents were never resolved) would still get marked `"complete"` if `pdfs_failed == 0`. That would permanently hide the gap from every future run. Gating on both counters closes that hole. This is the one place worth being stricter than the minimum — getting this gate wrong is exactly the kind of thing that silently erodes data completeness over time without ever showing up as an error.

**Crash-safety is unchanged**: if the process is killed mid-loop (crash, SIGKILL, network death, disconnect) before the marker-setting line is ever reached, the marker is never set, and the vehicle is correctly fully re-scanned on the next run — identical to today's behavior for a partial vehicle. Nothing about existing resumability changes for a vehicle that *isn't* fully done.

### 3c. New script: `scripts/backfill_vehicle_complete_markers.py`

Retroactively marks whichever vehicles are **already fully completed** as of whenever this script runs, **without trusting remembered/printed log numbers from any prior run** — the manifest plus one fresh, cheap `list_communications` call per vehicle (a call `run_full_ingest` makes anyway, so this adds no meaningful new NHTSA load) is the authoritative source of truth.

For each vehicle in `scripts/seed_vehicles.json`:
1. Construct the `VehicleKey`, call `client.list_communications(vehicle)` once to get NHTSA's **current** authoritative set of `nhtsa_id`s and `records_found` — this must be fetched fresh, not assumed from an old log, since NHTSA could have published new bulletins for that vehicle since any prior run.
2. Group the vehicle's existing manifest keys (prefix `f"{vehicle.slug}/"`, excluding the `__complete__` marker itself) by their `nhtsa_id` segment.
3. Mark the vehicle complete (`manifest.mark_vehicle_complete(vehicle.slug, records_found)`) **only if**:
   - Every `nhtsa_id` in the freshly-fetched `records` list has at least one corresponding manifest entry, **and**
   - No manifest entry for that vehicle has `status == "failed"`.
4. If either condition fails, print exactly why (e.g. "NHTSA now lists 5 nhtsa_ids for this vehicle but only 3 are in the manifest — 2 new records since the last run, needs a real re-scan") and leave it unmarked. **This is correct, not a bug** — if upstream NHTSA data genuinely grew, that vehicle should get a real (if partial) re-scan, not be force-marked complete.

CLI behavior: default to `--dry-run` (print what *would* be marked, persist nothing); require an explicit `--apply` flag to actually call `mark_vehicle_complete` and write to disk. Always run `--dry-run` first and read the output before `--apply`.

---

## 4. Operational sequence (execute in this exact order)

> **Before starting**: confirm you're looking at the right machine/SSD. Run `git log --oneline -5` and compare against what you expect; run the runbook's §3.1 sanity check (SSD mounted, `data/chroma_db`/`data/etl_workspace` symlinks resolve, chunk count matches `docs/ingestion_speed_log.md`'s last known total) before touching anything. If the numbers don't line up, STOP and figure out why before proceeding — do not assume you're pointed at the right store.

1. **Stop the currently-running batch, if one is running on this machine**: check `ps -p "$(cat ingest_batch.pid)"`. If alive: `pkill -TERM -f "python scripts/ingest_seed_vehicles.py"`, wait a few seconds, confirm dead, escalate to `pkill -KILL -f "..."` only if still alive. (Don't use `scripts/pause_ingestion_and_eject.sh` for this step specifically — that also ejects the SSD, which isn't wanted if you're about to relaunch on the same machine right after. Use it only if you actually need to physically disconnect the drive.) Manifest safety is already guaranteed regardless of how it's stopped: every `mark_status`/`save()` call is synchronous and already durable before any kill signal lands.
2. **Apply the code changes** from §3a and §3b.
3. **Write the new tests** (§5 below) into `tests/unit/test_etl_loader.py` and run `uv run pytest tests/unit/test_etl_loader.py -v` — all must pass, including the three pre-existing tests unmodified, before proceeding.
4. **Run the full lint/type gate**: `uv run ruff check backend/ etl/ && uv run black --check backend/ etl/ && uv run mypy backend/` (adjust paths if `mypy` isn't configured for `etl/` — check `pyproject.toml`/`mypy.ini` first; don't skip this step even if `etl/` turns out to be excluded, since `manifest.py`/`pipeline.py` changes still need to type-check cleanly against whatever config applies).
5. **Write `scripts/backfill_vehicle_complete_markers.py`** per §3c.
6. **Manual dry-run against a throwaway copy first** (see §5) — do not skip this even though it feels slow. Confirm correctness before touching the real manifest.
7. **Run the backfill script `--dry-run` against the real manifest** (`data/etl_workspace/ingest_manifest.json`, reached via the `data/etl_workspace` symlink to the SSD) — read-only, safe. Confirm the vehicles it identifies as complete match what you expect (the vehicles that finished cleanly in prior runs — check `docs/ingestion_speed_log.md` and `docs/ingestion_status.md` for what's already known to be done).
8. **Re-run with `--apply`** once the dry-run output looks correct.
9. **Relaunch the batch**, exactly per `docs/onsite_ingestion_runbook.md` §3.3:
   ```bash
   nohup caffeinate -i uv run --group etl python scripts/ingest_seed_vehicles.py \
     > ingest_batch.log 2>&1 &
   echo $! > ingest_batch.pid
   ```
10. **Verify it actually worked**: tail `ingest_batch.log` for the first minute or two. Every already-complete vehicle should print its "Processing X..." line and move on almost instantly (no resolve/sleep delay per record); the first vehicle that ISN'T already marked complete should be the first one to take normal per-record time. If any supposedly-complete vehicle doesn't skip instantly, **stop and investigate** — don't assume the fix worked just because the process is running.
11. **Relaunch the watchdog** — `scripts/ingestion_watchdog.sh` is already persisted on disk in this repo; run it as a background process (e.g. via `nohup bash scripts/ingestion_watchdog.sh > watchdog.log 2>&1 &`, or via whatever background-process mechanism your environment provides) so crash/stall/completion detection and per-vehicle speed logging (into `docs/ingestion_speed_log.md`) continue. It exits its own loop whenever the tracked PID changes or the batch completes/crashes, so it needs restarting after any relaunch — this is expected, not a bug.
12. **Also consider relaunching `scripts/ingestion_safety_snapshot.sh`** if it isn't already running independently — it takes retention-capped (12 max) incremental snapshots of the live `chroma_db` every 30 minutes with a corruption tripwire (alerts if chunk count ever decreases between cycles). Not strictly required by this fix, but was part of the safety posture for this ingestion session and is worth keeping running for the remainder of it.

---

## 5. Verification / testing plan

**New unit tests** in `tests/unit/test_etl_loader.py`, matching the existing `tempfile.TemporaryDirectory()` + fresh `IngestManifest(manifest_path)` pattern already used by the three tests already there:

- `test_mark_and_is_vehicle_complete`: mark a vehicle complete, assert `is_vehicle_complete` is `True` for that slug and `False` for an unrelated one. Reload the manifest from disk (construct a new `IngestManifest(manifest_path)` pointed at the same file) and confirm it persists.
- `test_vehicle_complete_marker_is_scoped_per_vehicle`: mirrors the existing `test_manifest_is_scoped_per_vehicle` — marking one vehicle complete must not mark a different vehicle complete.
- `test_reset_vehicle_clears_complete_marker`: mark a vehicle complete, call `reset_vehicle(slug)`, assert `is_vehicle_complete` now returns `False`.
- Confirm the three pre-existing tests (`test_manifest`, `test_manifest_is_scoped_per_vehicle`, `test_manifest_reset_vehicle`) still pass completely unmodified.
- A `run_full_ingest`-level test: mock/monkeypatch `NhtsaManufacturerCommunicationsClient` so `resolve_documents` raises an exception (or a test-failure assertion) if it's ever called; pre-seed a manifest with `mark_vehicle_complete` for that vehicle's slug; call `run_full_ingest`; assert it returns successfully **without ever invoking the mocked `resolve_documents`** — this is the test that actually proves the network+sleep cost is skipped, not just the download step.

**Manual dry-run against a throwaway copy, before trusting anything against the real manifest**:
```bash
cp data/etl_workspace/ingest_manifest.json /tmp/manifest_test_copy.json
```
Point a scratch `IngestManifest` instance at `/tmp/manifest_test_copy.json` (not the real path), run the backfill script's logic against it (or a temporary variant pointed at the scratch file), then call `run_full_ingest` for one already-completed vehicle against that same scratch manifest plus a scratch `config.workspace_dir` (e.g. `/tmp/etl_scratch_workspace`) — confirm it returns near-instantly, with matching counts, and **zero new network calls** appearing in the log for that vehicle. Only after this confirms correct behavior should the real manifest be backfilled (§4 step 7-8) and the real batch relaunched (§4 step 9).

**Full gate before considering this done**: `uv run pytest tests/unit/ -v` (not just the one file — confirm nothing else broke), plus the lint/type-check commands in §4 step 4.
