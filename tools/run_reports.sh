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

check_not() {
  ! grep -q "$2" "$1" || { echo "FAIL: $1 unexpectedly contains '$2'"; exit 1; }
  echo "ok: $1 does not contain '$2'"
}

sh tools/make_fixtures.sh

# Sync the committed skin/package into the dev tree so the scenario runs
# exercise the committed skin/package, not a stale dev-weewx copy.
sh tools/sync_dev.sh

run_scenario full
check "$OUT/aurora.html" 'up to date'
check "$OUT/aurora.html" 'id="kp-chart"'
check "$OUT/aurora.html" 'data-snapshot-url'
check "$OUT/aurora.html" 'Driveway.jpg'
check "$OUT/aurora.html" 'Driveway.jpg?v='
check "$OUT/aurora.html" 'card h-100 text-center'
check "$OUT/aurora.html" 'd-flex flex-column justify-content-center'
check "$OUT/aurora.html" 'id="auroraModal"'
check "$OUT/aurora.html" 'js/aurora-gallery.js'
check "$OUT/aurora.html" 'clearsky_chart.gif?v='
check "$OUT/aurora.html" 'aurora-clearsky-img'
check "$OUT/index.html" '>Viewing</a>'
check "$OUT/index.html" 'id="rsg-r-now"'
check "$OUT/index.html" '<span>Impacts</span>'
check "$OUT/index.html" 'Current data as of'
check "$OUT/yesterday.html" 'Data from yesterday'
check "$OUT/week.html" 'Data from the past week:'
check "$OUT/month.html" 'Data from the past month:'
check "$OUT/year.html" 'Data from the past year:'
check "$OUT/archive.html" 'Available weather history'


check "$OUT/index.html" 'Radio Blackout</small>'
check "$OUT/css/aurora.css" 'min-width: 1660px'
check "$OUT/index.html" 'id="rsg-g-max"'
check "$OUT/index.html" 'xraysLongUrl'
check "$OUT/index.html" 'protonsUrl'
check "$OUT/index.html" '>National Weather Service</a>'
check "$OUT/index.html" 'wunderground.com/dashboard/pws/KWIGILMA2'
check "$OUT/index.html" 'href="https://www.windy.com"'
check "$OUT/index.html" 'Apparent Temperature'
check "$OUT/index.html" 'Cloud Base'
check "$OUT/index.html" '>Solar Activity</h5>'
check "$OUT/index.html" 'img/aurora-borealis.svg'
for p in yesterday week month year archive; do
  check "$OUT/$p.html" 'aurora.css?v='
done
check "$OUT/css/aurora.css" 'aurora-status-card .card-body'
check "$OUT/index.html" 'aurora-status-card'
check "$OUT/gallery.html" 'aurora-modal-trigger'
check "$OUT/solar.html" 'regions-tbody'
check "$OUT/solar.html" 'kp-forecast-chart'
check "$OUT/solar.html" 'card h-100 text-center'
check "$OUT/index.html" 'data-toggle="dropdown"'
check "$OUT/index.html" 'dropdown-item" href="yesterday.html'
check "$OUT/index.html" '>Past</a>'
check "$OUT/month.html" 'dropdown-item active" href="month.html'
check "$OUT/archive.html" 'dropdown-toggle active'

run_scenario partial
check "$OUT/aurora.html" 'stale data'
check_not "$OUT/aurora.html" 'clearsky_chart.gif'
check_not "$OUT/aurora.html" '>Clear Sky Chart<'
check_not "$OUT/aurora.html" 'clearsky_chart.gif'
check "$OUT/gallery.html" 'Still encoding'

run_scenario empty
check "$OUT/gallery.html" 'No timelapses found yet'

run_scenario nocam
check "$OUT/aurora.html" 'Viewing section is disabled'

echo "ALL-OK"
