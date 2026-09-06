#!/bin/sh
# One-time dev bootstrap: venv (if missing), configs, seeded DB, fixtures, sync.
set -e
cd "$(dirname "$0")/.."
WEEWX_SRC=${WEEWX_SRC:-/home/greg/workspace/weewx}
[ -x .venv/bin/python ] || {
  python3 -m venv .venv
  .venv/bin/pip install -q "$WEEWX_SRC" pytest
}
.venv/bin/python tools/make_dev_config.py
.venv/bin/python tools/seed_db.py
sh tools/make_fixtures.sh
sh tools/sync_dev.sh
