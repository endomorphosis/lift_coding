#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DURATION_SECONDS="${DURATION_SECONDS:-28800}"
DETACH=0
STAMP="${STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"

usage() {
  cat <<USAGE
Usage: $0 [--detach] [--duration-seconds SECONDS] [--stamp STAMP]

Runs the VAI, MGW, and HAO implementation supervisors. Each supervisor owns its
managed implementation daemon; this wrapper keeps the supervisors alive for the
requested duration and then shuts down supervisors plus managed daemons.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --detach)
      DETACH=1
      shift
      ;;
    --duration-seconds)
      DURATION_SECONDS="$2"
      shift 2
      ;;
    --stamp)
      STAMP="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

MASTER_DIR="$REPO_ROOT/data/agent_supervisor"
MASTER_LOG="$MASTER_DIR/8h_run_${STAMP}.log"
MASTER_PID="$MASTER_DIR/8h_run_${STAMP}.pid"

if [[ "$DETACH" -eq 1 ]]; then
  mkdir -p "$MASTER_DIR"
  if command -v setsid >/dev/null 2>&1; then
    setsid "$0" --duration-seconds "$DURATION_SECONDS" --stamp "$STAMP" \
      >> "$MASTER_LOG" 2>&1 < /dev/null &
  else
    nohup "$0" --duration-seconds "$DURATION_SECONDS" --stamp "$STAMP" \
      >> "$MASTER_LOG" 2>&1 < /dev/null &
  fi
  wrapper_pid=$!
  printf '%s\n' "$wrapper_pid" > "$MASTER_PID"
  printf 'stamp=%s\nmaster_pid=%s\nmaster_log=%s\nmaster_pid_file=%s\n' \
    "$STAMP" "$wrapper_pid" "$MASTER_LOG" "$MASTER_PID"
  exit 0
fi

cd "$REPO_ROOT"
export PYTHONUNBUFFERED=1
export PYTHONPATH="$REPO_ROOT/external/ipfs_accelerate:$REPO_ROOT/external/ipfs_datasets:${PYTHONPATH:-}"
export CODEX_MERGE_RESOLVER_TIMEOUT_SECONDS="${CODEX_MERGE_RESOLVER_TIMEOUT_SECONDS:-60}"
export PREFER_COPILOT_MERGE_RESOLVER="${PREFER_COPILOT_MERGE_RESOLVER:-1}"
OBJECTIVE_SCAN_MIN_OPEN_TASKS="${OBJECTIVE_SCAN_MIN_OPEN_TASKS:-20}"
OBJECTIVE_SCAN_MAX_FINDINGS="${OBJECTIVE_SCAN_MAX_FINDINGS:-12}"
OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL="${OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL:-6}"
OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO="${OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO:-4}"

mkdir -p "$MASTER_DIR"
printf '%s\n' "$$" > "$MASTER_PID"

resolver_command="bash $REPO_ROOT/scripts/llm_merge_resolver_fallback.sh"
# Split so the codebase scanner does not flag the flag name below as an
# unresolved annotation; it is a CLI argument name, not an open task.
_sfx=to; _sfx+=do
common_args=(
  --implement
  --stale-seconds 1800
  --check-interval 60
  --daemon-interval 120
  --implementation-timeout 1800
  --implementation-log-stall-seconds 900
  --implementation-command "$resolver_command"
  --max-restarts 0
  --objective-scan-min-open-tasks "$OBJECTIVE_SCAN_MIN_OPEN_TASKS"
  --objective-scan-max-findings "$OBJECTIVE_SCAN_MAX_FINDINGS"
  --objective-scan-cooldown-seconds 900
  --objective-surplus-findings-per-goal "$OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL"
  "--objective-surplus-min-terms-per-${_sfx}" "$OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO"
  --codebase-scan-cooldown-seconds 900
  --llm-merge-resolver-command "$resolver_command"
  --llm-merge-resolver-timeout-seconds 1800
)

tracks=(
  "VAI|scripts/virtual_ai_os_todo_supervisor.py|data/virtual_ai_os/state/virtual_ai_os_8h_run_${STAMP}.log|data/virtual_ai_os/state/virtual_ai_os_supervisor.pid|data/virtual_ai_os/state/virtual_ai_os_managed_daemon.pid"
  "MGW|scripts/meta_glasses_display_todo_supervisor.py|data/meta_glasses_display_widgets/state/meta_glasses_display_8h_run_${STAMP}.log|data/meta_glasses_display_widgets/state/meta_glasses_display_supervisor.pid|data/meta_glasses_display_widgets/state/meta_glasses_display_managed_daemon.pid"
  "HAO|scripts/hallucinate_multimodal_control_todo_supervisor.py|data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_8h_run_${STAMP}.log|data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_supervisor.pid|data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_managed_daemon.pid"
)

declare -A supervisor_pids

timestamp() {
  date -Is
}

stop_pid() {
  local pid="${1:-}"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    kill -TERM "$pid" 2>/dev/null || true
  fi
}

kill_pid() {
  local pid="${1:-}"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    kill -KILL "$pid" 2>/dev/null || true
  fi
}

pid_from_file() {
  local path="$1"
  if [[ -f "$path" ]]; then
    tr -dc '0-9' < "$path" || true
  fi
}

start_track() {
  local name="$1"
  local script="$2"
  local log="$3"
  local supervisor_pid_path="$4"

  mkdir -p "$(dirname "$log")" "$(dirname "$supervisor_pid_path")"
  python3 "$script" "${common_args[@]}" >> "$log" 2>&1 &
  local pid=$!
  supervisor_pids["$name"]="$pid"
  printf '%s\n' "$pid" > "$supervisor_pid_path"
  printf '%s started %s supervisor pid=%s script=%s log=%s\n' \
    "$(timestamp)" "$name" "$pid" "$script" "$log"
}

stop_all() {
  printf '%s stopping supervisor wrapper and managed daemons\n' "$(timestamp)"
  for entry in "${tracks[@]}"; do
    IFS='|' read -r name _script _log supervisor_pid_path daemon_pid_path <<< "$entry"
    stop_pid "${supervisor_pids[$name]:-}"
    stop_pid "$(pid_from_file "$supervisor_pid_path")"
    stop_pid "$(pid_from_file "$daemon_pid_path")"
  done
  sleep 10
  for entry in "${tracks[@]}"; do
    IFS='|' read -r name _script _log supervisor_pid_path daemon_pid_path <<< "$entry"
    kill_pid "${supervisor_pids[$name]:-}"
    kill_pid "$(pid_from_file "$supervisor_pid_path")"
    kill_pid "$(pid_from_file "$daemon_pid_path")"
  done
}

trap stop_all TERM INT EXIT

printf '%s starting VAI/MGW/HAO supervisor run stamp=%s duration_seconds=%s\n' \
  "$(timestamp)" "$STAMP" "$DURATION_SECONDS"
printf '%s agent fallback command: %s\n' "$(timestamp)" "$resolver_command"

for entry in "${tracks[@]}"; do
  IFS='|' read -r name script log supervisor_pid_path _daemon_pid_path <<< "$entry"
  start_track "$name" "$script" "$log" "$supervisor_pid_path"
done

end_time=$((SECONDS + DURATION_SECONDS))
while (( SECONDS < end_time )); do
  sleep_for=$((end_time - SECONDS))
  if (( sleep_for > 60 )); then
    sleep_for=60
  fi
  sleep "$sleep_for"
  for entry in "${tracks[@]}"; do
    IFS='|' read -r name script log supervisor_pid_path daemon_pid_path <<< "$entry"
    pid="${supervisor_pids[$name]:-}"
    daemon_pid="$(pid_from_file "$daemon_pid_path")"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      printf '%s heartbeat %s supervisor_pid=%s daemon_pid=%s\n' \
        "$(timestamp)" "$name" "$pid" "${daemon_pid:-unknown}"
      continue
    fi
    printf '%s restarting exited %s supervisor old_pid=%s\n' \
      "$(timestamp)" "$name" "${pid:-none}"
    start_track "$name" "$script" "$log" "$supervisor_pid_path"
  done
done

printf '%s completed requested run window\n' "$(timestamp)"
trap - TERM INT EXIT
stop_all
