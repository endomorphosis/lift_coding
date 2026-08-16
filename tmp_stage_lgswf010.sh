#!/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
OUT="$ROOT/tmp_stage_result.txt"
{
  echo "start"
  echo "PWD=$ROOT"
  cd "$ROOT"
  echo "=== check ignore ==="
  git -C external/ipfs_accelerate check-ignore -v \
    ipfs_accelerate_py/agent_supervisor/core/world_snapshot_contracts.py \
    test/agent_supervisor/core/test_world_snapshot_contracts.py || true
  echo "=== force add submodule files ==="
  git -C external/ipfs_accelerate add -f -- \
    ipfs_accelerate_py/agent_supervisor/core/world_snapshot_contracts.py \
    test/agent_supervisor/core/test_world_snapshot_contracts.py
  echo "=== submodule ls-files ==="
  git -C external/ipfs_accelerate ls-files --stage -- \
    ipfs_accelerate_py/agent_supervisor/core/world_snapshot_contracts.py \
    test/agent_supervisor/core/test_world_snapshot_contracts.py || true
  echo "=== add receipt ==="
  git add -- artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-010.json
  echo "=== superproject status ==="
  git status --short -- \
    artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-010.json \
    external/ipfs_accelerate || true
  echo "=== pytest ==="
  export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
  export PYTHONPATH="$ROOT/external/ipfs_accelerate${PYTHONPATH:+:$PYTHONPATH}"
  /usr/bin/python3.12 -m pytest -q \
    external/ipfs_accelerate/test/agent_supervisor/core/test_world_snapshot_contracts.py
  echo "done"
} >"$OUT" 2>&1 || {
  echo "FAILED rc=$?" >>"$OUT"
  exit 1
}
