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

import os
import time

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
AURORA_PREFIX = "AuroraCam_"
CLOUD_PREFIX = "CloudCam_"
SPACEWEATHER_PREFIX = "SpaceWeather_"
SNAPSHOT_NAME = "snapshot.jpg"
THUMB_SUFFIX = ".thumbnail.jpg"

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
