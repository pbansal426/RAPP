#!/usr/bin/env python3
"""Batch-ingest a JSON list of vehicles into the ChromaDB knowledge base.

This is the primary driver for the on-site ingestion phase (see
`docs/onsite_ingestion_runbook.md`). It reads `scripts/seed_vehicles.json`
and runs the full NHTSA-TSB ingestion pipeline for each vehicle in order,
writing chunks into the live vector store (`data/chroma_db`).

Design goals for an unattended, hours-long run on a second machine:

- **Resumable**: the per-vehicle `ingest_manifest.json` already skips PDFs
  ingested on a prior run, so re-running after a crash/interrupt continues
  where it left off rather than re-downloading everything.
- **Continues past failures**: one vehicle failing (network blip, lock,
  bad PDF) never aborts the batch -- it's logged and the run moves on.
- **Auto-heals NHTSA naming mismatches**: NHTSA's model names sometimes
  differ from the common name (e.g. "Silverado 1500" is listed as
  "Silverado", a "300h" is just "ES"). When a vehicle returns zero
  records, this retries ONCE with a simplified model name before giving up.
- **Emits a paste-ready status table**: at the end it prints a Markdown
  table row per vehicle, ready to paste straight into
  `docs/ingestion_status.md` -- no manual bookkeeping.

Usage:
    uv run --group etl python scripts/ingest_seed_vehicles.py
    uv run --group etl python scripts/ingest_seed_vehicles.py --seed-file path/to/list.json

IMPORTANT: leave `USE_GEMINI_EMBEDDINGS` unset/false. The live store is
built with ChromaDB's local all-MiniLM-L6-v2 (384-dim) embeddings; mixing
in Gemini (768-dim) embeddings corrupts retrieval. See the runbook.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from etl.config import EtlConfig
from etl.load.manifest import IngestManifest
from etl.models import VehicleKey
from etl.pipeline import IngestSummary, run_full_ingest

load_dotenv()

# Trailing model tokens that NHTSA frequently drops from its own model
# naming (bed/size designators). Used only for the ONE simplified-name
# retry when a vehicle returns zero records -- never to silently change
# what gets ingested when the original name already matched.
_TRAILING_TRIM_TOKENS = {"1500", "2500", "3500", "150", "250", "350"}


def _simplify_model(model: str) -> str | None:
    """Return a simplified model name to retry, or None if there's nothing
    conservative to try. Only strips a trailing size/bed token (e.g.
    "Silverado 1500" -> "Silverado"); deliberately does NOT guess at
    multi-word nameplates like "Grand Cherokee"."""
    tokens = model.split()
    if len(tokens) >= 2 and tokens[-1] in _TRAILING_TRIM_TOKENS:
        return " ".join(tokens[:-1])
    return None


def _ingest_one(
    v_data: dict[str, object],
    config: EtlConfig,
    manifest: IngestManifest,
) -> tuple[VehicleKey, str, IngestSummary | None, str]:
    """Ingest a single vehicle. Returns (vehicle, status, summary, note).

    status is one of: "DONE", "SKIPPED", "FAILED".
    """
    vehicle = VehicleKey(
        year=int(v_data["year"]),  # type: ignore[call-overload]
        make=str(v_data["make"]),
        model=str(v_data["model"]),
    )
    print(f"\nProcessing {vehicle} ...")

    try:
        summary = run_full_ingest(vehicle, config, manifest, load=True)
    except Exception as exc:  # noqa: BLE001 -- one bad vehicle must not abort the batch
        print(f"  FAILED: {exc}")
        return vehicle, "FAILED", None, f"error: {exc}"

    # Zero records usually means NHTSA doesn't list this vehicle under this
    # exact model name. Retry once with a simplified nameplate before skipping.
    note = ""
    if summary.records_found == 0:
        simplified = _simplify_model(vehicle.model)
        if simplified:
            retry_vehicle = VehicleKey(
                year=vehicle.year, make=vehicle.make, model=simplified
            )
            print(
                f"  0 records under '{vehicle.model}'; retrying as '{simplified}' ..."
            )
            try:
                retry_summary = run_full_ingest(
                    retry_vehicle, config, manifest, load=True
                )
            except Exception as exc:  # noqa: BLE001
                print(f"  FAILED on retry: {exc}")
                return vehicle, "FAILED", None, f"retry error: {exc}"
            if retry_summary.records_found > 0:
                print(f"  Matched under simplified name '{simplified}'.")
                return (
                    retry_vehicle,
                    "DONE",
                    retry_summary,
                    f"matched NHTSA as '{simplified}'",
                )
        print("  SKIPPED: no NHTSA match under this name.")
        return vehicle, "SKIPPED", summary, "no NHTSA match under this name"

    _print_summary(summary)
    return vehicle, "DONE", summary, note


def _print_summary(summary: IngestSummary) -> None:
    print(f"  Records Found:          {summary.records_found}")
    print(f"  PDFs Ingested:          {summary.pdfs_ingested}")
    print(f"  PDFs Skipped (no text): {summary.pdfs_skipped_no_text}")
    print(f"  PDFs Failed:            {summary.pdfs_failed}")
    print(f"  Chunks Loaded:          {summary.chunks_loaded}")


def _status_table_row(
    vehicle: VehicleKey, status: str, summary: IngestSummary | None, note: str
) -> str:
    """A Markdown row matching docs/ingestion_status.md's column order."""
    today = datetime.now(UTC).date().isoformat()
    icon = {"DONE": "✅ Done", "SKIPPED": "⏭️ Skipped", "FAILED": "❌ Failed"}[status]
    if note:
        icon = f"{icon} — {note}"
    rec = summary.records_found if summary else 0
    ing = summary.pdfs_ingested if summary else 0
    skip = summary.pdfs_skipped_no_text if summary else 0
    fail = summary.pdfs_failed if summary else 0
    chunks = summary.chunks_loaded if summary else 0
    return (
        f"| {vehicle.year} | {vehicle.make} | {vehicle.model} | {icon} "
        f"| {rec} | {ing} | {skip} | {fail} | {chunks} | {today} |"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed-file",
        type=Path,
        default=Path(__file__).parent / "seed_vehicles.json",
        help="JSON list of {year, make, model} objects to ingest.",
    )
    args = parser.parse_args()

    with open(args.seed_file) as f:
        vehicles_data = json.load(f)

    config = EtlConfig()
    manifest_path = config.workspace_dir / "ingest_manifest.json"
    manifest = IngestManifest(str(manifest_path))

    print("=" * 64)
    print(f"Starting batch ingestion of {len(vehicles_data)} vehicles")
    print(f"Seed file: {args.seed_file}")
    print(f"Workspace: {config.workspace_dir}")
    print("=" * 64)

    totals = {
        "records_found": 0,
        "pdfs_ingested": 0,
        "pdfs_skipped": 0,
        "pdfs_failed": 0,
        "chunks_loaded": 0,
    }
    table_rows: list[str] = []
    status_counts = {"DONE": 0, "SKIPPED": 0, "FAILED": 0}

    for v_data in vehicles_data:
        vehicle, status, summary, note = _ingest_one(v_data, config, manifest)
        status_counts[status] += 1
        table_rows.append(_status_table_row(vehicle, status, summary, note))
        if summary is not None:
            totals["records_found"] += summary.records_found
            totals["pdfs_ingested"] += summary.pdfs_ingested
            totals["pdfs_skipped"] += summary.pdfs_skipped_no_text
            totals["pdfs_failed"] += summary.pdfs_failed
            totals["chunks_loaded"] += summary.chunks_loaded

    print("\n" + "=" * 64)
    print("Batch Ingestion Summary")
    print("=" * 64)
    print(
        f"  Vehicles: {status_counts['DONE']} done, "
        f"{status_counts['SKIPPED']} skipped, {status_counts['FAILED']} failed"
    )
    print(f"  Records Found:          {totals['records_found']}")
    print(f"  PDFs Ingested:          {totals['pdfs_ingested']}")
    print(f"  PDFs Skipped (no text): {totals['pdfs_skipped']}")
    print(f"  PDFs Failed:            {totals['pdfs_failed']}")
    print(f"  Chunks Loaded:          {totals['chunks_loaded']}")

    print("\n" + "-" * 64)
    print("Paste these rows into docs/ingestion_status.md:")
    print("-" * 64)
    for row in table_rows:
        print(row)


if __name__ == "__main__":
    main()
