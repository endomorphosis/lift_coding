# Autoencoder inventory — 14 September 2026

The autoencoders are present. Two different model lineages must be kept separate: Portland's legacy legal-IR advisor and the paper's AF-029 models trained on its own frozen train/selection partitions. Neither existing checkpoint is itself a text-to-canonical-IR decoder.

This inventory read code, checkpoint metadata, and pre-existing development/qualification receipts. It did not open held-out final examples, run inference or training, download models, or start services. File hashes in the accompanying JSON distinguish freshly computed hashes from identities copied from retained AF-029 receipts.

## Portland legacy model

Repository: `/home/barberb/portland-laws.github.io/ipfs_datasets_py`, commit `6cd037c7738f44904add46391537588e67f6f238`.

The exact checkpoint pinned by the semantic round-trip benchmark is:

`archive/workspace/todo-queues/legal-ir-daemon-restart12-20260608T075001Z-best-8h-autoencoder.state.json`

It exists locally, is 25,895,338 bytes, and freshly hashes to `1446cb1859ddf4ed40fb5576f6e320eece4cec268a008c5c07bffeaf959cd8dd` (CID `bafkreiaui3frqwo56twub62vo33ogihozzgoyjukacgfyb5772xzlhgy3u`). It contains real learned feature/embedding/logit tables, including 52,142 feature embedding rows and 32,746 feature family-logit rows. It has no decoded-embedding sample memory; the loader's export excludes all memory heads, source text, source identifiers, and target embeddings. Its global stable export has 64 features.

The implementation is `ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_autoencoder.py`: `ModalAutoencoderTrainingState.from_dict` / `.load_json`, `AdaptiveModalAutoencoder`, `.encode`, `.decode`, `.evaluate`, and `.export_stable_legal_ir_features`. Input is a `LegalSample` (source text, deterministic modal IR, frame choices, and a declared source embedding); decode returns an embedding vector, not CanonicalRuleIR. CPU operation is supported; no model download or long-running server is required to load/export this checkpoint. `build_us_code_sample` defaults to a mock embedding and must receive the actual declared embedding for measured embedding claims.

There is also a distinct 398,209,746-byte `workspace/todo-queues/legal-ir-autoencoder-canonical.state.json`, recommended by the retained 30 June weight review as an average of ten historical states. Do not silently substitute it for the frozen 25.9 MB checkpoint. Historical cosine/CE scores in that review are training/development diagnostics and are not paper held-out semantic measurements.

The actual missing component is explicit in `benchmarks/semantic_roundtrip/constructors/autoencoder_guided.py` and `causal_autoencoder_guidance.py`: no implemented, qualified adapter maps the stable learned features into source-grounded canonical field changes. The retained `workspace/benchmarks/semantic-roundtrip-compositions/causal_autoencoder_guidance_qualification.json` excludes all 12 guided compositions with `unavailable_no_reviewed_causal_l1_adapter`. Its review-CID and change-receipt fields are software qualification requirements; they do not establish a need for NeurIPS manuscript reviewers. Loading a checkpoint alone will not enable those arms, and adding a no-op annotation must not be scored as guidance.

## Paper AF-029 models

The real training output root is:

`/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/af029_recovery/memory_lifetime_recovery/resource_amendment_v1/run_v1/output`

`checkpoints/native_training/manifest.json` records three seeds (104729, 130363, 155921), three T2 models with five applied packed-CPU candidate updates per seed, and three matched T3 models with 256 isolated proof-head updates. T2/T3 disable sample memory. Training/selection comprise 69/15 rows; the final test did not select settings. The encoder is real cached `sentence-transformers/all-MiniLM-L6-v2` revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` with the recorded windowed preprocessing, not the mock embedding default.

All six final checkpoint files exist under `evidence/native_training/states/T{2,3}-{seed}-final.json`; each is approximately 5.879 GB JSON. Their exact paths, sizes, state identities, and retained file hashes are in `autoencoder_inventory.json`. This discovery used metadata rather than parsing six large states. They have different identities and training populations from the Portland checkpoint; do not mix results or swap them under an existing arm name.

The AF-029 training evaluator `diagnostic_eval` (run_native_training.py:414) calls encode/decode and measures vector cosine/MSE and modal-family CE. Its item records explicitly leave source fidelity null. `emit_split` evaluates train and selection; it is not a held-out final text-to-IR evaluation. T3 deliberately preserves T2 reconstruction parameters, so identical reconstruction scores do not imply T3 failed to train. Its isolated proof heads require their own prediction/output evaluation.

## Smallest meaningful next evaluation

1. Keep existing training and checkpoints. First build a bounded consumer qualification using constructed or development examples, with a declared fixed output vocabulary and no final-data access. Freeze the consumer code and inference settings before a final evaluation.
2. For T2, evaluate its actual modal-family or fixed-vocabulary view predictions, separately from any downstream canonical IR claims. Build source-only features and cached source embeddings. Disable sample memory and exclude compiler/reference targets from the prediction call. Predictions should be written before the scorer reads references. Compare with the declared T0 baseline on the same source families.
3. Do not pass reference-derived keys into `_legal_ir_view_distribution(sample, target_distribution, ...)`: that function uses target keys to determine candidate output labels. Supply a fixed declared vocabulary through a source-only prediction wrapper instead. Also bypass embedding routines that choose candidates with target-vector assistance if asserting source-independent reconstruction. Source embedding input for an autoencoder is valid, but reconstructing its own input embedding is not evidence that natural-language legal meaning was preserved.
4. For canonical-guidance claims, implement a genuine feature-to-field adapter, retain exact before/after field changes and feature IDs, and independently code-review its source-vocabulary/cardinality behavior. Predeclare the adapter and compare guidance on/off. A global stable-feature export alone cannot justify canonical-field mutations.
5. Load one AF-029 state in an isolated child process with a hard timeout, limited threads, and a measured memory ceiling. Prefer a bounded extraction/compact representation for only the needed heads after verifying equivalence; the naive JSON loader creates several copies and is an avoidable resource hazard. Release the process after the batch. Keep Leanstral as a separate optional, one-shot runner; these local AE diagnostics do not require it.

## Commands and APIs (not executed here)

The frozen legacy export is already implemented and can be qualified with a 60-second CPU-only process; this exports learned features and does not score semantics:

```sh
cd /home/barberb/portland-laws.github.io/ipfs_datasets_py
timeout --signal=TERM --kill-after=5s 60s env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 -B -c 'from benchmarks.semantic_roundtrip.constructors.autoencoder_guided import load_frozen_autoencoder_guidance; g = load_frozen_autoencoder_guidance(); print(g.state_sha256, g.stable_export["feature_count"])'
```

The loader API `load_frozen_autoencoder_guidance(path)` verifies the exact hash/CID before export. `StableLegalIRFeatureExport.to_dict()` provides `feature_count` and `stable_features`. The command uses the local checkout and remains unexecuted in this discovery pass.

AF-029's existing loader is `load_state_checkpoint(path)` in the frozen `execution_source/.../evaluation/run_native_training.py`; it verifies embedded state identity, protected parameter fingerprint, and input identity, then uses `ModalAutoencoderTrainingState.from_dict`. Do not invoke that training script's main function merely to evaluate a checkpoint. A source-only evaluation CLI is still required and should expose `--checkpoint`, `--sources`, `--output`, `--timeout`, `--threads`, and `--max-rss`; it must reject target/reference paths at inference. No pretend executable command is provided for this missing consumer.

## Follow-up runtime qualification

The recovered legacy checkpoint has now been successfully loaded and exported through its actual native loader in 2.673 seconds (367.89 MiB peak RSS), yielding 64 stable features. The existing `lift_coding/.venv` supplies multiformats; no installation was needed. See `native_compiler_probe/README.md` and the full JSON receipts. The native canonical compiler also ran on six constructed inputs: four successes and two typed abstentions. This follow-up accessed no final-test examples, loaded no AF029 large checkpoint, and started no service.
