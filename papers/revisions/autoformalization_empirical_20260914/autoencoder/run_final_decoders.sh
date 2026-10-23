#!/bin/bash
set -euo pipefail
A=papers/revisions/autoformalization_empirical_20260914/autoencoder
S=papers/revisions/autoformalization_empirical_20260914/pipeline/final.sources.jsonl
PARENT_SHA=699d6107b5d5558059a6f704fb5634d18a45969c33350a6f4a8c29dbf89181eb
PROFILE_SHA=531c37db1b0c464750ed1c34951fb3ac35002a4bb74addf4ba00da86d4642e75
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 CUDA_VISIBLE_DEVICES=
.venv/bin/python -B "$A/bind_final_inputs.py" --profile "$A/scientific_profile.json" --profile-sha256 "$PROFILE_SHA" --sources "$S" --embeddings "$A/final/source_embeddings.jsonl" --parent-protocol-sha256 "$PARENT_SHA" --output "$A/final/input_binding.json"
timeout --signal=TERM --kill-after=10s 5400s .venv/bin/python -B "$A/cached_execution_parallel.py" --sources "$S" --embeddings "$A/final/source_embeddings.jsonl" --freeze "$A/final/input_binding.json" --split final --output-dir "$A/final/worker0" --amendment "$A/cache_execution_amendment.json" --worker-index 0 --cpu-affinity 14,15 > "$A/final/worker0.log" 2>&1 &
worker0_pid=$!
timeout --signal=TERM --kill-after=10s 5400s .venv/bin/python -B "$A/cached_execution_parallel.py" --sources "$S" --embeddings "$A/final/source_embeddings.jsonl" --freeze "$A/final/input_binding.json" --split final --output-dir "$A/final/worker1" --amendment "$A/cache_execution_amendment.json" --worker-index 1 --cpu-affinity 16,17 > "$A/final/worker1.log" 2>&1 &
worker1_pid=$!
wait "$worker0_pid"
wait "$worker1_pid"
python3 -B "$A/collect_cached_workers.py" --root "$A/final" --sources "$S" --split final --freeze "$A/final/input_binding.json" --amendment "$A/cache_execution_amendment.json"
python3 -B "$A/training_mean_baseline.py" --sources "$S" --output "$A/final/training_mean.raw_predictions.jsonl" --freeze "$A/training_mean_baseline.freeze.json"
python3 -B "$A/complete_mean_prediction_metadata.py" --raw "$A/final/training_mean.raw_predictions.jsonl" --output "$A/final/training_mean.predictions.jsonl"
.venv/bin/python -B "$A/score_embeddings.py" --predictions "$A/final/training_mean.predictions.jsonl" --embeddings "$A/final/source_embeddings.jsonl" --output "$A/final/training_mean.scores.json"
.venv/bin/python -B "$A/score_embeddings.py" --predictions "$A/final/T0.predictions.jsonl" --embeddings "$A/final/source_embeddings.jsonl" --output "$A/final/T0.scores.json"
for seed in 104729 130363 155921; do
 timeout --signal=TERM --kill-after=10s 600s prlimit --as=4294967296:4294967296 .venv/bin/python -B "$A/derive_t1.py" --t0-predictions "$A/final/T0.predictions.jsonl" --sources "$S" --embeddings "$A/final/source_embeddings.jsonl" --compact "$A/compact/T1-$seed.json" --freeze "$A/final/input_binding.json" --output "$A/final/T1-$seed.predictions.jsonl"
 .venv/bin/python -B "$A/score_embeddings.py" --predictions "$A/final/T1-$seed.predictions.jsonl" --embeddings "$A/final/source_embeddings.jsonl" --output "$A/final/T1-$seed.scores.json"
 .venv/bin/python -B "$A/score_embeddings.py" --predictions "$A/final/T2-$seed.predictions.jsonl" --embeddings "$A/final/source_embeddings.jsonl" --output "$A/final/T2-$seed.scores.json"
 timeout --signal=TERM --kill-after=10s 600s prlimit --as=4294967296:4294967296 .venv/bin/python -B "$A/derive_t3.py" --t2-predictions "$A/final/T2-$seed.predictions.jsonl" --t2-compact "$A/compact/T2-$seed.json" --t3-compact "$A/compact/T3-$seed.json" --freeze "$A/final/input_binding.json" --output "$A/final/T3-$seed.predictions.jsonl"
 .venv/bin/python -B "$A/score_embeddings.py" --predictions "$A/final/T3-$seed.predictions.jsonl" --embeddings "$A/final/source_embeddings.jsonl" --output "$A/final/T3-$seed.scores.json"
done
