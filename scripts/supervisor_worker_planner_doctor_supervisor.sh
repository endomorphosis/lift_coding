#!/usr/bin/env bash
# Operate parallel implementation supervisor lanes for the WPD board.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ACCEL_ROOT="${REPO_ROOT}/external/ipfs_accelerate"
PYTHON_BIN="${WPD_PYTHON_BIN:-python3}"
RUNNER_MODULE="${WPD_RUNNER_MODULE:-ipfs_accelerate_py.agent_supervisor.runtime.multi_supervisor_runner}"
LABEL="worker-planner-doctor"
TARGET_BRANCH="agent/worker-planner-doctor-integration"
LANE_COUNT="${WPD_LANE_COUNT:-3}"
DURATION_SECONDS="${WPD_DURATION_SECONDS:-28800}"

PLAN_PATH="implementation_plan/docs/47-supervisor-worker-planner-doctor-integration-plan-2026-08-06.md"
OBJECTIVE_PATH="implementation_plan/docs/47-supervisor-worker-planner-doctor-integration.objectives.md"
TODO_PATH="implementation_plan/docs/47-supervisor-worker-planner-doctor-integration.todo.md"
SCHEDULER_PATH="config/supervisor_worker_planner_doctor_integration_scheduler.json"
SUPERVISOR_CONFIG_PATH="config/supervisor_worker_planner_doctor_supervisor.json"
VALIDATOR_PATH="scripts/validate_supervisor_worker_planner_doctor_board.py"
LAUNCHER_PATH="scripts/supervisor_worker_planner_doctor_supervisor.sh"
ENTRY_SCRIPT="external/ipfs_accelerate/scripts/ops/agent_supervisor/implementation_supervisor_entry.py"

DEFAULT_STATE_BASE="${XDG_STATE_HOME:-${HOME}/.local/state}/ipfs_accelerate_py/worker-planner-doctor-v1"
PROGRAM_ROOT="${IPFS_WPD_STATE_ROOT:-${DEFAULT_STATE_BASE}}"
RUNTIME_ROOT="${PROGRAM_ROOT}/runtime"
STATE_ROOT="${PROGRAM_ROOT}/state"
WORKTREE_ROOT="${PROGRAM_ROOT}/worktrees"
MERGE_QUEUE_ROOT="${PROGRAM_ROOT}/merge-queue"
MASTER_PID_PATH="${RUNTIME_ROOT}/master.pid"
MASTER_LOG_PATH="${RUNTIME_ROOT}/master.log"
MASTER_DIR="${RUNTIME_ROOT}"

export IPFS_WPD_STATE_ROOT="${PROGRAM_ROOT}"
export PYTHONPATH="${ACCEL_ROOT}:${REPO_ROOT}/external/ipfs_datasets:${REPO_ROOT}/external/ipfs_kit${PYTHONPATH:+:${PYTHONPATH}}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=0
export IPFS_DATASETS_AUTO_INSTALL=false
export IPFS_AUTO_INSTALL=false
export IPFS_DATASETS_PY_MINIMAL_IMPORTS=1
export IPFS_ACCEL_SKIP_CORE="${IPFS_ACCEL_SKIP_CORE:-0}"
# Reviewed ordered provider route (multi_supervisor_runner seal_ordered_implementation_provider_route)
export IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER="grok_cli"
export IPFS_ACCELERATE_AGENT_IMPLEMENTATION_FALLBACK_PROVIDER="codex"
export IPFS_ACCELERATE_AGENT_IMPLEMENTATION_FALLBACK_TRIGGER="primary_quota_exhausted"
export IPFS_ACCELERATE_AGENT_GROK_MODEL="grok-4.5"
export IPFS_ACCELERATE_AGENT_CODEX_MODEL="gpt-5.6-terra"
export IPFS_ACCELERATE_AGENT_CODEX_REASONING_EFFORT="medium"
export IPFS_ACCELERATE_AGENT_RECLAIM_DEAD_WORKTREE_LEASES_ON_STARTUP="${IPFS_ACCELERATE_AGENT_RECLAIM_DEAD_WORKTREE_LEASES_ON_STARTUP:-1}"
# Avoid legacy "auto" selection if present in the parent environment
unset IMPLEMENTATION_DAEMON_COMMAND 2>/dev/null || true

CONTROL_PATHS=(
  "${PLAN_PATH}"
  "${OBJECTIVE_PATH}"
  "${TODO_PATH}"
  "${SCHEDULER_PATH}"
  "${SUPERVISOR_CONFIG_PATH}"
  "${VALIDATOR_PATH}"
  "${LAUNCHER_PATH}"
)

die() {
  echo "error: $*" >&2
  exit 2
}

require_branch() {
  local branch
  branch="$(git -C "${REPO_ROOT}" branch --show-current)"
  if [[ "${branch}" != "${TARGET_BRANCH}" ]]; then
    die "refusing branch '${branch}'; expected '${TARGET_BRANCH}' (use worktree .worktrees/worker-planner-doctor)"
  fi
}

validate_board() {
  "${PYTHON_BIN}" "${REPO_ROOT}/${VALIDATOR_PATH}" --check-all
}

doctor() {
  require_branch
  for rel in "${CONTROL_PATHS[@]}"; do
    [[ -f "${REPO_ROOT}/${rel}" ]] || die "missing control artifact: ${rel}"
  done
  validate_board >/dev/null
  echo "doctor: healthy"
  echo "  repo=${REPO_ROOT}"
  echo "  branch=$(git -C "${REPO_ROOT}" branch --show-current)"
  echo "  state=${PROGRAM_ROOT}"
  echo "  lanes=${LANE_COUNT}"
}

status() {
  echo "=== WPD supervisor status ==="
  echo "state_root=${PROGRAM_ROOT}"
  if [[ -f "${MASTER_PID_PATH}" ]]; then
    local pid
    pid="$(tr -d '[:space:]' <"${MASTER_PID_PATH}" || true)"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      echo "master_pid=${pid} (alive)"
    else
      echo "master_pid=${pid:-none} (stale or missing process)"
    fi
  else
    echo "master_pid=none"
  fi
  if [[ -f "${MASTER_LOG_PATH}" ]]; then
    echo "--- master log (tail) ---"
    tail -n 40 "${MASTER_LOG_PATH}" || true
  fi
  # Per-lane task state if present
  if [[ -d "${STATE_ROOT}" ]]; then
    find "${STATE_ROOT}" -name '*task_state.json' 2>/dev/null | head -20 | while read -r p; do
      echo "lane_state=${p}"
    done
  fi
  validate_board | "${PYTHON_BIN}" -c 'import json,sys; d=json.load(sys.stdin); print("board_valid=", d.get("valid")); print("ready=", d.get("ready_task_ids")); print("completed=", d.get("completed_task_ids"))'
}

start() {
  require_branch
  doctor
  mkdir -p "${RUNTIME_ROOT}" "${STATE_ROOT}" "${WORKTREE_ROOT}" "${MERGE_QUEUE_ROOT}"

  if [[ -f "${MASTER_PID_PATH}" ]]; then
    local pid
    pid="$(tr -d '[:space:]' <"${MASTER_PID_PATH}" || true)"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      echo "WPD supervisor already running (pid=${pid})"
      status
      return 0
    fi
    rm -f "${MASTER_PID_PATH}"
  fi

  # multi_supervisor_runner expects accelerate on PYTHONPATH and entry relative to repo
  if [[ ! -f "${REPO_ROOT}/${ENTRY_SCRIPT}" ]]; then
    die "missing implementation entry: ${ENTRY_SCRIPT}"
  fi

  (
    cd "${REPO_ROOT}"
    # shellcheck disable=SC2086
    nohup "${PYTHON_BIN}" -m "${RUNNER_MODULE}" \
      --repo-root "${REPO_ROOT}" \
      --duration-seconds "${DURATION_SECONDS}" \
      --heartbeat-interval-seconds 5 \
      --exit-when-all-tracks-terminal \
      --master-dir "${MASTER_DIR}" \
      --master-log "${MASTER_LOG_PATH}" \
      --master-pid-path "${MASTER_PID_PATH}" \
      --label "${LABEL}" \
      --implementation-track "wpd|${ENTRY_SCRIPT}|${STATE_ROOT}|wpd" \
      --implementation-supervisor-lanes-per-track "${LANE_COUNT}" \
      --implementation-supervisor-strict-task-sharding \
      --common-arg=--todo-path \
      --common-arg="${TODO_PATH}" \
      --common-arg=--task-prefix \
      --common-arg=WPD- \
      --common-arg=--implement \
      --common-arg=--max-task-attempts \
      --common-arg=5 \
      --common-arg=--implementation-retry-budget \
      --common-arg=3 \
      --common-arg=--validation-retry-budget \
      --common-arg=3 \
      --common-arg=--merge-retry-budget \
      --common-arg=3 \
      --common-arg=--implementation-timeout \
      --common-arg=7200 \
      --common-arg=--implementation-max-timeout \
      --common-arg=10800 \
      --common-arg=--implementation-log-stall-seconds \
      --common-arg=1200 \
      --common-arg=--daemon-interval \
      --common-arg=60 \
      --common-arg=--check-interval \
      --common-arg=30 \
      --common-arg=--stale-seconds \
      --common-arg=1800 \
      --common-arg=--watchdog-startup-grace-seconds \
      --common-arg=300 \
      --common-arg=--worktree-root \
      --common-arg="${WORKTREE_ROOT}" \
      --common-arg=--worktree-submodule-path \
      --common-arg=external/ipfs_accelerate \
      --common-arg=--worktree-submodule-path \
      --common-arg=external/ipfs_datasets \
      --common-arg=--worktree-submodule-path \
      --common-arg=external/ipfs_kit \
      --common-arg=--merge-target-branch \
      --common-arg="${TARGET_BRANCH}" \
      --common-arg=--merge-queue-dir \
      --common-arg="${MERGE_QUEUE_ROOT}" \
      --common-arg=--implementation-protected-path \
      --common-arg="${PLAN_PATH}" \
      --common-arg=--implementation-protected-path \
      --common-arg="${OBJECTIVE_PATH}" \
      --common-arg=--implementation-protected-path \
      --common-arg="${TODO_PATH}" \
      --common-arg=--implementation-protected-path \
      --common-arg="${SCHEDULER_PATH}" \
      --common-arg=--implementation-protected-path \
      --common-arg="${SUPERVISOR_CONFIG_PATH}" \
      --common-arg=--implementation-protected-path \
      --common-arg="${VALIDATOR_PATH}" \
      --common-arg=--implementation-protected-path \
      --common-arg="${LAUNCHER_PATH}" \
      --common-arg=--no-objective-task-janitor \
      --common-arg=--no-objective-goal-refinement \
      --common-arg=--no-objective-goal-migration \
      --common-arg=--no-reconciliation-guardrail \
      --common-arg=--no-retry-budget-guardrail \
      --common-arg=--no-dependency-guardrail \
      --common-arg=--log-level \
      --common-arg=INFO \
      >"${MASTER_LOG_PATH}.launch" 2>&1 &
    echo $! >"${MASTER_PID_PATH}"
  )

  sleep 2
  status
  echo "started WPD parallel supervisor (lanes=${LANE_COUNT})"
  echo "logs: ${MASTER_LOG_PATH}"
}

stop() {
  if [[ -f "${MASTER_PID_PATH}" ]]; then
    local pid
    pid="$(tr -d '[:space:]' <"${MASTER_PID_PATH}" || true)"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" || true
      sleep 2
      if kill -0 "${pid}" 2>/dev/null; then
        kill -9 "${pid}" || true
      fi
      echo "stopped master pid=${pid}"
    fi
    rm -f "${MASTER_PID_PATH}"
  else
    echo "no master pid file"
  fi
  # Best-effort stop of lane children
  pkill -f "label=${LABEL}" 2>/dev/null || true
  pkill -f "worker-planner-doctor" 2>/dev/null || true
}

case "${1:-}" in
  doctor) doctor ;;
  status) status ;;
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  validate) validate_board ;;
  *)
    echo "usage: $0 {doctor|validate|start|status|stop|restart}" >&2
    exit 2
    ;;
esac
