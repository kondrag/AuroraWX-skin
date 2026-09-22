"""Tests for scanner.scan_archive(): the date-dir calendar view.

The archive contract (staged by link_archive_to_site.sh as
d/<YYYYMMDD> -> /var/local/timelapse/<YYYYMMDD>) is:

  d/<YYYYMMDD>/AuroraCam_<YYYYMMDD>_640x360.mp4
  d/<YYYYMMDD>/AuroraCam_<YYYYMMDD>_2560x1440.mp4   (never exposed)
  d/<YYYYMMDD>/AuroraCam_<YYYYMMDD>.thumbnail.jpg
  d/<YYYYMMDD>/CloudCam_<YYYYMMDD>_640x360.mp4
  d/<YYYYMMDD>/CloudCam_<YYYYMMDD>.thumbnail.jpg
  d/<YYYYMMDD>/SpaceWeather_<YYYYMMDD>.gif
  d/<YYYYMMDD>/k-index_<YYYYMMDD>.json

URLs are cam_dir-relative paths ("d/<date>/<file>"); the caller prefixes
them with the configured web-server alias, same as scan_directory().
"""

import json
import pytest
import os
import time

from user.aurorawx import scanner

NOW = 1789944256  # fixed epoch late on 2026-09-20 (a Sunday)


def date_compacts(now_ts, count):
    """count YYYYMMDD strings ending with now_ts's local date, oldest first."""
    lt = time.localtime(now_ts)
    out = []
    for i in range(count):
        t = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday - i,
                         12, 0, 0, 0, 0, -1))
        out.append(time.strftime("%Y%m%d", time.localtime(t)))
    return out


def make(path, mtime=None, size=1024):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def seed_date_dir(root, date, *, aurora=True, cloud=True, spaceweather=True,
                  high_res=False, kp_samples=None):
    d = root / "d" / date
    if aurora:
        make(d / ("AuroraCam_%s_640x360.mp4" % date), mtime=NOW - 3600)
        make(d / ("AuroraCam_%s.thumbnail.jpg" % date), mtime=NOW - 3600)
    if high_res:
        make(d / ("AuroraCam_%s_2560x1440.mp4" % date), mtime=NOW - 3600)
    if cloud:
        make(d / ("CloudCam_%s_640x360.mp4" % date), mtime=NOW - 1800)
        make(d / ("CloudCam_%s.thumbnail.jpg" % date), mtime=NOW - 1800)
    if spaceweather:
        make(d / ("SpaceWeather_%s.gif" % date), mtime=NOW - 900)
    if kp_samples is not None:
        rows = [{"time_tag": tag, "Kp": kp, "a_running": 8,
                 "station_count": 8} for tag, kp in kp_samples]
        (d / ("k-index_%s.json" % date)).write_text(json.dumps(rows))


def all_cells(result):
    return [c for week in result["weeks"] for c in week if c]


def test_calendar_covers_35_days_mon_aligned(tmp_path):
    dates = date_compacts(NOW, 35)
    seed_date_dir(tmp_path, dates[0])
    seed_date_dir(tmp_path, dates[3])
    r = scanner.scan_archive(tmp_path, now_ts=NOW)
    assert r["enabled"] is True
    assert r["calendar_days"] == 35
    cells = all_cells(r)
    assert len(cells) == 35
    assert [c["date_iso"] for c in cells] == [
        "%s-%s-%s" % (d[:4], d[4:6], d[6:8]) for d in reversed(dates)
    ]
    # rows are whole weeks of 7; every slot is a real cell
    assert all(len(week) == 7 for week in r["weeks"])
    assert all(c is not None for week in r["weeks"] for c in week)
    # NOW is a Sunday, so 35 days is exactly five Mon-Sun weeks, all in window
    assert len(r["weeks"]) == 5
    assert all(c["in_window"] is True for c in cells)
    # first cell lands on Monday of its row
    assert time.strptime(cells[0]["date_iso"], "%Y-%m-%d").tm_wday == 0


def test_grid_full_weeks_with_out_of_window_cells(tmp_path):
    now_mon = NOW + 86400  # 2026-09-21, a Monday
    dates = date_compacts(now_mon, 35)  # 2026-08-18 .. 2026-09-21
    seed_date_dir(tmp_path, dates[-1])
    r = scanner.scan_archive(tmp_path, now_ts=now_mon)
    weeks = r["weeks"]
    # 35 days ending on a Monday span six whole Mon-Sun weeks
    assert len(weeks) == 6
    for week in weeks:
        assert len(week) == 7
        assert all(c is not None for c in week)
    cells = [c for week in weeks for c in week]
    assert len(cells) == 42
    # leading placeholder: the Monday before the window starts
    assert cells[0]["date_iso"] == "2026-08-17"
    assert cells[0]["in_window"] is False
    assert cells[0]["day_of_month"] == "17"
    assert cells[0]["kp_text"] is None
    assert cells[0]["aurora_video"] is None
    # first in-window day
    assert cells[1]["date_iso"] == "2026-08-18"
    assert cells[1]["in_window"] is True
    # today is the last in-window cell (after the one leading placeholder)
    assert cells[35]["date_iso"] == "2026-09-21"
    assert cells[35]["in_window"] is True
    assert cells[35]["is_today"] is True
    # trailing placeholders: the rest of the current week (future days)
    assert [c["date_iso"] for c in cells[36:]] == [
        "2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25",
        "2026-09-26", "2026-09-27"]
    assert all(c["in_window"] is False and c["is_today"] is False
               for c in cells[36:])


def test_media_and_today_flags(tmp_path):
    dates = date_compacts(NOW, 35)
    seed_date_dir(tmp_path, dates[0], high_res=True)
    seed_date_dir(tmp_path, dates[1], aurora=False)
    r = scanner.scan_archive(tmp_path, now_ts=NOW)
    cells = {c["date_iso"]: c for c in all_cells(r)}
    today = cells["%s-%s-%s" % (dates[0][:4], dates[0][4:6], dates[0][6:8])]
    assert today["is_today"] is True
    assert today["aurora_video"] == \
        "d/%s/AuroraCam_%s_640x360.mp4" % (dates[0], dates[0])
    assert today["aurora_thumbnail"] == \
        "d/%s/AuroraCam_%s.thumbnail.jpg" % (dates[0], dates[0])
    assert today["cloud_video"] == \
        "d/%s/CloudCam_%s_640x360.mp4" % (dates[0], dates[0])
    assert today["spaceweather"] == "d/%s/SpaceWeather_%s.gif" % (dates[0],
                                                                 dates[0])
    assert today["aurora_mtime"] == NOW - 3600
    # high-res never leaks into the calendar
    yesterday = cells["%s-%s-%s" % (dates[1][:4], dates[1][4:6],
                                    dates[1][6:8])]
    assert yesterday["aurora_video"] is None
    assert yesterday["cloud_video"] is not None
    for c in cells.values():
        for key in ("aurora_video", "cloud_video"):
            assert not (c[key] or "").endswith("_2560x1440.mp4")
    # an unseeded date is an empty cell, not an error
    empty = cells["%s-%s-%s" % (dates[20][:4], dates[20][4:6],
                                dates[20][6:8])]
    assert empty["aurora_video"] is None
    assert empty["kp_peak"] is None


def test_missing_dir_does_not_raise(tmp_path):
    r = scanner.scan_archive(tmp_path / "nope", now_ts=NOW)
    assert r["enabled"] is True
    assert "error" in r
    assert all_cells(r) == []


# --- Kp: peak over the nautical night window -----------------------------
# Window ground truth from the generator's astral implementation
# (night_upload.night_window, lat 45.1666 lon -90.8076 America/Chicago):
#   2026-09-20: dusk 2026-09-20T01:10:28Z .. dawn 2026-09-20T10:43:43Z
#   2026-12-21: dusk 2026-12-20T23:34:53Z .. dawn 2026-12-21T12:27:28Z

KP_DIR_DATE = date_compacts(NOW, 35)[0]


def test_kp_peak_only_inside_night_window(tmp_path):
    seed_date_dir(tmp_path, KP_DIR_DATE, kp_samples=[
        ("2026-09-20T00:30:00", 3.0),   # before nautical dusk: excluded
        ("2026-09-20T03:00:00", 5.33),  # inside
        ("2026-09-20T06:00:00", 4.67),  # inside, lower
        ("2026-09-20T11:00:00", 6.0),   # after nautical dawn: excluded
    ])
    r = scanner.scan_archive(tmp_path, now_ts=NOW)
    today = all_cells(r)[-1]
    assert today["kp_peak"] == 5.33
    # 5.33 = G1 band in the current SWPC palette (yellow, up to 5.33)
    assert today["kp_level"] == 5
    assert today["kp_css"] == "kp-band-1"


def test_kp_uses_previous_days_file_for_early_utc_dusk(tmp_path):
    dates = [time.strftime("%Y%m%d", time.localtime(
        time.mktime((2026, 12, 21 - i, 12, 0, 0, 0, 0, -1)))) for i in (0, 1)]
    now_ts = time.mktime((2026, 12, 21, 18, 0, 0, 0, 0, -1))
    seed_date_dir(tmp_path, dates[1], kp_samples=[
        ("2026-12-20T23:45:00", 7.0),  # inside the 21st's window (UTC 20th!)
    ])
    seed_date_dir(tmp_path, dates[0], kp_samples=[
        ("2026-12-21T06:00:00", 3.0),  # inside, lower
    ])
    r = scanner.scan_archive(tmp_path, now_ts=now_ts)
    cells = {c["date_iso"]: c for c in all_cells(r)}
    assert cells["2026-12-21"]["kp_peak"] == 7.0
    assert cells["2026-12-21"]["kp_level"] == 7


def test_kp_level_mapping():
    # level = round-half-up of the peak Kp (NOAA band centers, e.g.
    # 4.67 = "5-" -> 5, 5.33 = "5+" -> 5), clamped to 0..9
    assert scanner.kp_level(0.0) == 0
    assert scanner.kp_level(0.33) == 0
    assert scanner.kp_level(0.67) == 1
    assert scanner.kp_level(1.0) == 1
    assert scanner.kp_level(2.5) == 3
    assert scanner.kp_level(4.0) == 4
    assert scanner.kp_level(4.33) == 4
    assert scanner.kp_level(4.67) == 5
    assert scanner.kp_level(5.67) == 6
    assert scanner.kp_level(8.99) == 9
    assert scanner.kp_level(9.0) == 9
    assert scanner.kp_level(9.33) == 9   # clamped


def test_kp_missing_or_malformed_is_silent(tmp_path):
    seed_date_dir(tmp_path, date_compacts(NOW, 35)[1])
    bad = tmp_path / "d" / date_compacts(NOW, 35)[2]
    bad.mkdir(parents=True)
    (bad / ("k-index_%s.json" % date_compacts(NOW, 35)[2])).write_text("not json")
    (tmp_path / "d" / date_compacts(NOW, 35)[3]).mkdir(parents=True)
    (tmp_path / "d" / date_compacts(NOW, 35)[3] /
     ("k-index_%s.json" % date_compacts(NOW, 35)[3])).write_text('{"a": 1}')
    (tmp_path / "d" / date_compacts(NOW, 35)[4]).mkdir(parents=True)
    tag_date = "%s-%s-%s" % (date_compacts(NOW, 35)[4][:4],
                             date_compacts(NOW, 35)[4][4:6],
                             date_compacts(NOW, 35)[4][6:8])
    (tmp_path / "d" / date_compacts(NOW, 35)[4] /
     ("k-index_%s.json" % date_compacts(NOW, 35)[4])).write_text(json.dumps([
         {"time_tag": "%sT03:00:00" % tag_date},       # no Kp: skipped
         {"Kp": 6.0},                                  # no time_tag: skipped
         {"time_tag": "%sT06:00:00" % tag_date, "Kp": 2.0},
     ]))
    r = scanner.scan_archive(tmp_path, now_ts=NOW)
    cells = all_cells(r)
    assert cells[-2]["kp_peak"] is None
    assert cells[-3]["kp_peak"] is None
    assert cells[-4]["kp_peak"] is None
    assert cells[-5]["kp_peak"] == 2.0


def test_night_window_matches_astral_reference():
    """scanner.night_window_utc vs astral nautical twilight, same
    convention as the generator's night_upload.night_window."""
    pytest.importorskip("astral")
    from datetime import date as date_cls, datetime, timedelta, timezone
    from zoneinfo import ZoneInfo
    from astral import Depression, LocationInfo
    from astral.sun import sun

    location = LocationInfo("Observer", "", timezone="America/Chicago",
                            latitude=45.1666, longitude=-90.8076)

    def reference(day):
        # date is a LOCAL date when tzinfo is passed (night_upload
        # convention): dusk of local date day-1, dawn of local date day
        dusk = sun(location.observer, date=day - timedelta(days=1),
                   tzinfo=location.timezone,
                   dawn_dusk_depression=Depression.NAUTICAL)["dusk"]
        dawn = sun(location.observer, date=day,
                   tzinfo=location.timezone,
                   dawn_dusk_depression=Depression.NAUTICAL)["dawn"]
        return (dusk.astimezone(timezone.utc),
                dawn.astimezone(timezone.utc))

    for day in (date_cls(2026, 9, 20), date_cls(2026, 12, 21),
                date_cls(2026, 6, 21), date_cls(2026, 3, 8),
                date_cls(2026, 11, 1), date_cls(2026, 1, 1)):
        start, end = scanner.night_window_utc(day)
        a_start, a_end = reference(day)
        # independent NOAA/Meeus implementations drift ~2 min from
        # astral's solar model; 300s tolerance guards against tz/DST/sign
        # bugs (which are hour/day-scale) while allowing model drift
        assert abs(start - a_start.timestamp()) < 300, day
        assert abs(end - a_end.timestamp()) < 300, day


def test_kp_band_mapping():
    # bands mirror the SWPC planetary K-index chart zones
    assert scanner.kp_band(0.0) == 0
    assert scanner.kp_band(4.33) == 0
    assert scanner.kp_band(4.67) == 1
    assert scanner.kp_band(5.33) == 1
    assert scanner.kp_band(5.67) == 2
    assert scanner.kp_band(6.67) == 3
    assert scanner.kp_band(7.67) == 4
    assert scanner.kp_band(8.67) == 4
    assert scanner.kp_band(9.0) == 5
    assert scanner.kp_band(None) is None


def test_kp_scale_legend_in_result(tmp_path):
    seed_date_dir(tmp_path, KP_DIR_DATE)
    r = scanner.scan_archive(tmp_path, now_ts=NOW)
    scale = r["kp_scale"]
    assert len(scale) == 6
    assert [s["css"] for s in scale] == ["kp-band-%d" % i for i in range(6)]
    assert all(s.get("label") for s in scale)


def test_kp_text_is_one_decimal_or_none(tmp_path):
    # today is the last (Sunday) cell of the flattened grid
    seed_date_dir(tmp_path, "20260920", kp_samples=[("2026-09-20T03:00:00", 5.33)])
    cells = all_cells(scanner.scan_archive(tmp_path, now_ts=NOW))
    assert cells[-1]["kp_text"] == "5.3"
    # earlier cells have no Kp file -> kp_text stays None
    assert all(c["kp_text"] is None for c in cells[:-1])


def test_month_classes_alternate_by_calendar_month(tmp_path):
    seed_date_dir(tmp_path, date_compacts(NOW, 35)[0])
    result = scanner.scan_archive(str(tmp_path), now_ts=NOW)
    cells = all_cells(result)
    # 35 days back from Sun 2026-09-20 spans Aug and Sep 2026.
    seen = {}  # YYYYMM -> class of its first cell
    for cell in cells:
        yyyymm = cell["date_iso"][:7].replace("-", "")
        seen.setdefault(yyyymm, cell["month_class"])
        assert cell["month_class"] == seen[yyyymm]
    # Newest month (contains today) is even, the previous one odd.
    assert seen["202609"] == "tl-month-even"
    assert seen["202608"] == "tl-month-odd"


def test_month_classes_alternate_across_three_months(tmp_path):
    seed_date_dir(tmp_path, date_compacts(NOW, 62)[0])
    result = scanner.scan_archive(str(tmp_path), now_ts=NOW, calendar_days=62)
    order = []  # distinct months, newest first
    for cell in all_cells(result):
        yyyymm = cell["date_iso"][:7].replace("-", "")
        if not order or order[-1][0] != yyyymm:
            order.append((yyyymm, cell["month_class"]))
    assert [cls for _, cls in order] == ["tl-month-even", "tl-month-odd",
                                         "tl-month-even"]
