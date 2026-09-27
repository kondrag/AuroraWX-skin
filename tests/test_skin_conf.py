import os

import configobj

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKIN_CONF = os.path.join(ROOT, "skins", "aurorawx", "skin.conf")


def load_skin_conf():
    return configobj.ConfigObj(SKIN_CONF, encoding="utf-8")


def test_signal_quality_has_label():
    # Without this label the telemetry card title falls back to the raw
    # database key "rxCheckPercent".
    label = load_skin_conf()["Labels"]["Generic"]["rxCheckPercent"]
    assert label == "Signal Quality"


def test_signal_quality_in_telemetry_order():
    order = load_skin_conf()["Extras"]["Appearance"]["telemetry_order"]
    assert "rxCheckPercent" in order
