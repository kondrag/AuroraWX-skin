"""Search list extension exposing the $aurora namespace to auroraWX templates.

Registered in skins/aurorawx/skin.conf:

    [CheetahGenerator]
        search_list_extensions = user.aurorawx.searchlist.AuroraSearchList

The package lives in the WeeWX user directory (bin/user). WeeWX puts bin/
(the parent of the user directory) on sys.path, hence the "user." prefix on
imports. Neither construction nor get_extension_list() can raise:
any failure degrades to a no_data/disabled state (spec section 4).
"""

import os
import time

import weewx.cheetahgenerator

from user.aurorawx import scanner

ASSET_FILES = ("css/aurora.css", "js/aurora-gallery.js")


def format_ts(ts, fmt):
    """Format an epoch timestamp with a strftime pattern (local time).

    Exposed to templates as $aurora.format_ts. Returns ts unchanged when
    either argument is missing so template misuse never raises.
    """
    if ts is None or not fmt:
        return ts
    try:
        return time.strftime(fmt, time.localtime(ts))
    except (TypeError, ValueError):
        return ts


class AuroraSearchList(weewx.cheetahgenerator.SearchList):

    def __init__(self, generator):
        weewx.cheetahgenerator.SearchList.__init__(self, generator)
        extras = self.generator.skin_dict.get("Extras", {})
        cfg = extras.get("Aurora", {}) if hasattr(extras, "get") else {}
        if not hasattr(cfg, "get"):
            cfg = {}
        self.cam_dir = str(cfg.get("cam_dir", "") or "")
        self.cam_url = str(cfg.get("cam_url", "") or "").rstrip("/")
        try:
            self.stale_minutes = int(float(cfg.get("stale_after_minutes", 30)))
        except (ValueError, TypeError, OverflowError):
            self.stale_minutes = 30
        self.night_publish_by = str(cfg.get("night_publish_by", "07:00"))
        self.day_publish_by = str(cfg.get("day_publish_by", "19:00"))
        self.cameras = self._read_cameras(cfg)
        self.clearsky_chart = str(cfg.get("clearsky_chart_filename",
                                          "clearsky_chart.gif") or "")
        self.calendar_days = self._read_int(
            cfg, "calendar_days", scanner.DEFAULT_CALENDAR_DAYS)
        self.latitude = self._read_float(
            cfg, "latitude", scanner.DEFAULT_LATITUDE)
        self.longitude = self._read_float(
            cfg, "longitude", scanner.DEFAULT_LONGITUDE)
        self.tz_name = str(cfg.get("tz_name", scanner.DEFAULT_TZ_NAME) or "")
        self.asset_version = self._compute_asset_version()

    @staticmethod
    def _read_int(cfg, key, default):
        try:
            return int(float(cfg.get(key, default)))
        except (ValueError, TypeError, OverflowError):
            return default

    @staticmethod
    def _read_float(cfg, key, default):
        try:
            return float(cfg.get(key, default))
        except (ValueError, TypeError, OverflowError):
            return default

    @staticmethod
    def _read_cameras(cfg):
        """Normalize the [[[cameras]]] config to a list of dicts.

        Each [[[[<key>]]]] subsection becomes {key, label, image}; a
        scalar or absent section degrades to an empty list (the scanner
        then applies its snapshot.jpg default).
        """
        try:
            raw = cfg.get("cameras")
            if not hasattr(raw, "items"):
                return []
            cameras = []
            for key, sub in raw.items():
                sub = sub if hasattr(sub, "get") else {}
                cameras.append({
                    "key": str(key),
                    "label": str(sub.get("label", "") or key),
                    "image": str(sub.get("image", "") or ""),
                })
            return cameras
        except Exception:
            return []

    def _compute_asset_version(self):
        """Max mtime of the skin's custom css/js, for cache-busting ?v=.

        Never raises: any failure degrades to 1.
        """
        try:
            skin_dict = self.generator.skin_dict
            skin_root = str(skin_dict.get("SKIN_ROOT", "skins"))
            skin_dir = os.path.join(skin_root, str(skin_dict.get("skin", "")))
            if not os.path.isabs(skin_dir):
                config_dict = getattr(self.generator, "config_dict", {})
                weewx_root = config_dict.get("WEEWX_ROOT", "") \
                    if hasattr(config_dict, "get") else ""
                skin_dir = os.path.join(str(weewx_root), skin_dir)
            best = 0
            for rel in ASSET_FILES:
                try:
                    best = max(best, int(os.path.getmtime(os.path.join(skin_dir, rel))))
                except OSError:
                    continue
            return best or 1
        except Exception:
            return 1

    def _abs_url(self, filename):
        if not filename:
            return None
        return "%s/%s" % (self.cam_url, filename) if self.cam_url else filename

    def get_extension_list(self, timespan, db_lookup):
        data = {
            "enabled": False, "status": "disabled", "cam_dir": self.cam_dir,
            "asset_version": self.asset_version,
            "snapshot": {"exists": False, "url": None, "mtime": None,
                         "age_minutes": None, "is_stale": True},
            "aurora_videos": [], "cloud_videos": [], "spaceweather": [],
            "days": [], "cameras": [],
            "calendar": {"enabled": False, "cam_dir": self.cam_dir,
                         "calendar_days": self.calendar_days,
                         "weeks": [], "kp_scale": [], "error": None},
            "format_ts": format_ts,
            "clearsky_chart": {"exists": False, "url": None, "mtime": None,
                               "age_minutes": None, "is_stale": True},
        }
        if self.cam_dir:
            try:
                scanned = scanner.scan_directory(
                    self.cam_dir,
                    stale_minutes=self.stale_minutes,
                    night_publish_by=self.night_publish_by,
                    day_publish_by=self.day_publish_by,
                    cameras=self.cameras,
                    clearsky_chart=self.clearsky_chart)
                data.update(scanned)
                data["enabled"] = True
                data["calendar"] = scanner.scan_archive(
                    self.cam_dir,
                    calendar_days=self.calendar_days,
                    latitude=self.latitude,
                    longitude=self.longitude,
                    tz_name=self.tz_name)
                data["calendar"].setdefault("error", None)
            except Exception as e:  # belt and braces: never break a report run
                data.update({"enabled": True, "status": scanner.NO_DATA,
                             "error": repr(e)})
            data["snapshot"]["url"] = self._abs_url(data["snapshot"]["url"])
            chart = data.get("clearsky_chart")
            if chart:
                chart["url"] = self._abs_url(chart["url"])
            for camera in data["cameras"]:
                camera["url"] = self._abs_url(camera["url"])
            for key in ("aurora_videos", "cloud_videos"):
                for entry in data[key]:
                    entry["url"] = self._abs_url(entry["url"])
                    entry["thumbnail"] = self._abs_url(entry["thumbnail"])
            for entry in data["spaceweather"]:
                entry["url"] = self._abs_url(entry["url"])
            for day in data["days"]:
                for key in ("aurora_video", "cloud_video", "spaceweather",
                            "aurora_thumbnail", "cloud_thumbnail"):
                    day[key] = self._abs_url(day[key])
            if data.get("latest"):
                for key in ("aurora_video", "aurora_thumbnail",
                            "cloud_video", "cloud_thumbnail",
                            "spaceweather"):
                    data["latest"][key] = self._abs_url(data["latest"][key])
            for week in data["calendar"].get("weeks") or []:
                for cell in week:
                    if not cell:
                        continue
                    for key in ("aurora_video", "aurora_thumbnail",
                                "cloud_video", "cloud_thumbnail",
                                "spaceweather"):
                        cell[key] = self._abs_url(cell[key])
        return [{"aurora": data}]
