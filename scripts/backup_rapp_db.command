#!/usr/bin/env bash
# Double-click this file in Finder to back up rapp.db to the SSD (opens in Terminal).
# Tip: right-click -> Make Alias and drop the alias on your Desktop or Dock.
# It just calls backup_rapp_db.sh so there is one source of truth.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/backup_rapp_db.sh"

echo
echo "(You can close this window.)"
