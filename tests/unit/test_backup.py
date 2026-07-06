"""Tests for backend/core/backup.py (rapp.db -> SSD backup helper)."""

import sqlite3
from pathlib import Path

from backend.core import backup


def _make_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)")
    conn.execute("INSERT INTO users (email) VALUES ('a@b.com')")
    conn.commit()
    conn.close()


def test_backup_writes_consistent_copy(tmp_path, monkeypatch):
    src = tmp_path / "rapp.db"
    _make_db(src)
    backup_dir = tmp_path / "backups"

    monkeypatch.setattr(backup, "_source_db_path", lambda: src)
    monkeypatch.setenv("RAPP_BACKUP_DIR", str(backup_dir))

    dest = backup.backup_rapp_db()

    assert dest is not None
    assert dest.exists()
    # The copy is a valid, queryable SQLite DB with the source's row.
    conn = sqlite3.connect(str(dest))
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("SELECT email FROM users").fetchone()[0] == "a@b.com"
    conn.close()


def test_backup_noop_when_source_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "_source_db_path", lambda: tmp_path / "absent.db")
    monkeypatch.setenv("RAPP_BACKUP_DIR", str(tmp_path / "backups"))

    assert backup.backup_rapp_db() is None


def test_backup_noop_when_ssd_absent(tmp_path, monkeypatch):
    src = tmp_path / "rapp.db"
    _make_db(src)
    monkeypatch.setattr(backup, "_source_db_path", lambda: src)
    # Parent of the override dir does not exist -> treated as "drive not mounted".
    monkeypatch.setenv("RAPP_BACKUP_DIR", str(tmp_path / "missing_volume" / "backups"))

    assert backup.backup_rapp_db() is None


def test_prune_keeps_only_newest(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    # Chronologically-sortable timestamped names, oldest first.
    names = [f"rapp.db.2026010{i:01d}T000000Z" for i in range(1, 10)]  # 9 files
    for name in names:
        (backup_dir / name).write_text("x")

    backup._prune(backup_dir, keep=5)

    remaining = sorted(p.name for p in backup_dir.glob("rapp.db.*"))
    assert remaining == names[-5:]  # newest 5 survive
