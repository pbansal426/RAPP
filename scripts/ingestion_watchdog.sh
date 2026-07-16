#!/usr/bin/env bash
# Background health monitor for the on-site ingestion batch (see
# docs/onsite_ingestion_runbook.md). Detects crashes, stalls, unexpected
# tracebacks, and normal completion; logs incidents to
# docs/ingestion_incident_log.md and appends per-vehicle throughput rows to
# docs/ingestion_speed_log.md on every vehicle-boundary transition. Does NOT
# act on what it finds (no auto-relaunch, no git operations) -- that's left
# to whoever (human or AI agent) is notified, since relaunch decisions need
# a sanity re-check first (see pause_ingestion_and_eject.sh's resume notes).
#
# Meant to be run via a long-lived background process/Monitor, not
# interactively -- it loops forever (every 2 min) until the batch either
# completes or crashes.
#
# Usage: ./scripts/ingestion_watchdog.sh

REPO="/Users/prathambansal/Dev/RAPP/RAPP"
PID_FILE="$REPO/ingest_batch.pid"
LOG_FILE="$REPO/ingest_batch.log"
PROGRESS_FILE="$REPO/data/etl_workspace/progress.json"
INCIDENT_LOG="$REPO/docs/ingestion_incident_log.md"
SPEED_LOG="$REPO/docs/ingestion_speed_log.md"

last_updated_at=""
stall_ticks=0
traceback_seen=0
last_vehicle=$(jq -r '.vehicle // empty' "$PROGRESS_FILE" 2>/dev/null)
last_vehicle_start=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
last_vehicle_records=""
last_vehicle_pdfs=""
last_vehicle_chunks=""

while true; do
  sleep 120
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  if [ ! -f "$PID_FILE" ]; then
    echo "WATCHDOG_CRASHED: pid file missing at $now"
    { echo ""; echo "## Incident: PID file missing — $now"; echo "ingest_batch.pid no longer exists. Unknown cause -- check whether a batch is even supposed to be running."; } >> "$INCIDENT_LOG"
    break
  fi

  pid=$(cat "$PID_FILE")

  if ! ps -p "$pid" > /dev/null 2>&1; then
    if grep -q "Batch Ingestion Summary" "$LOG_FILE" 2>/dev/null; then
      echo "WATCHDOG_COMPLETE: batch finished normally at $now (pid $pid no longer running, summary present in log)"
    else
      echo "WATCHDOG_CRASHED: process $pid no longer running, no completion summary found, at $now"
      {
        echo ""
        echo "## Incident: Process died unexpectedly — $now"
        echo "Last 60 lines of ingest_batch.log:"
        echo '```'
        tail -60 "$LOG_FILE" 2>/dev/null
        echo '```'
        echo "Last known progress.json:"
        echo '```json'
        cat "$PROGRESS_FILE" 2>/dev/null
        echo '```'
      } >> "$INCIDENT_LOG"
    fi
    break
  fi

  cur_updated_at=$(jq -r '.updated_at // empty' "$PROGRESS_FILE" 2>/dev/null)
  if [ -n "$cur_updated_at" ] && [ "$cur_updated_at" = "$last_updated_at" ]; then
    stall_ticks=$((stall_ticks + 1))
  else
    stall_ticks=0
  fi
  last_updated_at="$cur_updated_at"

  if [ "$stall_ticks" -eq 7 ]; then
    echo "WATCHDOG_STALLED: no progress.json update in ~14+ min while process $pid is still alive, at $now"
    {
      echo ""
      echo "## Incident: Possible stall — $now"
      echo "progress.json has not changed in 7+ checks (~14 min) while process $pid is still running."
      echo '```json'
      cat "$PROGRESS_FILE" 2>/dev/null
      echo '```'
    } >> "$INCIDENT_LOG"
  fi

  if [ "$traceback_seen" -eq 0 ] && tail -300 "$LOG_FILE" 2>/dev/null | grep -q "Traceback (most recent call last)"; then
    traceback_seen=1
    echo "WATCHDOG_TRACEBACK: unexpected Python traceback detected in log at $now"
    {
      echo ""
      echo "## Incident: Unexpected traceback detected — $now"
      echo "Process is still alive, but a Python traceback appeared in the log."
      echo '```'
      tail -100 "$LOG_FILE"
      echo '```'
    } >> "$INCIDENT_LOG"
  fi

  cur_vehicle=$(jq -r '.vehicle // empty' "$PROGRESS_FILE" 2>/dev/null)
  cur_records=$(jq -r '.records_found // empty' "$PROGRESS_FILE" 2>/dev/null)
  cur_pdfs=$(jq -r '.pdfs_ingested // empty' "$PROGRESS_FILE" 2>/dev/null)
  cur_chunks=$(jq -r '.chunks_loaded // empty' "$PROGRESS_FILE" 2>/dev/null)

  if [ -n "$cur_vehicle" ] && [ "$cur_vehicle" != "$last_vehicle" ]; then
    if [ -n "$last_vehicle" ]; then
      start_epoch=$(date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$last_vehicle_start" +%s 2>/dev/null || echo 0)
      end_epoch=$(date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$now" +%s 2>/dev/null || echo 0)
      dur_min="?"
      rate="?"
      if [ "$start_epoch" != "0" ] && [ "$end_epoch" != "0" ]; then
        dur_min=$(awk "BEGIN{printf \"%.1f\", ($end_epoch-$start_epoch)/60}")
        if [ -n "$last_vehicle_pdfs" ] && [ "$last_vehicle_pdfs" != "0" ]; then
          rate=$(awk "BEGIN{printf \"%.0f\", $last_vehicle_pdfs/(($end_epoch-$start_epoch)/60)}")
        fi
      fi
      echo "WATCHDOG_VEHICLE_DONE: $last_vehicle finished at $now (~$dur_min min, ~$rate pdfs/min)"
      printf "| ? | %s | %s | %s | %s | %s | %s | %s | %s | live-tracked |\n" \
        "$last_vehicle" "$last_vehicle_records" "$last_vehicle_pdfs" "$last_vehicle_chunks" \
        "$last_vehicle_start" "$now" "$dur_min" "$rate" >> "$SPEED_LOG"
    fi
    last_vehicle="$cur_vehicle"
    last_vehicle_start="$now"
  fi
  last_vehicle_records="$cur_records"
  last_vehicle_pdfs="$cur_pdfs"
  last_vehicle_chunks="$cur_chunks"

done
