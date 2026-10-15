#!/bin/bash
# Chunked pathspec checkout driver for the datasets pin advance.
# Resumable: completed chunk names are recorded in chunks.done.
# Each chunk is a bounded promisor blob batch over HTTPS (part 1 proved
# HTTPS reliable here; the single-stream SSH checkout stalled mid-pack).
set -u
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="ssh -i /home/hatch/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new"
REPO="$HOME/workspace/lift_coding/external/ipfs_datasets"
PA="$HOME/workspace/lift_coding/visual_check/fv_state/pin_advance"
TIP=f4a823231ad52c9252504810a1b00ed4738346b6
HTTPS=https://github.com/endomorphosis/ipfs_datasets_py.git
cd "$REPO" || exit 1
touch "$PA/chunks.done"

declare -A SPECS
ORDER=()
while IFS=$'\t' read -r chunk spec; do
  [ -z "$chunk" ] && continue
  if [ -z "${SPECS[$chunk]+x}" ]; then ORDER+=("$chunk"); SPECS[$chunk]=""; fi
  SPECS[$chunk]+="$spec "
done < "$PA/chunks.tsv"

ok=0; fail=0; skip=0
for chunk in "${ORDER[@]}"; do
  if grep -qxF "$chunk" "$PA/chunks.done"; then skip=$((skip+1)); continue; fi
  echo "=== CHUNK $chunk :: ${SPECS[$chunk]}" >> "$PA/chunks.log"
  # shellcheck disable=SC2086
  timeout --signal=TERM --kill-after=30 480 git -c remote.origin.url="$HTTPS" \
    checkout "$TIP" -- ${SPECS[$chunk]} >> "$PA/chunks.log" 2>&1
  rc=$?
  if [ $rc -eq 0 ]; then
    echo "$chunk" >> "$PA/chunks.done"
    echo "OK   $chunk" >> "$PA/chunks.log"
    ok=$((ok+1))
  else
    echo "FAIL $chunk rc=$rc" >> "$PA/chunks.log"
    fail=$((fail+1))
  fi
done
echo "DRIVER-DONE ok=$ok fail=$fail skip=$skip" >> "$PA/chunks.log"
echo "DRIVER-DONE ok=$ok fail=$fail skip=$skip"
