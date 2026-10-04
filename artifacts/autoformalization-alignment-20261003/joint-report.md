# Joint complementary-example selection — 2026-10-03

All **25 frozen geometries and 75 comparisons completed**. Hard joint selection raises the raw baseline's authored complementary-example support from **103/120 to 120/120**, while reducing nDCG from **.9168 to .9013**. It reaches the available top-20 support ceiling in every geometry. The remaining formal-target support losses are therefore candidate-availability failures on this panel, rather than further selector-retention failures.

These are repeated, exposed synthetic development comparisons. They establish neither independent source fidelity nor successful formalization generation or useful proofs. No production model or policy is selected.

The [compact machine report](joint-01/report.json) contains every geometry's group/style summaries and SHA-bound paths to 25 detailed artifacts. Preserve those files together. The [runbook](../../external/ipfs_datasets/docs/autoencoders/alignment_joint_retrieval_experiment.md) documents execution and the objectives. [joint-validation.json](joint-validation.json) binds source files, commands, inputs, and evidence.

## Fixed experiment

The study reuses the same 360 training rows, 120 development rows, 90 training candidates, prior ridge probe, prediction distributions, and all 12 projection checkpoints. No model, probe, or calibration is fitted. Every geometry compares MMR, hard joint coverage, and soft joint coverage, selecting five examples from its exact normalized cosine shortlist of 20. All 3,000 MMR query/geometry rankings and selection traces replay the previous study exactly, with zero cosine-score difference.

A candidate supplies an actor/modality/object triple and an action/modality/object triple. Hard coverage rewards only the two argmax-predicted triples. Soft coverage weights distinct triples by products of their three predicted facet masses. Each family-triple receives credit once; the two family sums are averaged. Both selectors use `.7 × normalized cosine + .3 × marginal coverage`.

The soft products are an uncalibrated factorized proxy. They are not probabilities of complementary support in one common context. Hard predictions can be wrong, and relevance-weighted greedy selection does not generally guarantee available support. Development reference labels enter only after rankings are fixed.

## Full comparison

Projected cells average the three fixed seeds; no best seed is chosen. Support requires both an actor/modality/object demonstration and an action/modality/object demonstration in the selected set. nDCG measures authored core-facet relevance over the same training pool. These are separate objectives.

| Geometry / prior action-negative weight | MMR support / nDCG | Hard joint support / nDCG | Soft joint support / nDCG |
| --- | --- | --- | --- |
| Raw 384D | 85.8% / .9168 | **100% / .9013** | 100% / .8684 |
| Projected source 384D / 1 | 90.3% / .9106 | 100% / .8933 | 86.7% / .8852 |
| Projected source 384D / 2 | 93.3% / .9152 | 100% / .8940 | 94.7% / .8868 |
| Projected source 512D / 1 | 89.2% / .9060 | 100% / .8929 | 83.1% / .8827 |
| Projected source 512D / 2 | 92.2% / .9105 | 100% / .8935 | 88.9% / .8848 |
| Projected formal 384D / 1 | 65.3% / .7927 | 98.9% / .8917 | 70.3% / .8328 |
| Projected formal 384D / 2 | 62.5% / .7958 | 95.8% / .8697 | 70.0% / .8262 |
| Projected formal 512D / 1 | 66.4% / .7939 | 98.1% / .8953 | 68.6% / .8337 |
| Projected formal 512D / 2 | 61.4% / .7691 | 94.2% / .8627 | 63.3% / .8129 |

Hard selection recovers all 17 raw-MMR misses, which occur in executor/issue. Its overall relevance still falls because improvements in that group accompany relevance losses elsewhere. All 12 projected-source hard arms also reach 100% support; their mean nDCG remains below the raw hard control. Learned source heads therefore add no complementary support beyond this inexpensive raw control on this panel.

Hard selection improves both support and nDCG in every aggregate formal arm relative to its own MMR control. This is a substantive selection improvement, but formal aggregate relevance still trails raw MMR and raw hard selection. It is not evidence that the learned formal representation improves the overall system.

Soft selection reaches 100% raw support but reduces raw nDCG further. It also has mixed support effects in projected-source arms. The result preserves the earlier warning that predicted coverage and relevance can diverge; the soft objective should not be promoted from its name or aggregate averages.

## Previously weak compositions

For the previously investigated 384D, action-negative-weight-2 checkpoints, three-seed means are:

| Geometry / held-out group | MMR support / nDCG | Hard joint support / nDCG | Soft joint support / nDCG | Top-20 support ceiling |
| --- | --- | --- | --- | --- |
| Source clerk/certify | 100% / .8572 | 100% / .8295 | 100% / .8263 | 100% |
| Source officer/inspect | 95.8% / .9335 | 100% / .9152 | 100% / .9009 | 100% |
| Formal clerk/certify | 4.2% / .6564 | **79.2% / .7684** | **0% / .6956** | 79.2% |
| Formal officer/inspect | 77.8% / .8362 | 100% / .9006 | 90.3% / .8604 | 100% |

Hard selection recovers every available formal clerk/certify combination in these shortlists, but about one fifth lack the required action demonstration. Soft selection still loses complementary support completely, even as its nDCG rises. That negative result shows why relevance alone is insufficient to assess compositional demonstration sets.

Across all 12 formal geometries, hard selection covers 1,393/1,440 query/geometry outcomes; all 47 misses coincide with the available shortlist ceiling. All lack action support, while actor support is available in every formal shortlist. The misses comprise 16 custodian/register, 20 clerk/certify, and 11 executor/issue outcomes. These are repeated outcomes for the same 120 queries, not 1,440 independent sources. Equality with every geometry's ceiling is an observed result, not an algorithmic guarantee. Shortlist ceilings are authored post-ranking diagnostics and never supply oracle labels or choices to selection.

## Implications for the improvement plan

1. Retain raw MMR and raw hard joint selection as separate fixed controls. MMR preserves stronger aggregate relevance; hard joint supplies complementary examples more consistently here. Test their downstream effect on generated formal statements before treating retrieval support as an autoformalization improvement.
2. Prioritize action-sensitive formal candidate discovery and compositional representation. Hard selection now exhausts available support in this panel, so further selector tuning cannot recover demonstrations excluded by the fixed shortlist. A future source/formal retrieval union must retain the same shortlist and demonstration budgets for a fair comparison.
3. Move evaluation toward richer, independently reviewed sources: nonempty conditions, exceptions and temporal clauses, scope, binding, unseen vocabulary, and additional domains and logic families. The present four-facet probe/evaluation and five development groups cannot qualify those capabilities. The formal codec has seven facet blocks, but its three qualifier blocks contain only empty fields here.
4. Complete source-only review and identity/author-independence evidence before measuring primary fidelity. The same [40-item reviewer handoff](projection-01/reviewer_items.json) remains pending, with zero preliminary adjudication candidates. No reviewer annotations or sign-offs were synthesized.
5. Admit the independent 8D, native 768D, and Leanstral embedding lanes before numerical comparison. Inspected 768D asset directories and downstream decoder checkpoint were unconfigured; this does not establish their global absence. Leanstral's declared 4096D hidden width still requires an actual embedding interface and pooling/tokenizer/checkpoint receipts. The [comprehensive plan](../../implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md) keeps statement alignment, proof-state alignment, generation, family routing, and native checking as separate work packages.

This recipe was designed in response to development diagnostics. Its fixed comparisons are useful for diagnosis, but the reused panel is not an independent final test. All individual retrieved candidates remain limited to three of four authored core matches by the actor/action holdout. Retrieving complementary examples does not itself compose the missing full rule.

## Validation and scope

All **387 focused tests passed in 13.63 seconds**, exit 0. Ruff passed for the five new Python files. The actual joint CLI completed in **28.82 seconds**, exit 0. Tests include wrong-prediction and available-but-missed counterexamples, exact shortlist reuse, reference-label mutation without ranking changes, prohibited refitting, frozen evidence corruption, and a partial-deadline run retaining every configured geometry ID.

Report payload SHA256: `abd168c599270594a762d75ab7ddb252b5c789cfcf2dff04c2df970834057652`.

The report is about 554 KB; its 25 bound geometry files total about 43.34 MB. They retain all 9,000 policy-query rows and selection traces. Full shortlist IDs are reconstructible from the bound inputs and recorded shortlist digest; they are not embedded in each trace.

All 22 listed source bindings, 25 detail artifacts, 12 checkpoints, frozen probe/predictions, and protected AF-002 protocol were verified. The code bindings are a partial dependency manifest. No encoder or LLM was loaded, no model was trained, and no provider, native prover, or sealed final-test input was used. Independent fidelity remains `unavailable`, native useful-proof coverage remains `unrun`, and qualification and production admission remain false.
