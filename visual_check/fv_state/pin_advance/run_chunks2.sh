#!/bin/bash
# Pass-2 chunked checkout driver: fine-grained chunks (<=250 files per dir
# chunk, <=120 pathspecs per list chunk). Resumable via chunks2.done.
# Transport: stored config (origin = HTTPS, http.version = HTTP/1.1).
set -u
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="ssh -i /home/hatch/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new"
REPO="$HOME/workspace/lift_coding/external/ipfs_datasets"
PA="$HOME/workspace/lift_coding/visual_check/fv_state/pin_advance"
TIP=f4a823231ad52c9252504810a1b00ed4738346b6
cd "$REPO" || exit 1
touch "$PA/chunks2.done"

declare -A SPECS
ORDER=()
while IFS=$'\t' read -r chunk spec; do
  [ -z "$chunk" ] && continue
  if [ -z "${SPECS[$chunk]+x}" ]; then ORDER+=("$chunk"); SPECS[$chunk]=""; fi
  SPECS[$chunk]+="$spec "
done < "$PA/chunks2.tsv"

ok=0; fail=0; skip=0
for chunk in "${ORDER[@]}"; do
  if grep -qxF "$chunk" "$PA/chunks2.done"; then skip=$((skip+1)); continue; fi
  echo "=== CHUNK $chunk" >> "$PA/chunks2.log"
  # shellcheck disable=SC2086
  timeout --signal=TERM --kill-after=30 600 git checkout "$TIP" -- ${SPECS[$chunk]} >> "$PA/chunks2.log" 2>&1
  rc=$?
  if [ $rc -eq 0 ]; then
    echo "$chunk" >> "$PA/chunks2.done"
    echo "OK   $chunk" >> "$PA/chunks2.log"
    ok=$((ok+1))
  else
    echo "FAIL $chunk rc=$rc" >> "$PA/chunks2.log"
    fail=$((fail+1))
  fi
done
echo "DRIVER2-DONE ok=$ok fail=$fail skip=$skip" >> "$PA/chunks2.log"
echo "DRIVER2-DONE ok=$ok fail=$fail skip=$skip"
