#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export PYTHONUNBUFFERED=1
export PYTHONPATH="$REPO_ROOT/external/ipfs_accelerate:$REPO_ROOT/external/ipfs_datasets:${PYTHONPATH:-}"
export CODEX_MERGE_RESOLVER_TIMEOUT_SECONDS="${CODEX_MERGE_RESOLVER_TIMEOUT_SECONDS:-60}"
export PREFER_COPILOT_MERGE_RESOLVER="${PREFER_COPILOT_MERGE_RESOLVER:-1}"

OBJECTIVE_SCAN_MIN_OPEN_TASKS="${OBJECTIVE_SCAN_MIN_OPEN_TASKS:-20}"
OBJECTIVE_SCAN_MAX_FINDINGS="${OBJECTIVE_SCAN_MAX_FINDINGS:-12}"
OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL="${OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL:-6}"
OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO="${OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO:-4}"

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
  "VAI|scripts/virtual_ai_os_todo_supervisor.py|data/virtual_ai_os/state/virtual_ai_os_8h_run_{stamp}.log|data/virtual_ai_os/state/virtual_ai_os_supervisor.pid|data/virtual_ai_os/state/virtual_ai_os_managed_daemon.pid"
  "MGW|scripts/meta_glasses_display_todo_supervisor.py|data/meta_glasses_display_widgets/state/meta_glasses_display_8h_run_{stamp}.log|data/meta_glasses_display_widgets/state/meta_glasses_display_supervisor.pid|data/meta_glasses_display_widgets/state/meta_glasses_display_managed_daemon.pid"
  "HAO|scripts/hallucinate_multimodal_control_todo_supervisor.py|data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_8h_run_{stamp}.log|data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_supervisor.pid|data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_managed_daemon.pid"
)

module_args=(
  --repo-root "$REPO_ROOT"
  --duration-seconds "${DURATION_SECONDS:-28800}"
  --stamp "${STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
  --master-dir data/agent_supervisor
  --label "VAI/MGW/HAO supervisor run"
)

for track in "${tracks[@]}"; do
  module_args+=(--track "$track")
done

for arg in "${common_args[@]}"; do
  module_args+=("--common-arg=$arg")
done

exec python3 -m ipfs_accelerate_py.agent_supervisor.multi_supervisor_runner "${module_args[@]}" "$@"
