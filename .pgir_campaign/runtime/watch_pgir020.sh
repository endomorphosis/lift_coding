#!/usr/bin/env bash
# Watch the current PGIR-020 attempt across all lanes.
# Uses the newest pgir-020-attempt-*.log and the Workspace: header inside it.
# FAILED only if the board is still open, the log is quiet >900s, and no
# grok/provider process is live on that workspace.
set -euo pipefail
TODO=/home/barberb/lift_coding/.pgir_campaign/worktrees/accelerate-authority/docs/architecture/proof_grounded_ir_learning.todo.md
ROOT=/home/barberb/lift_coding/.pgir_campaign/runtime/parallel

latest_log() {
  ls -t "$ROOT"/lane-*/implementation_logs/pgir-020-attempt-*.log 2>/dev/null | head -1
}

workspace_from_log() {
  local log="$1"
  awk -F': ' '/^Workspace: / { print $2; exit }' "$log"
}

board_status() {
  python3 -c '
from pathlib import Path
text = Path("'"$TODO"'").read_text()
i = text.find("## PGIR-020")
print("completed" if "- Status: completed" in text[i:i+200] else "open")
'
}

workspace_live() {
  local ws="$1"
  [ -n "$ws" ] || return 1
  python3 - "$ws" <<'PY'
import sys
from pathlib import Path
needle = sys.argv[1].encode()
for proc in Path("/proc").iterdir():
    if not proc.name.isdigit():
        continue
    try:
        cmd = (proc / "cmdline").read_bytes()
    except OSError:
        continue
    if needle in cmd and (b"grok" in cmd or b"pgir_implementation_provider" in cmd or b"grok_cli_runner" in cmd):
        sys.exit(0)
sys.exit(1)
PY
}

while true; do
  if [ "$(board_status)" = "completed" ]; then
    printf 'DONE\n'
    exit 0
  fi
  LOG=$(latest_log || true)
  if [ -n "${LOG:-}" ] && [ -f "$LOG" ]; then
    now=$(date +%s)
    mtime=$(stat -c %Y "$LOG")
    quiet=$((now - mtime))
    ws=$(workspace_from_log "$LOG")
    live=0
    if workspace_live "$ws"; then
      live=1
    fi
    if [ "$quiet" -gt 900 ] && [ "$live" -eq 0 ]; then
      printf 'FAILED\n'
      exit 1
    fi
  fi
  sleep 30
done
