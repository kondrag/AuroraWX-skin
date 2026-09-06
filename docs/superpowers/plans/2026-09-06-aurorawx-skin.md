# auroraWX Skin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build auroraWX, a WeeWX 5.x extension that forks NeoWX Material into a unified weather + aurora site driven entirely by the WeeWX report engine (spec: `docs/superpowers/specs/2026-09-06-aurorawx-skin-design.md`).

**Architecture:** Skin fork of NeoWX Material (`skins/aurorawx/`) plus a stdlib-only Python package (`bin/user/aurorawx/`) providing an `AuroraSearchList` SLE that exposes `$aurora.*` (asset scan + pipeline status) to templates. Aurora live data (NOAA SWPC) is fetched client-side by a small vanilla-JS module; camera assets are referenced in place via a web-server alias (never copied).

**Tech Stack:** WeeWX 5.x CheetahGenerator + SearchList API, Cheetah templates, ApexCharts (bundled by NeoWX), Python stdlib, pytest. Reference checkout for installing WeeWX: `/home/greg/workspace/weewx`.

**Forked-template conventions** (verified in `/home/greg/workspace/neowx-material/src/`): every page is `#encoding UTF-8` + doctype + `<body class="${Extras.Appearance.mode}-theme main-bg" ontouchstart="">` + `#attr $active_nav = '<page>'` + `#include "header.inc"` / `"footer.inc"` / `"js.inc"`. Cards are `<div class="card"><div class="card-body">…` with `h5.card-title`. Translations via `$Extras.Translations[$Extras.language].<key>`. Nav toggles via `$Extras.Header.<page>_nav_link == "yes"`.

**Environment notes:**
- WeeWX is NOT installed system-wide. Tasks install it into `.venv/` from the local checkout. All python/test commands use `.venv/bin/python` / `.venv/bin/pytest`.
- Run every command from the repo root `/home/greg/workspace/aurora-skin`.
- `dev-weewx/`, `fixtures/cam_dir/`, and `.venv/` are gitignored dev artifacts.

---

### Task 1: Scaffolding + dev environment

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
.venv/
dev-weewx/
fixtures/cam_dir/
__pycache__/
*.pyc
dist/
*.tar.gz
```

- [ ] **Step 2: Create the venv and install WeeWX + pytest from the local checkout**

```bash
python3 -m venv .venv
.venv/bin/pip install -q /home/greg/workspace/weewx pytest
```

Expected: no errors (pulls CT3, configobj, Pillow, ephem, PyMySQL, pyserial, pyusb).

- [ ] **Step 3: Verify**

```bash
.venv/bin/python -c "import weewx, Cheetah.Template, configobj; print(weewx.__version__)"
.venv/bin/weectl --help >/dev/null && echo weectl-ok
```

Expected: prints `5.2.0` (or later) and `weectl-ok`.

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: add gitignore for auroraWX dev environment"
```

---

### Task 2: Fork NeoWX Material into skins/aurorawx

**Files:**
- Create: everything under `skins/aurorawx/` (copied)
- Modify: `skins/aurorawx/skin.conf`
- Modify: `skins/aurorawx/header.inc`
- Delete: `skins/aurorawx/camera.html.tmpl`, build-only files

- [ ] **Step 1: Copy the runtime skin files**

```bash
mkdir -p skins
cp -r /home/greg/workspace/neowx-material/src skins/aurorawx
rm -rf skins/aurorawx/scss skins/aurorawx/package.json skins/aurorawx/yarn.lock
rm skins/aurorawx/camera.html.tmpl
```

(`scss/`, `package.json`, `yarn.lock` are upstream build inputs, not runtime; `camera.html.tmpl` is absorbed into the aurora hub per spec §3.)

- [ ] **Step 2: Skin identity — top of `skins/aurorawx/skin.conf`**

Find the `SKIN_NAME` / `SKIN_VERSION` scalars near the top and set:

```ini
SKIN_NAME = auroraWX
SKIN_VERSION = 1.0.0
```

- [ ] **Step 3: Nav config — `skin.conf`, `[Extras][[Header]]`**

Replace the line `camera_nav_link = yes` with:

```ini
        aurora_nav_link = yes
        gallery_nav_link = yes
        solar_nav_link = yes
```

- [ ] **Step 4: Nav markup — `skins/aurorawx/header.inc`**

Replace the whole camera block (the `#if $Extras.Header.camera_nav_link == "yes"` … matching `#end if`, around lines 102–112) with three blocks in the same style:

```cheetah
                #if $Extras.Header.aurora_nav_link == "yes"
                    #if $active_nav == 'aurora'
                    <li class="nav-item active mr-3">
                        <a class="nav-link" href="aurora.html">$Extras.Translations[$Extras.language].aurora</a>
                    </li>
                    #else
                    <li class="nav-item mr-3">
                        <a class="nav-link" href="aurora.html">$Extras.Translations[$Extras.language].aurora</a>
                    </li>
                    #end if
                #end if

                #if $Extras.Header.gallery_nav_link == "yes"
                    #if $active_nav == 'gallery'
                    <li class="nav-item active mr-3">
                        <a class="nav-link" href="gallery.html">$Extras.Translations[$Extras.language].gallery</a>
                    </li>
                    #else
                    <li class="nav-item mr-3">
                        <a class="nav-link" href="gallery.html">$Extras.Translations[$Extras.language].gallery</a>
                    </li>
                    #end if
                #end if

                #if $Extras.Header.solar_nav_link == "yes"
                    #if $active_nav == 'solar'
                    <li class="nav-item active mr-3">
                        <a class="nav-link" href="solar.html">$Extras.Translations[$Extras.language].solar</a>
                    </li>
                    #else
                    <li class="nav-item mr-3">
                        <a class="nav-link" href="solar.html">$Extras.Translations[$Extras.language].solar</a>
                    </li>
                    #end if
                #end if
```

- [ ] **Step 5: Template registration — `skin.conf`, `[CheetahGenerator][[ToDate]]`**

Find the `[[[camera]]]` block inside `[[ToDate]]` and replace it with:

```ini
        [[[aurora]]]
            template = aurora.html.tmpl
        [[[gallery]]]
            template = gallery.html.tmpl
        [[[solar]]]
            template = solar.html.tmpl
```

- [ ] **Step 6: SLE registration — `skin.conf`, directly under `[CheetahGenerator]` (before its first subsection)**

```ini
    search_list_extensions = aurorawx.searchlist.AuroraSearchList
```

- [ ] **Step 7: Translations — `skin.conf`, `[Extras][[Translations]]`**

Append to the `[[[en]]]` section (after the `hemispheres` line):

```ini
            aurora = Aurora
            gallery = Timelapses
            solar = Solar
```

Append the same three lines with the same English values to every other language section (`[[[ca]]]`, `[[[de]]]`, `[[[es]]]`, `[[[fi]]]`, `[[[fr]]]`, `[[[it]]]`) so all configured languages resolve the keys. (English placeholders are acceptable; missing keys would break rendering for that language.)

- [ ] **Step 8: Aurora config — `skin.conf`, insert immediately before the line `[CheetahGenerator]`**

```ini
    # Aurora / camera integration
    # -------------------------------------------------------------------------
    #
    [[Aurora]]

        # Directory the external capture pipeline writes into.
        # Empty disables the whole aurora section.
        cam_dir =

        # URL prefix under which the web server serves cam_dir
        # (web-server alias; this skin never copies camera files).
        cam_url = /cam

        # Local time (HH:MM) after which a still-missing night timelapse
        # means "still encoding" (night video finalizes early morning).
        night_publish_by = 07:00

        # Local time (HH:MM) after which a still-missing day timelapse
        # means "still encoding".
        day_publish_by = 19:00

        # snapshot.jpg older than this many minutes counts as stale.
        stale_after_minutes = 30

        # Client-side refresh intervals (seconds).
        snapshot_refresh_seconds = 30
        noaa_refresh_seconds = 120

        # NOAA SWPC feeds fetched by client-side JavaScript.
        kp_url = https://services.swpc.noaa.gov/json/planetary_k_index_1m.json
        wind_url = https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json
        mag_url = https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json
        xrays_url = https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json
        flux_url = https://services.swpc.noaa.gov/products/summary/10cm-flux.json
        regions_url = https://services.swpc.noaa.gov/json/solar_regions.json
```

- [ ] **Step 9: Verify the config parses and no camera references remain**

```bash
.venv/bin/python -c "import configobj; c=configobj.ConfigObj('skins/aurorawx/skin.conf'); print(c['SKIN_NAME'], c['Extras']['Aurora']['cam_url'], c['CheetahGenerator']['search_list_extensions'])"
grep -ri camera skins/aurorawx --include='*.tmpl' --include='*.inc' --include='skin.conf' || echo no-camera-refs
```

Expected: `auroraWX /cam aurorawx.searchlist.AuroraSearchList` and `no-camera-refs`.

- [ ] **Step 10: Commit**

```bash
git add skins/aurorawx
git commit -m "feat: fork neowx-material into skins/aurorawx with aurora nav and config"
```

---

### Task 3: scanner.py (TDD)

**Files:**
- Create: `bin/user/aurorawx/__init__.py`
- Create: `bin/user/aurorawx/scanner.py`
- Test: `tests/conftest.py`
- Test: `tests/test_scanner.py`

- [ ] **Step 1: Create package init and conftest**

`bin/user/aurorawx/__init__.py`:

```python
"""auroraWX support package (installed into the WeeWX user directory)."""

__version__ = "1.0.0"
```

`tests/conftest.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "user"))
```

- [ ] **Step 2: Write the failing tests**

`tests/test_scanner.py`:

```python
import os
import time

from aurorawx import scanner

NOW = 1789000000  # fixed epoch; tests are timezone-independent by construction


def make(path, mtime=None, size=1024):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def day_file_name(prefix, ext, ts):
    return "%s_%s%s" % (prefix, scanner.DAYS[time.gmtime(ts).tm_wday], ext)


def seed_week(d, prefix, ext, count=7, step=86400):
    """count files, one per day, ending 'count-1' days before NOW."""
    for i in range(count):
        ts = NOW - (count - i) * step
        make(d / day_file_name(prefix, ext, ts), mtime=ts, size=1024 * (i + 1))
```

Note: filenames use the UTC weekday of their mtime, exactly matching what the
scanner will derive back out of the mtime, so the assertions below are
timezone-independent.

```python
def test_full_directory_is_ok(tmp_path):
    seed_week(tmp_path, scanner.AURORA_PREFIX, ".mp4")
    seed_week(tmp_path, scanner.CLOUD_PREFIX, ".mp4")
    seed_week(tmp_path, scanner.SPACEWEATHER_PREFIX, ".gif")
    make(tmp_path / "snapshot.jpg", mtime=NOW - 60)
    r = scanner.scan_directory(tmp_path, now_ts=NOW)
    assert r["enabled"] is True
    assert r["status"] == scanner.OK
    assert r["snapshot"]["exists"] is True
    assert r["snapshot"]["age_minutes"] == 1
    assert r["snapshot"]["is_stale"] is False
    assert len(r["aurora_videos"]) == 7
    assert len(r["cloud_videos"]) == 7
    assert len(r["spaceweather"]) == 7


def test_lists_sorted_newest_first(tmp_path):
    seed_week(tmp_path, scanner.AURORA_PREFIX, ".mp4")
    make(tmp_path / "snapshot.jpg", mtime=NOW - 60)
    r = scanner.scan_directory(tmp_path, now_ts=NOW)
    mtimes = [e["mtime"] for e in r["aurora_videos"]]
    assert mtimes == sorted(mtimes, reverse=True)


def test_dates_come_from_mtime(tmp_path):
    ts = NOW - 3 * 86400
    name = day_file_name(scanner.AURORA_PREFIX, ".mp4", ts)
    make(tmp_path / name, mtime=ts)
    make(tmp_path / "snapshot.jpg", mtime=NOW - 60)
    r = scanner.scan_directory(tmp_path, now_ts=NOW)
    e = r["aurora_videos"][0]
    assert e["url"] == name
    assert e["date_iso"] == time.strftime("%Y-%m-%d", time.localtime(ts))
    assert e["day_name"] == time.strftime("%A", time.localtime(ts))


def test_size_mb(tmp_path):
    make(tmp_path / "CloudCam_Monday.mp4", mtime=NOW - 3600, size=3 * 1024 * 1024)
    make(tmp_path / "snapshot.jpg", mtime=NOW - 60)
    r = scanner.scan_directory(tmp_path, now_ts=NOW)
    assert r["cloud_videos"][0]["size_mb"] == 3.0


def test_empty_dir_is_no_data(tmp_path):
    r = scanner.scan_directory(tmp_path, now_ts=NOW)
    assert r["status"] == scanner.NO_DATA
    assert r["enabled"] is True
    assert r["days"] == []


def test_missing_dir_does_not_raise(tmp_path):
    r = scanner.scan_directory(tmp_path / "nope", now_ts=NOW)
    assert r["status"] == scanner.NO_DATA
    assert "error" in r


def test_missing_today_video_after_publish_is_encoding(tmp_path):
    seed_week(tmp_path, scanner.AURORA_PREFIX, ".mp4")  # newest is yesterday
    make(tmp_path / "snapshot.jpg", mtime=NOW - 60)
    # 09:00 local on the "now" day: today's night video is overdue
    lt = time.localtime(NOW)
    nine_am = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 9, 0, 0, 0, 0, -1))
    r = scanner.scan_directory(tmp_path, now_ts=nine_am)
    assert r["status"] == scanner.ENCODING


def test_stale_snapshot_outranks_encoding(tmp_path):
    seed_week(tmp_path, scanner.AURORA_PREFIX, ".mp4")
    make(tmp_path / "snapshot.jpg", mtime=NOW - 2 * 3600)
    lt = time.localtime(NOW)
    nine_am = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 9, 0, 0, 0, 0, -1))
    r = scanner.scan_directory(tmp_path, now_ts=nine_am)
    assert r["status"] == scanner.STALE


def test_snapshot_stale_flag(tmp_path):
    make(tmp_path / "snapshot.jpg", mtime=NOW - 45 * 60)
    r = scanner.scan_directory(tmp_path, now_ts=NOW, stale_minutes=30)
    assert r["snapshot"]["age_minutes"] == 45
    assert r["snapshot"]["is_stale"] is True
    assert r["status"] == scanner.STALE


def test_days_combined_view(tmp_path):
    ts1 = NOW - 2 * 86400
    ts2 = NOW - 86400
    make(tmp_path / day_file_name(scanner.AURORA_PREFIX, ".mp4", ts1), mtime=ts1)
    make(tmp_path / day_file_name(scanner.CLOUD_PREFIX, ".mp4", ts2), mtime=ts2)
    make(tmp_path / day_file_name(scanner.SPACEWEATHER_PREFIX, ".gif", ts2), mtime=ts2)
    make(tmp_path / "snapshot.jpg", mtime=NOW - 60)
    r = scanner.scan_directory(tmp_path, now_ts=NOW)
    dates = [d["date_iso"] for d in r["days"]]
    assert dates == sorted(dates, reverse=True)
    assert len(r["days"]) == 2
    assert r["days"][0]["aurora_video"] is None
    assert r["days"][0]["cloud_video"].startswith("CloudCam_")
    assert r["days"][0]["spaceweather"].startswith("SpaceWeather_")
    assert r["days"][1]["aurora_video"].startswith("AuroraCam_")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_scanner.py -v`
Expected: ERROR — `ModuleNotFoundError: No module named 'aurorawx'`.

- [ ] **Step 4: Implement `bin/user/aurorawx/scanner.py`**

```python
"""Asset discovery for the auroraWX skin.

Scans the camera directory maintained by the external capture pipeline.
The directory contract is:

  AuroraCam_<Day>.mp4      night aurora timelapse, one per weekday
  CloudCam_<Day>.mp4       day cloud timelapse, one per weekday
  SpaceWeather_<Day>.gif   daily 3-day Kp history chart
  snapshot.jpg             live all-sky image, constantly overwritten

<Day> is a capitalized weekday name (Monday..Sunday). The true date of a
file is its mtime, not the weekday name (files are overwritten weekly).

Pure stdlib, no WeeWX imports. scan_directory() never raises.
"""

import os
import time

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
AURORA_PREFIX = "AuroraCam_"
CLOUD_PREFIX = "CloudCam_"
SPACEWEATHER_PREFIX = "SpaceWeather_"
SNAPSHOT_NAME = "snapshot.jpg"

NO_DATA = "no_data"
STALE = "stale"
ENCODING = "encoding"
OK = "ok"


def _parse_hhmm(value, default_minutes):
    try:
        hh, mm = value.split(":")
        return int(hh) * 60 + int(mm)
    except (ValueError, AttributeError):
        return default_minutes


def _local_minutes_of_day(now_ts):
    lt = time.localtime(now_ts)
    return lt.tm_hour * 60 + lt.tm_min


def _media_entry(path, now_ts, today_iso):
    st = os.stat(path)
    lt = time.localtime(st.st_mtime)
    return {
        "url": os.path.basename(path),
        "mtime": int(st.st_mtime),
        "size_mb": round(st.st_size / (1024.0 * 1024.0), 1),
        "date_iso": time.strftime("%Y-%m-%d", lt),
        "day_name": time.strftime("%A", lt),
        "is_today": time.strftime("%Y-%m-%d", lt) == today_iso,
        "age_hours": round(max(0, now_ts - st.st_mtime) / 3600.0, 1),
    }


def scan_directory(cam_dir, now_ts=None, stale_minutes=30,
                   night_publish_by="07:00", day_publish_by="19:00"):
    """Scan cam_dir; return a plain-dict description of its contents.

    Keys: enabled, cam_dir, status, snapshot, aurora_videos,
    cloud_videos, spaceweather, days, and (on I/O error) error.
    URLs are bare filenames; the caller prefixes them with the configured
    web-server alias. Status priority: no_data > stale > encoding > ok.
    Never raises.
    """
    now_ts = time.time() if now_ts is None else now_ts
    today_iso = time.strftime("%Y-%m-%d", time.localtime(now_ts))
    result = {
        "enabled": True,
        "cam_dir": cam_dir,
        "status": NO_DATA,
        "snapshot": {"exists": False, "url": SNAPSHOT_NAME, "mtime": None,
                     "age_minutes": None, "is_stale": True},
        "aurora_videos": [],
        "cloud_videos": [],
        "spaceweather": [],
        "days": [],
    }
    try:
        snapshot_path = os.path.join(cam_dir, SNAPSHOT_NAME)
        if os.path.isfile(snapshot_path):
            st = os.stat(snapshot_path)
            age_minutes = int(max(0, now_ts - st.st_mtime) // 60)
            result["snapshot"] = {
                "exists": True, "url": SNAPSHOT_NAME, "mtime": int(st.st_mtime),
                "age_minutes": age_minutes,
                "is_stale": age_minutes > stale_minutes,
            }
        for name in sorted(os.listdir(cam_dir)):
            path = os.path.join(cam_dir, name)
            if not os.path.isfile(path):
                continue
            if name.startswith(AURORA_PREFIX) and name.endswith(".mp4"):
                result["aurora_videos"].append(_media_entry(path, now_ts, today_iso))
            elif name.startswith(CLOUD_PREFIX) and name.endswith(".mp4"):
                result["cloud_videos"].append(_media_entry(path, now_ts, today_iso))
            elif name.startswith(SPACEWEATHER_PREFIX) and name.endswith(".gif"):
                result["spaceweather"].append(_media_entry(path, now_ts, today_iso))
    except OSError as e:
        result["error"] = str(e)
        return result

    for key in ("aurora_videos", "cloud_videos", "spaceweather"):
        result[key].sort(key=lambda e: e["mtime"], reverse=True)

    # Combined per-day view (rolling week), newest first.
    slots = {"aurora_videos": "aurora_video", "cloud_videos": "cloud_video",
             "spaceweather": "spaceweather"}
    by_date = {}
    for key, slot in slots.items():
        for e in result[key]:
            day = by_date.setdefault(e["date_iso"], {
                "date_iso": e["date_iso"], "day_name": e["day_name"],
                "is_today": e["is_today"], "aurora_video": None,
                "cloud_video": None, "spaceweather": None})
            day[slot] = e["url"]
    result["days"] = sorted(by_date.values(),
                            key=lambda d: d["date_iso"], reverse=True)

    has_media = bool(result["aurora_videos"] or result["cloud_videos"]
                     or result["spaceweather"])
    if not has_snapshot_file(result) and not has_media:
        result["status"] = NO_DATA
    elif result["snapshot"]["is_stale"]:
        result["status"] = STALE
    else:
        night_limit = _parse_hhmm(night_publish_by, 7 * 60)
        after_publish = _local_minutes_of_day(now_ts) >= night_limit
        today_done = any(e["is_today"] for e in result["aurora_videos"])
        result["status"] = ENCODING if (after_publish and not today_done) else OK
    return result


def has_snapshot_file(result):
    return result["snapshot"]["exists"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_scanner.py -v`
Expected: all 10 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add bin/user/aurorawx tests
git commit -m "feat: aurora asset scanner with rolling-week discovery and pipeline status"
```

---

### Task 4: searchlist.py (TDD)

**Files:**
- Create: `bin/user/aurorawx/searchlist.py`
- Test: `tests/test_searchlist.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_searchlist.py`:

```python
import configobj

from aurorawx.searchlist import AuroraSearchList
from tests.test_scanner import NOW, day_file_name, make


class FakeGenerator:
    def __init__(self, skin_dict):
        self.skin_dict = skin_dict


def make_sle(cam_dir=None, cam_url="/cam"):
    cfg = configobj.ConfigObj()
    cfg["Extras"] = {"Aurora": {}}
    if cam_dir is not None:
        cfg["Extras"]["Aurora"]["cam_dir"] = str(cam_dir)
        cfg["Extras"]["Aurora"]["cam_url"] = cam_url
    return AuroraSearchList(FakeGenerator(cfg))


def test_disabled_when_no_cam_dir():
    aurora = make_sle(None).get_extension_list(None, None)[0]["aurora"]
    assert aurora["enabled"] is False
    assert aurora["status"] == "disabled"


def test_urls_get_alias_prefix(tmp_path):
    make(tmp_path / day_file_name("AuroraCam_", ".mp4", NOW - 86400), mtime=NOW - 86400)
    make(tmp_path / "snapshot.jpg", mtime=NOW - 60)
    aurora = make_sle(tmp_path, cam_url="/cam").get_extension_list(None, None)[0]["aurora"]
    assert aurora["enabled"] is True
    assert aurora["snapshot"]["url"] == "/cam/snapshot.jpg"
    assert aurora["aurora_videos"][0]["url"].startswith("/cam/AuroraCam_")
    assert aurora["days"][0]["aurora_video"].startswith("/cam/AuroraCam_")


def test_io_error_is_contained():
    aurora = make_sle("/definitely/not/a/real/dir").get_extension_list(None, None)[0]["aurora"]
    assert aurora["enabled"] is True
    assert aurora["status"] == "no_data"
```

Note: `AuroraSearchList.__init__` only reads `skin_dict`; `get_extension_list`
ignores `timespan`/`db_lookup`, so `None` is fine.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_searchlist.py -v`
Expected: FAIL/ERROR — `ModuleNotFoundError: No module named 'aurorawx.searchlist'`.

- [ ] **Step 3: Implement `bin/user/aurorawx/searchlist.py`**

```python
"""Search list extension exposing the $aurora namespace to auroraWX templates.

Registered in skins/aurorawx/skin.conf:

    [CheetahGenerator]
        search_list_extensions = aurorawx.searchlist.AuroraSearchList

The package lives in the WeeWX user directory (bin/user), which WeeWX puts
on sys.path, so imports are absolute. get_extension_list() can never raise:
any failure degrades to a no_data/disabled state (spec section 4).
"""

import weewx.cheetahgenerator

from aurorawx import scanner


class AuroraSearchList(weewx.cheetahgenerator.SearchList):

    def __init__(self, generator):
        weewx.cheetahgenerator.SearchList.__init__(self, generator)
        extras = self.generator.skin_dict.get("Extras", {})
        cfg = extras.get("Aurora", {})
        self.cam_dir = str(cfg.get("cam_dir", "") or "")
        self.cam_url = str(cfg.get("cam_url", "") or "").rstrip("/")
        self.stale_minutes = int(float(cfg.get("stale_after_minutes", 30)))
        self.night_publish_by = str(cfg.get("night_publish_by", "07:00"))
        self.day_publish_by = str(cfg.get("day_publish_by", "19:00"))

    def _abs_url(self, filename):
        if not filename:
            return None
        return "%s/%s" % (self.cam_url, filename) if self.cam_url else filename

    def get_extension_list(self, timespan, db_lookup):
        data = {
            "enabled": False, "status": "disabled", "cam_dir": self.cam_dir,
            "snapshot": {"exists": False, "url": None, "mtime": None,
                         "age_minutes": None, "is_stale": True},
            "aurora_videos": [], "cloud_videos": [], "spaceweather": [],
            "days": [],
        }
        if self.cam_dir:
            try:
                scanned = scanner.scan_directory(
                    self.cam_dir,
                    stale_minutes=self.stale_minutes,
                    night_publish_by=self.night_publish_by,
                    day_publish_by=self.day_publish_by)
                data.update(scanned)
                data["enabled"] = True
            except Exception as e:  # belt and braces: never break a report run
                data.update({"enabled": True, "status": scanner.NO_DATA,
                             "error": repr(e)})
            data["snapshot"]["url"] = self._abs_url(data["snapshot"]["url"])
            for key in ("aurora_videos", "cloud_videos", "spaceweather"):
                for entry in data[key]:
                    entry["url"] = self._abs_url(entry["url"])
            for day in data["days"]:
                for key in ("aurora_video", "cloud_video", "spaceweather"):
                    day[key] = self._abs_url(day[key])
        return [{"aurora": data}]
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `.venv/bin/pytest tests -v`
Expected: all scanner + searchlist tests PASS.

- [ ] **Step 5: Commit**

```bash
git add bin/user/aurorawx/searchlist.py tests/test_searchlist.py
git commit -m "feat: AuroraSearchList exposing \$aurora with alias-prefixed URLs"
```

---

### Task 5: aurora.js + css/aurora.css

**Files:**
- Create: `skins/aurorawx/js/modules/aurora.js`
- Create: `skins/aurorawx/css/aurora.css`

(The `js/modules/` dir already exists in the fork; the existing `copy_once = js/*, css/*` globs in `skin.conf` pick up both new files — no CopyGenerator changes needed.)

- [ ] **Step 1: Create `skins/aurorawx/js/modules/aurora.js`**

Config arrives via a `<script type="application/json" id="aurora-config">` block emitted by each aurora page (Tasks 6/8/9). `window.theme_mode` is set globally by `js.inc`.

```javascript
/* auroraWX live-data module. No dependencies. Reads its config from the
   JSON <script id="aurora-config"> block emitted by each aurora page.
   All fetches degrade silently to em-dashes on failure. */
(function () {
  'use strict';

  var cfgEl = document.getElementById('aurora-config');
  if (!cfgEl) return;
  var cfg = JSON.parse(cfgEl.textContent);
  var page = cfg.page || '';

  var QUIET = '#43a047', MODERATE = '#fdd835', ELEVATED = '#fb8c00', STORM = '#e53935';

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function lastOf(json) {
    return Array.isArray(json) ? json[json.length - 1] : json;
  }

  function pick(obj, names) {
    if (!obj) return null;
    for (var i = 0; i < names.length; i++) {
      var v = obj[names[i]];
      if (v !== undefined && v !== null && !isNaN(Number(v))) return Number(v);
    }
    return null;
  }

  function fetchJson(url) {
    return fetch(url, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function normalizeKp(json) {
    var out = [];
    (Array.isArray(json) ? json : []).forEach(function (e) {
      var kp = pick(e, ['kp_index', 'estimated_kp', 'kp']);
      if (kp === null || !e.time_tag) return;
      var t = new Date(String(e.time_tag).replace(' ', 'T') + 'Z').getTime();
      if (!isNaN(t)) out.push({ t: t, kp: kp });
    });
    out.sort(function (a, b) { return a.t - b.t; });
    return out;
  }

  /* Status rule (old-site parity): Kp>=5 storm; Kp>=4 & Bz<-5 elevated;
     Kp>=3 moderate; else quiet. */
  function badgeFor(kp, bz) {
    if (kp >= 5) return { text: 'STORM', color: STORM };
    if (kp >= 4 && bz < -5) return { text: 'ELEVATED', color: ELEVATED };
    if (kp >= 3) return { text: 'MODERATE', color: MODERATE };
    return { text: 'QUIET', color: QUIET };
  }

  function renderStatus(kpSeries, bz, wind) {
    var kp = kpSeries.length ? kpSeries[kpSeries.length - 1].kp : null;
    var b = badgeFor(kp === null ? -1 : kp, bz === null ? 0 : bz);
    setText('kp-now', kp === null ? '\u2014' : kp.toFixed(1));
    setText('bz-now', bz === null ? '\u2014' : bz.toFixed(1));
    setText('wind-now', wind === null ? '\u2014' : String(Math.round(wind)));
    setText('kp-peak', kpSeries.length
      ? String(Math.max.apply(null, kpSeries.map(function (p) { return p.kp; })))
      : '\u2014');
    var badge = document.getElementById('aurora-badge');
    if (badge) {
      badge.textContent = b.text;
      badge.style.backgroundColor = b.color;
    }
  }

  function renderKpChart(kpSeries) {
    var el = document.getElementById('kp-chart');
    if (!el || !window.ApexCharts || !kpSeries.length) return;
    var cutoff = Date.now() - 24 * 3600 * 1000;
    var data = kpSeries.filter(function (p) { return p.t >= cutoff; })
      .map(function (p) {
        return { x: p.t, y: p.kp,
                 fillColor: p.kp >= 5 ? STORM : p.kp >= 4 ? ELEVATED
                          : p.kp >= 3 ? MODERATE : QUIET };
      });
    var chart = new ApexCharts(el, {
      chart: { type: 'bar', height: 220, animations: { enabled: false } },
      theme: { mode: window.theme_mode || 'dark' },
      plotOptions: { bar: { columnWidth: '90%' } },
      dataLabels: { enabled: false },
      xaxis: { type: 'datetime' },
      yaxis: { min: 0, max: 9, tickAmount: 9 },
      series: [{ name: 'Kp', data: data }]
    });
    chart.render();
  }

  function xrayClass(flux) {
    if (flux === null) return '\u2014';
    if (flux >= 1e-4) return 'X';
    if (flux >= 1e-5) return 'M';
    if (flux >= 1e-6) return 'C';
    if (flux >= 1e-7) return 'B';
    return 'A';
  }

  function fetchSpaceWeather() {
    var bz = null, wind = null;
    var kpPromise = fetchJson(cfg.kpUrl).then(normalizeKp)
      .catch(function () { return []; });
    var magPromise = cfg.magUrl
      ? fetchJson(cfg.magUrl)
          .then(function (j) { bz = pick(lastOf(j), ['bz_gsm']); })
          .catch(function () {})
      : Promise.resolve();
    var windPromise = cfg.windUrl
      ? fetchJson(cfg.windUrl)
          .then(function (j) { wind = pick(lastOf(j), ['proton_speed', 'speed']); })
          .catch(function () {})
      : Promise.resolve();

    Promise.all([kpPromise, magPromise, windPromise]).then(function (res) {
      renderStatus(res[0], bz, wind);
      if (page === 'aurora' || page === 'solar') renderKpChart(res[0]);
    });

    if (page === 'solar') {
      fetchJson(cfg.xraysUrl).then(function (j) {
        var rows = (Array.isArray(j) ? j : []).filter(function (e) {
          return String(e.energy || '').indexOf('0.05-0.4') !== -1;
        });
        setText('xray-class', xrayClass(pick(lastOf(rows), ['obs_flux', 'flux'])));
      }).catch(function () { setText('xray-class', '\u2014'); });

      fetchJson(cfg.fluxUrl).then(function (j) {
        var f = pick(j, ['Flux', 'flux']);
        setText('f107', f === null ? '\u2014' : String(Math.round(f)) + ' sfu');
      }).catch(function () { setText('f107', '\u2014'); });

      fetchJson(cfg.regionsUrl).then(function (j) {
        var tbody = document.getElementById('regions-tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        (Array.isArray(j) ? j : []).forEach(function (r) {
          if (String(r.status || '').toLowerCase().indexOf('gone') !== -1) return;
          var tr = document.createElement('tr');
          [r.region, r.location, r.area, r.mc_class, r.c_events, r.m_events,
           r.x_events, r.status].forEach(function (v) {
            var td = document.createElement('td');
            td.textContent = (v === undefined || v === null || v === '') ? '\u2014' : v;
            tr.appendChild(td);
          });
          tbody.appendChild(tr);
        });
        if (!tbody.children.length) {
          tbody.innerHTML = '<tr><td colspan="8" class="text-muted">' +
            'No active regions reported.</td></tr>';
        }
      }).catch(function () {
        var tbody = document.getElementById('regions-tbody');
        if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="text-muted">' +
          'Region data unavailable.</td></tr>';
      });
    }
  }

  function refreshSnapshot() {
    var img = document.getElementById('snapshot-img');
    if (!img || !cfg.snapshotUrl) return;
    var sep = cfg.snapshotUrl.indexOf('?') === -1 ? '?' : '&';
    var bust = cfg.snapshotUrl + sep + 't=' + Date.now();
    var probe = new Image();
    probe.onload = function () {
      img.src = bust;
      fetch(cfg.snapshotUrl, { method: 'HEAD', cache: 'no-store' })
        .then(function (r) {
          var lm = r.headers.get('Last-Modified');
          if (lm) {
            var ageMin = Math.max(0,
              Math.round((Date.now() - new Date(lm).getTime()) / 60000));
            setText('snapshot-age', 'updated ' + ageMin + ' min ago');
          }
        }).catch(function () {});
    };
    probe.src = bust;
  }

  fetchSpaceWeather();
  setInterval(fetchSpaceWeather, (cfg.noaaRefreshSeconds || 120) * 1000);
  if (cfg.snapshotRefreshSeconds && cfg.snapshotUrl) {
    setInterval(refreshSnapshot, cfg.snapshotRefreshSeconds * 1000);
  }
})();
```

- [ ] **Step 2: Create `skins/aurorawx/css/aurora.css`**

```css
/* auroraWX additions on top of the NeoWX Material styles. */

.aurora-hero {
  position: relative;
  overflow: hidden;
}

.aurora-hero-img {
  display: block;
  width: 100%;
  max-height: 60vh;
  object-fit: cover;
}

.aurora-hero-overlay {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: .75rem 1rem;
  background: linear-gradient(transparent, rgba(0, 0, 0, .65));
  display: flex;
  align-items: center;
}

.live-badge {
  text-transform: uppercase;
  letter-spacing: .08em;
}

.aurora-badge {
  color: #fff;
  padding: .35em .8em;
  border-radius: .25rem;
  background-color: #607d8b;
}

.aurora-placeholder {
  border: 1px dashed rgba(128, 128, 128, .5);
  border-radius: .25rem;
  min-height: 160px;
}

.aurora-status-card .display-4 {
  line-height: 1;
}
```

- [ ] **Step 3: Syntax-check the JS**

```bash
node --check skins/aurorawx/js/modules/aurora.js 2>/dev/null || echo "node unavailable; skipped"
```

Expected: no output (valid) or the skip note.

- [ ] **Step 4: Commit**

```bash
git add skins/aurorawx/js/modules/aurora.js skins/aurorawx/css/aurora.css
git commit -m "feat: client-side aurora live data module and styles"
```

---

### Task 6: aurora.html.tmpl (hub page)

**Files:**
- Create: `skins/aurorawx/aurora.html.tmpl`

- [ ] **Step 1: Create the template**

```cheetah
#encoding UTF-8
## +-------------------------------------------------------------------------+
## |    aurora.html.tmpl                 Template file for "aurora" page     |
## +-------------------------------------------------------------------------+

<!DOCTYPE html>
<html lang="$Extras.language">
<head>
  <title>
    $Extras.Translations[$Extras.language].aurora | $station.location
  </title>
  #include "head.inc"
  <link rel="stylesheet" href="css/aurora.css">
</head>
<body class="${Extras.Appearance.mode}-theme main-bg" ontouchstart="">

#attr $active_nav = 'aurora'
#include "header.inc"

<script type="application/json" id="aurora-config">
{
  "page": "aurora",
  "kpUrl": "$Extras.Aurora.kp_url",
  "windUrl": "$Extras.Aurora.wind_url",
  "magUrl": "$Extras.Aurora.mag_url",
  "noaaRefreshSeconds": $int($Extras.Aurora.noaa_refresh_seconds),
  "snapshotRefreshSeconds": $int($Extras.Aurora.snapshot_refresh_seconds),
  "snapshotUrl": "$aurora.snapshot.url"
}
</script>

<main data-aurora-page="aurora">
  <div class="container-fluid d-flex-xxl">

  #if not $aurora.enabled
    <div class="row my-4">
      <div class="col-12">
        <div class="card">
          <div class="card-body text-center py-5">
            <h5 class="card-title">$Extras.Translations[$Extras.language].aurora</h5>
            <p class="card-text mb-0">
              Aurora section is disabled. Set <code>cam_dir</code> under
              <code>[Extras][[Aurora]]</code> to enable it.
            </p>
          </div>
        </div>
      </div>
    </div>
  #else

    <!-- Hero: live all-sky image -->
    <div class="row my-4">
      <div class="col-12">
        <div class="card aurora-hero">
          #if $aurora.snapshot.exists
          <img id="snapshot-img" src="$aurora.snapshot.url" class="aurora-hero-img"
               alt="Live all-sky camera">
          #else
          <div class="aurora-placeholder d-flex align-items-center justify-content-center">
            <span class="text-muted">No camera image available</span>
          </div>
          #end if
          <div class="aurora-hero-overlay">
            <span class="badge badge-danger live-badge">Live</span>
            <span class="ml-2 text-white-50" id="snapshot-age">
              #if $aurora.snapshot.exists
              updated $aurora.snapshot.age_minutes min ago
              #else
              no image
              #end if
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Activity cards -->
    <div class="row my-4">
      <div class="col-6 col-md-3 mb-3">
        <div class="card text-center">
          <div class="card-body">
            <div class="display-4" id="kp-now">&mdash;</div>
            <div class="text-muted">Kp index</div>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3 mb-3">
        <div class="card text-center">
          <div class="card-body">
            <div class="py-2"><span class="badge aurora-badge" id="aurora-badge">&hellip;</span></div>
            <div class="text-muted">Activity</div>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3 mb-3">
        <div class="card text-center">
          <div class="card-body">
            <div class="display-4" id="bz-now">&mdash;</div>
            <div class="text-muted">Bz (nT)</div>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3 mb-3">
        <div class="card text-center">
          <div class="card-body">
            <div class="display-4" id="wind-now">&mdash;</div>
            <div class="text-muted">Solar wind (km/s)</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Viewing conditions + Kp chart -->
    <div class="row my-4">
      <div class="col-12 col-lg-6 mb-3">
        <div class="card h-100">
          <div class="card-body">
            <h5 class="card-title">Viewing conditions</h5>
            <table class="table table-sm mb-0">
              <tr><td>Temperature</td><td class="text-right">$current.outTemp</td></tr>
              <tr><td>Humidity</td><td class="text-right">$current.outHumidity</td></tr>
              <tr><td>Wind</td><td class="text-right">$current.windSpeed $current.windDir.ordinal_compass</td></tr>
              <tr><td>Moon</td><td class="text-right">$almanac.moon_phase ($almanac.moon_fullness)</td></tr>
              #if $almanac.hasExtras
              <tr><td>Astro dusk</td><td class="text-right">$almanac(horizon=-6).sun.set</td></tr>
              <tr><td>Astro dawn</td><td class="text-right">$almanac(horizon=-6).sun.rise</td></tr>
              #end if
            </table>
          </div>
        </div>
      </div>
      <div class="col-12 col-lg-6 mb-3">
        <div class="card h-100">
          <div class="card-body">
            <h5 class="card-title">Kp index, last 24 hours</h5>
            <div id="kp-chart"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pipeline status + links -->
    <div class="row mb-4">
      <div class="col-12">
        <div class="card">
          <div class="card-body d-flex flex-wrap align-items-center">
            <div class="mr-auto">
              <span class="text-muted mr-2">Archive status:</span>
              #if $aurora.status == 'ok'
              <span class="badge badge-success">up to date</span>
              #elif $aurora.status == 'stale'
              <span class="badge badge-warning">stale data</span>
              #elif $aurora.status == 'encoding'
              <span class="badge badge-info">tonight's timelapse still encoding</span>
              #else
              <span class="badge badge-secondary">no data</span>
              #end if
            </div>
            <a class="btn btn-outline-light btn-sm mr-2" href="gallery.html">Timelapse gallery</a>
            <a class="btn btn-outline-light btn-sm" href="solar.html">Solar activity</a>
          </div>
        </div>
      </div>
    </div>

  #end if

  </div>
</main>

#include "footer.inc"
#include "js.inc"
<script src="js/modules/aurora.js"></script>

</body>
</html>
```

- [ ] **Step 2: Sanity checks**

```bash
grep -c 'aurora-config' skins/aurorawx/aurora.html.tmpl
grep -n 'camera.html' skins/aurorawx/aurora.html.tmpl || echo no-camera-links
```

Expected: a count `>= 1` and `no-camera-links`.

- [ ] **Step 3: Commit**

```bash
git add skins/aurorawx/aurora.html.tmpl
git commit -m "feat: aurora hub page with hero image, live activity, viewing conditions"
```

---

### Task 7: gallery.html.tmpl

**Files:**
- Create: `skins/aurorawx/gallery.html.tmpl`

- [ ] **Step 1: Create the template**

```cheetah
#encoding UTF-8
## +-------------------------------------------------------------------------+
## |    gallery.html.tmpl                Template file for "gallery" page    |
## +-------------------------------------------------------------------------+

<!DOCTYPE html>
<html lang="$Extras.language">
<head>
  <title>
    $Extras.Translations[$Extras.language].gallery | $station.location
  </title>
  #include "head.inc"
  <link rel="stylesheet" href="css/aurora.css">
</head>
<body class="${Extras.Appearance.mode}-theme main-bg" ontouchstart="">

#attr $active_nav = 'gallery'
#include "header.inc"

<main data-aurora-page="gallery">
  <div class="container-fluid d-flex-xxl">

  #if not $aurora.enabled
    <div class="row my-4">
      <div class="col-12">
        <div class="card">
          <div class="card-body text-center py-5">
            <h5 class="card-title">$Extras.Translations[$Extras.language].gallery</h5>
            <p class="card-text mb-0">
              Aurora section is disabled. Set <code>cam_dir</code> under
              <code>[Extras][[Aurora]]</code> to enable it.
            </p>
          </div>
        </div>
      </div>
    </div>
  #else
    <div class="row my-4">
      <div class="col-12">
        <h4>$Extras.Translations[$Extras.language].gallery
          <small class="text-muted ml-2">last $len($aurora.days) days</small></h4>
      </div>
    </div>

    #for $day in $aurora.days
    <div class="row my-3">
      <div class="col-12">
        <div class="card">
          <div class="card-body">
            <h5 class="card-title">$day.day_name
              <small class="text-muted ml-2">$day.date_iso
                #if $day.is_today <span class="badge badge-info ml-1">today</span> #end if
              </small>
            </h5>
            <div class="row">
              <div class="col-md-7 mb-3">
                <h6>Aurora cam</h6>
                #if $day.aurora_video
                <video controls preload="none" class="w-100 rounded">
                  <source src="$day.aurora_video" type="video/mp4">
                </video>
                #else
                <div class="aurora-placeholder d-flex align-items-center justify-content-center">
                  <span class="text-muted">Still encoding</span>
                </div>
                #end if
              </div>
              <div class="col-md-5 mb-3">
                <h6>Cloud cam</h6>
                #if $day.cloud_video
                <video controls preload="none" class="w-100 rounded">
                  <source src="$day.cloud_video" type="video/mp4">
                </video>
                #else
                <div class="aurora-placeholder d-flex align-items-center justify-content-center">
                  <span class="text-muted">Still encoding</span>
                </div>
                #end if
              </div>
              #if $day.spaceweather
              <div class="col-12">
                <h6>Space weather (3-day Kp)</h6>
                <img src="$day.spaceweather" class="img-fluid rounded"
                     alt="Kp history $day.date_iso">
              </div>
              #end if
            </div>
          </div>
        </div>
      </div>
    </div>
    #end for

    #if not $aurora.days
    <div class="row my-4">
      <div class="col-12">
        <div class="card">
          <div class="card-body text-center py-5 text-muted">
            No timelapses found yet.
          </div>
        </div>
      </div>
    </div>
    #end if
  #end if

  </div>
</main>

#include "footer.inc"
#include "js.inc"

</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add skins/aurorawx/gallery.html.tmpl
git commit -m "feat: timelapse gallery page from \$aurora.days"
```

---

### Task 8: solar.html.tmpl

**Files:**
- Create: `skins/aurorawx/solar.html.tmpl`

- [ ] **Step 1: Create the template**

```cheetah
#encoding UTF-8
## +-------------------------------------------------------------------------+
## |    solar.html.tmpl                  Template file for "solar" page      |
## +-------------------------------------------------------------------------+

<!DOCTYPE html>
<html lang="$Extras.language">
<head>
  <title>
    $Extras.Translations[$Extras.language].solar | $station.location
  </title>
  #include "head.inc"
  <link rel="stylesheet" href="css/aurora.css">
</head>
<body class="${Extras.Appearance.mode}-theme main-bg" ontouchstart="">

#attr $active_nav = 'solar'
#include "header.inc"

<script type="application/json" id="aurora-config">
{
  "page": "solar",
  "kpUrl": "$Extras.Aurora.kp_url",
  "windUrl": "$Extras.Aurora.wind_url",
  "magUrl": "$Extras.Aurora.mag_url",
  "xraysUrl": "$Extras.Aurora.xrays_url",
  "fluxUrl": "$Extras.Aurora.flux_url",
  "regionsUrl": "$Extras.Aurora.regions_url",
  "noaaRefreshSeconds": $int($Extras.Aurora.noaa_refresh_seconds),
  "snapshotRefreshSeconds": 0
}
</script>

<main data-aurora-page="solar">
  <div class="container-fluid d-flex-xxl">

    <div class="row my-4">
      <div class="col-6 col-md-2 mb-3">
        <div class="card text-center">
          <div class="card-body">
            <div class="display-4" id="kp-now">&mdash;</div>
            <div class="text-muted">Kp index</div>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-2 mb-3">
        <div class="card text-center">
          <div class="card-body">
            <div class="display-4" id="kp-peak">&mdash;</div>
            <div class="text-muted">Kp 24 h peak</div>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-2 mb-3">
        <div class="card text-center">
          <div class="card-body">
            <div class="display-4" id="bz-now">&mdash;</div>
            <div class="text-muted">Bz (nT)</div>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-2 mb-3">
        <div class="card text-center">
          <div class="card-body">
            <div class="display-4" id="wind-now">&mdash;</div>
            <div class="text-muted">Wind (km/s)</div>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-2 mb-3">
        <div class="card text-center">
          <div class="card-body">
            <div class="display-4" id="xray-class">&mdash;</div>
            <div class="text-muted">X-ray class</div>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-2 mb-3">
        <div class="card text-center">
          <div class="card-body">
            <div class="h4 py-1" id="f107">&mdash;</div>
            <div class="text-muted">F10.7 flux</div>
          </div>
        </div>
      </div>
    </div>

    <div class="row my-4">
      <div class="col-12 mb-3">
        <div class="card">
          <div class="card-body">
            <h5 class="card-title">Kp index, last 24 hours</h5>
            <div id="kp-chart"></div>
          </div>
        </div>
      </div>
      <div class="col-12">
        <div class="card">
          <div class="card-body">
            <h5 class="card-title">Active sunspot regions</h5>
            <div class="table-responsive">
              <table class="table table-sm mb-0">
                <thead>
                  <tr>
                    <th>Region</th><th>Location</th><th>Area</th><th>Mag class</th>
                    <th>C</th><th>M</th><th>X</th><th>Status</th>
                  </tr>
                </thead>
                <tbody id="regions-tbody">
                  <tr><td colspan="8" class="text-muted">Loading&hellip;
                    (requires JavaScript)</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</main>

#include "footer.inc"
#include "js.inc"
<script src="js/modules/aurora.js"></script>

</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add skins/aurorawx/solar.html.tmpl
git commit -m "feat: solar activity page with live SWPC data"
```

---

### Task 9: index.html.tmpl aurora status card

**Files:**
- Modify: `skins/aurorawx/index.html.tmpl`

- [ ] **Step 1: Insert the status card**

In `skins/aurorawx/index.html.tmpl`, find the line `<hr class="my-4 rowdivider">` (inside `<main>`, after the values row) and insert this block immediately **before** it:

```cheetah
    #if $aurora.enabled
    <div class="row my-4">
      <div class="col-12">
        <div class="card aurora-status-card">
          <div class="card-body d-flex flex-wrap align-items-center">
            <div class="mr-4 text-center">
              <div class="display-4 mb-0" id="kp-now">&mdash;</div>
              <small class="text-muted">Kp</small>
            </div>
            <div class="mr-auto">
              <span class="badge aurora-badge" id="aurora-badge">&hellip;</span>
              <div class="small text-muted mt-1">
                Bz <span id="bz-now">&mdash;</span> nT &middot;
                wind <span id="wind-now">&mdash;</span> km/s
              </div>
            </div>
            <a class="btn btn-outline-light btn-sm" href="aurora.html">Details &rarr;</a>
          </div>
        </div>
      </div>
    </div>
    #end if
```

- [ ] **Step 2: Add the config block + script**

Find the line `#include "js.inc"` (after `#include "footer.inc"`, near the end) and insert immediately **after** it:

```cheetah
<script type="application/json" id="aurora-config">
{
  "page": "index",
  "kpUrl": "$Extras.Aurora.kp_url",
  "windUrl": "$Extras.Aurora.wind_url",
  "magUrl": "$Extras.Aurora.mag_url",
  "noaaRefreshSeconds": $int($Extras.Aurora.noaa_refresh_seconds),
  "snapshotRefreshSeconds": 0
}
</script>
<script src="js/modules/aurora.js"></script>
```

- [ ] **Step 3: Verify**

```bash
grep -c 'aurora-status-card' skins/aurorawx/index.html.tmpl
grep -c 'aurora-config' skins/aurorawx/index.html.tmpl
```

Expected: `1` and `1`.

- [ ] **Step 4: Commit**

```bash
git add skins/aurorawx/index.html.tmpl
git commit -m "feat: aurora status card on current conditions page"
```

---

### Task 10: Dev WeeWX install, seeded DB, fixtures, offline report runs

**Files:**
- Create: `tools/setup_dev.sh`
- Create: `tools/make_dev_config.py`
- Create: `tools/seed_db.py`
- Create: `tools/make_fixtures.sh`
- Create: `tools/sync_dev.sh`

- [ ] **Step 1: Create `tools/make_dev_config.py`**

```python
#!/usr/bin/env python3
"""Create dev-weewx/weewx-data/weewx-<scenario>.conf files from the stock
weewx.conf template. Scenarios: full, partial, empty, nocam."""
import os

import configobj

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = os.path.join(ROOT, "dev-weewx", "weewx-data")
SRC = "/home/greg/workspace/weewx/src/weewx_data/weewx.conf"

SCENARIOS = {
    "full": os.path.join(ROOT, "fixtures", "cam_dir", "full"),
    "partial": os.path.join(ROOT, "fixtures", "cam_dir", "partial"),
    "empty": os.path.join(ROOT, "fixtures", "cam_dir", "empty"),
    "nocam": "",
}


def main():
    os.makedirs(os.path.join(DATA_ROOT, "archive"), exist_ok=True)
    for scenario, cam_dir in SCENARIOS.items():
        conf = configobj.ConfigObj(SRC)
        conf["WEEWX_ROOT"] = DATA_ROOT
        conf["Station"]["location"] = "Aurora Test Site"
        conf["Station"]["latitude"] = "45.0"
        conf["Station"]["longitude"] = "-93.0"
        conf["Station"]["altitude"] = ["300", "meter"]
        for report in ("StandardReport", "SmartphoneReport", "MobileReport",
                       "Ftp", "RSYNC"):
            if report in conf["StdReport"]:
                conf["StdReport"][report]["enable"] = "false"
        conf["StdReport"]["AuroraWXReport"] = {
            "skin": "aurorawx",
            "enable": "true",
            "Extras": {"Aurora": {"cam_dir": cam_dir, "cam_url": "/cam"}},
        }
        out = os.path.join(DATA_ROOT, "weewx-%s.conf" % scenario)
        conf.filename = out
        conf.write()
        print("wrote", out)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create `tools/seed_db.py`**

```python
#!/usr/bin/env python3
"""Seed a synthetic WeeWX archive DB (two weeks of 5-min records, US units)
for offline report testing. Idempotent: removes any previous database.
Run with .venv/bin/python (needs the weewx package)."""
import math
import os
import random
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "dev-weewx", "weewx-data", "archive", "weewx.sdb")

import weewx.manager  # noqa: E402

CONFIG = {
    "DataBindings": {"wx_binding": {
        "database": "archive_sqlite",
        "table_name": "archive",
        "manager": "weewx.manager.DaySummaryManager",
        "schema": "weewx.schemas.wview_extended.schema"}},
    "Databases": {"archive_sqlite": {"database_name": DB_PATH,
                                     "driver": "weedb.sqlite"}},
}


def record_for(ts):
    lt = time.localtime(ts)
    hour = lt.tm_hour + lt.tm_min / 60.0
    daily = math.sin((hour - 9) / 24.0 * 2 * math.pi)  # peak ~15:00 local
    temp = 46 + 16 * daily + random.uniform(-1.5, 1.5)
    hum = max(25, min(98, 70 - 20 * daily + random.uniform(-4, 4)))
    wind = max(0.0, 6 + 5 * math.sin(ts / 7200.0) + random.uniform(-2, 2))
    rain = 0.01 if random.random() < 0.03 else 0
    rad = (max(0.0, 900 * math.sin(math.pi * (hour - 6.5) / 13.0)
               + random.uniform(-20, 20)) if 6.5 < hour < 19.5 else 0.0)
    return {
        "dateTime": int(ts), "usUnits": 1, "interval": 5,
        "outTemp": round(temp, 1), "outHumidity": round(hum),
        "dewpoint": round(temp - (100 - hum) / 5.0, 1),
        "barometer": round(29.92 + 0.25 * math.sin(ts / 86400.0), 3),
        "windSpeed": round(wind, 1),
        "windGust": round(wind + random.uniform(0, 6), 1),
        "windDir": int((ts / 480) % 360), "windGustDir": int((ts / 480) % 360),
        "rain": rain, "rainRate": round(0.12 * rain * 12, 2),
        "radiation": round(rad, 1), "UV": round(max(0.0, rad / 90.0), 1),
        "inTemp": 70.5, "inHumidity": 42,
    }


def main():
    random.seed(42)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    for suffix in ("", "-journal", "-wal", "-shm"):
        try:
            os.remove(DB_PATH + suffix)
        except OSError:
            pass
    dbm = weewx.manager.open_manager_with_config(CONFIG, "wx_binding")
    end = int(time.time()) // 300 * 300
    start = end - 14 * 86400
    count = 0
    for ts in range(start, end + 1, 300):
        dbm.addRecord(record_for(ts))
        count += 1
    dbm.closeDbm()
    print("seeded %d records into %s" % (count, DB_PATH))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create `tools/make_fixtures.sh`**

```sh
#!/bin/sh
# Create the camera-directory fixtures used by the offline report tests.
set -e
cd "$(dirname "$0")/.."
FIX=fixtures/cam_dir
rm -rf "$FIX"
mkdir -p "$FIX/full" "$FIX/partial" "$FIX/empty"
touch "$FIX/empty/.keep"

for day in Monday Tuesday Wednesday Thursday Friday Saturday Sunday; do
  for pre in AuroraCam CloudCam; do
    dd if=/dev/zero of="$FIX/full/${pre}_${day}.mp4" bs=1024 count=64 2>/dev/null
  done
  dd if=/dev/zero of="$FIX/full/SpaceWeather_${day}.gif" bs=1024 count=48 2>/dev/null
done
touch -d '1 minute ago' "$FIX/full/snapshot.jpg"

OLD_DAY=$(date -d '3 days ago' +%A)
dd if=/dev/zero of="$FIX/partial/AuroraCam_${OLD_DAY}.mp4" bs=1024 count=64 2>/dev/null
dd if=/dev/zero of="$FIX/partial/CloudCam_${OLD_DAY}.mp4" bs=1024 count=64 2>/dev/null
dd if=/dev/zero of="$FIX/partial/SpaceWeather_${OLD_DAY}.gif" bs=1024 count=48 2>/dev/null
touch -d '3 days ago' "$FIX"/partial/AuroraCam_* "$FIX"/partial/CloudCam_* "$FIX"/partial/SpaceWeather_*
dd if=/dev/zero of="$FIX/partial/snapshot.jpg" bs=1024 count=48 2>/dev/null
touch -d '2 hours ago' "$FIX/partial/snapshot.jpg"

echo "fixtures created under $FIX"
```

- [ ] **Step 4: Create `tools/sync_dev.sh`**

```sh
#!/bin/sh
# Copy the skin + python package into the dev weewx-data tree (mirrors what
# `weectl extension install` would do on a real install).
set -e
cd "$(dirname "$0")/.."
DATA=dev-weewx/weewx-data
mkdir -p "$DATA/bin/user" "$DATA/skins"
rm -rf "$DATA/skins/aurorawx" "$DATA/bin/user/aurorawx"
cp -r skins/aurorawx "$DATA/skins/aurorawx"
cp -r bin/user/aurorawx "$DATA/bin/user/aurorawx"
find "$DATA" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
echo "synced skin + package into $DATA"
```

- [ ] **Step 5: Create `tools/setup_dev.sh`**

```sh
#!/bin/sh
# One-time dev bootstrap: venv (if missing), configs, seeded DB, fixtures, sync.
set -e
cd "$(dirname "$0")/.."
[ -x .venv/bin/python ] || {
  python3 -m venv .venv
  .venv/bin/pip install -q /home/greg/workspace/weewx pytest
}
.venv/bin/python tools/make_dev_config.py
.venv/bin/python tools/seed_db.py
sh tools/make_fixtures.sh
sh tools/sync_dev.sh
```

- [ ] **Step 6: Run the bootstrap**

```bash
sh tools/setup_dev.sh
```

Expected output ends with `seeded NNNN records` (N ≈ 4032), `fixtures created under fixtures/cam_dir`, `synced skin + package`.

- [ ] **Step 7: Run the report for all four scenarios**

```bash
for s in full partial empty nocam; do
  echo "=== $s ==="
  PYTHONPATH="$PWD/dev-weewx/weewx-data/bin" \
    .venv/bin/weectl report run AuroraWXReport --config="dev-weewx/weewx-data/weewx-$s.conf" || exit 1
done
```

Expected: each run completes with no tracebacks. (PYTHONPATH guarantees
`user.aurorawx` resolves; bin/user is a namespace package, matching how
WeeWX resolves `user.<name>` search-list extensions.)

- [ ] **Step 8: Verify the generated HTML per scenario**

```bash
OUT=dev-weewx/weewx-data/public_html
grep -q 'id="kp-chart"' $OUT/aurora.html
grep -q 'video/mp4' $OUT/gallery.html
grep -q 'regions-tbody' $OUT/solar.html
grep -q 'aurora-status-card' $OUT/index.html
grep -q 'Still encoding' $OUT/gallery.html          # partial: today missing
grep -q 'stale data' $OUT/aurora.html               # partial: 2 h old snapshot
grep -q 'up to date' $OUT/aurora.html               # full
grep -q 'No timelapses found yet' $OUT/gallery.html # empty
grep -q 'Aurora section is disabled' $OUT/aurora.html  # nocam
echo ALL-OK
```

Expected: `ALL-OK` (no grep failures; each line is an assertion).

- [ ] **Step 9: Optional visual check**

```bash
ln -sfn "$PWD/fixtures/cam_dir/full" dev-weewx/weewx-data/public_html/cam
(cd dev-weewx/weewx-data/public_html && ../../.venv/bin/python -m http.server 8765)
```

Browse `http://localhost:8765/aurora.html` — hero image, nav, dark mode all render (live NOAA values need internet; they degrade to em-dashes offline). Ctrl-C to stop.

- [ ] **Step 10: Measure report cycle time (regression guard)**

```bash
time PYTHONPATH="$PWD/dev-weewx/weewx-data/bin" \
  .venv/bin/weectl report run AuroraWXReport --config=dev-weewx/weewx-data/weewx-full.conf
```

Expected: completes in a few seconds (this is the per-archive-cycle cost the daemon will pay every 5 minutes).

- [ ] **Step 11: Commit**

```bash
git add tools
git commit -m "test: offline report harness with seeded synthetic DB and cam fixtures"
```

---

### Task 11: install.py, generated manifest, README

**Files:**
- Create: `install.py`
- Create: `tools/gen_install.py`
- Create: `README.md`
- Test: `tests/test_install.py`

- [ ] **Step 1: Write the failing test**

`tests/test_install.py`:

```python
import importlib.util
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_install():
    spec = importlib.util.spec_from_file_location(
        "aurorawx_install", os.path.join(ROOT, "install.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_generated_manifest_in_sync():
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "gen_install.py"), "--check"],
        capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout + r.stderr).strip()


def test_loader_lists_every_shipped_file():
    installer = load_install().loader()
    listed = set()
    for dest, files in installer.files:
        listed.update(files)
    on_disk = set()
    for base in ("bin", "skins"):
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, base)):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fn in filenames:
                if fn.endswith(".pyc"):
                    continue
                on_disk.add(os.path.relpath(os.path.join(dirpath, fn), ROOT)
                            .replace(os.sep, "/"))
    assert on_disk == listed, (on_disk - listed, listed - on_disk)


def test_installer_metadata_and_config():
    installer = load_install().loader()
    assert installer["name"] == "aurorawx"
    assert installer["version"] == "1.0.0"
    report = installer["config"]["StdReport"]["AuroraWXReport"]
    assert report["skin"] == "aurorawx"
    assert report["enable"] == "true"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_install.py -v`
Expected: FAIL/ERROR — `install.py` does not exist yet.

- [ ] **Step 3: Create `tools/gen_install.py`**

```python
#!/usr/bin/env python3
"""Regenerate the generated skin-file list inside install.py.

Run after adding/removing files under skins/aurorawx:

    python tools/gen_install.py            # rewrite
    python tools/gen_install.py --check    # exit 1 if stale (used by tests)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIN_DIR = os.path.join(ROOT, "skins", "aurorawx")
INSTALL = os.path.join(ROOT, "install.py")
BEGIN = "# --- BEGIN GENERATED SKIN FILES"
END = "# --- END GENERATED SKIN FILES ---"


def skin_files():
    out = []
    for dirpath, dirnames, filenames in os.walk(SKIN_DIR):
        dirnames.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            out.append(os.path.relpath(full, ROOT).replace(os.sep, "/"))
    return sorted(out)


def render(files):
    lines = [BEGIN + " (tools/gen_install.py) ---", "SKIN_FILES = ["]
    lines += ["    '%s'," % f for f in files]
    lines += ["]", END]
    return "\n".join(lines)


def main():
    block = render(skin_files())
    with open(INSTALL) as f:
        content = f.read()
    pre, _, rest = content.partition(BEGIN)
    _, _, post = rest.partition(END)
    new = pre + block + post
    if "--check" in sys.argv:
        if new != content:
            sys.exit("install.py skin file list is stale; run tools/gen_install.py")
        sys.exit(0)
    with open(INSTALL, "w") as f:
        f.write(new)
    print("updated %s (%d skin files)" % (INSTALL, len(skin_files())))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create `install.py`**

```python
"""auroraWX installer for WeeWX 5.x.

Install with:  weectl extension install <this-file-or-package>
Remove with:   weectl extension uninstall aurorawx
"""
from weecfg.extension import ExtensionInstaller

VERSION = "1.0.0"

# --- BEGIN GENERATED SKIN FILES (tools/gen_install.py) ---
SKIN_FILES = []
# --- END GENERATED SKIN FILES ---


def loader():
    return AuroraWXInstaller()


class AuroraWXInstaller(ExtensionInstaller):

    def __init__(self):
        super(AuroraWXInstaller, self).__init__({
            "version": VERSION,
            "name": "aurorawx",
            "description": "Material-design weather + aurora skin for WeeWX 5.x"
                           " (NeoWX Material fork with camera timelapses and"
                           " live space weather).",
            "author": "Greg",
            "author_email": "",
            "config": {
                "StdReport": {
                    "AuroraWXReport": {"skin": "aurorawx", "enable": "true"},
                },
            },
            "files": [
                ("bin/user", [
                    "bin/user/aurorawx/__init__.py",
                    "bin/user/aurorawx/scanner.py",
                    "bin/user/aurorawx/searchlist.py",
                ]),
                ("skins/aurorawx", SKIN_FILES),
            ],
        })
```

Then generate the manifest:

```bash
.venv/bin/python tools/gen_install.py
```

Expected: `updated .../install.py (N skin files)`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_install.py -v`
Expected: all 3 PASS.

- [ ] **Step 6: Create `README.md`**

```markdown
# auroraWX

A WeeWX 5.x skin that unifies [NeoWX Material](https://github.com/brewster76/fuzzy-archer)-
style weather pages with an aurora observatory section: live all-sky camera,
rolling 7-day timelapse archive, and live space-weather (NOAA SWPC) data.

auroraWX is a fork of [NeoWX Material](https://neoground.com/projects/neowx)
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
alias. Drop this convention must hold (flat directory, date = file mtime):

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
    for s in full partial empty nocam; do
      PYTHONPATH="$PWD/dev-weewx/weewx-data/bin" \
        .venv/bin/weectl report run AuroraWXReport \
        --config=dev-weewx/weewx-data/weewx-$s.conf
    done

`tools/gen_install.py` regenerates the file manifest in `install.py`
run it after adding/removing skin files; `tests/test_install.py` enforces it.

## Licenses

- auroraWX additions: MIT
- NeoWX Material (upstream): MIT, © 2020-2021 Neoground GmbH
- Bundled libraries (ApexCharts, Bootstrap, MDB, jQuery, Weather Icons,
  Rubik font): their own MIT/OFL licenses, unchanged from upstream
```

- [ ] **Step 7: Run the full test suite**

Run: `.venv/bin/pytest tests -v`
Expected: all tests PASS (scanner, searchlist, install).

- [ ] **Step 8: Commit**

```bash
git add install.py tools/gen_install.py README.md tests/test_install.py
git commit -m "feat: extension installer with generated manifest and README"
```

---

### Task 12: Packaging + install/uninstall verification

**Files:**
- Create: `dist/aurorawx-1.0.0.tar.gz` (artifact, gitignored)
- Scratch: `dev-weewx/ext-test/` (gitignored)

- [ ] **Step 1: Build the package**

```bash
git ls-files install.py bin skins -z | xargs -0 tar czf dist/aurorawx-1.0.0.tar.gz
tar tzf dist/aurorawx-1.0.0.tar.gz | head
```

Expected: archive lists `install.py`, `bin/user/aurorawx/*`, `skins/aurorawx/*` and nothing else.

- [ ] **Step 2: Create a scratch WeeWX root for the install test**

```bash
mkdir -p dev-weewx/ext-test/archive
.venv/bin/python - <<'EOF'
import configobj, os
ROOT = os.path.abspath('dev-weewx/ext-test')
conf = configobj.ConfigObj('/home/greg/workspace/weewx/src/weewx_data/weewx.conf')
conf['WEEWX_ROOT'] = ROOT
conf['Station']['location'] = 'Ext Test'
conf['Station']['latitude'] = '45.0'
conf['Station']['longitude'] = '-93.0'
for r in ('StandardReport', 'SmartphoneReport', 'MobileReport', 'Ftp', 'RSYNC'):
    if r in conf['StdReport']:
        conf['StdReport'][r]['enable'] = 'false'
conf['Databases']['archive_sqlite']['database_name'] = \
    os.path.abspath('dev-weewx/weewx-data/archive/weewx.sdb')  # reuse seeded DB
conf.filename = os.path.join(ROOT, 'weewx.conf')
conf.write()
print('scratch conf written')
EOF
```

- [ ] **Step 3: Install the extension**

```bash
.venv/bin/weectl extension install dist/aurorawx-1.0.0.tar.gz --config=dev-weewx/ext-test/weewx.conf
```

Expected: "Installing extension ... 'aurorawx'" and finishing without errors. Verify:

```bash
test -f dev-weewx/ext-test/bin/user/aurorawx/searchlist.py && echo pkg-ok
test -f dev-weewx/ext-test/skins/aurorawx/aurora.html.tmpl && echo skin-ok
grep -q 'AuroraWXReport' dev-weewx/ext-test/weewx.conf && echo conf-ok
```

- [ ] **Step 4: Run a report from the installed copy**

```bash
PYTHONPATH="$PWD/dev-weewx/ext-test/bin" \
  .venv/bin/weectl report run AuroraWXReport --config=dev-weewx/ext-test/weewx.conf
grep -q 'id="kp-chart"' dev-weewx/ext-test/public_html/aurora.html && echo report-ok
```

Expected: `report-ok` (the run uses the seeded DB and the empty default
`cam_dir`, so the page renders in its disabled state — which is also the
correct degradation behavior).

- [ ] **Step 5: Uninstall and verify clean removal**

```bash
.venv/bin/weectl extension uninstall aurorawx --config=dev-weewx/ext-test/weewx.conf
test ! -e dev-weewx/ext-test/bin/user/aurorawx && echo pkg-removed
test ! -e dev-weewx/ext-test/skins/aurorawx && echo skin-removed
grep -q 'AuroraWXReport' dev-weewx/ext-test/weewx.conf || echo conf-removed
```

Expected: all three checks pass (files and config section replayed out).

- [ ] **Step 6: Full test suite + final commit**

```bash
.venv/bin/pytest tests -v
git status --short
```

Expected: all tests PASS; working tree clean except gitignored artifacts.
If anything is dirty, commit it with a descriptive message.

---

## Self-Review (completed during plan writing)

**Spec coverage:** §3 layout → Tasks 2/3/4; §4 SLE + $aurora → Task 4; §5 pages → Tasks 6-9; §6 live data + snapshot → Task 5; §7 config → Task 2 Step 8 (+README reference table); §8 status states → Tasks 3 (unit) + 10 (scenario runs); §9 degradation matrix → Task 10 Step 8 (all four branches asserted); §10 installer/packaging → Tasks 11-12; §11 offline testing (seeded synthetic DB, three aurora-data scenarios + disabled) → Task 10; §12 performance → Task 10 Step 10; §13 README/docs → Task 11 Step 6; §14 aurora-archive-v2 unchanged → no tasks touch it (per spec: no changes needed); §15 migration notes → README "Migration" section. Cloud cover/visibility appear only when the station provides them — the hub table deliberately lists only tags every station has (spec §5).

**Placeholder scan:** none — every code step contains complete code; every run step has expected output.

**Type consistency:** scanner keys (`status`, `snapshot.exists/age_minutes/is_stale`, `days[].aurora_video/cloud_video/spaceweather`, `*.url`) match between scanner.py (Task 3), searchlist.py (Task 4), templates (Tasks 6-9), and scenario greps (Task 10). SLE registration string `aurorawx.searchlist.AuroraSearchList` (Task 2 Step 6) matches the module path (Task 4). JS config keys (`kpUrl`, `snapshotUrl`, …) match the JSON blocks in Tasks 6/8/9. Installer name `aurorawx` matches the uninstall command in Task 12.



