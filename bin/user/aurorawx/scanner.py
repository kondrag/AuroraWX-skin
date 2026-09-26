"""Asset discovery for the auroraWX skin.

Scans the camera directory maintained by the external capture pipeline.
The directory contract is:

  AuroraCam_<Day>.mp4      night aurora timelapse, one per weekday
  AuroraCam_<Day>.thumbnail.jpg   poster frame for the night timelapse
  CloudCam_<Day>.mp4       day cloud timelapse, one per weekday
  CloudCam_<Day>.thumbnail.jpg    poster frame for the day timelapse
  SpaceWeather_<Day>.gif   daily 3-day Kp history chart
  snapshot.jpg             live all-sky image, constantly overwritten

<Day> is a capitalized weekday name (Monday..Sunday). The true date of a
file is its mtime, not the weekday name (files are overwritten weekly).
Files are grouped into day cards by the weekday of their mtime; a card's
date is the most recent occurrence of that weekday, so a card can show
last week's content — flagged update_pending — until the pipeline
overwrites the files for the current week.

Pure stdlib, no WeeWX imports. scan_directory() never raises.
"""

import json
import math
import os
import re
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
AURORA_PREFIX = "AuroraCam_"
CLOUD_PREFIX = "CloudCam_"
SPACEWEATHER_PREFIX = "SpaceWeather_"
SNAPSHOT_NAME = "snapshot.jpg"
THUMB_SUFFIX = ".thumbnail.jpg"

ARCHIVE_SUBDIR = "d"
DEFAULT_CALENDAR_DAYS = 35
DATE_DIR_RE = re.compile(r"^\d{8}$")

# "latest" staging links (refreshed every pipeline run): always point at
# the most recent archived asset regardless of the 7-day weekday rotation.
AURORA_LATEST_VIDEO = "AuroraCam_latest.mp4"
AURORA_LATEST_THUMB = "AuroraCam_latest.thumbnail.jpg"
CLOUD_LATEST_VIDEO = "CloudCam_latest.mp4"
CLOUD_LATEST_THUMB = "CloudCam_latest.thumbnail.jpg"
SPACEWEATHER_LATEST = "SpaceWeather_latest.gif"
LATEST_NAMES = (AURORA_LATEST_VIDEO, AURORA_LATEST_THUMB,
                CLOUD_LATEST_VIDEO, CLOUD_LATEST_THUMB,
                SPACEWEATHER_LATEST)
# Compactly describes the latest-card slots: (video slot, video file,
# thumb slot or None, thumb file or None, size slots, mtime slot,
# pending slot, unit). Mirrors the day-card slot_specs asymmetry where
# "spaceweather" is an image (KB), not a video (MB).
LATEST_SPECS = (
    ("aurora_video", AURORA_LATEST_VIDEO, "aurora_thumbnail",
     AURORA_LATEST_THUMB, ("aurora_size_mb",), "aurora_mtime",
     "aurora_pending", "mb"),
    ("cloud_video", CLOUD_LATEST_VIDEO, "cloud_thumbnail",
     CLOUD_LATEST_THUMB, ("cloud_size_mb",), "cloud_mtime",
     "cloud_pending", "mb"),
    ("spaceweather", SPACEWEATHER_LATEST, None, None,
     ("spaceweather_size_mb", "spaceweather_size_kb"), "spaceweather_mtime",
     "spaceweather_pending", "kb"),
)
DATE_COMPACT_RE = re.compile(r"(20\d{6})")

# Night-window defaults: observer location, mirrors the timelapse
# generator's night_upload.py (scripts/sun.py convention).
DEFAULT_LATITUDE = 45.1666
DEFAULT_LONGITUDE = -90.8076
DEFAULT_TZ_NAME = "America/Chicago"
NAUTICAL_ZENITH = 102.0  # 90 + 12 degrees depression
KP_FILE_FMT = "k-index_%s.json"
NOAA_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Color bands mirror the SWPC planetary K-index chart zones (peak Kp is
# banded by the same thresholds SWPC uses to color its bars; labels are
# the NOAA G-scale). Hex colors live in css/aurora.css as .kp-band-<n>.
KP_BANDS = (
    {"max_kp": 4.33, "label": "Kp < 5  Quiet", "css": "kp-band-0"},
    {"max_kp": 5.33, "label": "Kp 5  G1 Minor", "css": "kp-band-1"},
    {"max_kp": 6.33, "label": "Kp 6  G2 Moderate", "css": "kp-band-2"},
    {"max_kp": 7.33, "label": "Kp 7  G3 Strong", "css": "kp-band-3"},
    {"max_kp": 8.67, "label": "Kp 8  G4 Severe", "css": "kp-band-4"},
    {"max_kp": 9.01, "label": "Kp 9  G5 Extreme", "css": "kp-band-5"},
)

DEFAULT_CAMERAS = ({"key": "sky", "label": "Sky camera",
                    "image": SNAPSHOT_NAME},)

NO_DATA = "no_data"
STALE = "stale"
ENCODING = "encoding"
OK = "ok"


def _parse_hhmm(value, default_minutes):
    try:
        hh, mm = value.split(":")
        hh, mm = int(hh), int(mm)
    except (ValueError, AttributeError):
        return default_minutes
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return default_minutes
    return hh * 60 + mm


def _local_minutes_of_day(now_ts):
    lt = time.localtime(now_ts)
    return lt.tm_hour * 60 + lt.tm_min


def _thumb_for(url, thumbs):
    """Thumbnail filename matching a video url, or None if absent."""
    candidate = os.path.splitext(url)[0] + THUMB_SUFFIX
    return candidate if candidate in thumbs else None


def _file_mtime(cam_dir, name):
    """mtime of cam_dir/name, or None when name is None/unreadable."""
    if not name:
        return None
    try:
        return int(os.stat(os.path.join(cam_dir, name)).st_mtime)
    except OSError:
        return None


def _most_recent_weekday_midnight(now_ts, wday):
    """Epoch of local midnight for the most recent occurrence of wday."""
    lt = time.localtime(now_ts)
    days_back = (lt.tm_wday - wday) % 7
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday - days_back,
                        0, 0, 0, 0, 0, -1))


def _media_entry(path, now_ts, today_iso):
    st = os.stat(path)
    lt = time.localtime(st.st_mtime)
    return {
        "url": os.path.basename(path),
        "mtime": int(st.st_mtime),
        "size_mb": round(st.st_size / (1024.0 * 1024.0), 1),
        "size_kb": int(round(st.st_size / 1024.0)),
        "date_iso": time.strftime("%Y-%m-%d", lt),
        "day_name": DAYS[lt.tm_wday],
        "is_today": time.strftime("%Y-%m-%d", lt) == today_iso,
        "age_hours": round(max(0, now_ts - st.st_mtime) / 3600.0, 1),
    }


def _normalize_camera(cam):
    """Coerce one cameras config entry to {key, label, image}."""
    if not isinstance(cam, dict):
        return dict(DEFAULT_CAMERAS[0])
    image = str(cam.get("image", "") or "")
    key = str(cam.get("key", "") or "")
    if not key:
        key = os.path.splitext(image)[0].lower() or "sky"
    return {"key": key, "label": str(cam.get("label", "") or key),
            "image": image}


def _missing_camera(cam):
    return {
        "key": cam["key"],
        "label": cam.get("label", cam["key"]),
        "image": cam["image"],
        "exists": False, "url": cam["image"], "mtime": None,
        "age_minutes": None, "is_stale": True,
    }


def scan_directory(cam_dir, now_ts=None, stale_minutes=30,
                   night_publish_by="07:00", day_publish_by="19:00",
                   cameras=None, clearsky_chart="clearsky_chart.gif"):
    """Scan cam_dir; return a plain-dict description of its contents.

    Keys: enabled, cam_dir, status, snapshot, cameras, clearsky_chart,
    aurora_videos, cloud_videos, spaceweather, days, and (on I/O error)
    error. URLs are bare filenames; the caller prefixes them with the
    configured web-server alias. Status priority: no_data > stale >
    encoding > ok. cameras is a list of {key, label, image} dicts; the
    first camera doubles as the legacy "snapshot" entry and drives
    staleness status. clearsky_chart names the Clear Sky Chart image
    written by the external pipeline; "" disables it.
    Never raises.
    """
    now_ts = time.time() if now_ts is None else now_ts
    if cameras is None:
        cameras = DEFAULT_CAMERAS
    cameras = [_normalize_camera(c) for c in cameras] or \
        list(DEFAULT_CAMERAS)
    today_iso = time.strftime("%Y-%m-%d", time.localtime(now_ts))
    first = _missing_camera(cameras[0])
    result = {
        "enabled": True,
        "cam_dir": str(cam_dir) if cam_dir else "",
        "status": NO_DATA,
        "snapshot": {"exists": False, "url": first["image"], "mtime": None,
                     "age_minutes": None, "is_stale": True},
        "cameras": [_missing_camera(c) for c in cameras],
        "clearsky_chart": {
            "exists": False, "url": clearsky_chart or "", "mtime": None,
            "age_minutes": None, "is_stale": True,
        },
        "aurora_videos": [],
        "cloud_videos": [],
        "spaceweather": [],
        "days": [],
        "latest": None,
    }
    if not cam_dir:
        result["error"] = "camera directory not configured"
        return result
    try:
        for idx, (cam, entry) in enumerate(zip(cameras, result["cameras"])):
            # a file may vanish between isfile and stat; degrade to the
            # missing default instead of aborting the whole report
            try:
                if cam["image"]:
                    path = os.path.join(cam_dir, cam["image"])
                    if os.path.isfile(path):
                        st = os.stat(path)
                        age_minutes = int(max(0, now_ts - st.st_mtime) // 60)
                        entry.update({
                            "exists": True, "url": cam["image"],
                            "mtime": int(st.st_mtime),
                            "age_minutes": age_minutes,
                            "is_stale": age_minutes > stale_minutes,
                        })
            except OSError:
                pass
            if idx == 0:
                result["snapshot"] = dict(entry)
        if clearsky_chart:
            try:
                path = os.path.join(cam_dir, clearsky_chart)
                if os.path.isfile(path):
                    st = os.stat(path)
                    age_minutes = int(max(0, now_ts - st.st_mtime) // 60)
                    result["clearsky_chart"].update({
                        "exists": True, "url": clearsky_chart,
                        "mtime": int(st.st_mtime),
                        "age_minutes": age_minutes,
                        "is_stale": age_minutes > stale_minutes,
                    })
            except OSError:
                pass
        thumbs = set()
        for name in sorted(os.listdir(cam_dir)):
            path = os.path.join(cam_dir, name)
            if not os.path.isfile(path):
                continue
            if name in LATEST_NAMES:
                continue
            # a file may vanish (or briefly lock) between isfile and stat;
            # skip it instead of aborting the whole report
            try:
                if name.startswith(AURORA_PREFIX) and name.endswith(".mp4"):
                    result["aurora_videos"].append(_media_entry(path, now_ts, today_iso))
                elif name.startswith(CLOUD_PREFIX) and name.endswith(".mp4"):
                    result["cloud_videos"].append(_media_entry(path, now_ts, today_iso))
                elif name.startswith(SPACEWEATHER_PREFIX) and name.endswith(".gif"):
                    result["spaceweather"].append(_media_entry(path, now_ts, today_iso))
                elif (name.endswith(THUMB_SUFFIX)
                      and (name.startswith(AURORA_PREFIX)
                           or name.startswith(CLOUD_PREFIX))):
                    thumbs.add(name)
            except OSError:
                continue
    except OSError as e:
        result["error"] = str(e)
        return result

    for key in ("aurora_videos", "cloud_videos", "spaceweather"):
        result[key].sort(key=lambda e: e["mtime"], reverse=True)
    for entry in result["aurora_videos"] + result["cloud_videos"]:
        entry["thumbnail"] = _thumb_for(entry["url"], thumbs)
        entry["thumbnail_mtime"] = _file_mtime(cam_dir,
                                               entry["thumbnail"])

    # Combined per-day view: one card per weekday seen in the directory,
    # newest card first. A card's date is the most recent occurrence of
    # that weekday, so an asset whose mtime predates the card date is
    # last week's content and is flagged update_pending. The
    # "spaceweather" slot holds the chart filename, not a video — the
    # naming asymmetry with the *_video slots is intentional.
    slot_specs = (
        ("aurora_videos", "aurora_video", "aurora_thumbnail",
         "aurora_size_mb", "aurora_mtime", "aurora_pending"),
        ("cloud_videos", "cloud_video", "cloud_thumbnail",
         "cloud_size_mb", "cloud_mtime", "cloud_pending"),
        ("spaceweather", "spaceweather", None,
         "spaceweather_size_mb", "spaceweather_mtime",
         "spaceweather_pending"),
    )
    by_weekday = {}
    for key, slot, thumb_slot, size_slot, mtime_slot, pending_slot in slot_specs:
        for e in result[key]:  # lists iterate newest-first: keep newest
            lt = time.localtime(e["mtime"])
            card_ts = _most_recent_weekday_midnight(now_ts, lt.tm_wday)
            day = by_weekday.setdefault(lt.tm_wday, {
                "date_iso": time.strftime("%Y-%m-%d",
                                          time.localtime(card_ts)),
                "day_name": DAYS[lt.tm_wday],
                "is_today": today_iso == time.strftime("%Y-%m-%d",
                                                       time.localtime(card_ts)),
                "aurora_video": None, "aurora_thumbnail": None,
                "aurora_thumbnail_mtime": None,
                "aurora_size_mb": None, "aurora_mtime": None,
                "aurora_pending": False,
                "cloud_video": None, "cloud_thumbnail": None,
                "cloud_thumbnail_mtime": None,
                "cloud_size_mb": None, "cloud_mtime": None,
                "cloud_pending": False,
                "spaceweather": None, "spaceweather_size_mb": None,
                "spaceweather_size_kb": None,
                "spaceweather_mtime": None, "spaceweather_pending": False})
            if day[slot] is None:
                day[slot] = e["url"]
                if thumb_slot:
                    day[thumb_slot] = e["thumbnail"]
                    day[thumb_slot + "_mtime"] = e["thumbnail_mtime"]
                day[size_slot] = e["size_mb"]
                if slot == "spaceweather":
                    day["spaceweather_size_kb"] = e["size_kb"]
                day[mtime_slot] = e["mtime"]
                day[pending_slot] = e["mtime"] < card_ts
    result["days"] = sorted(by_weekday.values(),
                            key=lambda d: d["date_iso"], reverse=True)
    result["latest"] = _latest_card(cam_dir, now_ts, today_iso)

    has_media = bool(result["aurora_videos"] or result["cloud_videos"]
                     or result["spaceweather"])
    if not has_snapshot_file(result) and not has_media:
        result["status"] = NO_DATA
    elif result["snapshot"]["is_stale"]:
        result["status"] = STALE
    else:
        today_aurora = any(e["is_today"] for e in result["aurora_videos"])
        today_cloud = any(e["is_today"] for e in result["cloud_videos"])
        minutes = _local_minutes_of_day(now_ts)
        night_pending = (minutes >= _parse_hhmm(night_publish_by, 7 * 60)
                         and not today_aurora)
        day_pending = (minutes >= _parse_hhmm(day_publish_by, 19 * 60)
                       and not today_cloud)
        result["status"] = ENCODING if (night_pending or day_pending) else OK
    return result


def has_snapshot_file(result):
    return result["snapshot"]["exists"]


def _latest_date_iso(cam_dir, now_ts):
    """Anchor date for the latest card: YYYYMMDD found in a latest
    link's resolved target path, else that file's mtime date."""
    for _slot, name, *_rest in LATEST_SPECS:
        path = os.path.join(cam_dir, name)
        if not os.path.exists(path):
            continue
        target = os.path.realpath(path)
        m = DATE_COMPACT_RE.search(target)
        if m:
            c = m.group(1)
            ts = time.mktime((int(c[:4]), int(c[4:6]), int(c[6:8]),
                              12, 0, 0, 0, 0, -1))
            return time.strftime("%Y-%m-%d", time.localtime(ts))
        try:
            st = os.stat(path)
        except OSError:
            continue
        return time.strftime("%Y-%m-%d", time.localtime(st.st_mtime))
    return None


def _latest_card(cam_dir, now_ts, today_iso):
    """Card for the newest available assets, from the *_latest staging
    links. Same key set as a day card, plus latest=True; None when the
    pipeline has staged no latest links yet."""
    card = {
        "date_iso": None, "day_name": None,
        "is_today": False, "latest": True,
        "aurora_video": None, "aurora_thumbnail": None,
        "aurora_thumbnail_mtime": None, "aurora_size_mb": None,
        "aurora_mtime": None, "aurora_pending": False,
        "cloud_video": None, "cloud_thumbnail": None,
        "cloud_thumbnail_mtime": None, "cloud_size_mb": None,
        "cloud_mtime": None, "cloud_pending": False,
        "spaceweather": None, "spaceweather_size_mb": None,
        "spaceweather_size_kb": None, "spaceweather_mtime": None,
        "spaceweather_pending": False,
    }
    found = False
    for slot, name, thumb_slot, thumb_name, size_slots, mtime_slot, \
            pending_slot, unit in LATEST_SPECS:
        path = os.path.join(cam_dir, name)
        try:
            if not os.path.isfile(path):
                continue
            st = os.stat(path)
        except OSError:
            continue
        found = True
        card[slot] = name
        card[mtime_slot] = int(st.st_mtime)
        if unit == "mb":
            card[size_slots[0]] = round(st.st_size / (1024 * 1024), 1)
        else:
            card[size_slots[0]] = round(st.st_size / (1024 * 1024), 1)
            card[size_slots[1]] = int(st.st_size // 1024)
        if thumb_slot:
            thumb_path = os.path.join(cam_dir, thumb_name)
            if os.path.isfile(thumb_path):
                card[thumb_slot] = thumb_name
                try:
                    card[thumb_slot + "_mtime"] = int(os.stat(thumb_path).st_mtime)
                except OSError:
                    pass
        # latest links are refreshed every pipeline run, so an asset is
        # by definition current: pending never applies
        card[pending_slot] = False
    if not found:
        return None
    iso = _latest_date_iso(cam_dir, now_ts)
    if iso is None:
        iso = today_iso
    card["date_iso"] = iso
    try:
        wday = time.strptime(iso, "%Y-%m-%d").tm_wday
        card["day_name"] = DAYS[wday]
    except ValueError:
        pass
    card["is_today"] = iso == today_iso
    return card


def _iso(date_compact):
    return "%s-%s-%s" % (date_compact[:4], date_compact[4:6],
                         date_compact[6:8])


def _shift_compact(date_compact, days):
    """date_compact shifted by whole days (local time, noon anchor)."""
    lt = time.strptime(date_compact, "%Y%m%d")
    t = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday + days,
                     12, 0, 0, 0, 0, -1))
    return time.strftime("%Y%m%d", time.localtime(t))


def _out_cell(date_compact, today_iso):
    """Date-only placeholder cell outside the history window."""
    iso = _iso(date_compact)
    return {
        "date_iso": iso,
        "date_compact": date_compact,
        "day_name": time.strftime("%A", time.strptime(iso, "%Y-%m-%d")),
        "day_of_month": date_compact[6:8].lstrip("0") or "0",
        "is_today": iso == today_iso,
        "in_window": False,
        "aurora_video": None, "aurora_thumbnail": None,
        "aurora_mtime": None,
        "cloud_video": None, "cloud_thumbnail": None, "cloud_mtime": None,
        "spaceweather": None, "spaceweather_mtime": None,
        "kp_peak": None, "kp_text": None, "kp_level": None, "kp_css": "",
    }


def _archive_file(sub_dir, name):
    """(path exists, mtime) for sub_dir/name; missing files yield (False, None)."""
    path = os.path.join(sub_dir, name)
    try:
        return os.path.isfile(path), int(os.stat(path).st_mtime)
    except OSError:
        return False, None


def _archive_cell(sub_dir, date_compact, today_iso,
                  latitude, longitude, tz_name):
    """Calendar cell for one archived date; cam_dir-relative asset paths."""
    day_dir = os.path.join(sub_dir, date_compact)
    iso = _iso(date_compact)
    cell = {
        "date_iso": iso,
        "date_compact": date_compact,
        "day_name": time.strftime("%A", time.strptime(iso, "%Y-%m-%d")),
        "day_of_month": date_compact[6:8].lstrip("0") or "0",
        "is_today": iso == today_iso,
        "in_window": True,
        "aurora_video": None, "aurora_thumbnail": None,
        "aurora_mtime": None,
        "cloud_video": None, "cloud_thumbnail": None, "cloud_mtime": None,
        "spaceweather": None, "spaceweather_mtime": None,
        "kp_peak": None, "kp_text": None, "kp_level": None, "kp_css": "",
    }

    def set_asset(slot, thumb_slot, mtime_slot, name, thumb_name):
        exists, mtime = _archive_file(day_dir, name)
        if exists:
            cell[slot] = "%s/%s/%s" % (ARCHIVE_SUBDIR, date_compact, name)
            cell[mtime_slot] = mtime
            if thumb_slot:
                thumb_exists, _ = _archive_file(day_dir, thumb_name)
                if thumb_exists:
                    cell[thumb_slot] = "%s/%s/%s" % (ARCHIVE_SUBDIR,
                                                     date_compact, thumb_name)

    set_asset("aurora_video", "aurora_thumbnail", "aurora_mtime",
              "AuroraCam_%s_640x360.mp4" % date_compact,
              "AuroraCam_%s%s" % (date_compact, THUMB_SUFFIX))
    set_asset("cloud_video", "cloud_thumbnail", "cloud_mtime",
              "CloudCam_%s_640x360.mp4" % date_compact,
              "CloudCam_%s%s" % (date_compact, THUMB_SUFFIX))
    set_asset("spaceweather", None, "spaceweather_mtime",
              "SpaceWeather_%s.gif" % date_compact, None)

    day = datetime.strptime(iso, "%Y-%m-%d").date()
    window = night_window_utc(day, latitude, longitude, tz_name)
    kp_peak = _kp_peak_for(sub_dir, date_compact, window)
    if kp_peak is not None:
        cell["kp_peak"] = kp_peak
        cell["kp_text"] = "%.1f" % kp_peak
        level = kp_level(kp_peak)
        cell["kp_level"] = level
        band = kp_band(kp_peak)
        cell["kp_css"] = KP_BANDS[band]["css"] if band is not None else ""
    return cell


def kp_level(kp):
    """NOAA Kp band (0..9) for a peak Kp value: round-half-up, clamped.

    Band centers are the integers; SWPC colors 4.67 ("5-") and 5.33
    ("5+") with the Kp-5 band, so round-half-up reproduces the official
    10-color scale. Returns None for non-numeric input.
    """
    try:
        kp = float(kp)
    except (TypeError, ValueError):
        return None
    return max(0, min(9, int(math.floor(kp + 0.5))))


def kp_band(kp):
    """SWPC color-band index (0..5) for a peak Kp value; None if not numeric.

    Thresholds match the zones on SWPC's planetary K-index chart:
    <=4.33 green, <=5.33 yellow, <=6.33 light orange, <=7.33 orange,
    <=8.67 red, else dark red.
    """
    try:
        kp = float(kp)
    except (TypeError, ValueError):
        return None
    for idx, band in enumerate(KP_BANDS):
        if kp <= band["max_kp"]:
            return idx
    return len(KP_BANDS) - 1


def _julian_century(year, month, day):
    y, m = year, month
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + day + b - 1524.5
    return (jd - 2451545.0) / 36525.0


def _sun_declination_and_equation_of_time(year, month, day):
    """NOAA solar calculator: (declination degrees, equation-of-time minutes)."""
    t = _julian_century(year, month, day)
    l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360.0
    m = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    c = (math.sin(math.radians(m)) * (1.914602 - t * (0.004817 + 0.000014 * t))
         + math.sin(math.radians(2 * m)) * (0.019993 - 0.000101 * t)
         + math.sin(math.radians(3 * m)) * 0.000289)
    true_long = l0 + c
    app_long = (true_long - 0.00569
                - 0.00478 * math.sin(math.radians(125.04 - 1934.136 * t)))
    mean_obliq = 23.0 + (26.0 + (21.448 - t * (46.815 + t * (0.00059
                          - t * 0.001813))) / 60.0) / 60.0
    obliq = mean_obliq + 0.00256 * math.cos(math.radians(125.04 - 1934.136 * t))
    decl = math.degrees(math.asin(math.sin(math.radians(obliq))
                                  * math.sin(math.radians(app_long))))
    var_y = math.tan(math.radians(obliq / 2.0)) ** 2
    eot = 4.0 * math.degrees(
        var_y * math.sin(2 * math.radians(l0))
        - 2 * e * math.sin(math.radians(m))
        + 4 * e * var_y * math.sin(math.radians(m)) * math.cos(2 * math.radians(l0))
        - 0.5 * var_y * var_y * math.sin(4 * math.radians(l0))
        - 1.25 * e * e * math.sin(2 * math.radians(m)))
    return decl, eot


def _tz_minutes_east(tz, year, month, day):
    """Local-UTC offset minutes for noon on the date, honoring DST."""
    if tz is not None:
        naive = datetime(year, month, day, 12)
        offset = naive.replace(tzinfo=tz).utcoffset()
        if offset is not None:
            return int(offset.total_seconds() // 60)
    lt = time.mktime((year, month, day, 12, 0, 0, 0, 0, -1))
    return int(time.localtime(lt).tm_gmtoff or 0) // 60


def _local_to_epoch(tz, year, month, day, minutes):
    naive = datetime(year, month, day) + timedelta(minutes=minutes)
    if tz is not None:
        return naive.replace(tzinfo=tz).timestamp()
    return time.mktime((naive.year, naive.month, naive.day,
                        naive.hour, naive.minute, naive.second, 0, 0, -1))


def night_window_utc(day, latitude=DEFAULT_LATITUDE,
                     longitude=DEFAULT_LONGITUDE,
                     tz_name=DEFAULT_TZ_NAME):
    """Nautical dusk on day-1 through nautical dawn on day, UTC epochs.

    Mirrors the timelapse generator's night_upload.night_window (astral,
    Depression.NAUTICAL); computed with the NOAA solar equations to keep
    the scanner stdlib-only. Falls back to the system zone when tz_name
    is unknown. Returns (start_epoch, end_epoch).
    """
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = None
    y, m, d = day.year, day.month, day.day
    prev = day - timedelta(days=1)

    def twilight(year, month, day_, evening):
        decl, eot = _sun_declination_and_equation_of_time(year, month, day_)
        # per-date UTC offset: dusk and dawn can straddle a DST change
        tz_off = _tz_minutes_east(tz, year, month, day_)
        noon = 720.0 - 4.0 * longitude - eot + tz_off
        cos_h = ((math.cos(math.radians(NAUTICAL_ZENITH))
                  - math.sin(math.radians(latitude)) * math.sin(math.radians(decl)))
                 / (math.cos(math.radians(latitude)) * math.cos(math.radians(decl))))
        cos_h = max(-1.0, min(1.0, cos_h))  # polar day/night degenerate case
        ha = 4.0 * math.degrees(math.acos(cos_h))
        return _local_to_epoch(tz, year, month, day_,
                               noon + ha if evening else noon - ha)

    start = twilight(prev.year, prev.month, prev.day, evening=True)
    end = twilight(y, m, d, evening=False)
    return start, end


def _load_kp_samples(path):
    """Leniently parse a k-index_<date>.json file into (utc_epoch, kp).

    Malformed files and rows are skipped: a calendar cell must render
    even when NOAA's product format hiccups. Never raises.
    """
    try:
        with open(path, "r") as f:
            rows = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            when = datetime.strptime(str(row["time_tag"]),
                                     NOAA_TIME_FORMAT).replace(
                tzinfo=timezone.utc)
            out.append((when.timestamp(), float(row["Kp"])))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _kp_peak_for(sub_dir, date_compact, window):
    """Peak Kp in window from k-index_<date>.json in this date's dir
    unioned with the previous day's file (in its own dir): early-UTC dusk
    windows reach into the prior day's product."""
    try:
        prev = (datetime.strptime(date_compact, "%Y%m%d")
                - timedelta(days=1)).strftime("%Y%m%d")
    except ValueError:
        prev = None
    samples = []
    if prev:
        samples.extend(_load_kp_samples(os.path.join(sub_dir, prev,
                                                     KP_FILE_FMT % prev)))
    samples.extend(_load_kp_samples(os.path.join(
        sub_dir, date_compact, KP_FILE_FMT % date_compact)))
    start, end = window
    inside = [kp for when, kp in samples if start <= when <= end]
    return max(inside) if inside else None


def _pretty_range(start_compact, end_compact):
    """Human label like "Aug 24 – Sep 21, 2026" (en dash; the year is
    shown on the end date, and on the start date too when they differ)."""
    s = time.strptime(start_compact, "%Y%m%d")
    e = time.strptime(end_compact, "%Y%m%d")

    def part(st, with_year):
        txt = "%s %d" % (time.strftime("%b", st), st.tm_mday)
        return "%s, %d" % (txt, st.tm_year) if with_year else txt

    return "%s – %s" % (part(s, s.tm_year != e.tm_year), part(e, True))


def scan_archive(cam_dir, now_ts=None, calendar_days=DEFAULT_CALENDAR_DAYS,
                 latitude=DEFAULT_LATITUDE, longitude=DEFAULT_LONGITUDE,
                 tz_name=DEFAULT_TZ_NAME):
    """Scan the staged date-dir tree (d/<YYYYMMDD>/) for the calendar view.

    Returns a dict with the same conventions as scan_directory(): plain
    data, cam_dir-relative URLs, never raises. The grid is a fixed set of
    whole Mon-Sun weeks -- ceil(calendar_days / 7) rows ending with the
    Sunday of now_ts's week -- so its size never drifts with weekday
    alignment. Cells after today are placeholders (in_window=False, date
    fields only); every cell up to today can carry data, so the number of
    data days shown is calendar_days minus the forward padding (the
    configured maximum only when today is a Sunday). "range_start_iso",
    "range_end_iso" and "range_pretty" describe that data window.
    """
    now_ts = time.time() if now_ts is None else now_ts
    try:
        calendar_days = max(1, int(calendar_days))
    except (TypeError, ValueError):
        calendar_days = DEFAULT_CALENDAR_DAYS
    result = {
        "enabled": True,
        "cam_dir": str(cam_dir) if cam_dir else "",
        "calendar_days": calendar_days,
        "weeks": [],
        "range_start_iso": None, "range_end_iso": None,
        "range_pretty": None,
        "kp_scale": [{"label": b["label"], "css": b["css"]}
                     for b in KP_BANDS],
    }
    if not cam_dir:
        result["error"] = "archive directory not configured"
        return result
    try:
        sub_dir = os.path.join(cam_dir, ARCHIVE_SUBDIR)
        if not os.path.isdir(sub_dir):
            result["error"] = "archive tree not staged: %s" % sub_dir
            return result
        lt = time.localtime(now_ts)
        today_compact = time.strftime("%Y%m%d", lt)
        today_iso = _iso(today_compact)
        # Whole weeks ending with the current week's Sunday; the start
        # therefore always lands on a Monday (no backward padding).
        sunday_offset = 6 - lt.tm_wday
        total_days = -(-calendar_days // 7) * 7   # ceil to whole weeks
        grid = []
        for offset in range(sunday_offset - (total_days - 1),
                            sunday_offset + 1):
            date_compact = _shift_compact(today_compact, offset)
            if _iso(date_compact) <= today_iso:
                grid.append(_archive_cell(sub_dir, date_compact, today_iso,
                                          latitude, longitude, tz_name))
            else:
                grid.append(_out_cell(date_compact, today_iso))
        # Alternating shade per calendar month (newest month = even).
        months = []
        for cell in grid:
            key = cell["date_iso"][:7]
            if key not in months:
                months.append(key)
        for cell in grid:
            parity = (len(months) - 1 - months.index(cell["date_iso"][:7])) % 2
            cell["month_class"] = ("tl-month-even" if parity == 0
                                   else "tl-month-odd")
        result["range_start_iso"] = _iso(grid[0]["date_compact"])
        result["range_end_iso"] = today_iso
        result["range_pretty"] = _pretty_range(grid[0]["date_compact"],
                                               today_compact)
    except OSError as e:
        result["error"] = str(e)
        return result

    result["weeks"] = [grid[i:i + 7] for i in range(0, len(grid), 7)]
    return result
