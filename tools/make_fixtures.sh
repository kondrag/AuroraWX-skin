#!/bin/sh
# Create the camera-directory fixtures used by the offline report tests.
set -e
cd "$(dirname "$0")/.."
FIX=fixtures/cam_dir
rm -rf "$FIX"
mkdir -p "$FIX/full" "$FIX/partial" "$FIX/empty"
touch "$FIX/empty/.keep"

for day in Monday Tuesday Wednesday Thursday Friday Saturday Sunday; do
  for pre in AuroraCam CloudCam; do
    dd if=/dev/zero of="$FIX/full/${pre}_${day}.mp4" bs=1024 count=64 2>/dev/null
  done
  dd if=/dev/zero of="$FIX/full/SpaceWeather_${day}.gif" bs=1024 count=48 2>/dev/null
done
touch -d '1 minute ago' "$FIX/full/snapshot.jpg"

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

echo "fixtures created under $FIX"
