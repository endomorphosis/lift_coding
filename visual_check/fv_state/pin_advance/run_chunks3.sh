#!/bin/bash
# Pass-3 parallel chunk driver. Usage: run_chunks3.sh <partition 1|2|3>
# Uses a PRIVATE index file (seeded from the real index) so 3 drivers can
# run concurrently without index.lock contention; paths are disjoint by
# construction. The real index is rebuilt from the tip tree afterwards.
set -u
P=$1
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="ssh -i /home/hatch/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new"
REPO="$HOME/workspace/lift_coding/external/ipfs_datasets"
PA="$HOME/workspace/lift_coding/visual_check/fv_state/pin_advance"
TIP=f4a823231ad52c9252504810a1b00ed4738346b6
export GIT_INDEX_FILE="$PA/index.p$P"
cd "$REPO" || exit 1
touch "$PA/chunks3.p$P.done"

declare -A SPECS
ORDER=()
while IFS=$'\t' read -r chunk spec; do
  [ -z "$chunk" ] && continue
  if [ -z "${SPECS[$chunk]+x}" ]; then ORDER+=("$chunk"); SPECS[$chunk]=""; fi
  SPECS[$chunk]+="$spec "
done < "$PA/chunks3.p$P.tsv"

ok=0; fail=0; skip=0
for chunk in "${ORDER[@]}"; do
  if grep -qxF "$chunk" "$PA/chunks3.p$P.done"; then skip=$((skip+1)); continue; fi
  echo "=== CHUNK $chunk" >> "$PA/chunks3.p$P.log"
  # shellcheck disable=SC2086
  timeout --signal=TERM --kill-after=30 900 git checkout "$TIP" -- ${SPECS[$chunk]} >> "$PA/chunks3.p$P.log" 2>&1
  rc=$?
  if [ $rc -eq 0 ]; then
    echo "$chunk" >> "$PA/chunks3.p$P.done"
    echo "OK   $chunk" >> "$PA/chunks3.p$P.log"
    ok=$((ok+1))
  else
    echo "FAIL $chunk rc=$rc" >> "$PA/chunks3.p$P.log"
    fail=$((fail+1))
  fi
done
echo "DRIVER3-P$P-DONE ok=$ok fail=$fail skip=$skip" >> "$PA/chunks3.p$P.log"
echo "DRIVER3-P$P-DONE ok=$ok fail=$fail skip=$skip"
