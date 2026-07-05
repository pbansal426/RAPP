"""Pretty-print the live ingestion progress snapshot for `watch`-ing.

    watch -n 1 uv run python -m etl.progress_view

Reads the same data/etl_workspace/progress.json that run_full_ingest()
writes after every PDF -- no dependency on log verbosity, works whether or
not -v was passed to the ingest itself.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from etl.config import EtlConfig


def render(payload: dict[str, Any]) -> str:
    total_processed = (
        int(payload.get("pdfs_ingested", 0) or 0)
        + int(payload.get("pdfs_skipped_no_text", 0) or 0)
        + int(payload.get("pdfs_failed", 0) or 0)
    )
    records_found = payload.get("records_found")
    bar = ""
    if isinstance(records_found, int) and records_found > 0:
        width = 30
        filled = min(width, round(width * total_processed / records_found))
        bar = f"[{'#' * filled}{'.' * (width - filled)}] {total_processed}/{records_found} records\n"

    lines = [
        f"Vehicle:  {payload.get('vehicle', '?')}",
        f"Status:   {payload.get('status', '?')}",
        bar.rstrip("\n"),
        f"Ingested: {payload.get('pdfs_ingested', 0)}   "
        f"Skipped: {payload.get('pdfs_skipped_no_text', 0)}   "
        f"Failed: {payload.get('pdfs_failed', 0)}",
        f"Chunks loaded so far: {payload.get('chunks_loaded', 0)}",
        f"Current file: {payload.get('current_file') or '-'}",
        f"Last updated: {payload.get('updated_at', '?')}",
    ]
    return "\n".join(line for line in lines if line)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live-view etl ingestion progress")
    parser.add_argument("--workspace", type=Path, default=None)
    args = parser.parse_args(argv)

    config = EtlConfig()
    workspace_dir = args.workspace or config.workspace_dir
    progress_path = workspace_dir / "progress.json"

    if not progress_path.exists():
        print(f"No ingestion in progress (no {progress_path} found).")
        return 0

    try:
        payload = json.loads(progress_path.read_text())
    except json.JSONDecodeError:
        print("progress.json is mid-write, try again in a moment.")
        return 0

    print(render(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
