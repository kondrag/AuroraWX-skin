import importlib.util
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_install():
    spec = importlib.util.spec_from_file_location(
        "aurorawx_install", os.path.join(ROOT, "install.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_generated_manifest_in_sync():
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "gen_install.py"), "--check"],
        capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout + r.stderr).strip()


def test_loader_lists_every_shipped_file():
    installer = load_install().loader()
    listed = set()
    for dest, files in installer["files"]:
        listed.update(files)
    on_disk = set()
    for base in ("bin", "skins"):
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, base)):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fn in filenames:
                if fn.endswith(".pyc"):
                    continue
                on_disk.add(os.path.relpath(os.path.join(dirpath, fn), ROOT)
                            .replace(os.sep, "/"))
    assert on_disk == listed, {"unlisted on disk": on_disk - listed,
                               "listed but missing": listed - on_disk}


def test_installer_metadata_and_config():
    installer = load_install().loader()
    assert installer["name"] == "aurorawx"
    assert installer["version"] == "1.0.0"
    report = installer["config"]["StdReport"]["AuroraWXReport"]
    assert report["skin"] == "aurorawx"
    assert report["enable"] == "true"
