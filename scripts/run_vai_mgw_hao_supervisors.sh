#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export PYTHONUNBUFFERED=1
export PYTHONPATH="$REPO_ROOT/external/ipfs_accelerate:$REPO_ROOT/external/ipfs_datasets:${PYTHONPATH:-}"
export CODEX_MERGE_RESOLVER_TIMEOUT_SECONDS="${CODEX_MERGE_RESOLVER_TIMEOUT_SECONDS:-60}"
export PREFER_COPILOT_MERGE_RESOLVER="${PREFER_COPILOT_MERGE_RESOLVER:-1}"

resolver_command="bash $REPO_ROOT/scripts/llm_merge_resolver_fallback.sh"

module_args=(
  --repo-root "$REPO_ROOT"
  --duration-seconds "${DURATION_SECONDS:-28800}"
  --stamp "${STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
  --master-dir data/agent_supervisor
  --label "VAI/MGW/HAO supervisor run"
  --implementation-supervisor-defaults
  --implementation-supervisor-command "$resolver_command"
  --implementation-track "VAI|scripts/virtual_ai_os_todo_supervisor.py|data/virtual_ai_os/state|virtual_ai_os"
  --implementation-track "MGW|scripts/meta_glasses_display_todo_supervisor.py|data/meta_glasses_display_widgets/state|meta_glasses_display"
  --implementation-track "HAO|scripts/hallucinate_multimodal_control_todo_supervisor.py|data/hallucinate_multimodal_control/state|hallucinate_multimodal_control"
)

exec python3 -m ipfs_accelerate_py.agent_supervisor.multi_supervisor_runner "${module_args[@]}" "$@"
