#!/bin/bash
set -euo pipefail
exec 9>/tmp/autoformalization-empirical-heavy.lock
flock 9
A=papers/revisions/autoformalization_empirical_20260914/autoencoder
S=papers/completion/runtime_bootstrap/unblock_20260912/af029_recovery/memory_lifetime_recovery/resource_amendment_v1/execution_source/papers/completion/autoformalization/receipts/snapshots/AF-004/selection.sources.jsonl
for arm in T0 T1 T2 T3; do
  args=()
  if test "$arm" != T0; then args+=(--compact "$A/compact/$arm-104729.json"); fi
  if test "$arm" = T2 || test "$arm" = T3; then args+=(--vectors "$A/vectors/T2-104729"); fi
  timeout --kill-after=5s 300s .venv/bin/python -B "$A/source_only_eval.py" --sources "$S" --embeddings "$A/selection/source_embeddings.jsonl" --output "$A/selection/$arm-104729.fixed2.projection.jsonl" --split selection "${args[@]}"
  .venv/bin/python -B "$A/score_embeddings.py" --predictions "$A/selection/$arm-104729.fixed2.projection.jsonl" --embeddings "$A/selection/source_embeddings.jsonl" --output "$A/selection/$arm-104729.fixed2.projection.scores.json"
done
