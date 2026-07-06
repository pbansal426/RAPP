#!/usr/bin/env bash
# Back up the irreplaceable rapp.db (user accounts + saved repairs) to the external
# SSD. Consistent (SQLite online-backup API) and safe to run any number of times --
# repeated runs just rotate within the keep-last-N window. No-ops cleanly when the
# SSD is unplugged. Single source of truth is backend/core/backup.py; this is a thin
# wrapper so it can be driven from Finder (backup_rapp_db.command) or `make backup-db`.
set -euo pipefail

# Resolve the repo root from this script's location so it works regardless of cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

exec uv run python -m backend.core.backup
