#!/usr/bin/env bash
# Launch six UIIR implementation lanes with Grok-first agent dispatch.
#
# Intentionally does NOT pass --production-provider-policy.
# That policy forces typed Grok-implement + independent Codex review, which
# blocks board progress when Codex is quota-exhausted. Ordinary agent
# implement uses Grok (grok_quota_codex: Codex only after verified Grok quota).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

export PYTHONPATH="${ROOT}/external/ipfs_accelerate${PYTHONPATH:+:${PYTHONPATH}}"
export PYTHONUNBUFFERED=1

# Force Grok Build agent implement. Do not require independent Codex review.
# (Typed production packet policy is not used by this launcher.)
export IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER="${IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER:-grok}"
export IPFS_ACCELERATE_AGENT_GROK_MODEL="${IPFS_ACCELERATE_AGENT_GROK_MODEL:-grok-4.5}"
export IPFS_ACCELERATE_AGENT_GROK_PERMISSION_MODE="${IPFS_ACCELERATE_AGENT_GROK_PERMISSION_MODE:-bypassPermissions}"
export IPFS_ACCELERATE_AGENT_GROK_BIN="${IPFS_ACCELERATE_AGENT_GROK_BIN:-${HOME}/.local/bin/grok}"

# Never force the typed production packet route for this board.
# (Values 0/false/no/off disable the typed route when a task claims it.)
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
SHARD_COUNT=6

mkdir -p "$STATE_ROOT" "$WORKTREE_ROOT" "$MERGE_QUEUE_DIR" "$LOG_DIR"

stop_lane() {
  local lane="$1"
  local unit="uiir-lane-${lane}.service"
  if command -v systemctl >/dev/null 2>&1; then
    systemctl --user stop "$unit" 2>/dev/null || true
    systemctl --user reset-failed "$unit" 2>/dev/null || true
  fi
  # Kill any residual unmanaged daemon for this state prefix.
  pkill -f "state-prefix uiir_lane_${lane}" 2>/dev/null || true
  pkill -f "state-dir .*ui_ux_ir/state/lane-${lane}" 2>/dev/null || true
}

start_lane() {
  local lane="$1"
  local state_dir="${STATE_ROOT}/lane-${lane}"
  local worktree_dir="${WORKTREE_ROOT}/lane-${lane}"
  local log_path="${LOG_DIR}/uiir-lane-${lane}.log"
  mkdir -p "$state_dir" "$worktree_dir"

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
    --strict-task-sharding
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
    nohup "${cmd[@]}" >>"$log_path" 2>&1 &
    echo "started background lane ${lane} pid=$! log=$log_path"
  fi
}

MODE="${1:-start}"
case "$MODE" in
  stop)
    for lane in 0 1 2 3 4 5; do
      stop_lane "$lane"
      echo "stopped lane ${lane}"
    done
    ;;
  start|restart)
    for lane in 0 1 2 3 4 5; do
      stop_lane "$lane"
      start_lane "$lane"
    done
    echo "provider=${IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER} production_route=${IPFS_ACCELERATE_AGENT_PRODUCTION_PROVIDER_ROUTE}"
    echo "merge_target=${UIIR_MERGE_TARGET_BRANCH}"
    ;;
  status)
    if command -v systemctl >/dev/null 2>&1; then
      systemctl --user --no-pager --full status uiir-lane-{0,1,2,3,4,5}.service 2>&1 | head -80 || true
    fi
    pgrep -af 'uiir_lane_|ui_ux_ir/state/lane-' 2>/dev/null | head -20 || echo "no uiir lane processes"
    ;;
  *)
    echo "usage: $0 {start|stop|restart|status}" >&2
    exit 2
    ;;
esac
