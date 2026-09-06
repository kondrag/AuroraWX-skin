import os
import time

from user.aurorawx import scanner

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


def test_full_directory_is_ok(tmp_path):
    seed_week(tmp_path, scanner.AURORA_PREFIX, ".mp4")
    seed_week(tmp_path, scanner.CLOUD_PREFIX, ".mp4")
    seed_week(tmp_path, scanner.SPACEWEATHER_PREFIX, ".gif")
    # scan pre-deadline (06:30 local) so today's night video is not yet due
    lt = time.localtime(NOW)
    scan_ts = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 6, 30, 0, 0, 0, -1))
    make(tmp_path / "snapshot.jpg", mtime=scan_ts - 60)
    r = scanner.scan_directory(tmp_path, now_ts=scan_ts)
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
    # 09:00 local on the "now" day: today's night video is overdue
    lt = time.localtime(NOW)
    nine_am = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 9, 0, 0, 0, 0, -1))
    make(tmp_path / "snapshot.jpg", mtime=nine_am - 60)  # live at scan time
    r = scanner.scan_directory(tmp_path, now_ts=nine_am)
    assert r["status"] == scanner.ENCODING


def test_missing_today_cloud_video_after_day_publish_is_encoding(tmp_path):
    seed_week(tmp_path, scanner.AURORA_PREFIX, ".mp4")
    # today's aurora video is done, so the night branch must not fire
    lt = time.localtime(NOW)
    noon = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 12, 0, 0, 0, 0, -1))
    make(tmp_path / day_file_name(scanner.AURORA_PREFIX, ".mp4", noon), mtime=noon)
    # 20:00 local on the "now" day: past day_publish_by, today's cloud video missing
    eight_pm = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 20, 0, 0, 0, 0, -1))
    make(tmp_path / "snapshot.jpg", mtime=eight_pm - 60)  # live at scan time
    r = scanner.scan_directory(tmp_path, now_ts=eight_pm)
    assert r["status"] == scanner.ENCODING


def test_stale_snapshot_outranks_encoding(tmp_path):
    seed_week(tmp_path, scanner.AURORA_PREFIX, ".mp4")
    lt = time.localtime(NOW)
    nine_am = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 9, 0, 0, 0, 0, -1))
    make(tmp_path / "snapshot.jpg", mtime=nine_am - 2 * 3600)  # stale at scan time
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
