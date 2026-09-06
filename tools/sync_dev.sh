#!/bin/sh
# Copy the skin + python package into the dev weewx-data tree (mirrors what
# `weectl extension install` would do on a real install).
set -e
cd "$(dirname "$0")/.."
DATA=dev-weewx/weewx-data
mkdir -p "$DATA/bin/user" "$DATA/skins"
rm -rf "$DATA/skins/aurorawx" "$DATA/bin/user/aurorawx"
cp -r skins/aurorawx "$DATA/skins/aurorawx"
cp -r bin/user/aurorawx "$DATA/bin/user/aurorawx"
find "$DATA" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
echo "synced skin + package into $DATA"
