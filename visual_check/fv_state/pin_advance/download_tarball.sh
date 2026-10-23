#!/bin/bash
# Resumable codeload tarball download of the pin-target tree.
# Rationale (documented in PROGRESS.md): git lazy-fetch moves blobs in many
# small proxy round trips (round-trip-bound, hours); the tarball is ONE
# resumable CDN stream — stream death is cheap because curl -C - resumes.
set -u
PA="$HOME/workspace/lift_coding/visual_check/fv_state/pin_advance"
URL="https://codeload.github.com/endomorphosis/ipfs_datasets_py/tar.gz/f4a823231ad52c9252504810a1b00ed4738346b6"
OUT="$PA/tip.tar.gz"
LOG="$PA/download.log"
for i in $(seq 1 60); do
  sz=$(stat -c%s "$OUT" 2>/dev/null || echo 0)
  echo "attempt $i start $(date -u +%FT%TZ) have=$sz" >> "$LOG"
  curl -C - --speed-limit 10240 --speed-time 90 -o "$OUT" "$URL" >> "$LOG" 2>&1
  rc=$?
  sz=$(stat -c%s "$OUT" 2>/dev/null || echo 0)
  echo "attempt $i end rc=$rc size=$sz $(date -u +%FT%TZ)" >> "$LOG"
  if [ $rc -eq 0 ]; then
    echo "DOWNLOAD-COMPLETE size=$sz" >> "$LOG"
    exit 0
  fi
  sleep 5
done
echo "DOWNLOAD-EXHAUSTED" >> "$LOG"
exit 1
