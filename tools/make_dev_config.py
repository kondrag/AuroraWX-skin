#!/usr/bin/env python3
"""Create dev-weewx/weewx-data/weewx-<scenario>.conf files from the stock
weewx.conf template. Scenarios: full, partial, empty, nocam."""
import os

import configobj

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = os.path.join(ROOT, "dev-weewx", "weewx-data")
SRC = os.environ.get("WEEWX_SRC", "/home/greg/workspace/weewx")
STOCK_CONF = os.path.join(SRC, "src", "weewx_data", "weewx.conf")

SCENARIOS = {
    "full": os.path.join(ROOT, "fixtures", "cam_dir", "full"),
    "partial": os.path.join(ROOT, "fixtures", "cam_dir", "partial"),
    "empty": os.path.join(ROOT, "fixtures", "cam_dir", "empty"),
    "nocam": "",
}


def main():
    os.makedirs(os.path.join(DATA_ROOT, "archive"), exist_ok=True)
    for scenario, cam_dir in SCENARIOS.items():
        conf = configobj.ConfigObj(STOCK_CONF)
        conf["WEEWX_ROOT"] = DATA_ROOT
        conf["Station"]["location"] = "Aurora Test Site"
        conf["Station"]["latitude"] = "45.0"
        conf["Station"]["longitude"] = "-93.0"
        conf["Station"]["altitude"] = ["300", "meter"]
        for report in ("StandardReport", "SmartphoneReport", "MobileReport",
                       "Ftp", "FTP", "RSYNC"):
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
