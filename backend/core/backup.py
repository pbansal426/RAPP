"""Consistent, dependency-free backups of the SQLite ``rapp.db``.

``rapp.db`` (user accounts + saved repairs) is the one piece of app data that is
*irreplaceable* -- the vector store can be rebuilt from source PDFs, but a lost
account cannot. It lives on the internal disk (the authoritative copy); this module
writes a *second* copy onto the external SSD so the internal disk is never the only
place it exists.

Everything backup-related routes through :func:`backup_rapp_db` so there is a single
implementation: the FastAPI startup hook (``backend/app.py``), the ``scripts/`` CLI
wrappers, and ``make backup-db`` all call it. Backups use SQLite's online-backup API
(``Connection.backup``), which is transactionally consistent even while the server is
writing -- a raw file copy of a live WAL-mode DB can capture a torn snapshot.

The destination is on the SSD (derived from the ``data/chroma_db`` symlink's target,
or overridden via ``RAPP_BACKUP_DIR``). When the SSD is unplugged the destination
simply does not exist, and this is a clean no-op -- callers must never treat that as
an error.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import structlog

from backend.core.database import DATABASE_URL

logger = structlog.get_logger()

# How many timestamped copies to keep on the SSD. Each is ~1 MB; running the backup
# repeatedly ("spamming" the manual trigger) just rotates within this window.
KEEP_LAST = 20


def _source_db_path() -> Path | None:
    """Filesystem path of the live SQLite DB, or ``None`` for a non-SQLite backend."""
    prefix = "sqlite:///"
    if not DATABASE_URL.startswith(prefix):
        # Postgres/other in prod -- this local-durability helper doesn't apply.
        return None
    return Path(DATABASE_URL[len(prefix) :])


def _backup_dir() -> Path | None:
    """Directory on the SSD to write backups into, or ``None`` if unavailable.

    Resolution order:
      1. ``RAPP_BACKUP_DIR`` env override, if set.
      2. Sibling ``backups/`` next to the SSD data root, derived from the
         ``data/chroma_db`` symlink's target (``<ssd_root>/backups``).

    Returns ``None`` (a clean no-op signal) when the SSD is unplugged or no symlink
    is present -- never raises for the ordinary "drive not connected" case.
    """
    override = os.environ.get("RAPP_BACKUP_DIR")
    if override:
        base = Path(override)
        return base if base.parent.exists() else None

    chroma_link = Path("data/chroma_db")
    if not chroma_link.is_symlink():
        return None
    ssd_root = Path(os.readlink(chroma_link)).parent
    # ssd_root exists only when the SSD is actually mounted.
    return ssd_root / "backups" if ssd_root.exists() else None


def _prune(backup_dir: Path, keep: int = KEEP_LAST) -> None:
    """Keep only the newest ``keep`` ``rapp.db.*`` snapshots in ``backup_dir``."""
    snapshots = sorted(
        backup_dir.glob("rapp.db.*"),
        key=lambda p: p.name,  # timestamped names sort chronologically
    )
    for stale in snapshots[:-keep] if keep > 0 else snapshots:
        try:
            stale.unlink()
        except OSError as exc:  # pragma: no cover - best-effort cleanup
            logger.warning(
                "Failed to prune old backup", path=str(stale), error=str(exc)
            )


def backup_rapp_db() -> Path | None:
    """Write a consistent copy of ``rapp.db`` to the SSD, pruning old copies.

    Returns the path written, or ``None`` when there is nothing to do (non-SQLite
    backend, source DB missing, or SSD unplugged). Safe to call any number of times.
    """
    src = _source_db_path()
    if src is None or not src.exists():
        logger.info("Skipping rapp.db backup: no local SQLite DB present")
        return None

    backup_dir = _backup_dir()
    if backup_dir is None:
        logger.info("Skipping rapp.db backup: SSD backup location unavailable")
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    dest = backup_dir / f"rapp.db.{stamp}"

    source = sqlite3.connect(str(src))
    try:
        target = sqlite3.connect(str(dest))
        try:
            with target:
                source.backup(target)
        finally:
            target.close()
    finally:
        source.close()

    _prune(backup_dir)
    logger.info("Backed up rapp.db", dest=str(dest))
    return dest


def backup_rapp_db_safe() -> None:
    """Best-effort backup that never raises -- for the startup hook.

    Startup must not be blocked or failed by a backup problem, so any unexpected
    error is logged and swallowed.
    """
    try:
        backup_rapp_db()
    except Exception as exc:  # noqa: BLE001 - deliberately never fail startup
        logger.warning("rapp.db startup backup failed (continuing)", error=str(exc))


if __name__ == "__main__":
    result = backup_rapp_db()
    if result is not None:
        print(f"✅ Backed up rapp.db -> {result}")
    else:
        print(
            "⚠️  No backup written "
            "(SSD not connected, or no local SQLite rapp.db). Nothing lost."
        )
