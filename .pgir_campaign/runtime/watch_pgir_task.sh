#!/usr/bin/env bash
# Watch one PGIR task across all lanes.
# Usage: watch_pgir_task.sh PGIR-021
# DONE when the board status is completed.
# FAILED only if the board is still open, there is no live lock/provider/grok
# for the current workspace, and the newest attempt log is quiet >900s
# (or missing for >900s after we first observed an open task).
set -euo pipefail
TASK="${1:?usage: watch_pgir_task.sh PGIR-NNN}"
TODO=/home/barberb/lift_coding/.pgir_campaign/worktrees/accelerate-authority/docs/architecture/proof_grounded_ir_learning.todo.md
ROOT=/home/barberb/lift_coding/.pgir_campaign/runtime/parallel
slug=$(echo "$TASK" | tr '[:upper:]' '[:lower:]')

latest_log() {
  ls -t "$ROOT"/lane-*/implementation_logs/${slug}-attempt-*.log 2>/dev/null | head -1
}

workspace_from_log() {
  awk -F': ' '/^Workspace: / { print $2; exit }' "$1"
}

board_status() {
  python3 -c '
from pathlib import Path
import sys
text = Path("'"$TODO"'").read_text()
tid = sys.argv[1]
i = text.find("## " + tid)
print("completed" if "- Status: completed" in text[i:i+200] else "open")
' "$TASK"
}

lock_live_for_task() {
  python3 - "$TASK" <<'PY'
import json, sys
from pathlib import Path
task = sys.argv[1]
root = Path("/home/barberb/lift_coding/.pgir_campaign/runtime/parallel")
for lock_path in root.glob("lane-*/implementation.lock"):
    try:
        data = json.loads(lock_path.read_text())
    except Exception:
        continue
    if str(data.get("task_id") or "") != task:
        continue
    pid = int(data.get("pid") or 0)
    if pid and Path(f"/proc/{pid}").exists():
        sys.exit(0)
sys.exit(1)
PY
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
    if needle in cmd and (
        b"grok" in cmd
        or b"pgir_implementation_provider" in cmd
        or b"grok_cli_runner" in cmd
    ):
        sys.exit(0)
sys.exit(1)
PY
}

first_seen=$(date +%s)
while true; do
  if [ "$(board_status)" = "completed" ]; then
    printf 'DONE\n'
    exit 0
  fi
  live=0
  if lock_live_for_task; then
    live=1
  fi
  LOG=$(latest_log || true)
  quiet=0
  if [ -n "${LOG:-}" ] && [ -f "$LOG" ]; then
    now=$(date +%s)
    mtime=$(stat -c %Y "$LOG")
    quiet=$((now - mtime))
    ws=$(workspace_from_log "$LOG")
    if workspace_live "$ws"; then
      live=1
    fi
  else
    now=$(date +%s)
    quiet=$((now - first_seen))
  fi
  if [ "$quiet" -gt 900 ] && [ "$live" -eq 0 ]; then
    printf 'FAILED\n'
    exit 1
  fi
  sleep 30
done
