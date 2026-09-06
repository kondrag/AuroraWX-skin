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
