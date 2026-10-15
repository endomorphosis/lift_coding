#!/usr/bin/env bash
set -euo pipefail
TODO=/home/barberb/lift_coding/.pgir_campaign/worktrees/accelerate-authority/docs/architecture/proof_grounded_ir_learning.todo.md
LOG=/home/barberb/lift_coding/.pgir_campaign/runtime/parallel/lane-2/implementation_logs/pgir-013-attempt-1.log
while true; do
  status=$(python3 -c '
from pathlib import Path
text = Path("'"$TODO"'").read_text()
i = text.find("## PGIR-013")
chunk = text[i:i+200]
print("completed" if "- Status: completed" in chunk else "open")
')
  if [ "$status" = "completed" ]; then
    printf 'DONE\n'
    exit 0
  fi
  if [ -f "$LOG" ]; then
    now=$(date +%s)
    mtime=$(stat -c %Y "$LOG")
    quiet=$((now - mtime))
    if [ "$quiet" -gt 900 ] && pgrep -f 'codex exec --approve-for-me --ephemeral' >/dev/null; then
      printf 'FAILED\n'
      exit 1
    fi
  fi
  sleep 30
done
