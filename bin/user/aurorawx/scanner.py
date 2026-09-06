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
