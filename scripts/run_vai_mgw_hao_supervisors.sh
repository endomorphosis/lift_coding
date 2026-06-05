#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export PYTHONUNBUFFERED=1
export PYTHONPATH="$REPO_ROOT/external/ipfs_accelerate:$REPO_ROOT/external/ipfs_datasets:${PYTHONPATH:-}"
export CODEX_MERGE_RESOLVER_TIMEOUT_SECONDS="${CODEX_MERGE_RESOLVER_TIMEOUT_SECONDS:-60}"
export PREFER_COPILOT_MERGE_RESOLVER="${PREFER_COPILOT_MERGE_RESOLVER:-1}"

exec python3 "$REPO_ROOT/scripts/run_vai_mgw_hao_supervisors.py" "$@"
