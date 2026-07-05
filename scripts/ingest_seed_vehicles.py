#!/usr/bin/env python3
import json
from pathlib import Path

from dotenv import load_dotenv

from etl.config import EtlConfig
from etl.load.manifest import IngestManifest
from etl.models import VehicleKey
from etl.pipeline import run_full_ingest

load_dotenv()


def main() -> None:
    script_dir = Path(__file__).parent
    seed_file = script_dir / "seed_vehicles.json"

    with open(seed_file) as f:
        vehicles_data = json.load(f)

    config = EtlConfig()
    manifest_path = config.workspace_dir / "ingest_manifest.json"
    manifest = IngestManifest(str(manifest_path))

    totals = {
        "records_found": 0,
        "pdfs_ingested": 0,
        "pdfs_skipped": 0,
        "pdfs_failed": 0,
        "chunks_loaded": 0,
    }

    print("=" * 60)
    print("Starting Seed Vehicle Ingestion")
    print("=" * 60)

    for v_data in vehicles_data:
        vehicle = VehicleKey(
            year=v_data["year"], make=v_data["make"], model=v_data["model"]
        )
        print(f"\nProcessing {vehicle}...")

        try:
            summary = run_full_ingest(vehicle, config, manifest, load=True)

            print(f"  Records Found: {summary.records_found}")
            print(f"  PDFs Ingested: {summary.pdfs_ingested}")
            print(f"  PDFs Skipped (no text): {summary.pdfs_skipped_no_text}")
            print(f"  PDFs Failed: {summary.pdfs_failed}")
            print(f"  Chunks Loaded: {summary.chunks_loaded}")

            totals["records_found"] += summary.records_found
            totals["pdfs_ingested"] += summary.pdfs_ingested
            totals["pdfs_skipped"] += summary.pdfs_skipped_no_text
            totals["pdfs_failed"] += summary.pdfs_failed
            totals["chunks_loaded"] += summary.chunks_loaded

        except Exception as e:
            print(f"  Failed to process vehicle {vehicle}: {e}")

    print("\n" + "=" * 60)
    print("Total Seed Vehicle Ingestion Summary")
    print("=" * 60)
    print(f"  Records Found: {totals['records_found']}")
    print(f"  PDFs Ingested: {totals['pdfs_ingested']}")
    print(f"  PDFs Skipped (no text): {totals['pdfs_skipped']}")
    print(f"  PDFs Failed: {totals['pdfs_failed']}")
    print(f"  Chunks Loaded: {totals['chunks_loaded']}")


if __name__ == "__main__":
    main()
