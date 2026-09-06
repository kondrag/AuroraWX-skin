#!/bin/sh
# Run AuroraWXReport for all four scenarios, asserting each scenario's
# expected output immediately after its run (public_html is overwritten
# by every run, so assertions cannot be batched at the end).
# Refreshes fixtures first: the full scenario's "fresh" snapshot is only
# valid for ~30 minutes after tools/make_fixtures.sh created it.
set -e
cd "$(dirname "$0")/.."
DATA=dev-weewx/weewx-data
OUT="$DATA/public_html"

run_scenario() {
  PYTHONPATH="$PWD/$DATA/bin" .venv/bin/weectl report run AuroraWXReport \
    --config="$DATA/weewx-$1.conf" 2>&1 | tee "/tmp/aurora-run-$1.log"
  if grep -qE 'Traceback|ERROR ' "/tmp/aurora-run-$1.log"; then
    echo "FAIL: tracebacks/errors in $1 run"; exit 1
  fi
}

check() {
  grep -q "$2" "$1" || { echo "FAIL: $1 missing '$2'"; exit 1; }
  echo "ok: $1 contains '$2'"
}

sh tools/make_fixtures.sh

# Sync the committed skin/package into the dev tree so the scenario runs
# exercise the committed skin/package, not a stale dev-weewx copy.
sh tools/sync_dev.sh

run_scenario full
check "$OUT/aurora.html" 'up to date'
check "$OUT/aurora.html" 'id="kp-chart"'
check "$OUT/index.html" 'aurora-status-card'
check "$OUT/gallery.html" 'video/mp4'
check "$OUT/solar.html" 'regions-tbody'

run_scenario partial
check "$OUT/aurora.html" 'stale data'
check "$OUT/gallery.html" 'Still encoding'

run_scenario empty
check "$OUT/gallery.html" 'No timelapses found yet'

run_scenario nocam
check "$OUT/aurora.html" 'Aurora section is disabled'

echo "ALL-OK"
