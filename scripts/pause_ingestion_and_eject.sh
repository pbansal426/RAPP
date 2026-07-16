#!/usr/bin/env bash
# Safely pause the on-site knowledge-base ingestion batch and eject the SSD
# so the laptop can be returned to its owner. See
# docs/onsite_ingestion_runbook.md for the full ingestion process this
# pauses, and the "Resuming after a pause" section below for how to
# continue on a different machine.
#
# Safe by design, not just by luck: the pipeline's manifest
# (data/etl_workspace/ingest_manifest.json) records each PDF as ingested
# only after it's fully chunked and written to the vector store, so killing
# the process at any point loses at most the one PDF that was in flight --
# never corrupts already-ingested data. This mirrors the resumability
# guarantee already documented in the runbook for a crash/disconnect; a
# deliberate pause is no more risky than an accidental one.
#
# Usage: ./scripts/pause_ingestion_and_eject.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SSD_VOLUME="/Volumes/Extreme SSD"

echo "== Pausing ingestion batch =="

if pgrep -f "python scripts/ingest_seed_vehicles.py" > /dev/null 2>&1; then
  echo "Sending SIGTERM to the ingestion process..."
  pkill -TERM -f "python scripts/ingest_seed_vehicles.py" || true
  sleep 5
  if pgrep -f "python scripts/ingest_seed_vehicles.py" > /dev/null 2>&1; then
    echo "Still running after SIGTERM -- sending SIGKILL..."
    pkill -KILL -f "python scripts/ingest_seed_vehicles.py" || true
    sleep 2
  fi
else
  echo "No running ingestion process found (already stopped)."
fi

# caffeinate was launched wrapping the ingestion command specifically to
# keep the Mac awake for it -- once the batch is paused there's nothing left
# for it to keep alive, so clean it up too rather than leaving an orphaned
# process holding a power assertion for no reason.
if pgrep -f "caffeinate.*ingest_seed_vehicles" > /dev/null 2>&1; then
  echo "Stopping the associated caffeinate process..."
  pkill -f "caffeinate.*ingest_seed_vehicles" || true
fi

if pgrep -f "python scripts/ingest_seed_vehicles.py" > /dev/null 2>&1; then
  echo "ERROR: ingestion process is still running after SIGTERM+SIGKILL. Refusing to eject the SSD while it may still be writing. Investigate manually." >&2
  exit 1
fi

echo "Ingestion process confirmed stopped."
echo ""
echo "== Current progress snapshot (for the incident/status log) =="
cat "$REPO_DIR/data/etl_workspace/progress.json" 2>/dev/null || echo "(progress.json not found)"
echo ""

echo "== Ejecting SSD =="
if diskutil info "$SSD_VOLUME" > /dev/null 2>&1; then
  diskutil eject "$SSD_VOLUME"
  echo "SSD safely ejected. It is now safe to physically disconnect the drive."
else
  echo "SSD volume '$SSD_VOLUME' not currently mounted -- nothing to eject."
fi

cat <<'EOF'

== Paused. Safe to hand back the laptop. ==

Resuming on a different machine:
  1. Ensure this repo's current branch (with the updated
     scripts/seed_vehicles.json and this session's docs) is pulled there --
     check `git log --oneline -5` matches what you expect before proceeding.
  2. Physically connect the SSD to that machine; confirm it mounts at
     /Volumes/Extreme SSD (or update the path in this script / the runbook's
     §3.1 symlink commands if it mounts elsewhere).
  3. Re-run the runbook's §3.1 setup exactly (recreate the data/chroma_db
     and data/etl_workspace symlinks if this is a fresh clone) and its
     sanity-check command -- confirm the chunk count is AT LEAST what it was
     when this was paused (see the progress snapshot printed above / the
     latest entry in docs/ingestion_speed_log.md), never lower. A lower
     count means you are not pointed at the same live store.
  4. Re-launch the exact same background command from runbook §3.3:
       nohup caffeinate -i uv run --group etl python scripts/ingest_seed_vehicles.py \
         > ingest_batch.log 2>&1 &
       echo $! > ingest_batch.pid
     The manifest skips everything already ingested, so this picks up
     exactly where the pause left off -- at most the one in-flight PDF from
     the pause moment gets re-downloaded, nothing else repeats.
EOF
