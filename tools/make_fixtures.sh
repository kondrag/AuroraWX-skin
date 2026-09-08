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

OLD_DAY=$(date -d '3 days ago' +%A)
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
