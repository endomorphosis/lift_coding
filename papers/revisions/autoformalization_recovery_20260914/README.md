# Autoformalization recovery — 14 September 2026

This document records the initial recovery diagnosis. The subsequent [empirical revision](../autoformalization_empirical_20260914/README.md) now contains completed native compiler/model cohorts and ongoing learned evaluation. Its [task list](../autoformalization_empirical_20260914/EMPIRICAL_TODO.md) is the current progress record.

At the initial recovery inspection, the original empirical programme was incomplete. The previous 29/29 figure described a narrowed manuscript workflow, and should not have been presented as completion of the requested experiments. The author's clarification about unavailable outside reviewers did not cancel automated evaluation work.

The final PDF matches its retained build. Real three-seed training and 114 guidance diagnostics ran, but all three promotions returned `no_candidate`. The 1,913-unit final population remains unrun. The primary tables contain status entries rather than the planned measurements. The detailed causes and original evidence links are in [INCOMPLETENESS_AUDIT.md](INCOMPLETENESS_AUDIT.md).

## What was recovered and actually checked

| Component | Observed recovery result |
|---|---|
| Native Lean/solvers | Three positive controls accepted, two invalid candidates rejected; six Z3/CVC5 results agree with the declared first-order controls. |
| Actual canonical compiler | Six constructed examples through the real external module and existing project virtualenv: four successful IR outputs, two explicit abstentions. No implementation replica or installation. |
| Portland autoencoder | Located, hash/CID verified, loaded through the actual API, and exported 64 learned features. CPU-only process exited after 2.67 seconds, using about 368 MiB peak RSS. |
| Paper-training autoencoders | All six T2/T3 final checkpoint files located. Their approximately 5.879 GB JSON files were inventoried rather than loaded simultaneously. |
| Temporary Leanstral | Initial startup timed out and cleaned up. One retry loaded in 251.469 seconds, completed five real local requests, and exited. Hard retry limits: 600 seconds total, 360 seconds startup, four CPU cores, 90 GiB memory, no swap. |
| Model proof checking | Original strict response protocol accepted 0/5. A separately recorded post-hoc extraction of first-turn chat framing verified two unedited generated proof bodies with Lean and no added axioms. Three other outputs remained inadmissible; four raw responses had reached the 128-token cap. This is not a confirmatory success-rate estimate. |

No final-test examples were accessed. No new training, downloads, external submission, or persistent service was started. The original PDFs, sources, and supplements remain unchanged. The permanent `ipfs-accelerate-leanstral.service` remains masked; cleanup verification found no temporary jobs, no owned server, and no listener on port 8080.

## Evidence and commands

- [Recovery tasks](RECOVERY_TODO.md): explicit remaining work; these are not new completed receipts in the historical supervisor database.
- [Autoencoder inventory](autoencoder_inventory.md) and [checkpoint manifest](autoencoder_inventory.json).
- [Native compiler and autoencoder checks](native_compiler_probe/README.md).
- [Native checker summary](native_probe_v2/summary.json).
- [Original model-run summary](leanstral_retry_probe/summary.json), [post-hoc framing recheck](saved_response_recheck/summary.json), and [cleanup verification](leanstral_final_cleanup.json).
- [Qualified runtime paths](runtime_profile.json).
- [Temporary runner instructions](../../../scripts/run_leanstral_ephemeral.md).

From the repository root, a fresh native-only check is:

```sh
python3 -B scripts/autoformalization_recovery_probe.py --native-only --output /tmp/af-native-recovery
```

Use a fresh output directory. The temporary model runner accepts a bounded client command and automatically releases its server when that command exits. The runner's 14 lifecycle tests and the probe's 9 proof/response-boundary tests passed. The first native probe's virtual-memory-limit failure and the first model startup timeout remain in the record.

## Remaining paper work

Build a source-only autoencoder prediction/evaluation path, implement actual learned-feature consumption with its qualification records, freeze model response framing and budgets, and execute the planned held-out automated comparisons before regenerating the paper's tables. Target-assisted reconstruction, global feature export, and status-filled tables cannot replace those results. Independent human semantic fidelity remains unmeasured; it is not an engineering execution gate.
