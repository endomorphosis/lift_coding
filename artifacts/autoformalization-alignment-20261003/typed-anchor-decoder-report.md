# Typed rule generation and learned source anchors

Date: 2026-10-04. Status: completed development experiment; every proposal remains unaccepted and every semantic review remains pending.

The new source-conditioned typed generator and separate learned anchor head reproduce all 16 weak TRAIN proposals under each of three fixed seeds, including all 124 source anchors. They match none of the six available weak DEV references; two unavailable positives remain in the eight-positive DEV denominator. This establishes a working training and output path while exposing a compositional generalization gap. It supplies no independent source-fidelity or production-quality estimate.

The [recovery report](typed-anchor-decoder-recovery-01/report.json), [fixed recovery plan](typed-anchor-decoder-recovery-01/plan.json) and [posthoc diagnostics](typed-anchor-decoder-recovery-01/posthoc_weak_diagnostics.json) preserve the results. The [improvement plan](../../implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md) incorporates their implications.

## Model and data boundaries

The retained typed owner, [legal_formula_learning.py](../../external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/legal_formula_learning.py), supplies a new TRAIN-fitted `source_conditioned_formula_v1` generation: source GRU, attention and formula GRU, with 44,257 parameters in 12 tensors. Its closed TRAIN vocabulary represents canonical aliases and flat qualifier lists; source and target sequences are bounded at 64 tokens. The prepared canonical targets need 19–22 typed tokens. These are separate checkpoint generations from the old incompatible retained vocabulary and from the native768 span-copy lineages.

The new [canonical_typed_anchors.py](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_typed_anchors.py) freezes the complete trained parent and its typed-token embeddings, then learns 4,354 parameters in eight tensors for start/end prediction. At inference, the parent generates a canonical rule from source text. Only that generated rule supplies the head's typed leaf queries. The head predicts complete original-character spans; ties, overlaps and incomplete proposals abstain. Exact source slices reconstruct the anchored byte-codec contract. No reference prefix, supplied candidate IR, grammar-constructed answer or target label enters inference.

The [34 inference requests](typed-anchor-decoder-recovery-01/inference_requests.json) contain only ID, exact source, declared context and the context-resolution requirement. Source warnings and the closed source vocabulary admit 22 requests, with six unsupported-profile outcomes, four clarification outcomes and two source-OOV outcomes retained in every denominator. Supplied unresolved context remains a clarification requirement. This baseline uses its own source-token encoder; it consumes none of the cached 8D, 384D, 768D or Leanstral vectors. No external embedding production, Leanstral inference or prover call ran.

Only 16 parser-derived weak TRAIN proposals from four source groups enter fitting. All 34 human reviews remain pending. Strong semantic, contrastive, proof and fidelity-evaluation masks remain zero. Each group has four records and 31 anchors; the prepared 0.25 group weights are not consumed by these APIs. The actual losses are token-normalized source cross-entropy and mean start/end cross-entropy per anchor per batch.

## Fixed experiment and interruption recovery

Seeds 1729, 1730 and 1731 use learning rate 0.008, batch size eight, source hidden width 64 and token/query embedding width 32. Source and head each complete 100 epochs and 200 updates per seed. Zero-step controls and last completed checkpoints are retained; tuning is empty and DEV labels select no checkpoint. All twelve primary and three private generation receipts are saved before this run parses the six weak DEV proposal bodies. The cohort was previously exposed development material.

The [original runner](run_typed_anchor_decoder.py) hit SIGXCPU at its 240-second CPU safety limit. Its [failure inventory](typed-anchor-decoder-recovery-01/interrupted_stage_inventory.json) freezes all 36 partial files and 11 checkpoints. All three source fits and two head fits were saved, totaling 1,000 durable updates. The third head's unsaved work is unknown within 0–200 updates; the first worker's final CPU, RSS and wall observations are unavailable.

The separately frozen [recovery runner](run_typed_anchor_decoder_recovery.py) restored those assets and trained only the missing seed1731 head from its saved zero-step state. It set native thread environment limits before Torch import and Torch intra/inter-op threads to one. Recovery took 11.066 seconds wall, 11.060 seconds worker CPU and 737,108 KiB peak RSS. These measurements concern recovery alone. The cause of the first worker's CPU consumption has not been established.

Completed checkpoint ancestry contains exactly 1,200 updates. Actual attempted experiment work is bounded at 1,210–1,410 updates, including the recorded disposable ten-update timing canary and the unsaved interruption interval. Unit-test fixture updates and historical training are outside that experiment accounting. No source fit was repeated during recovery.

## Free-running results

| Seed | Final canonical TRAIN weak exact | Final complete TRAIN weak exact | Final canonical / complete DEV weak exact | Complete proposals / all requests | Anchor abstentions |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1729 | 16 / 16 | 16 / 16 | 0 / 8, with six references available | 17 / 34 | 5 |
| 1730 | 16 / 16 | 16 / 16 | 0 / 8, with six references available | 16 / 34 | 6 |
| 1731 | 16 / 16 | 16 / 16 | 0 / 8, with six references available | 16 / 34 | 6 |

Every initial source generator emits 22 structurally valid canonical proposals but matches no weak TRAIN or DEV reference. Each trained source generator still emits 22 canonical proposals, now matching all TRAIN references. Adding an initial anchor head produces zero complete proposals; training that head produces the counts above. The unchanged unsupported, clarification and OOV counts add 12 requests to each row's outcome accounting.

Posthoc facet comparisons on the six available DEV references identify action/object mismatches in all six seed1729 rules; seed1730 has five actor and three action/object mismatches; seed1731 has three actor, three action and six object mismatches. These labels are weak diagnostics. Seed1729's extra DEV proposal has exactly the reference's span coordinates while assigning `notify`/`applicant` where the weak reference assigns `retain`/`filing`. Correct offsets alone therefore cannot establish symbol interpretation. The structural transport contract permits such a proposal; it does not grant acceptance.

Recovery replays every completed original output exactly. Pipeline parent receipts match the same-seed canonical-only generation bitwise. Three disjoint private source/head restores reproduce complete final receipts exactly, with actual numerical state, checkpoint metadata and Torch RNG unchanged. Hooks record 132 canonical-only source-generation encoder forwards, 198 pipeline source-generation forwards, 198 frozen anchor-feature forwards and 198 head forwards. Method invocation counts and actual numerical forwards are recorded separately. The nested proposal's `model_executed=False` flag describes static transport validation; generation provenance resides in the enclosing observations.

## Verification and next work

The seven-file focused suite passed **537 tests in 9.49 seconds**, including 63 new head/checkpoint/inference tests. Ruff passes the implementation, tests, both experiment runners and the saved-artifact validator. Independent read-only reviews checked experiment boundaries; the [independent artifact audit](typed-anchor-independent-audit-01/audit.json) verifies 440 file bindings and all checkpoint, replay and diagnostic joins. The [stage validation](typed-anchor-decoder-validation-01/validation.json) recomputes joins, masks, checkpoint progress, weak comparisons and transport structure from saved files; it performs no numerical replay or semantic review. All 336 preceding checked bindings, previous codec/test pins, partial files, checkpoint owners, the frozen protocol and the clean isolated decoder checkout remain preserved.

Final validation found the earlier isolated checkout absent from disk and Git's worktree registration, although its local branch still identified commit `64bc5734dc82db72e955f2e809b770127e9b6cfc`. It was restored at the same path and branch from that commit; all 16 frozen source-file bindings match the committed and restored bytes. A persistent Git worktree lock now marks its study references. The disappearance's cause is unknown. The new typed-anchor owner remains separately hash-bound in the canonical tree.

The next experiment should address source-to-symbol binding and novel facet combinations using a new independently reviewed, group-split corpus. Compare source-grounded symbol inventories, explicit actor/action/object binding objectives and profile-bound symbol-to-anchor consistency checks, retaining this source-only baseline. Freeze new arms and their selection rules before using development results. More epochs on the same 16 examples have no demonstrated generalization benefit.

Then compare real, disabled, zero and full-order rotated conditioning independently for 8D, 384D and 768D; preserve raw retrieval controls and evaluate context interpretation separately. Full byte generation remains an untrained alternative requiring an actual matched-budget comparison. Source/formal contrastive alignment, verified demonstration retrieval, bounded Leanstral repair and Leanstral hidden-layer pooling retain the independent evaluation and runtime boundaries in the improvement plan. This canary changes no production compiler, selected encoder, logic-family catalog or acceptance policy.
