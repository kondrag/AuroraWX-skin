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
# Real installs ship a stub bin/user/extensions.py (weeutil.startup imports
# it on every start). Without it weewx logs "ERROR ... Cannot load user
# extensions", which run_reports.sh rightly treats as a failure.
if [ ! -f "$DATA/bin/user/extensions.py" ]; then
  cat > "$DATA/bin/user/extensions.py" <<'EOF'
# Stub matching the file a real weewx install ships in bin/user/,
# so weeutil.startup's "import user.extensions" succeeds.
def load_extensions(engine, config_dict):
    pass
EOF
fi
find "$DATA" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
echo "synced skin + package into $DATA"
