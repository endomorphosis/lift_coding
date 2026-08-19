#!/usr/bin/env bash
set -euo pipefail

FACP_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)"
FACP_CONFIG="config/formal_assurance_control_plane_scheduler.json"
FACP_SCHEDULER="$FACP_ROOT/external/ipfs_accelerate/scripts/ops/agent_supervisor/configured_board_scheduler.py"
FACP_VALIDATOR="$FACP_ROOT/scripts/validate_formal_assurance_control_plane_board.py"
FACP_RUNTIME="$FACP_ROOT/data/agent_supervisor/formal_assurance_control_plane_v2"
FACP_STATE="$FACP_RUNTIME/state"
FACP_LOGS="$FACP_RUNTIME/logs"
FACP_MASTER_PID="$FACP_STATE/configured-board-master.pid"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=0
export IPFS_DATASETS_AUTO_INSTALL=false
export IPFS_AUTO_INSTALL=false
export IPFS_DATASETS_PY_MINIMAL_IMPORTS=1
export IPFS_ACCELERATE_AGENT_GROK_BIN="${IPFS_ACCELERATE_AGENT_GROK_BIN:-/home/barberb/.local/bin/grok}"
export PYTHONPATH="$FACP_ROOT/external/ipfs_accelerate:$FACP_ROOT/external/ipfs_datasets:$FACP_ROOT/external/ipfs_kit${PYTHONPATH:+:$PYTHONPATH}"

facp_scheduler() {
  python3 "$FACP_SCHEDULER" --repo-root "$FACP_ROOT" --config "$FACP_CONFIG" "$@"
}

facp_master_identity() {
  if [[ ! -f "$FACP_MASTER_PID" ]]; then
    return 1
  fi
  local facp_pid
  facp_pid="$(tr -d '[:space:]' < "$FACP_MASTER_PID")"
  if [[ ! "$facp_pid" =~ ^[1-9][0-9]*$ ]] || ! kill -0 "$facp_pid" 2>/dev/null; then
    return 1
  fi
  local facp_cmd facp_cwd
  facp_cmd="$(tr '\0' ' ' < "/proc/$facp_pid/cmdline")"
  facp_cwd="$(readlink -f "/proc/$facp_pid/cwd")"
  if [[ "$facp_cwd" != "$FACP_ROOT" ]] || [[ "$facp_cmd" != *"ipfs_accelerate_py.agent_supervisor.runtime.multi_supervisor_runner"* ]]; then
    return 2
  fi
  printf '%s\t%s\t%s\n' "$facp_pid" "$facp_cwd" "$facp_cmd"
}

facp_status() {
  printf 'controller_root=%s\n' "$FACP_ROOT"
  printf 'branch=%s\n' "$(git -C "$FACP_ROOT" branch --show-current)"
  if facp_identity="$(facp_master_identity)"; then
    printf 'master=live\t%s\n' "$facp_identity"
  else
    facp_identity_status=$?
    if [[ "$facp_identity_status" -eq 2 ]]; then
      printf 'master=identity_mismatch\n'
    else
      printf 'master=absent_or_dead\n'
    fi
  fi

  local facp_latest_log=""
  if [[ -d "$FACP_LOGS" ]]; then
    facp_latest_log="$(find "$FACP_LOGS" -maxdepth 1 -type f -name 'configured-board-*.log' -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -n 1 | cut -d' ' -f2-)"
  fi
  if [[ -n "$facp_latest_log" ]]; then
    printf 'latest_log=%s\n' "$facp_latest_log"
    tail -n 20 "$facp_latest_log"
  fi

  python3 - "$FACP_STATE" <<'PY'
import json
import sys
from pathlib import Path

state = Path(sys.argv[1])
for path in sorted(state.glob("lane-*/*_supervisor_status.json")):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"file": str(path), "read_error": str(exc)}, sort_keys=True))
        continue
    keys = (
        "status",
        "updated_at",
        "supervisor_pid",
        "daemon_pid",
        "restart_count",
        "last_exit_code",
        "last_recycle_reason",
        "active_worker_count",
        "stalled_without_active_worker",
        "backpressure",
        "backpressure_reasons",
    )
    print(json.dumps({"file": str(path), **{key: payload.get(key) for key in keys}}, sort_keys=True))
for path in sorted(state.glob("lane-*/*_task_state.json")):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"file": str(path), "read_error": str(exc)}, sort_keys=True))
        continue
    keys = (
        "heartbeat_at",
        "last_progress_at",
        "active_task_id",
        "active_phase",
        "implementation_in_progress",
        "completed_count",
        "task_count",
        "ready_count",
        "eligible_ready_count",
        "blocked_count",
        "blocked_task_ids",
        "selection_idle_reason",
        "last_implementation_returncode",
        "last_merge_returncode",
        "last_merge_error",
    )
    print(json.dumps({"file": str(path), **{key: payload.get(key) for key in keys}}, sort_keys=True))
PY
}

facp_doctor() {
  python3 "$FACP_VALIDATOR" --check-all
  facp_scheduler preflight
}

facp_start() {
  local facp_identity_status=0
  facp_master_identity >/dev/null 2>&1 || facp_identity_status=$?
  if [[ "$facp_identity_status" -eq 0 ]]; then
    printf 'formal-assurance supervisor is already live\n' >&2
    facp_status
    return 0
  fi
  if [[ "$facp_identity_status" -eq 2 ]]; then
    printf 'refusing launch: master PID belongs to a foreign process\n' >&2
    return 2
  fi
  facp_doctor
  facp_scheduler launch --implement --duration-seconds "${FACP_DURATION_SECONDS:-28800}"
  facp_status
}

facp_stop() {
  local facp_identity=""
  local facp_identity_status=0
  facp_identity="$(facp_master_identity)" || facp_identity_status=$?
  if [[ "$facp_identity_status" -ne 0 ]]; then
    if [[ "$facp_identity_status" -eq 2 ]]; then
      printf 'refusing stop: master PID belongs to a foreign process\n' >&2
      return 2
    fi
    printf 'formal-assurance supervisor is not live\n'
    return 0
  fi
  local facp_pid
  facp_pid="${facp_identity%%$'\t'*}"
  kill -TERM "$facp_pid"
  printf 'sent SIGTERM to verified master pid %s\n' "$facp_pid"
}

case "${1:-}" in
  doctor)
    facp_doctor
    ;;
  dry-run)
    facp_doctor
    facp_scheduler launch --implement --dry-run
    ;;
  start)
    facp_start
    ;;
  status)
    facp_status
    ;;
  stop)
    facp_stop
    ;;
  *)
    printf 'usage: %s {doctor|dry-run|start|status|stop}\n' "$0" >&2
    exit 64
    ;;
esac
