#!/bin/bash
set -euo pipefail
A=papers/revisions/autoformalization_empirical_20260914/autoencoder
S=papers/revisions/autoformalization_empirical_20260914/pipeline/final.sources.jsonl
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 CUDA_VISIBLE_DEVICES=
while ! test -f "$A/final/worker0/execution_receipt.json" || ! test -f "$A/final/worker1/execution_receipt.json"; do
 if ! kill -0 58585 2>/dev/null && ! test -f "$A/final/worker0/execution_receipt.json"; then exit 71; fi
 if ! kill -0 58586 2>/dev/null && ! test -f "$A/final/worker1/execution_receipt.json"; then exit 72; fi
 sleep 10
done
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
