# Retrieval policies and review ingestion — 2026-10-03

All **25 frozen geometries and 75 policy comparisons completed**. Geometric diversity improves this panel's raw retrieval coverage and relevance without training another projection model. Predicted-facet coverage weakens raw-geometry retrieval despite perfect authored-label argmax predictions from its probe. The [full report](retrieval-01/report.json) retains per-item rankings and selection traces; the [compact summary](retrieval-summary.json) provides smaller group/style tables. The [runbook](../../external/ipfs_datasets/docs/autoencoders/alignment_retrieval_experiment.md) documents reproduction and review ingestion.

These are exposed synthetic development results. They do not establish independent source fidelity, successful formalization generation, or useful native proofs. No production promotion is made.

## Fixed comparison

The study reuses the same 360 training rows, 120 development rows, and 90 unique training candidates. It retains **every** prior projection checkpoint: raw source geometry, 12 projected source geometries, and 12 projected formal geometries. Each supplies a normalized cosine shortlist of 20 candidates; every policy selects five from that exact shortlist. No previous best seed or checkpoint is selected.

The policies are cosine ranking, maximum marginal relevance (`mmr`), and independent predicted-facet coverage (`facet_cover`). MMR keeps query relevance while penalizing similarity to examples already selected. Facet coverage uses a single training-only raw-384D ridge probe shared by all geometries. Query reference labels enter only afterward for evaluation.

Values for projected geometries below average all three fixed seeds. Support means joint actor/modality/object and action/modality/object demonstrations both occur in the selected set. nDCG measures authored core-facet relevance over the same candidate pool.

| Geometry / prior action-negative weight | Cosine support / nDCG | MMR support / nDCG | Facet cover support / nDCG |
| --- | --- | --- | --- |
| Raw 384D | 60.8% / .8772 | **85.8% / .9168** | 36.7% / .7218 |
| Projected source 384D / 1 | 66.9% / .8661 | 90.3% / .9106 | 80.8% / .8784 |
| Projected source 384D / 2 | 80.8% / .8750 | 93.3% / .9152 | 86.9% / .8783 |
| Projected source 512D / 1 | 64.7% / .8629 | 89.2% / .9060 | 76.9% / .8724 |
| Projected source 512D / 2 | 71.7% / .8680 | 92.2% / .9105 | 83.6% / .8805 |
| Projected formal 384D / 1 | 57.8% / .8066 | 65.3% / .7927 | 64.4% / .8234 |
| Projected formal 384D / 2 | 52.8% / .7980 | 62.5% / .7958 | 58.6% / .8149 |
| Projected formal 512D / 1 | 56.7% / .8080 | 66.4% / .7939 | 65.8% / .8264 |
| Projected formal 512D / 2 | 47.8% / .7805 | 61.4% / .7691 | 58.3% / .8011 |

Raw MMR raises complementary support by **25.0 percentage points**, from 73/120 to 103/120, and nDCG from .8772 to .9168. This establishes a stronger inexpensive development control. The 384D weighted source arm plus MMR has higher support at 93.3%, but slightly lower nDCG than raw MMR. Those are separate objectives, and the reused development panel does not justify selecting a final production model.

The individual candidate ceiling remains three of four facets because actor–action combinations are held out. Retrieval supplies complementary demonstrations; it does not reconstruct the missing complete rule or prove its interpretation. Only five development groups are present, so comparisons remain descriptive without rowwise significance claims.

## What happened to the regressions

The [previous projection study](projection-report.md) exposed different failure modes. Formal clerk/certify retrieval omitted certify demonstrations across all wording styles. Projected source officer/inspect retrieval crowded out officer demonstrations, especially in wording style 2. Clerk/certify source retrieval also gained many lower-ranked candidates matching neither its actor nor its action.

For the previously investigated 384D, weight-2 source geometry, three-seed means now show:

| Held-out group | Cosine support / nDCG | MMR support / nDCG | Top-20 support ceiling |
| --- | --- | --- | --- |
| Clerk/certify | 97.2% / .8111 | 100% / .8572 | 100% |
| Officer/inspect | 81.9% / .8907 | 95.8% / .9335 | 100% |

The source selector repairs most of the support loss, but clerk/certify relevance still falls below raw MMR's .9114. This remains a composition regression to investigate.

The corresponding formal clerk/certify geometry remains substantially weaker: MMR support is only 4.2%, against a 79.2% top-20 ceiling. In about one fifth of those shortlist outcomes the required action demonstration is absent entirely; in most other cases selection still discards it. Formal officer/inspect support also does not improve under these selectors. Increasing diversity alone therefore does not resolve the formal representation problem.

Shortlist ceilings use the selector's exact normalized shortlist, including deterministic ties. They are post-ranking authored diagnostics and never feed gold facets or an oracle choice into selection.

## Why the predicted-facet policy failed

The train-only ridge probe matches all four authored core labels on all 120 development rows. That is a narrow label diagnostic, not independent semantic fidelity. Its softmax masses remain uncalibrated: mean winning mass is about .396 for actors and .398 for actions, leaving roughly 60% total mass on other labels.

Independent coverage rewards newly covered label values once each. After a correct value has been covered, incorrect alternatives can still earn coverage credit. It also lacks the joint modality/object constraints required by the support metric. These mechanisms are consistent with raw facet-cover support falling to 36.7% despite correct argmax labels. The counterexample tests and observed result motivate a separate future joint-support objective, with training-only calibration, rather than promoting this policy.

## Review ingestion is runnable; review is still pending

The new [admission CLI](../../external/ipfs_datasets/scripts/ops/legal_ir/admit_alignment_reviews.py) accepts SHA-pinned organizer and reviewer files and writes a fresh receipt. The [current CLI receipt](review-admission-02/review_admission.json) and the experiment's admission record retain **40 pending items**, zero preliminary adjudication candidates, and no authenticated reviewer or author-independence evidence. No human annotations were synthesized.

Completed submissions must preserve exact source/item bindings and supply typed facets, explicit ambiguity/unsupported flags, reviewer identity, and UTC time. Incomplete slots stay pending. Conflicting annotations stay disputed. Matching submissions from two declared reviewer IDs create only an unauthenticated preliminary candidate; agreement alone grants no fidelity, proof, or production authority. The reader rejects changed digests, duplicate JSON keys, altered sources, symlinks, and nonregular inputs.

Continue handing reviewers only [reviewer_items.json](projection-01/reviewer_items.json). Keep organizer references and admission receipts separate from their source-only handoff.

## Next improvements

1. Keep raw MMR as a required inexpensive control when comparing new encoders, autoencoder representations, or learned alignment. Evaluate it on independently grouped, richer source material before production changes.
2. Test joint actor/action–modality–object coverage using inference-available facet predictions, with any calibration fitted on training-only folds. Preserve the current negative result and retain the same demonstration budget.
3. Improve compositional formal alignment and action-sensitive candidate discovery. Track shortlist availability separately from selector retention so missing demonstrations are not mistaken for selection failures.
4. Complete source-only human review and independence attestations before measuring the primary fidelity endpoint. Add nonempty qualifiers, scope, and binder cases before claiming those capabilities.
5. Preserve independent 8D, 768D, and Leanstral embedding lanes. Native input/checkpoint admission, broader profile support, proof-state traces, generation, and checker experiments remain separate dependencies in the [comprehensive plan](../../implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md).

## Evidence

The local computation completed in **26.96 seconds**. The probe used one CPU thread and float64 ridge; prior projection heads ran float32 inference. Existing projection, autoencoder, and source-encoder weights were not retrained. No LLM, provider, native prover, or sealed final-test input was used.

All **307 focused tests passed in 9.10 seconds**, exit 0; Ruff passed for the eight new Python files. Actual retrieval and review-admission CLIs also exited 0. [retrieval-validation.json](retrieval-validation.json) records commands and exact file identities. All 3,000 cosine query rankings reproduce the previous candidate ordering; small normalization score differences stay below 2.6e−7. Checkpoint generations and earlier evidence were preserved.

Report canonical payload SHA256: `481a36770b96820f6045582424fae02e81cbaeaa839fdaba755041f6e17c7841`.

The protected AF-002 protocol remains unchanged. Listed source bindings are not a complete dependency closure. Independent fidelity remains `unavailable`, native useful-proof coverage remains `unrun`, and qualification and production admission remain false.
