#!/usr/bin/env bash
# Launch six UIIR implementation lanes with Grok-first agent dispatch.
#
# Autonomy defaults for finishing the board without Codex:
# - No --production-provider-policy (typed Grok+Codex independent review).
# - PRODUCTION_PROVIDER_ROUTE=0 and ALLOW_RAW_MODEL_COMMAND=1.
# - Non-strict sharding so idle lanes claim any ready UIR- task.
# - Long implement timeouts / log-stall so Grok is not recycled mid-tool-call.
# - High max-restarts for multi-hour unattended runs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

export PYTHONPATH="${ROOT}/external/ipfs_accelerate${PYTHONPATH:+:${PYTHONPATH}}"
export PYTHONUNBUFFERED=1

# Force Grok Build agent implement. Do not require independent Codex review.
export IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER="${IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER:-grok}"
export IPFS_ACCELERATE_AGENT_GROK_MODEL="${IPFS_ACCELERATE_AGENT_GROK_MODEL:-grok-4.5}"
export IPFS_ACCELERATE_AGENT_GROK_PERMISSION_MODE="${IPFS_ACCELERATE_AGENT_GROK_PERMISSION_MODE:-bypassPermissions}"
export IPFS_ACCELERATE_AGENT_GROK_BIN="${IPFS_ACCELERATE_AGENT_GROK_BIN:-${HOME}/.local/bin/grok}"

# Never force the typed production packet route for this board.
export IPFS_ACCELERATE_AGENT_PRODUCTION_PROVIDER_ROUTE="${IPFS_ACCELERATE_AGENT_PRODUCTION_PROVIDER_ROUTE:-0}"
# Allow agent CLI when a task would otherwise claim the typed route.
export IPFS_ACCELERATE_AGENT_ALLOW_RAW_MODEL_COMMAND="${IPFS_ACCELERATE_AGENT_ALLOW_RAW_MODEL_COMMAND:-1}"

UIIR_MERGE_TARGET_BRANCH="${UIIR_MERGE_TARGET_BRANCH:-agent/ui-ux-ir}"
TODO_PATH="implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.todo.md"
OBJECTIVE_PATH="implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.objectives.md"
STATE_ROOT="data/agent_supervisor/ui_ux_ir/state"
WORKTREE_ROOT="data/agent_supervisor/ui_ux_ir/worktrees"
MERGE_QUEUE_DIR="data/agent_supervisor/ui_ux_ir/merge-queue"
LOG_DIR="data/agent_supervisor/ui_ux_ir/logs"
# Soft affinity only: without --strict-task-sharding, empty shards fall back to
# any ready UIR- task so the board keeps draining with 6 lanes.
SHARD_COUNT="${UIIR_SHARD_COUNT:-6}"
MAX_RESTARTS="${UIIR_MAX_RESTARTS:-200}"
IMPLEMENT_TIMEOUT="${UIIR_IMPLEMENTATION_TIMEOUT:-7200}"
LOG_STALL_SECONDS="${UIIR_IMPLEMENTATION_LOG_STALL_SECONDS:-3600}"

mkdir -p "$STATE_ROOT" "$WORKTREE_ROOT" "$MERGE_QUEUE_DIR" "$LOG_DIR"

_kill_lane_pids() {
  local lane="$1"
  local me=$$ parent=$PPID
  python3 - "$lane" "$me" "$parent" <<'PY'
import os, signal, sys
from pathlib import Path
lane, me, parent = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
token = f"uiir_lane_{lane}".encode()
for entry in Path("/proc").iterdir():
    if not entry.name.isdigit():
        continue
    pid = int(entry.name)
    if pid in {me, parent}:
        continue
    try:
        raw = (entry / "cmdline").read_bytes()
    except (OSError, PermissionError):
        continue
    if token not in raw:
        continue
    if b"implementation_supervisor" in raw or b"implementation_daemon" in raw:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
PY
}

stop_lane() {
  local lane="$1"
  local unit="uiir-lane-${lane}.service"
  if command -v systemctl >/dev/null 2>&1; then
    systemctl --user stop "$unit" 2>/dev/null || true
    systemctl --user reset-failed "$unit" 2>/dev/null || true
  fi
  _kill_lane_pids "$lane"
}

start_lane() {
  local lane="$1"
  local state_dir="${STATE_ROOT}/lane-${lane}"
  local worktree_dir="${WORKTREE_ROOT}/lane-${lane}"
  local log_path="${LOG_DIR}/uiir-lane-${lane}.log"
  mkdir -p "$state_dir" "$worktree_dir"

  # NOTE: intentionally NO --strict-task-sharding so idle lanes claim any ready
  # UIR- work when their affinity shard is empty (board drain).
  local -a cmd=(
    /usr/bin/python3
    -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor
    --todo-path "$TODO_PATH"
    --task-prefix UIR-
    --state-dir "$state_dir"
    --state-prefix "uiir_lane_${lane}"
    --worktree-root "$worktree_dir"
    --merge-queue-dir "$MERGE_QUEUE_DIR"
    --merge-target-branch "$UIIR_MERGE_TARGET_BRANCH"
    --task-shard-count "$SHARD_COUNT"
    --task-shard-index "$lane"
    --worktree-submodule-path external/ipfs_datasets
    --worktree-submodule-path external/ipfs_accelerate
    --worktree-submodule-path swissknife
    --worktree-submodule-path hallucinate_app
    --objective-path "$OBJECTIVE_PATH"
    --objective-scan-max-findings 0
    --codebase-scan-max-findings 0
    --no-objective-goal-refinement
    --no-objective-goal-completion-reconcile
    --implementation-protected-path implementation_plan/docs/45-ipfs-datasets-ui-ux-ir-plan-2026-07-31.md
    --implementation-protected-path "$OBJECTIVE_PATH"
    --implementation-protected-path "$TODO_PATH"
    --implement
    --daemon-interval 60
    --check-interval 30
    --max-restarts "$MAX_RESTARTS"
    --max-task-attempts 0
    --implementation-log-stall-seconds "$LOG_STALL_SECONDS"
    --implementation-timeout "$IMPLEMENT_TIMEOUT"
  )

  if command -v systemd-run >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
    systemd-run --user --collect \
      --unit="uiir-lane-${lane}" \
      --description="UIIR Grok-first agent supervisor lane ${lane}" \
      --property=Type=simple \
      --property="WorkingDirectory=${ROOT}" \
      --property=Restart=on-failure \
      --property=RestartSec=5s \
      --property=KillMode=control-group \
      --property=TimeoutStopSec=30s \
      --property="SuccessExitStatus=143 SIGTERM" \
      --setenv=PYTHONPATH="${PYTHONPATH}" \
      --setenv=PYTHONUNBUFFERED=1 \
      --setenv=IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER="${IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER}" \
      --setenv=IPFS_ACCELERATE_AGENT_GROK_MODEL="${IPFS_ACCELERATE_AGENT_GROK_MODEL}" \
      --setenv=IPFS_ACCELERATE_AGENT_GROK_PERMISSION_MODE="${IPFS_ACCELERATE_AGENT_GROK_PERMISSION_MODE}" \
      --setenv=IPFS_ACCELERATE_AGENT_GROK_BIN="${IPFS_ACCELERATE_AGENT_GROK_BIN}" \
      --setenv=IPFS_ACCELERATE_AGENT_PRODUCTION_PROVIDER_ROUTE="${IPFS_ACCELERATE_AGENT_PRODUCTION_PROVIDER_ROUTE}" \
      --setenv=IPFS_ACCELERATE_AGENT_ALLOW_RAW_MODEL_COMMAND="${IPFS_ACCELERATE_AGENT_ALLOW_RAW_MODEL_COMMAND}" \
      "${cmd[@]}"
    echo "started systemd unit uiir-lane-${lane}"
  else
    nohup env \
      PYTHONPATH="${PYTHONPATH}" \
      PYTHONUNBUFFERED=1 \
      IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER="${IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER}" \
      IPFS_ACCELERATE_AGENT_GROK_MODEL="${IPFS_ACCELERATE_AGENT_GROK_MODEL}" \
      IPFS_ACCELERATE_AGENT_GROK_PERMISSION_MODE="${IPFS_ACCELERATE_AGENT_GROK_PERMISSION_MODE}" \
      IPFS_ACCELERATE_AGENT_GROK_BIN="${IPFS_ACCELERATE_AGENT_GROK_BIN}" \
      IPFS_ACCELERATE_AGENT_PRODUCTION_PROVIDER_ROUTE="${IPFS_ACCELERATE_AGENT_PRODUCTION_PROVIDER_ROUTE}" \
      IPFS_ACCELERATE_AGENT_ALLOW_RAW_MODEL_COMMAND="${IPFS_ACCELERATE_AGENT_ALLOW_RAW_MODEL_COMMAND}" \
      "${cmd[@]}" >>"$log_path" 2>&1 &
    echo "started background lane ${lane} pid=$! log=$log_path"
  fi
}

_stop_board_companion() {
  local unit="uiir-board-companion.service"
  if command -v systemctl >/dev/null 2>&1; then
    systemctl --user stop "$unit" 2>/dev/null || true
    systemctl --user reset-failed "$unit" 2>/dev/null || true
  fi
  python3 - <<'PY'
import os, signal
from pathlib import Path
me, parent = os.getpid(), os.getppid()
token = b"uiir_auto_complete_green_tasks"
for entry in Path("/proc").iterdir():
    if not entry.name.isdigit():
        continue
    pid = int(entry.name)
    if pid in {me, parent}:
        continue
    try:
        raw = (entry / "cmdline").read_bytes()
    except (OSError, PermissionError):
        continue
    if token in raw:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
PY
}

_start_board_companion() {
  _stop_board_companion
  local log_path="${LOG_DIR}/uiir-board-companion.log"
  # Re-check every 3 minutes so newly green landings unlock dependents.
  # Completion: manual + protected todo path otherwise stalls the cascade.
  local loop_cmd="while true; do /usr/bin/python3 \"${ROOT}/scripts/uiir_auto_complete_green_tasks.py\" --root \"${ROOT}\" || true; sleep 180; done"
  if command -v systemd-run >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
    systemd-run --user --collect \
      --unit="uiir-board-companion" \
      --description="UIIR board auto-complete green tasks companion" \
      --property=Type=simple \
      --property="WorkingDirectory=${ROOT}" \
      --property=Restart=on-failure \
      --property=RestartSec=15s \
      --property=KillMode=control-group \
      /bin/bash -c "${loop_cmd}"
    echo "started systemd unit uiir-board-companion"
  else
    nohup /bin/bash -c "${loop_cmd}" >>"$log_path" 2>&1 &
    echo "started board companion pid=$! log=$log_path"
  fi
}

MODE="${1:-start}"
case "$MODE" in
  stop)
    for lane in 0 1 2 3 4 5; do
      stop_lane "$lane"
      echo "stopped lane ${lane}"
    done
    _stop_board_companion
    echo "stopped board companion"
    ;;
  start|restart)
    for lane in 0 1 2 3 4 5; do
      stop_lane "$lane"
      start_lane "$lane"
    done
    _start_board_companion
    echo "provider=${IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER} production_route=${IPFS_ACCELERATE_AGENT_PRODUCTION_PROVIDER_ROUTE}"
    echo "merge_target=${UIIR_MERGE_TARGET_BRANCH} shards=${SHARD_COUNT} strict=no max_restarts=${MAX_RESTARTS}"
    echo "implement_timeout=${IMPLEMENT_TIMEOUT}s log_stall=${LOG_STALL_SECONDS}s"
    echo "board_companion=on (auto-complete green ready tasks every 180s)"
    ;;
  status)
    if command -v systemctl >/dev/null 2>&1; then
      systemctl --user --no-pager --full status uiir-lane-{0,1,2,3,4,5}.service 2>&1 | head -80 || true
      systemctl --user --no-pager --full status uiir-board-companion.service 2>&1 | head -20 || true
    fi
    python3 - <<'PY'
from pathlib import Path
import re
print("uiir supervisors/daemons:")
for entry in Path("/proc").iterdir():
    if not entry.name.isdigit():
        continue
    try:
        raw = (entry / "cmdline").read_bytes()
    except (OSError, PermissionError):
        continue
    if b"uiir_lane_" not in raw and b"uiir_auto_complete_green_tasks" not in raw:
        continue
    if b"uiir_auto_complete_green_tasks" in raw:
        print(f"  pid={entry.name} board_companion")
        continue
    if b"implementation_supervisor" in raw or b"implementation_daemon" in raw:
        m = re.search(rb"uiir_lane_(\d+)", raw)
        kind = "sup" if b"implementation_supervisor" in raw else "daemon"
        print(f"  pid={entry.name} {kind} lane={m.group(1).decode() if m else '?'}")
PY
    ;;
  *)
    echo "usage: $0 {start|stop|restart|status}" >&2
    exit 2
    ;;
esac
