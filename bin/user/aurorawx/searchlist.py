"""Search list extension exposing the $aurora namespace to auroraWX templates.

Registered in skins/aurorawx/skin.conf:

    [CheetahGenerator]
        search_list_extensions = user.aurorawx.searchlist.AuroraSearchList

The package lives in the WeeWX user directory (bin/user). WeeWX puts bin/
(the parent of the user directory) on sys.path, hence the "user." prefix on
imports. get_extension_list() can never raise:
any failure degrades to a no_data/disabled state (spec section 4).
"""

import weewx.cheetahgenerator

from user.aurorawx import scanner


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
