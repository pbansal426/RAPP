"""Entry point for the vertical-slice ingestion test.

    uv run --group etl python -m etl                # 2010 Toyota Corolla
    uv run --group etl python -m etl --year 2012 --make Honda --model Civic
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from etl.config import EtlConfig
from etl.load.audit import print_audit_log
from etl.load.manifest import IngestManifest
from etl.models import VehicleKey
from etl.pipeline import PipelineError, run_full_ingest, run_vertical_slice

log = logging.getLogger(__name__)

# Load environment variables early so vector store and other components see them.
load_dotenv()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m etl",
        description="RAPP vertical-slice ETL: NHTSA TSB PDF -> RAG-ready chunks",
    )
    parser.add_argument("--year", type=int, default=2010)
    parser.add_argument("--make", default="Toyota")
    parser.add_argument("--model", default="Corolla")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="override the PDF download directory (default: data/etl_workspace)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run full ingestion on all TSBs for the vehicle instead of the vertical slice",
    )
    parser.add_argument(
        "--load",
        action="store_true",
        help="Load the extracted documents into the vector store. Required when using --all.",
    )
    args = parser.parse_args(argv)

    # Progress goes to stderr so the audit log on stdout stays pipeable.
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s — %(message)s",
        stream=sys.stderr,
    )

    config = EtlConfig()
    if args.workspace is not None:
        config = dataclasses.replace(config, workspace_dir=args.workspace)
    vehicle = VehicleKey(year=args.year, make=args.make, model=args.model)

    if args.all:
        log.info(f"Starting full ingest for {vehicle}")
        manifest_path = config.workspace_dir / "ingest_manifest.json"
        manifest = IngestManifest(str(manifest_path))
        try:
            summary = run_full_ingest(vehicle, config, manifest, load=args.load)
            log.info("--- Ingestion Summary ---")
            log.info(f"Vehicle: {summary.vehicle}")
            log.info(f"Records found: {summary.records_found}")
            log.info(f"PDFs ingested: {summary.pdfs_ingested}")
            log.info(f"PDFs skipped (no text): {summary.pdfs_skipped_no_text}")
            log.info(f"PDFs failed: {summary.pdfs_failed}")
            log.info(f"Chunks loaded: {summary.chunks_loaded}")
        except PipelineError as exc:
            log.error("pipeline failed: %s", exc)
            return 1
    else:
        log.info(f"Starting vertical slice for {vehicle}")
        try:
            result = run_vertical_slice(vehicle, config)
        except PipelineError as exc:
            log.error("pipeline failed: %s", exc)
            return 1

        print_audit_log(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
