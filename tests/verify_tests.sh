#!/bin/bash

# verify_tests.sh
# Validation script to verify that the E2E test suite correctly passes under normal conditions,
# and catches faults injected via environment variables.

PORT=${PORT:-3699}
SERVER_PID=""

# Ensure any existing process on port 3699 is cleaned up
cleanup_port() {
  local pid
  pid=$(lsof -t -i:$PORT)
  if [ -n "$pid" ]; then
    echo "Cleaning up existing process on port $PORT (PID: $pid)..."
    kill -9 $pid 2>/dev/null || true
    sleep 1
  fi
}

start_server() {
  cleanup_port
  echo "Starting mock server on port $PORT..."
  MOCK_PORT=$PORT ./.venv/bin/python3 tests/mock_app.py > mock_app.log 2>&1 &
  SERVER_PID=$!
  sleep 2
}

stop_server() {
  if [ -n "$SERVER_PID" ]; then
    echo "Stopping mock server (PID: $SERVER_PID)..."
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
    SERVER_PID=""
  fi
  cleanup_port
}

# Run cleanup on script exit
trap stop_server EXIT

# Initialize counters
PASSED_TASKS=0
FAILED_TASKS=0

run_test_case() {
  local case_name="$1"
  local expected_to_pass="$2"
  local test_grep="$3"
  
  echo "======================================================================"
  echo "Running test case: $case_name"
  echo "Expected to pass: $expected_to_pass"
  echo "Test selector: $test_grep"
  echo "======================================================================"
  
  start_server
  
  if [ -n "$test_grep" ]; then
    FRONTEND_URL="http://localhost:$PORT" npx playwright test -g "$test_grep"
  else
    FRONTEND_URL="http://localhost:$PORT" npx playwright test
  fi
  
  local exit_code=$?
  stop_server
  
  if [ "$expected_to_pass" = "true" ]; then
    if [ $exit_code -eq 0 ]; then
      echo "✅ SUCCESS: Test passed under normal conditions as expected."
      PASSED_TASKS=$((PASSED_TASKS + 1))
    else
      echo "❌ FAILURE: Test failed under normal conditions (exit code: $exit_code)."
      FAILED_TASKS=$((FAILED_TASKS + 1))
    fi
  else
    if [ $exit_code -ne 0 ]; then
      echo "✅ SUCCESS: Test failed as expected under faulty conditions (exit code: $exit_code)."
      PASSED_TASKS=$((PASSED_TASKS + 1))
    else
      echo "❌ FAILURE: Test passed under faulty conditions, fault not caught!"
      FAILED_TASKS=$((FAILED_TASKS + 1))
    fi
  fi
  echo ""
}

# 1. Normal Conditions (All tests must pass)
export FAULTY_VIN_DECODING=false
export MISSING_WARNINGS=false
export BYPASS_PAYWALL_GATE=false
export SMALL_TOUCH_TARGETS=false
run_test_case "Normal Conditions (Whole Suite)" "true" ""

# 2. FAULTY_VIN_DECODING=true (Step 1 must fail)
export FAULTY_VIN_DECODING=true
export MISSING_WARNINGS=false
export BYPASS_PAYWALL_GATE=false
export SMALL_TOUCH_TARGETS=false
run_test_case "Faulty VIN Decoding (Step 1)" "false" "Step 1"

# 3. MISSING_WARNINGS=true (Safety Protocol must fail)
export FAULTY_VIN_DECODING=false
export MISSING_WARNINGS=true
export BYPASS_PAYWALL_GATE=false
export SMALL_TOUCH_TARGETS=false
run_test_case "Missing Warnings (Safety Protocol)" "false" "Safety Protocol"

# 4. BYPASS_PAYWALL_GATE=true (Step 3 & 4 must fail)
export FAULTY_VIN_DECODING=false
export MISSING_WARNINGS=false
export BYPASS_PAYWALL_GATE=true
export SMALL_TOUCH_TARGETS=false
run_test_case "Bypass Paywall Gate (Step 3 & 4)" "false" "Step 3"

# 5. SMALL_TOUCH_TARGETS=true (Step 1 & 2 must fail, checking Step 1 here)
export FAULTY_VIN_DECODING=false
export MISSING_WARNINGS=false
export BYPASS_PAYWALL_GATE=false
export SMALL_TOUCH_TARGETS=true
run_test_case "Small Touch Targets (Step 1)" "false" "Step 1"

echo "======================================================================"
echo "Verification Summary:"
echo "Passed: $PASSED_TASKS"
echo "Failed: $FAILED_TASKS"
echo "======================================================================"

if [ $FAILED_TASKS -eq 0 ]; then
  exit 0
else
  exit 1
fi
