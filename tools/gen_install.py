#!/usr/bin/env python3
"""Regenerate the generated skin-file list inside install.py.

Run after adding/removing files under skins/aurorawx:

    python tools/gen_install.py            # rewrite
    python tools/gen_install.py --check    # exit nonzero if stale (used by tests)

For testing, the GEN_INSTALL_INSTALL and GEN_INSTALL_SKIN_DIR environment
variables may override the default install.py / skins/aurorawx paths.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIN_DIR = os.path.join(ROOT, "skins", "aurorawx")
INSTALL = os.path.join(ROOT, "install.py")
BEGIN = "# --- BEGIN GENERATED SKIN FILES"
END = "# --- END GENERATED SKIN FILES ---"


def skin_files(skin_dir=SKIN_DIR):
    out = []
    for dirpath, dirnames, filenames in os.walk(skin_dir):
        dirnames.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            out.append(os.path.relpath(full, ROOT).replace(os.sep, "/"))
    return sorted(out)


def render(files):
    lines = [BEGIN + " (tools/gen_install.py) ---", "SKIN_FILES = ["]
    lines += ["    %r," % f for f in files]
    lines += ["]", END]
    return "\n".join(lines)


def main():
    install_path = os.environ.get("GEN_INSTALL_INSTALL", INSTALL)
    skin_dir = os.environ.get("GEN_INSTALL_SKIN_DIR", SKIN_DIR)
    files = skin_files(skin_dir)
    with open(install_path, encoding="utf-8") as f:
        content = f.read()

    if BEGIN not in content:
        sys.exit("%s: begin marker %r not found" % (install_path, BEGIN))
    pre, _, rest = content.partition(BEGIN)
    if END not in rest:
        sys.exit("%s: end marker %r not found after begin marker"
                 % (install_path, END))
    _, _, post = rest.partition(END)
    if BEGIN in post:
        sys.exit("%s: duplicate begin marker" % install_path)
    if not files:
        sys.exit("no skin files found under %s" % skin_dir)

    block = render(files)
    new = pre + block + post
    if "--check" in sys.argv:
        if new != content:
            sys.exit("install.py skin file list is stale; run tools/gen_install.py")
        sys.exit(0)
    with open(install_path, "w", encoding="utf-8") as f:
        f.write(new)
    print("updated %s (%d skin files)" % (install_path, len(files)))


if __name__ == "__main__":
    main()
