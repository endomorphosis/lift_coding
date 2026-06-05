#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export REPO_ROOT

exec python3 "$REPO_ROOT/scripts/run_vai_mgw_hao_supervisors.py" "$@"
