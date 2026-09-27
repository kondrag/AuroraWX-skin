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
check_not "$OUT/aurora.html" 'up to date'
check "$OUT/aurora.html" 'id="kp-chart"'
check "$OUT/aurora.html" 'data-snapshot-url'
check "$OUT/aurora.html" 'Driveway.jpg'
check "$OUT/aurora.html" 'Driveway.jpg?v='
check "$OUT/aurora.html" 'card kp-accent h-100 text-center'
check_not "$OUT/aurora.html" 'd-flex flex-column justify-content-center'
check "$OUT/aurora.html" 'id="auroraModal"'
check "$OUT/aurora.html" 'js/aurora-gallery.js'
check "$OUT/aurora.html" 'clearsky_chart.gif?v='
check "$OUT/aurora.html" 'aurora-clearsky-img'
check_not "$OUT/aurora.html" 'id="kp-now-card"'
check_not "$OUT/aurora.html" 'id="aurora-badge"'
check_not "$OUT/aurora.html" 'id="bz-now"'
check_not "$OUT/aurora.html" 'id="wind-now"'
check_not "$OUT/aurora.html" 'Bz (nT)'
check_not "$OUT/aurora.html" 'Solar wind (km/s)'
check "$OUT/aurora.html" 'card-body d-flex flex-column justify-content-between'
check "$OUT/aurora.html" 'id="kp-fcst-card"'
check "$OUT/aurora.html" 'Kp 24 h fcst'
check "$OUT/aurora.html" 'id="rsg-g-now"'
check "$OUT/aurora.html" 'id="rsg-s-now"'
check "$OUT/aurora.html" 'id="rsg-r-now"'
check "$OUT/aurora.html" '"kpForecastUrl"'
check "$OUT/aurora.html" '"xraysLongUrl"'
check "$OUT/aurora.html" '"protonsUrl"'
check "$OUT/aurora.html" 'card kp-accent'
check_not "$OUT/aurora.html" 'Archive status:'
check_not "$OUT/aurora.html" '>Timelapse gallery</a>'
check "$OUT/index.html" '>Viewing</a>'
check_not "$OUT/index.html" 'id="rsg-r-now"'
check_not "$OUT/index.html" '<span>Impacts</span>'
check "$OUT/index.html" 'Current conditions'
check_not "$OUT/index.html" 'Conditions as of'
# Title and header times: no seconds, no leading-zero hour (%-I strips it)
check_not "$OUT/index.html" 'Conditions as of [0-9][0-9]-[A-Z][a-z][a-z]-[0-9][0-9][0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'
check_not "$OUT/index.html" '[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]'
# Almanac page: dd-Mon-yyyy dates, hours without leading zero, no seconds
check "$OUT/almanac.html" '[0-9][0-9]-[A-Z][a-z][a-z]-[0-9][0-9][0-9][0-9]'
check_not "$OUT/almanac.html" '[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]'
check_not "$OUT/almanac.html" '[0-9][0-9]:[0-9][0-9]:[0-9][0-9]'
# Sun/moon rise/set times: no seconds (bare $almanac defaults used to render HH:MM:SS)
check_not "$OUT/index.html" '[0-9][0-9]:[0-9][0-9]:[0-9][0-9] [AP]M'
# Header date uses dd-Mon-yyyy; Gallery Latest card title carries no date
check "$OUT/index.html" "font-small\">$(date +'%d-%b-%Y')"
check_not "$OUT/index.html" "font-small\">$(date +'%m/%d/%Y')"
check "$OUT/gallery.html" '<h5 class="card-title">Latest</h5>'
check_not "$OUT/gallery.html" 'card-title">Latest$'
check_not "$OUT/day.html" 'Historical data from the past day'  # title is the bare date/range
check "$OUT/day.html" "$(date -d yesterday +'%b %-d, %Y')"
check_not "$OUT/week.html" 'Historical data from the past week'  # title is the bare date/range
check "$OUT/week.html" "$(date -d 'last monday' +'%b %-d, %Y') to"
check_not "$OUT/month.html" 'Historical data from the past month'  # title is the bare date/range
check "$OUT/month.html" "$(date -d "$(date +%Y-%m-01)" +'%b %-d, %Y') to"
check_not "$OUT/year.html" 'Historical data from the past year'  # title is the bare date/range
check "$OUT/year.html" "$(date -d 'Jan 1' +'%b %-d, %Y') to"
check "$OUT/archive.html" 'Available weather history'
# telemetry page: signal quality card + chart render from seeded rxCheckPercent data
check "$OUT/telemetry.html" 'Signal Quality'
check "$OUT/telemetry.html" 'id="rxCheckPercent-chart"'
check_not "$OUT/telemetry.html" '>rxCheckPercent</h5>'  # label must not fall back to raw key
# sensor status + about-station cards (ported from Seasons)
check "$OUT/telemetry.html" 'Sensor Status'
check "$OUT/telemetry.html" 'About this station'
check "$OUT/telemetry.html" 'WeeWX uptime'


check_not "$OUT/index.html" 'Radio Blackout</small>'
check "$OUT/css/aurora.css" 'min-width: 1660px'
check_not "$OUT/index.html" 'id="rsg-g-max"'
check "$OUT/index.html" 'xraysLongUrl'
check "$OUT/index.html" 'protonsUrl'
check "$OUT/index.html" '>National Weather Service</a>'
check "$OUT/index.html" 'wunderground.com/dashboard/pws/KWIGILMA2'
check "$OUT/index.html" 'href="https://www.windy.com"'
check "$OUT/index.html" 'Apparent Temperature'
check "$OUT/index.html" 'Cloud Base'
check_not "$OUT/index.html" '>Solar Activity</h5>'
check_not "$OUT/index.html" 'aurora-status-card'
check_not "$OUT/index.html" 'img/aurora-borealis.svg'
check "$OUT/index.html" 'id="header-kp-badge"'
    check "$OUT/index.html" 'Kp: <span id="header-kp">'
    check "$OUT/css/aurora.css" 'justify-content: space-between'
    check "$OUT/css/aurora.css" 'gap: 0.35rem'
    check "$OUT/css/aurora.css" 'padding-top: 0.35rem'
    check "$OUT/css/aurora.css" 'padding-bottom: 0.5rem'
for p in day week month year archive; do
  check "$OUT/$p.html" 'aurora.css?v='
done
# periods.js is regenerated every report run; without a cache-buster the
# browser can serve a <=10-min-old copy (Apache max-age=600) and the
# Historical period selector shows stale date ranges (year page included).
for p in day week month year; do
  check "$OUT/$p.html" 'periods.js?v='
done
# Day + week pages use the vendored flatpickr calendar; our period-picker.js
# wires it to the generated AuroraPeriods data (cache-busted, no selects).
for p in day week; do
  check "$OUT/$p.html" 'period-picker.js?v='
  check "$OUT/$p.html" 'js/vendor/flatpickr.min.js?v='
  check "$OUT/$p.html" 'css/flatpickr.min.css?v='
  check_not "$OUT/$p.html" '<select'
done
# Month + year pages keep the plain dropdown populated client-side from
# periods.js by js.inc (flatpickr must not appear there).
for p in month year; do
  check "$OUT/$p.html" 'src="periods.js?v='
  check "$OUT/$p.html" '<select class="form-control w-auto" data-periods='
  check_not "$OUT/$p.html" 'flatpickr'
  check_not "$OUT/$p.html" 'period-picker.js'
done
check_not "$OUT/css/aurora.css" 'aurora-status-card'
check "$OUT/gallery.html" 'aurora-modal-trigger'
check "$OUT/gallery.html" 'Nightly archive'
check "$OUT/gallery.html" 'tl-calendar'
check "$OUT/gallery.html" 'tl-legend'
check "$OUT/gallery.html" 'Kp 6.3'
check "$OUT/gallery.html" 'kp-band-2'
check "$OUT/gallery.html" 'tl-month-even'
check "$OUT/gallery.html" 'tl-month-odd'
# moon phase glyphs on every in-window day; the 35-day window spans a
# full synodic month, so both a new and a full moon cell must appear
check "$OUT/gallery.html" 'tl-chip-row'
check "$OUT/gallery.html" 'tl-moon'
check "$OUT/gallery.html" 'wi wi-moon-'
check "$OUT/gallery.html" 'aria-label="Full moon"'
check "$OUT/gallery.html" 'aria-label="New moon"'
# no-thumbnail cells reserve the same 16:9 slot so all date boxes align
check "$OUT/gallery.html" 'tl-cell-ph'
check "$OUT/gallery.html" 'card-title">Latest'
check_not "$OUT/gallery.html" '>today<'
check "$OUT/solar.html" 'regions-tbody'
check "$OUT/solar.html" 'kp-forecast-chart'
check "$OUT/solar.html" 'card h-100 text-center'
check_not "$OUT/solar.html" '>Impacts</h5>'
check_not "$OUT/solar.html" 'aurora-rsg'
check "$OUT/solar.html" 'id="rsg-g-card"'
check "$OUT/solar.html" 'id="rsg-s-card"'
check "$OUT/solar.html" 'id="rsg-r-card"'
check "$OUT/solar.html" 'id="rsg-g-now"'
check "$OUT/solar.html" 'id="rsg-s-now"'
check "$OUT/solar.html" 'id="rsg-r-now"'
check "$OUT/solar.html" '"xraysLongUrl"'
check "$OUT/solar.html" '"protonsUrl"'
check "$OUT/solar.html" 'id="kp-now-card"'
check "$OUT/solar.html" 'id="kp-peak-card"'
check "$OUT/solar.html" 'F10.7 flux (sfu)'
check "$OUT/solar.html" 'class="display-4" id="f107"'
check "$OUT/js/modules/aurora.js" 'peak.toFixed(1)'
check_not "$OUT/js/modules/aurora.js" "' sfu'"
check "$OUT/solar.html" 'card-body d-flex flex-column justify-content-between'
check "$OUT/solar.html" 'id="kp-fcst-card"'
check "$OUT/solar.html" 'id="kp-fcst"'
check "$OUT/solar.html" 'Kp 24 h fcst'
check "$OUT/solar.html" 'id="bt"'
check "$OUT/solar.html" 'Bt (nT)'
check "$OUT/solar.html" 'id="density"'
check "$OUT/solar.html" 'Density (p/cm³)'
check "$OUT/solar.html" 'card kp-accent'
check "$OUT/css/aurora.css" 'kp-accent-g5'
check "$OUT/js/modules/aurora.js" 'G1 MINOR'
check "$OUT/css/aurora.css" 'rsg-accent-l5'
check "$OUT/css/aurora.css" '#6a1b9a'
# value text centers vertically in the space above the pinned label;
# kp-fcst-card gets the same Kp-scale accent as the other Kp cards
check "$OUT/css/aurora.css" '.justify-content-between > .display-4'
check "$OUT/js/modules/aurora.js" "setKpAccent('kp-fcst-card'"
# live NOAA field names (rtsw_mag_1m.json has 'bt', rtsw_wind_1m.json has
# 'proton_density') and the kp-fcst max reads normalizeKpForecast's 'v' key
check "$OUT/js/modules/aurora.js" "'bt', 'bt_gsm'"
check "$OUT/js/modules/aurora.js" "'proton_density'"
check "$OUT/js/modules/aurora.js" 'p.v > max'
check "$OUT/index.html" 'data-toggle="dropdown"'
check "$OUT/index.html" 'dropdown-item" href="day.html'
check "$OUT/index.html" '>Historical</a>'
check "$OUT/month.html" 'dropdown-item active" href="month.html'
check "$OUT/archive.html" 'dropdown-toggle active'

# period-selection dropdowns (day/week/month pages, client-populated from periods.js)
check "$OUT/day.html" 'Select a period'
check "$OUT/week.html" 'Select a period'
check "$OUT/month.html" 'Select a period'
check "$OUT/day/day-$(date +%F).html" 'Select a period'
check "$OUT/periods.js" '"days"'
check "$OUT/periods.js" '"weeks"'
check "$OUT/periods.js" '"months"'
check "$OUT/periods.js" "$(date +%Y-%m)"
for p in day week month; do
  kind=days
  [ "$p" = week ] && kind=weeks
  [ "$p" = month ] && kind=months
  check "$OUT/$p.html" "data-periods=\"$kind\""
  check "$OUT/$p.html" 'src="periods.js?v='
  check "$OUT/$p.html" 'd-flex justify-content-between align-items-center'
  check_not "$OUT/$p.html" '<option value="day-'
done
check "$OUT/year.html" 'data-periods="years"'
check "$OUT/year.html" 'src="periods.js?v='
check "$OUT/year.html" 'justify-content-between align-items-center'
check "$OUT/day/day-$(date +%F).html" 'data-periods="days"'
check "$OUT/day/day-$(date +%F).html" 'src="periods.js?v='
check "$OUT/day/day-$(date +%F).html" 'd-flex justify-content-between align-items-center'
check_not "$OUT/day/day-$(date +%F).html" '<option value="day-'
check "$OUT/day/day-$(date +%F).html" 'period-picker.js?v='
check "$OUT/day/day-$(date +%F).html" 'js/vendor/flatpickr.min.js?v='
check "$OUT/day/day-$(date +%F).html" 'css/flatpickr.min.css?v='
check_not "$OUT/day/day-$(date +%F).html" '<select'
# current week archive page: Monday-start range title (requires week_start = 0
# in every scenario conf; a Sunday week_start shifts the binder one day back)
read -r WEEKFILE WEEKTITLE <<EOF
$(.venv/bin/python -c "import datetime; t=datetime.date.today(); m=t-datetime.timedelta(days=t.weekday()); e=m+datetime.timedelta(days=6); print('week-'+m.strftime('%Y-%m-%d')+'.html', m.strftime('%b %d, %Y')+' '+chr(0x2013)+' '+e.strftime('%b %d, %Y'))")
EOF
check "$OUT/week/$WEEKFILE" "$WEEKTITLE"
check "$OUT/week/$WEEKFILE" 'period-picker.js?v='
check "$OUT/week/$WEEKFILE" 'js/vendor/flatpickr.min.js?v='
check "$OUT/week/$WEEKFILE" 'css/flatpickr.min.css?v='
check_not "$OUT/week/$WEEKFILE" '<select'
check "$OUT/year/year-$(date +%Y).html" "$(date +%Y)"
check "$OUT/year/year-$(date +%Y).html" 'data-periods="years"'
check "$OUT/year/year-$(date +%Y).html" '<select class="form-control w-auto" data-periods='
check "$OUT/year/year-$(date +%Y).html" 'src="periods.js?v='
ls "$OUT"/week/week-*.html >/dev/null || { echo "FAIL: no week/week-*.html generated"; exit 1; }
echo "ok: week/week-*.html files generated"
ls "$OUT"/day/day-*.html >/dev/null || { echo "FAIL: no day/day-*.html generated"; exit 1; }
echo "ok: day/day-*.html files generated"

run_scenario partial
check_not "$OUT/aurora.html" 'stale data'
check_not "$OUT/aurora.html" 'clearsky_chart.gif'
check_not "$OUT/aurora.html" '>Clear Sky Chart<'
check_not "$OUT/aurora.html" 'clearsky_chart.gif'
check "$OUT/gallery.html" 'Still encoding'
check "$OUT/gallery.html" 'Archive calendar not available'

run_scenario empty
check "$OUT/gallery.html" 'No timelapses found yet'

run_scenario nocam
check "$OUT/aurora.html" 'Viewing section is disabled'

echo "ALL-OK"
