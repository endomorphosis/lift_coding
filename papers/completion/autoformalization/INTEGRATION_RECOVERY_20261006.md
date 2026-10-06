# Bounded recovery of historical autoformalization findings

This directory combines the retained early research snapshot with a bounded recovery from `agent/vericodegen-2026-autoformalization` at commit `091624a773179d24178d12bc1f410864885c10bf`. That branch was already an ancestor of workspace `origin/main` at `3b0162bebe0b7a09727081cb8c5f5c15378caba1`, but 1,082 of its files were absent from the effective main tree. An ancestry check alone therefore did not preserve its completed findings.

The recovery restores 23 absent files, totaling 699,974 bytes, from exact committed blobs: denominator accounting and its tests/contracts, three reproducible result tables and their summary, and authentic scalar training, checkpoint, cost and failed guidance-activation evidence. The existing protocol, experiment plan, source manifests, historical task board and manuscript are preserved. This is a partial historical recovery; it does not turn the early task board into a current completion ledger.

The corrected evidence records three-seed T2/T3 training and a separate check of saved training bytes. The original checker/container OOM remains failed. T2's perfect cosine and zero MSE were target-assisted projection measurements; they did not demonstrate source-free reconstruction. Its family cross-entropy was unchanged from T0. T3 feedback concerned compiler structural contracts. The subsequent AF-013 diagnostics returned `no_candidate` for all three seeds, with missing proof receipts, view-family weights, canonical contracts and promotion-eligible guidance. Learned features were not applied, T4 remained unavailable, and arm E remained locked.

These findings inform current work by keeping target-assisted reconstruction, actual source-only decoding, family coverage, compiler guidance and proof admission separately attributable. The historical accounting tool accepts supplied receipt classifications; it is not the current admission gate. Only an actual `lake build <Lib>` under the current pinned implementation can grant Lean admission. No restored file grants a checkpoint qualification, source-fidelity result, or statute formalization.

The metadata retains hashes and references to large checkpoints and external execution receipts. Those payloads and the full external dependency closure are not included in this recovery. Historical launchers, provider gateways, native model qualification routines and their runtime dependencies are intentionally outside this bounded selection. Restoring a scalar receipt is not rerunning or independently validating its historical model execution.

The pure replay commands are:

```bash
python3 -B -m unittest discover -s papers/completion/autoformalization/evaluation -p 'test_result_accounting.py'
python3 -B papers/completion/autoformalization/evaluation/final_correction/regenerate_tables.py --check
```

They verify 30 accounting tests and the exact three table hashes. They use synthetic accounting fixtures and retained metadata, with no model, encoder, provider, native theorem prover or final-test execution. The reconstruction summary SHA-256 is `d369e99ec3bcc9d1bbd12361ca73300d2297b5363806be77dcd2625889bb2276`.

The recovery inventory, exact blob/source hashes, main preimages, dependency bindings and validation receipts are recorded in `artifacts/autoencoder-integration-review-20261006/pipeline/`. Current autoencoder experiments and their qualification decisions remain in the canonical datasets implementation and its separately versioned evidence.
