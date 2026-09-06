#!/usr/bin/env python3
"""Regenerate the generated skin-file list inside install.py.

Run after adding/removing files under skins/aurorawx:

    python tools/gen_install.py            # rewrite
    python tools/gen_install.py --check    # exit 1 if stale (used by tests)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIN_DIR = os.path.join(ROOT, "skins", "aurorawx")
INSTALL = os.path.join(ROOT, "install.py")
BEGIN = "# --- BEGIN GENERATED SKIN FILES"
END = "# --- END GENERATED SKIN FILES ---"


def skin_files():
    out = []
    for dirpath, dirnames, filenames in os.walk(SKIN_DIR):
        dirnames.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            out.append(os.path.relpath(full, ROOT).replace(os.sep, "/"))
    return sorted(out)


def render(files):
    lines = [BEGIN + " (tools/gen_install.py) ---", "SKIN_FILES = ["]
    lines += ["    '%s'," % f for f in files]
    lines += ["]", END]
    return "\n".join(lines)


def main():
    block = render(skin_files())
    with open(INSTALL) as f:
        content = f.read()
    pre, _, rest = content.partition(BEGIN)
    _, _, post = rest.partition(END)
    new = pre + block + post
    if "--check" in sys.argv:
        if new != content:
            sys.exit("install.py skin file list is stale; run tools/gen_install.py")
        sys.exit(0)
    with open(INSTALL, "w") as f:
        f.write(new)
    print("updated %s (%d skin files)" % (INSTALL, len(skin_files())))


if __name__ == "__main__":
    main()
