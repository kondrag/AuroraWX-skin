# auroraWX

A WeeWX 5.x skin that unifies NeoWX Material-style weather pages with an
aurora observatory section: live all-sky camera, rolling 7-day timelapse
archive, and live space-weather (NOAA SWPC) data.

auroraWX is a fork of [NeoWX Material](https://github.com/neoground/neowx-material)
(MIT, © Neoground GmbH); aurora additions are MIT licensed as well.
Requires WeeWX 5.x. No dependencies beyond WeeWX itself (pure stdlib Python).

## Features

- All NeoWX Material pages: current conditions, yesterday/week/month/year,
  archive + NOAA reports, almanac, telemetry, dark mode, PWA manifest
- **Aurora hub** (`aurora.html`): live all-sky snapshot, Kp/Bz/solar-wind
  activity cards, viewing conditions (temperature, humidity, wind, moon,
  astronomical darkness), 24 h Kp chart
- **Timelapse gallery** (`gallery.html`): rolling 7-day AuroraCam/CloudCam
  videos + daily Kp history images, newest first
- **Solar activity** (`solar.html`): Kp, Bz, solar wind, X-ray class, F10.7,
  active sunspot regions — all live from NOAA SWPC, refreshed every 2 min
- Aurora status card on the front page
- Degrades cleanly: disabled (no `cam_dir`), no data, stale data, or
  "still encoding" states are all handled

## How it serves camera files (important)

auroraWX never copies your timelapses. You point it at the directory your
capture pipeline writes to and publish that directory under a web-server
alias. This convention must hold (flat directory, date = file mtime):

    AuroraCam_<Day>.mp4   CloudCam_<Day>.mp4   SpaceWeather_<Day>.gif
    snapshot.jpg

### Example: nginx

    location /cam/ {
        alias /home/greg/cam/;
    }

### Example: Apache

    Alias /cam /home/greg/cam
    <Directory /home/greg/cam>
        Require all granted
    </Directory>

### Example: lighttpd

    alias.url += ( "/cam" => "/home/greg/cam" )

### Example: Caddy

    handle_path /cam/* {
        root * /home/greg/cam
        file_server
    }

## Installation

    weectl extension install aurorawx.tar.gz

Then edit `weewx.conf` (or `skins/aurorawx/skin.conf`):

    [StdReport]
        [[AuroraWXReport]]
            skin = aurorawx
            enable = true
            [[[Extras]]]
                [[[[Aurora]]]]
                    cam_dir = /home/greg/cam
                    cam_url = /cam

Restart WeeWX. Point your browser at `public_html/aurora.html`.

### Configuration reference (`[Extras][[Aurora]]`)

| Key | Default | Meaning |
|---|---|---|
| `cam_dir` | *(empty)* | Camera directory; empty disables the aurora section |
| `cam_url` | `/cam` | URL prefix of the web-server alias for `cam_dir` |
| `night_publish_by` | `07:00` | Local time after which a missing night timelapse means "still encoding" |
| `day_publish_by` | `19:00` | Same for the day timelapse |
| `stale_after_minutes` | `30` | snapshot.jpg older than this = stale |
| `snapshot_refresh_seconds` | `30` | Client-side snapshot refresh |
| `noaa_refresh_seconds` | `120` | Client-side NOAA refresh |
| `kp_url`, `wind_url`, `mag_url`, `xrays_url`, `flux_url`, `regions_url` | NOAA SWPC feeds | Override for testing/offline |

NeoWX Material options (`[Extras][[Appearance]]`, `[[Charts]]`,
`[[Translations]]`, …) all work unchanged; see the upstream README.

## Offline report generation

    weectl report run AuroraWXReport --config=/etc/weewx/weewx.conf

`weectl report run` regenerates the skin against your existing database
without the daemon (it ignores `report_timing`).

## Migration from the old aurora-archive site

1. Install auroraWX alongside the old UI and run both for one full
   7-day rotation of timelapses (one week of parallel running).
2. Confirm the gallery matches the old site's archive page for the same
   days, and that the live Kp/solar data renders.
3. Retire the old generator; remove its generated HTML from the camera
   directory. The camera files themselves stay untouched.

## Development / testing

    sh tools/setup_dev.sh          # venv + seeded synthetic DB + fixtures
    .venv/bin/pytest tests -v      # unit tests
    sh tools/sync_dev.sh           # sync skin into dev-weewx/ after edits
    sh tools/run_reports.sh        # run all 4 scenarios + assert expected output

`tools/gen_install.py` regenerates the file manifest in `install.py`;
run it after adding/removing skin files; `tests/test_install.py` enforces it.

### Building the package

    git ls-files install.py bin skins -z | xargs -0 tar czf dist/aurorawx-1.0.0.tar.gz --transform 's#^#aurorawx/#'

The archive must contain a single top-level `aurorawx/` directory (WeeWX
derives the install path from the archive's common prefix).

## Troubleshooting

- Pages missing after a report run, with a `ValueError` in the log mentioning
  `noaa_refresh_seconds`: the value in `[Extras][[Aurora]]` must be a plain
  number (e.g. `120`). A garbage value makes WeeWX skip the affected templates.
- `Aurora section is disabled`: set `cam_dir` under `[Extras][[Aurora]]`.
- Stale snapshot warnings with a fresh image: check the clock/timezone of the
  machine writing `snapshot.jpg`; staleness is mtime-based.

## Licenses

- auroraWX additions: MIT
- NeoWX Material (upstream): MIT, © 2020-2021 Neoground GmbH
- Bundled libraries (ApexCharts, Bootstrap, MDB, jQuery, Weather Icons,
  Rubik font): their own MIT/OFL licenses, unchanged from upstream
