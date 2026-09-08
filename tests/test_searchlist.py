import configobj

from user.aurorawx import scanner
from user.aurorawx.searchlist import AuroraSearchList
from test_scanner import NOW, day_file_name, make


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


def test_thumbnail_urls_get_alias_prefix(tmp_path):
    name = day_file_name("AuroraCam_", ".mp4", NOW - 86400)
    thumb = name[:-len(".mp4")] + ".thumbnail.jpg"
    make(tmp_path / name, mtime=NOW - 86400)
    make(tmp_path / thumb, mtime=NOW - 86400)
    make(tmp_path / "snapshot.jpg", mtime=NOW - 60)
    aurora = make_sle(tmp_path, cam_url="/cam").get_extension_list(None, None)[0]["aurora"]
    assert aurora["aurora_videos"][0]["thumbnail"] == "/cam/" + thumb
    day = aurora["days"][0]
    assert day["aurora_thumbnail"] == "/cam/" + thumb
    assert day["cloud_thumbnail"] is None


def test_cameras_config_scanned_and_prefixed(tmp_path):
    import time
    make(tmp_path / "snapshot.jpg", mtime=time.time() - 60)
    make(tmp_path / "Driveway.jpg", mtime=time.time() - 600)
    cfg = configobj.ConfigObj()
    cfg["Extras"] = {"Aurora": {
        "cam_dir": str(tmp_path), "cam_url": "/cam",
        "cameras": {
            "sky": {"label": "Sky camera", "image": "snapshot.jpg"},
            "ground": {"label": "Ground camera", "image": "Driveway.jpg"},
        },
    }}
    aurora = AuroraSearchList(FakeGenerator(cfg)) \
        .get_extension_list(None, None)[0]["aurora"]
    keys = [c["key"] for c in aurora["cameras"]]
    assert keys == ["sky", "ground"]
    assert aurora["cameras"][0]["url"] == "/cam/snapshot.jpg"
    assert aurora["cameras"][1]["url"] == "/cam/Driveway.jpg"
    assert aurora["cameras"][1]["label"] == "Ground camera"
    assert aurora["cameras"][1]["age_minutes"] == 10
    assert aurora["snapshot"]["url"] == "/cam/snapshot.jpg"


def test_cameras_default_when_not_configured(tmp_path):
    make(tmp_path / "snapshot.jpg", mtime=NOW - 60)
    aurora = make_sle(tmp_path, cam_url="/cam").get_extension_list(None, None)[0]["aurora"]
    assert [c["key"] for c in aurora["cameras"]] == ["sky"]
    assert aurora["cameras"][0]["url"] == "/cam/snapshot.jpg"


def test_clearsky_chart_scanned_and_prefixed(tmp_path):
    import time
    make(tmp_path / "clearsky_chart.gif", mtime=time.time() - 300)
    cfg = configobj.ConfigObj()
    cfg["Extras"] = {"Aurora": {
        "cam_dir": str(tmp_path), "cam_url": "/cam",
        "clearsky_chart_filename": "clearsky_chart.gif",
    }}
    aurora = AuroraSearchList(FakeGenerator(cfg)) \
        .get_extension_list(None, None)[0]["aurora"]
    chart = aurora["clearsky_chart"]
    assert chart["exists"] is True
    assert chart["url"] == "/cam/clearsky_chart.gif"
    assert chart["age_minutes"] == 5


def test_clearsky_chart_missing_keeps_bare_url(tmp_path):
    cfg = configobj.ConfigObj()
    cfg["Extras"] = {"Aurora": {"cam_dir": str(tmp_path), "cam_url": "/cam"}}
    aurora = AuroraSearchList(FakeGenerator(cfg)) \
        .get_extension_list(None, None)[0]["aurora"]
    chart = aurora["clearsky_chart"]
    assert chart["exists"] is False
    assert chart["url"] == "/cam/clearsky_chart.gif"


def test_asset_version_from_skin_file_mtimes(tmp_path):
    css_dir = tmp_path / "css"
    js_dir = tmp_path / "js"
    css_dir.mkdir()
    js_dir.mkdir()
    make(css_dir / "aurora.css", mtime=NOW - 5000)
    make(js_dir / "aurora-gallery.js", mtime=NOW - 100)
    cfg = configobj.ConfigObj()
    cfg["Extras"] = {"Aurora": {}}
    cfg["SKIN_ROOT"] = str(tmp_path.parent)
    cfg["skin"] = tmp_path.name
    aurora = AuroraSearchList(FakeGenerator(cfg)).get_extension_list(None, None)[0]["aurora"]
    assert aurora["asset_version"] == NOW - 100


def test_asset_version_falls_back_when_skin_files_missing(tmp_path):
    cfg = configobj.ConfigObj()
    cfg["Extras"] = {"Aurora": {}}
    cfg["SKIN_ROOT"] = str(tmp_path)
    cfg["skin"] = "noskin"
    aurora = AuroraSearchList(FakeGenerator(cfg)).get_extension_list(None, None)[0]["aurora"]
    assert aurora["asset_version"] == 1


def test_asset_version_present_when_disabled():
    aurora = make_sle(None).get_extension_list(None, None)[0]["aurora"]
    assert aurora["enabled"] is False
    assert aurora["asset_version"] == 1


def test_io_error_is_contained():
    aurora = make_sle("/definitely/not/a/real/dir").get_extension_list(None, None)[0]["aurora"]
    assert aurora["enabled"] is True
    assert aurora["status"] == "no_data"


def test_garbage_config_does_not_raise_at_construction():
    cfg = configobj.ConfigObj()
    cfg["Extras"] = {"Aurora": {"stale_after_minutes": "abc"}}
    sle = AuroraSearchList(FakeGenerator(cfg))
    assert sle.stale_minutes == 30
    scalar_cfg = configobj.ConfigObj()
    scalar_cfg["Extras"] = "not-a-section"
    sle2 = AuroraSearchList(FakeGenerator(scalar_cfg))
    assert sle2.get_extension_list(None, None)[0]["aurora"]["enabled"] is False


def test_scalar_aurora_section_does_not_raise_at_construction():
    cfg = configobj.ConfigObj()
    cfg["Extras"] = {"Aurora": "not-a-section"}
    sle = AuroraSearchList(FakeGenerator(cfg))
    aurora = sle.get_extension_list(None, None)[0]["aurora"]
    assert aurora["enabled"] is False
    assert aurora["status"] == "disabled"


def test_scanner_crash_is_contained(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("simulated scanner crash")
    monkeypatch.setattr(scanner, "scan_directory", boom)
    aurora = make_sle("/tmp").get_extension_list(None, None)[0]["aurora"]
    assert aurora["enabled"] is True
    assert aurora["status"] == "no_data"
    assert "error" in aurora
    for key in ("snapshot", "aurora_videos", "cloud_videos", "spaceweather", "days"):
        assert key in aurora
