#!/usr/bin/env bash
set -euo pipefail
TODO=/home/barberb/lift_coding/.pgir_campaign/worktrees/accelerate-authority/docs/architecture/proof_grounded_ir_learning.todo.md
LOGDIR=/home/barberb/lift_coding/.pgir_campaign/runtime/parallel/lane-1/implementation_logs
latest_log() { ls -t "$LOGDIR"/pgir-060-attempt-*.log 2>/dev/null | head -1; }
while true; do
  status=$(python3 -c '
from pathlib import Path
text = Path("'"$TODO"'").read_text()
i = text.find("## PGIR-060")
print("completed" if "- Status: completed" in text[i:i+200] else "open")
')
  if [ "$status" = "completed" ]; then
    printf 'DONE\n'
    exit 0
  fi
  LOG=$(latest_log)
  if [ -n "${LOG:-}" ] && [ -f "$LOG" ]; then
    now=$(date +%s)
    mtime=$(stat -c %Y "$LOG")
    quiet=$((now - mtime))
    live=0
    if pgrep -f 'workspace-f5dee7c34fb0-a9ad0f936bc5' >/dev/null 2>&1; then
      live=1
    fi
    if [ "$quiet" -gt 900 ] && [ "$live" -eq 0 ]; then
      printf 'FAILED\n'
      exit 1
    fi
  fi
  sleep 30
done
