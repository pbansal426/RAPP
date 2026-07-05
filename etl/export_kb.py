"""Snapshot the live vector store into kb_export/ for a Git LFS commit.

data/chroma_db is a symlink to SSD-hosted storage (see docs/ingestion_status.md)
-- git cannot track files inside a symlinked directory, only the symlink
itself. This copies the current chroma_db state into kb_export/chroma_db,
a real in-repo directory that .gitattributes tracks via LFS, stripping
AppleDouble shadow files (._*, an exFAT/macOS artifact -- see the size
investigation in this session's history) and any in-progress lock file.

    uv run python -m etl.export_kb
    git add kb_export/ && git commit -m "..." && git push
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from etl.config import EtlConfig

# Never export a mid-write chroma_db: refuse if another ingest currently
# holds the workspace lock (see etl/pipeline.py's _workspace_lock).
_LOCK_FILENAME = ".etl.lock"


def _is_locked(workspace_dir: Path) -> bool:
    """The lock lives per-vehicle (workspace_dir/<vehicle-slug>/.etl.lock --
    see etl/pipeline.py's _workspace_lock), not directly under workspace_dir,
    so every per-vehicle subdirectory needs checking, not just the top
    level."""
    import fcntl

    for lock_path in workspace_dir.glob(f"*/{_LOCK_FILENAME}"):
        try:
            with open(lock_path) as f:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f, fcntl.LOCK_UN)
        except OSError:
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    config = EtlConfig()
    if _is_locked(config.workspace_dir):
        print(
            "Refusing to export: another etl ingest currently holds the "
            "workspace lock. Wait for it to finish first.",
            file=sys.stderr,
        )
        return 1

    source = Path("data/chroma_db")
    if not source.exists():
        print(f"No chroma_db found at {source} -- nothing to export.", file=sys.stderr)
        return 1

    dest = Path("kb_export/chroma_db")
    if dest.exists():
        shutil.rmtree(dest)

    shutil.copytree(
        source,
        dest,
        ignore=shutil.ignore_patterns("._*", _LOCK_FILENAME, "*.tmp"),
    )

    total_bytes = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
    print(f"Exported {source} -> {dest} ({total_bytes / 1_000_000:.1f} MB)")
    print("Next: git add kb_export/ && git commit -m '...' && git push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
