#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export PYTHONPATH="$REPO_ROOT/external/ipfs_accelerate${PYTHONPATH:+:$PYTHONPATH}"

exec python3 -m ipfs_accelerate_py.agent_supervisor.llm_merge_resolver_fallback "$@"
