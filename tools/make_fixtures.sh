#!/bin/sh
# Create the camera-directory fixtures used by the offline report tests.
# Requires GNU coreutils (date -d / touch -d). Fixture ages matter: the full
# scenario expects reports to run within ~30 min of fixture creation.
set -e
cd "$(dirname "$0")/.."
FIX=fixtures/cam_dir
rm -rf "$FIX"
mkdir -p "$FIX/full" "$FIX/partial" "$FIX/empty"
touch "$FIX/empty/.keep"

for day in Monday Tuesday Wednesday Thursday Friday Saturday Sunday; do
  # stamp each file onto its most recent weekday occurrence so the
  # weekday-keyed day cards come out current (not "update pending")
  if [ "$day" = "$(date +%A)" ]; then
    STAMP_VIDEO='30 minutes ago'
    STAMP_CHART='30 minutes ago'
  else
    STAMP_VIDEO="last $day 05:30"
    STAMP_CHART="last $day 12:00"
  fi
  for pre in AuroraCam CloudCam; do
    dd if=/dev/zero of="$FIX/full/${pre}_${day}.mp4" bs=1024 count=64 2>/dev/null
    dd if=/dev/zero of="$FIX/full/${pre}_${day}.thumbnail.jpg" bs=1024 count=8 2>/dev/null
    touch -d "$STAMP_VIDEO" "$FIX/full/${pre}_${day}.mp4" "$FIX/full/${pre}_${day}.thumbnail.jpg"
  done
  dd if=/dev/zero of="$FIX/full/SpaceWeather_${day}.gif" bs=1024 count=48 2>/dev/null
  touch -d "$STAMP_CHART" "$FIX/full/SpaceWeather_${day}.gif"
done
touch -d '1 minute ago' "$FIX/full/snapshot.jpg"
dd if=/dev/zero of="$FIX/full/Driveway.jpg" bs=1024 count=48 2>/dev/null
touch -d '1 minute ago' "$FIX/full/Driveway.jpg"
dd if=/dev/zero of="$FIX/full/clearsky_chart.gif" bs=1024 count=28 2>/dev/null
touch -d '5 minutes ago' "$FIX/full/clearsky_chart.gif"

# date-stamped archive tree (d/<YYYYMMDD>) for the Timelapses calendar;
# partial/empty intentionally have no d/ so the calendar renders its
# "not available" fallback there
for i in 1 2 3 4; do
  D=$(date -d "$i days ago" +%Y%m%d)
  mkdir -p "$FIX/full/d/$D"
  dd if=/dev/zero of="$FIX/full/d/$D/AuroraCam_${D}_640x360.mp4" bs=1024 count=64 2>/dev/null
  dd if=/dev/zero of="$FIX/full/d/$D/AuroraCam_${D}.thumbnail.jpg" bs=1024 count=8 2>/dev/null
  dd if=/dev/zero of="$FIX/full/d/$D/SpaceWeather_${D}.gif" bs=1024 count=48 2>/dev/null
  touch -d "$i days ago" "$FIX/full/d/$D"/*
done
# Kp samples inside the night window of the most recent archived date
# (03Z/09Z are safely between nautical dusk and dawn at the site year-round)
KD=$(date -d '1 day ago' +%Y%m%d)
cat > "$FIX/full/d/$KD/k-index_${KD}.json" <<EOF
[{"time_tag": "$(date -u -d '1 day ago' +%Y-%m-%dT)03:00:00", "Kp": 4.67, "a_running": 22, "station_count": 8},
 {"time_tag": "$(date -u -d '1 day ago' +%Y-%m-%dT)09:00:00", "Kp": 6.33, "a_running": 32, "station_count": 8}]
EOF

OLD_DAY=$(date -d '3 days ago' +%A)
# "latest" staging links (production: refreshed every pipeline run by
# link_archive_to_site.sh) pointing at the newest archived day
LD=$(date -d '1 day ago' +%Y%m%d)
ln -sfn "d/$LD/AuroraCam_${LD}_640x360.mp4" "$FIX/full/AuroraCam_latest.mp4"
ln -sfn "d/$LD/AuroraCam_${LD}.thumbnail.jpg" "$FIX/full/AuroraCam_latest.thumbnail.jpg"
ln -sfn "d/$LD/SpaceWeather_${LD}.gif" "$FIX/full/SpaceWeather_latest.gif"
dd if=/dev/zero of="$FIX/partial/AuroraCam_${OLD_DAY}.mp4" bs=1024 count=64 2>/dev/null
dd if=/dev/zero of="$FIX/partial/CloudCam_${OLD_DAY}.mp4" bs=1024 count=64 2>/dev/null
dd if=/dev/zero of="$FIX/partial/SpaceWeather_${OLD_DAY}.gif" bs=1024 count=48 2>/dev/null
touch -d '3 days ago' "$FIX"/partial/AuroraCam_* "$FIX"/partial/CloudCam_* "$FIX"/partial/SpaceWeather_*
# an incomplete day (chart only) so the gallery renders "Still encoding"
# placeholders for its missing videos
OLD_DAY2=$(date -d '2 days ago' +%A)
dd if=/dev/zero of="$FIX/partial/SpaceWeather_${OLD_DAY2}.gif" bs=1024 count=48 2>/dev/null
touch -d '2 days ago' "$FIX/partial/SpaceWeather_${OLD_DAY2}.gif"
dd if=/dev/zero of="$FIX/partial/snapshot.jpg" bs=1024 count=48 2>/dev/null
touch -d '2 hours ago' "$FIX/partial/snapshot.jpg"
dd if=/dev/zero of="$FIX/partial/Driveway.jpg" bs=1024 count=48 2>/dev/null
touch -d '2 hours ago' "$FIX/partial/Driveway.jpg"
# no clearsky_chart.gif in partial: card must hide when the file is absent

echo "fixtures created under $FIX"
