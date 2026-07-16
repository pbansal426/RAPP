#!/usr/bin/env bash
# Periodic incremental safety snapshots of the live chroma_db during an
# on-site ingestion session (see docs/onsite_ingestion_runbook.md), taken
# specifically because the SSD is formatted ExFAT (not journaling), so an
# abrupt physical disconnect mid-write carries real (if small) filesystem-
# corruption risk beyond the ordinary "lose one in-flight PDF" guarantee
# the manifest already provides for a clean process kill.
#
# Also does a monotonic sanity check on every cycle: a healthy running
# ingestion should never have its total chunk count DECREASE between
# snapshots. If it does, that's logged as an incident immediately rather
# than silently overwritten by the next snapshot.
#
# Retention-capped (MAX_SNAPSHOTS below) -- this does NOT grow unbounded.
#
# Usage: ./scripts/ingestion_safety_snapshot.sh

SSD="/Volumes/Extreme SSD/dev/RAPP_data"
REPO="/Users/prathambansal/Dev/RAPP/RAPP"
INCIDENT_LOG="$REPO/docs/ingestion_incident_log.md"
MAX_SNAPSHOTS=12
INTERVAL_SECONDS=1800
last_chunk_count=0

while true; do
  sleep "$INTERVAL_SECONDS"
  ts=$(date -u +"%Y%m%dT%H%M%SZ")

  if [ ! -d "$SSD/chroma_db" ]; then
    echo "SNAPSHOT_SKIPPED: chroma_db not found at expected path at $ts -- SSD may be disconnected"
    continue
  fi

  cur_chunk_count=$(uv run --project "$REPO" python -c "
import chromadb
from chromadb.config import Settings
c = chromadb.PersistentClient(path='$SSD/chroma_db', settings=Settings(anonymized_telemetry=False))
print(c.get_or_create_collection('repair_manuals').count())
" 2>/dev/null | tail -1)

  if [ -z "$cur_chunk_count" ]; then
    echo "SNAPSHOT_WARNING: could not read chunk count at $ts -- store may be mid-write or unreadable, skipping this cycle's snapshot"
    continue
  fi

  if [ "$last_chunk_count" != "0" ] && [ "$cur_chunk_count" -lt "$last_chunk_count" ]; then
    echo "SNAPSHOT_ALERT: chunk count DECREASED ($last_chunk_count -> $cur_chunk_count) at $ts -- possible corruption or rollback, investigate before trusting the store further"
    {
      echo ""
      echo "## Incident: chunk count decreased — $ts"
      echo "Previous snapshot cycle: $last_chunk_count chunks. This cycle: $cur_chunk_count chunks. A healthy running ingestion should never lose chunks. Do not assume this is benign -- verify the store before continuing."
    } >> "$INCIDENT_LOG"
  fi
  last_chunk_count="$cur_chunk_count"

  cp -R "$SSD/chroma_db" "$SSD/chroma_db.snapshot_$ts"
  size=$(du -sh "$SSD/chroma_db.snapshot_$ts" | cut -f1)
  echo "SNAPSHOT_TAKEN: chroma_db.snapshot_$ts ($size, $cur_chunk_count chunks)"

  snapshot_count=$(ls -d "$SSD"/chroma_db.snapshot_* 2>/dev/null | wc -l | tr -d ' ')
  if [ "$snapshot_count" -gt "$MAX_SNAPSHOTS" ]; then
    oldest=$(ls -d "$SSD"/chroma_db.snapshot_* | sort | head -1)
    rm -rf "$oldest"
    echo "SNAPSHOT_ROTATED: removed oldest snapshot ($oldest) to stay at $MAX_SNAPSHOTS max"
  fi

done
