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
    dbm = weewx.manager.open_manager_with_config(CONFIG, "wx_binding",
                                                 initialize=True)
    end = int(time.time()) // 300 * 300
    start = end - 14 * 86400
    count = 0
    for ts in range(start, end + 1, 300):
        dbm.addRecord(record_for(ts))
        count += 1
    dbm.close()
    print("seeded %d records into %s" % (count, DB_PATH))


if __name__ == "__main__":
    main()
