#!/usr/bin/env bash
# Launch the 3-lane PGIR supervisor with Grok 4.6 default and Codex
# gpt-5.6-terra fallback. Does not start if a parallel master is already live.
set -euo pipefail

PGIR_ROOT=/home/barberb/lift_coding/.pgir_campaign
export PGIR_REPO="$PGIR_ROOT/worktrees/accelerate-authority"
PGIR_RUNTIME="$PGIR_ROOT/runtime"
export PGIR_PY=/home/barberb/.local/bin/python
PGIR_CODEX=/usr/local/bin/codex
PGIR_TARGET=agent/proof-grounded-ir-learning
PGIR_TODO=docs/architecture/proof_grounded_ir_learning.todo.md
PGIR_OBJECTIVES=docs/architecture/proof_grounded_ir_learning.objectives.md
PROVIDER="$PGIR_RUNTIME/pgir_implementation_provider.sh"

export IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER=grok
export IPFS_ACCELERATE_AGENT_GROK_MODEL=grok-4.6
export IPFS_ACCELERATE_AGENT_GROK_BIN=/home/barberb/.local/bin/grok
export IPFS_ACCELERATE_AGENT_CODEX_MODEL=gpt-5.6-terra
export IMPLEMENTATION_DAEMON_COMMAND="$PROVIDER"

if pgrep -af 'multi_supervisor_runner' | grep -F 'proof-grounded-ir-learning-parallel' | grep -v grep >/dev/null; then
  echo "refusing launch: a proof-grounded-ir-learning-parallel master is already live" >&2
  exit 3
fi

if [[ "$(git -C "$PGIR_REPO" branch --show-current)" != "$PGIR_TARGET" ]]; then
  echo "refusing launch: unexpected branch $(git -C "$PGIR_REPO" branch --show-current)" >&2
  exit 2
fi

chmod +x "$PROVIDER"
PGIR_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
cd "$PGIR_REPO"
exec env PYTHONPATH="$PGIR_REPO" "$PGIR_PY" -m \
  ipfs_accelerate_py.agent_supervisor.runtime.multi_supervisor_runner \
  --python-executable "$PGIR_PY" \
  --repo-root "$PGIR_REPO" \
  --duration-seconds 28800 \
  --heartbeat-interval-seconds 30 \
  --supervisor-status-stale-seconds 600 \
  --stop-grace-seconds 10 \
  --stamp "$PGIR_STAMP" \
  --master-dir "$PGIR_RUNTIME/master" \
  --master-log "$PGIR_RUNTIME/master/pgir_parallel_master_${PGIR_STAMP}.log" \
  --master-pid-path "$PGIR_RUNTIME/master/pgir_parallel_master_${PGIR_STAMP}.pid" \
  --label proof-grounded-ir-learning-parallel \
  --implementation-track \
    "pgir|scripts/ops/agent_supervisor/implementation_supervisor_entry.py|$PGIR_RUNTIME/parallel|pgir_parallel" \
  --implementation-supervisor-lanes-per-track 3 \
  --common-arg=--implement \
  --common-arg=--stale-seconds \
  --common-arg=1800 \
  --common-arg=--check-interval \
  --common-arg=60 \
  --common-arg=--daemon-interval \
  --common-arg=120 \
  --common-arg=--implementation-timeout \
  --common-arg=7200 \
  --common-arg=--implementation-log-stall-seconds \
  --common-arg=900 \
  --common-arg=--max-restarts \
  --common-arg=3 \
  --common-arg=--implementation-command \
  --common-arg="$PROVIDER" \
  --common-arg=--llm-merge-resolver-command \
  --common-arg="$PGIR_CODEX exec --approve-for-me --ephemeral -m gpt-5.6-terra" \
  --common-arg=--llm-merge-resolver-timeout-seconds \
  --common-arg=1800 \
  --common-arg=--todo-path \
  --common-arg="$PGIR_TODO" \
  --common-arg=--task-prefix \
  --common-arg="## PGIR-" \
  --common-arg=--max-task-attempts \
  --common-arg=3 \
  --common-arg=--worktree-root \
  --common-arg="$PGIR_RUNTIME/worktrees" \
  --common-arg=--merge-queue-dir \
  --common-arg="$PGIR_RUNTIME/merge_queue" \
  --common-arg=--merge-target-branch \
  --common-arg="$PGIR_TARGET" \
  --common-arg=--worktree-submodule-path \
  --common-arg=ipfs_datasets_py \
  --common-arg=--implementation-protected-path \
  --common-arg="$PGIR_OBJECTIVES" \
  --common-arg=--implementation-protected-path \
  --common-arg="$PGIR_TODO" \
  --common-arg=--implementation-protected-path \
  --common-arg=data/agent_supervisor/proof_grounded_ir_learning/justice_dao_pinset.yaml \
  --common-arg=--objective-path \
  --common-arg="$PGIR_OBJECTIVES" \
  --common-arg=--objective-graph-path \
  --common-arg=data/agent_supervisor/proof_grounded_ir_learning/objective_graph.json \
  --common-arg=--objective-bundle-dir \
  --common-arg=data/agent_supervisor/proof_grounded_ir_learning/bundles \
  --common-arg=--objective-dataset-dir \
  --common-arg=data/agent_supervisor/proof_grounded_ir_learning/datasets \
  --common-arg=--objective-discovery-dir \
  --common-arg=data/agent_supervisor/proof_grounded_ir_learning/discovery \
  --common-arg=--objective-goal-prefix \
  --common-arg=PGIR-G \
  --common-arg=--objective-root-goal-id \
  --common-arg=PGIR-G000 \
  --common-arg=--no-objective-task-janitor \
  --common-arg=--no-objective-goal-completion-reconcile \
  --common-arg=--no-objective-goal-migration \
  --common-arg=--no-objective-goal-refinement \
  --common-arg=--no-objective-ast-dataset \
  --common-arg=--no-objective-todo-vector-index
