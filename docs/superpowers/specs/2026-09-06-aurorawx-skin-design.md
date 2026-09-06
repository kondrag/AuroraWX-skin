# auroraWX — Unified WeeWX Weather + Aurora Skin

**Design document** · 2026-09-06 · Status: awaiting approval

A WeeWX 5.x skin/extension that merges the weather site (based on NeoWX Material) and the
aurora/Northern-Lights site (replacing aurora-archive-v2's web UI) into a single site
generated entirely by the WeeWX report engine. The external camera capture/encode pipeline
is untouched.

---

## 1. Decisions (user-approved during brainstorming)

| Decision | Choice |
|---|---|
| Scope of aurora section | PROMPT.md's 4 features **plus** a solar activity page. Old Moon/Observing sky-chart pages dropped (moon phase folded into viewing conditions). |
| Asset serving | Web server **alias URL** to the existing camera directory — assets referenced in place, zero copying. |
| WeeWX version | 5.x (latest). APIs verified against local repo v5.2.0+ and the 5.5 docs. |
| Skin name | **auroraWX** (skin dir `skins/aurorawx`, report `AuroraWXReport`). |
| Architecture | **Fork-and-extend NeoWX Material**; stack modernization deferred. |
| Hub layout | Variant A — hero image + stacked panels. Status card, gallery, solar mockups approved. |

## 2. Research findings (basis for the design)

**aurora-archive-v2 contains only web presentation.** The capture/encode pipeline is
external: it drops files into one flat directory (rolling 7 days, true date = file mtime):
`AuroraCam_<Day>.mp4`, `CloudCam_<Day>.mp4` (360p, 4–17 MB), `SpaceWeather_<Day>.gif`
(3-day Kp chart, ~50 KB), `snapshot.jpg` (constantly overwritten = live image). No
thumbnails, no metadata files, no stored indices — the old UI fetched NOAA SWPC (1-min Kp,
solar wind, IMF Bz) and Open-Meteo live, refreshing client-side every 2 min. License: none
found — therefore **no code is copied from it**; only the asset naming contract is reused.

**NeoWX Material (MIT, v1.11)** is skin-only (no Python): include-based Cheetah templates,
all options via `$Extras.*`, ApexCharts 3.25 + Bootstrap 4 + MDB 4, dark mode via
`<body class="{mode}-theme">` + `prefers-color-scheme`. It has **no** live-update and no
forecast mechanism — anything live is new code. Its WeeWX-4-era installer
(`from setup import ExtensionInstaller`) still works on 5.x but will be modernized.

**WeeWX 5.x mechanics** (verified in source, `~/workspace/weewx`, v5.2.0-24):
- Reports run once per **archive record** (~5 min) via `StdReport` → `POST_LOOP`
  (`engine.py:842-891`); optional per-report `report_timing` cron lines
  (`reportengine.py:188-211`, doc: [Scheduling reports](https://www.weewx.com/docs/5.5/custom/report-scheduling/)).
- `CheetahGenerator` renders `[CheetahGenerator]`-declared templates; SLEs register via
  `search_list_extensions` (`cheetahgenerator.py:175-196`). Doc:
  [Cheetah generator](https://www.weewx.com/docs/5.5/custom/cheetah-generator/),
  [Search list extensions](https://www.weewx.com/docs/5.5/custom/sle/).
- SLE contract: subclass `weewx.cheetahgenerator.SearchList`, implement
  `get_extension_list(timespan, db_lookup)`, return `[{'tag': obj}]`. Doc section
  "Extending the list" (same SLE page).
- `CopyGenerator` keys are `copy_once`/`copy_always` only; `copy_once` is first-run gated,
  no mtime checks (`reportengine.py:582-623`) — irrelevant here since assets are aliased.
- Offline testing: `weectl report run [NAME…] [--config=…] [--epoch=… | --date=… --time=…]`;
  `weectl report list`. Doc: [weectl report](https://www.weewx.com/docs/5.5/utilities/weectl-report/).
- Extensions: `install.py` with `loader()` → `weecfg.extension.ExtensionInstaller`;
  `files=[(dest, [sources])]`; uninstall replays the files list
  (`weecfg/extension.py`). Doc: [weectl extension](https://www.weewx.com/docs/5.5/utilities/weectl-extension/).
- Python 3.7–3.13 (`pyproject.toml` classifiers); the extension uses **stdlib only**.
- `$almanac` provides moon phase/illumination (PyEphem or built-in fallback); **cloud
  cover is not computed by WeeWX** — see §8.

## 3. Architecture

Fork of NeoWX Material `src/` becomes `skins/aurorawx/`; a small Python package
(`bin/user/aurorawx/`) adds the aurora data layer. Weather pages ship unchanged except:
index gains the aurora status card, nav gains three entries, and `camera.html.tmpl`'s
webcam tiles move into the aurora hub (the local-fork camera page is absorbed).

```
aurorawx/                          ← extension root (this repo)
├── install.py                     # weecfg.extension.ExtensionInstaller
├── README.md                      # install (weectl extension install), config reference,
│                                  #   web-server alias examples (nginx/apache/caddy), troubleshooting
├── bin/user/aurorawx/
│   ├── __init__.py
│   ├── scanner.py                 # asset discovery: pure stdlib, no WeeWX imports, unit-testable
│   ├── searchlist.py              # AuroraSearchList(SearchList) → exposes $aurora.*
│   └── spaceweather.py            # client-side fetch definitions + shared constants (NOAA URLs)
└── skins/aurorawx/                # fork of neowx-material src/
    ├── skin.conf                  # NeoWX [Extras] + new [Extras][[Aurora]] + 3 nav flags
    ├── index.html.tmpl …          # existing NeoWX pages + aurora status card on index
    ├── aurora.html.tmpl           # NEW hub (latest image, activity, viewing conditions)
    ├── gallery.html.tmpl          # NEW timelapse gallery
    ├── solar.html.tmpl            # NEW solar activity
    ├── js/modules/aurora.js       # NEW snapshot refresh + NOAA live fetch + Kp chart
    └── css/, js/, img/, fonts/…   # inherited (css/js additions picked up by copy_once globs)
```

**Why no custom `ReportGenerator`:** PROMPT.md asked for "a generator that discovers
aurora assets and renders pages". The stock `CheetahGenerator` already renders pages, and
discovery is one `os.scandir` — so the generator role is fulfilled by `scanner.py` +
`AuroraSearchList` feeding templates. A custom `ReportGenerator` subclass was evaluated and
rejected: it would duplicate orchestration the stock generator already handles and add a
failure surface to every report run, with zero capability gain.

## 4. Integration mechanism

**`AuroraSearchList`** (registered: `search_list_extensions = user.aurorawx.AuroraSearchList`
in `skin.conf [CheetahGenerator]`; user SLEs are appended to the default search list, so
`$almanac`, `$span`, `$Extras` etc. keep working). Instantiated once per report run; the
scan result is computed once and shared by all templates in that run:

- `$aurora.enabled` — `cam_dir` configured and readable
- `$aurora.snapshot` — `{url, age_minutes, is_stale}`
- `$aurora.aurora_videos` / `$aurora.cloud_videos` / `$aurora.spaceweather` — lists of
  `{day_name, date, url, mtime, size_mb, is_today}`, newest first (7-day rolling window,
  date from mtime — replicating the old scanner contract)
- `$aurora.status` — pipeline state: `ok` | `stale` | `no_data` | `encoding`
  (night video missing past `night_publish_by` local time)

`scanner.py` never raises: all I/O is wrapped; failures return the `no_data` state with
empty lists. Since `get_extension_list()` is called inside the report run, this guarantees
aurora problems can never crash a report cycle (PROMPT.md degradation rule).

**Configuration** — all skin options stay in the NeoWX `$Extras.*` convention:

```ini
[Extras]
    [[Header]]
        aurora_nav_link = yes      # + gallery_nav_link, solar_nav_link
    [[Aurora]]
        cam_dir = /path/to/camera/dir          # empty → aurora section renders "disabled"
        cam_url = /cam                          # web-server alias prefix for cam_dir
        night_publish_by = 07:00                # local time after which a missing night
        day_publish_by = 19:00                  #   video means "still encoding"
        stale_after_minutes = 30                # snapshot staleness threshold
        snapshot_refresh_seconds = 30           # client-side auto-refresh
        noaa_refresh_seconds = 120              # client-side space-weather refresh
        kp_url = https://services.swpc.noaa.gov/json/planetary_k_index_1m.json
        wind_url = https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json
        mag_url = https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json
```

**weewx.conf stanza** (added by the installer's `config` dict; creates its own report —
NeoWX's practice of hijacking `StandardReport` is deliberately dropped because it mutates
user config globally):

```ini
[StdReport]
    [[AuroraWXReport]]
        skin = aurorawx
        enable = true
```

## 5. Cadence & binary asset strategy

- Pages regenerate per archive record (~5 min); optional `report_timing` lines can
  throttle heavy pages. No skin logic depends on a specific interval.
- `snapshot.jpg` is referenced in place at `<cam_url>/snapshot.jpg` (stable URL the
  pipeline overwrites) and refreshed client-side with a cache-buster; JS reads the HTTP
  `Last-Modified` header to display live staleness between WeeWX runs.
- Videos/GIFs are referenced in place (`preload="none"`). No copying, no symlinks, no
  thumbnails — report runs stay O(directory listing).
- Aurora indices are fetched **client-side** (2-min JS refresh, same pattern as the old
  site). The report engine makes **no network calls** — page content is never stale in a
  way that matters, and NOAA outages cannot slow or fail a report run.

## 6. Page map

All NeoWX pages preserved (index, yesterday, week, month, year, archive + NOAA txt,
almanac, telemetry). Additions (flat URLs, consistent with NeoWX):

| Page | URL | Content |
|---|---|---|
| Aurora hub | `aurora.html` | Hero all-sky image w/ LIVE badge + auto-refresh; activity cards (Kp number, status banner, Bz, solar wind); **viewing conditions panel** — WeeWX archive data (humidity, cloud-relevant obs, visibility proxy) × live aurora indices × `$almanac` moon phase/illumination + astro-dark window; Kp 24 h ApexCharts bar chart with green/amber/red thresholds |
| Gallery | `gallery.html` | 7 rolling nights, newest first: AuroraCam + CloudCam videos + SpaceWeather GIF per day, date chips, "still encoding" placeholder row for today |
| Solar | `solar.html` | Metric cards (Kp, wind, Bz, X-ray class, F10.7), Kp history chart, active-region table |
| Status card | `index.html` | Compact Material card: Kp, status badge, Bz/wind, "Details →"; structure server-rendered, values filled by JS every 2 min; hidden when aurora disabled |

## 7. Live data & degradation

`aurora.js` fetches NOAA JSON directly (Kp 1-min, solar wind, IMF), renders Kp chart +
status coloring (Kp≥5 storm; Kp≥4 & Bz<−5 elevated; Kp≥3 moderate; else quiet), and stamps
data age. Degradation matrix:

| Condition | Behavior |
|---|---|
| `cam_dir` unset | Aurora pages render a clean "disabled — configure `[Extras][[Aurora]]`" panel; status card + nav hidden |
| Pipeline down / empty dir | `no_data` badge, empty gallery with message; report run unaffected |
| Stale assets | Badge with age ("last update 43 min ago"); content still shown |
| Today's timelapse encoding | "Tonight's timelapse is still encoding" row; gallery shows through yesterday |
| NOAA unreachable (client) | Values grey out with age label; chart gaps; static HTML unaffected |
| JavaScript disabled | Indices show "— (requires JavaScript)"; images/videos/gallery fully server-rendered |
| Any scanner/IO error | `no_data` state; report run never fails |

## 8. Viewing conditions — data notes

- Humidity, temperature, wind: archive columns via normal tags (`$current.outHumidity`, …).
- **Moon**: `$almanac.moon_phase`, `$almanac.moon_fullness`, rise/set via `$almanac` — no new code.
- **Cloud cover**: WeeWX does not compute it (verified — only `cloudbase` exists). The hub
  shows what the archive *does* have; if the station records a cloud-related field it is
  displayed, otherwise the panel omits the value rather than faking it. A `cloudcover`
  xtype is out of scope for v1.
- **Visibility**: only shown if the station records a visibility field; omitted otherwise
  (never estimated). The panel labels each value's source honestly.
- Astro-dark window: computed from `$almanac(horizon=-6)` sun rise/set (NeoWX almanac page
  already uses this API).

## 9. Performance

One `os.scandir` of ≤21 files per report run (sub-millisecond). No Pillow/ffmpeg, no
thumbnail generation, no network I/O in the engine. Report cycle time unchanged. All new
JS is plain ES6 in one module (`aurora.js`); ApexCharts reused for the Kp chart (design-system
consistency); no new third-party dependencies.

## 10. Packaging

- `install.py` → `loader()` returning `ExtensionInstaller` with `version/name/description/
  author`, `files=[('bin/user', ['bin/user/aurorawx/…']), ('skins/aurorawx', […])]`,
  `config={'StdReport': {'AuroraWXReport': {...}}}`. Import from `weecfg.extension`
  (WeeWX 5-native; the v4 `setup` shim still exists but is not used).
- Install: `weectl extension install aurorawx.tar.gz`. Uninstall replays the `files` list
  and removes the config section — clean removal, no core-file edits.
- Dark mode: inherited mechanism; aurora pages always render their hero/imagery on the
  dark palette; aurora hub forces dark-friendly card styling in both themes.

## 11. Testing plan (Phase 3)

1. Fixture camera dirs: `full/` (7×3 assets + fresh snapshot), `partial/` (missing today's
   video, stale snapshot), `empty/` — pointed at via `cam_dir` in a test weewx.conf.
2. `weectl report run AuroraWXReport` against the real archive DB for each fixture
   (three scenarios per PROMPT.md); assert all templates render, badges/states correct.
3. Serve `HTML_ROOT` locally with the alias path; check dark/light, mobile layout, no JS
   console errors, broken-link scan (videos/GIF/snapshot reachable via alias).
4. Regression: report cycle time comparison before/after (log timestamps).

## 12. Licenses

NeoWX Material is MIT → fork/derive permitted, attribution kept in README. WeeWX is
GPL-3 — the extension interacts only via documented config/SLE interfaces and ships no
WeeWX code (installer imports `weecfg.extension` at runtime on the user's install).
aurora-archive-v2 is unlicensed → no code reused; only filename/mtime conventions
replicated (facts, not copyrightable expression).

## 13. aurora-archive-v2 — proposed changes

**None required.** The repo is presentation-only; the external pipeline keeps writing the
same files to the same directory. Optional (proposal only, not implemented): document the
asset naming/mtime contract in its README so the pipeline's interface is explicit.

## 14. Migration notes (retiring the old aurora web UI)

1. Stand up auroraWX; alias `cam_url` in the web server; verify parity checklist:
   live snapshot, 7-day gallery with date navigation, live Kp/Bz/wind banner, solar page,
   mobile + dark mode.
2. Run both sites in parallel for at least one full 7-day archive rotation.
3. Retire the old UI by removing whatever cron/job invoked `aurora-archive` page
   generation (the pipeline jobs stay); optionally keep the old directory reachable
   at a legacy URL for a grace period, then remove.
4. Update bookmarks/links; the old index/solar/weather/moon/observing/archive URLs are
   replaced by `aurora.html`, `solar.html`, weather pages, and (dropped) moon/observing.

## 15. Deferred (possible future phase)

JS/CSS stack modernization (Bootstrap 5, CSS-variable theming, ApexCharts upgrade),
forecast support, cloud-cover xtype, per-user themes. None block v1.
