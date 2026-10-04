# Projection experiment and review preparation — 2026-10-03

The next increment of the [improvement plan](../../implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md) now has working, independently versioned projection heads, a differentiable multi-positive loss, authenticated JSON checkpoints, and a candidate-blind review bundle. All **12 fixed configurations completed**, and each checkpoint reproduced its query projections exactly after reload. The [machine-readable report](projection-01/report.json) retains every configuration, training trace, ranking, and group/wording diagnostic. The [runbook](../../external/ipfs_datasets/docs/autoencoders/alignment_projection_experiment.md) describes reproduction.

The experiment finds a coverage signal in learned source retrieval, alongside weaker direct formal retrieval. It supports further development, not production promotion. Independently reviewed source fidelity remains unavailable, and native useful-proof coverage remains unrun.

## Common comparison and measured results

The existing panel has 360 synthetic training rows in 15 groups and 120 exposed development rows in five groups. Training contains 90 unique target rules, each with four wording variants. The comparison averages those source vectors by target and normalizes each mean, giving every arm the same **90 training candidates** and top-five budget. This pooled raw control differs from the earlier 360-row B1 control; comparisons below use the new matched pool.

Entire actor–action combinations are held out. No training rule can match all four development facets, so the individual core-match ceiling is 75%, already reached by raw retrieval. Complementary support instead asks whether the retrieved set includes an actor-supporting demonstration and an action-supporting demonstration, each also matching modality and object. It does not establish that a generator can combine those examples correctly.

The following values average **all three fixed seeds**, with no best-checkpoint selection. nDCG uses only modality, actor, action, and object, excluding the constant empty qualifier lists.

| Retrieval arm | Shared width | Action-negative weight | Complementary support @5 | Core nDCG @5 | Mean top-five core match |
| --- | --- | --- | --- | --- | --- |
| Raw pooled source control | 384 | — | 60.8% | 0.8772 | 68.3% |
| Projected source → source | 384 | 1 | 66.9% | 0.8661 | 67.8% |
| Projected source → source | 384 | 2 | 80.8% | 0.8750 | 68.2% |
| Projected source → source | 512 | 1 | 64.7% | 0.8629 | 67.5% |
| Projected source → source | 512 | 2 | 71.7% | 0.8680 | 67.9% |
| Projected source → formal | 384 | 1 | 57.8% | 0.8066 | 66.2% |
| Projected source → formal | 384 | 2 | 52.8% | 0.7980 | 65.3% |
| Projected source → formal | 512 | 1 | 56.7% | 0.8080 | 66.4% |
| Projected source → formal | 512 | 2 | 47.8% | 0.7805 | 64.3% |

The 384D projected source arm with action weighting increases complementary support by **20.0 percentage points**, while its mean nDCG is slightly below the raw control. Its support ranges from 71.7% to 87.5% across seeds; that range describes seed variation and is not a confidence interval. Every direct source-to-formal trial has lower nDCG than the raw control. Lower training losses therefore do not establish better development retrieval.

That aggregate coverage gain also hides composition regressions. For the 384D, weight-2 source arm, three-seed mean complementary-support changes against raw retrieval are:

| Held-out actor/action group | Support change |
| --- | --- |
| Custodian/register | +56.9 percentage points |
| Clerk/certify | −2.8 percentage points |
| Commissioner/retain | +26.4 percentage points |
| Executor/issue | +37.5 percentage points |
| Officer/inspect | −18.1 percentage points |

The corresponding direct formal arm loses nDCG in all five groups. Its clerk/certify complementary support drops from the raw control's 100% to 0% in every seed. These local regressions are material, despite improved aggregate source-retrieval coverage.

Nearest action agreement also trades against actor agreement. For example, the same 384D weighted source arm averages 22.5% nearest action agreement and 77.5% nearest actor agreement, compared with 10.8% and 89.2% for raw retrieval. Complementary coverage is more informative here than declaring an action-only gain to be improved meaning preservation.

There are only five held-out composition groups. Results are descriptive; no rowwise significance test, broad generalization claim, or independent fidelity estimate is supplied. The report includes all five groups and all four wording styles so local regressions remain inspectable.

## What was trained and preserved

The cached 384D GTE-small source vectors stay frozen. Separate linear heads map source `384 → d` and formal `22 → d`, for `d=384` or `512`, then normalize outputs. The formal codec fits vocabulary only from training targets, with explicit unknown buckets. It is a small categorical/bag rule representation; empty conditions, exceptions, and temporal fields leave scope and richer semantics untested.

Every trial uses symmetric multi-positive contrastive training for 80 fixed steps, SGD without momentum, learning rate 0.1, weight decay 0.0001, temperature 0.07, and seed 0, 1, or 2. Exact duplicate targets and their wording variants are positives. Weight 2 increases negative denominator contributions only when training rules share modality, actor, and object but differ in action. These are authored-facet distinctions, not independently checked semantic negatives.

Checkpoints bind their codec, source space, implementation bytes, training-file digest, and exact recipe. They use ordinary finite JSON tensors rather than pickle, and optimizer resumption is explicitly unsupported. Development targets do not enter fitting, query projection, candidate construction, ranking, early stopping, or checkpoint selection. A full integration test changes development targets and verifies unchanged checkpoint hashes and rankings.

The completed local run took **30.18 seconds**, using one CPU thread for projection training. It loaded no source encoder, existing autoencoder, Leanstral runtime, provider, or prover. The independent 8D and 768D lanes and the 4096D Leanstral embedding experiment remain separate, unexecuted comparison arms. Numerical source-encoder execution remains unauthenticated by the cached-vector archive.

## Prepared review material

[reviewer_items.json](projection-01/reviewer_items.json) contains **40 source-only items** with blank facet, ambiguity, and reviewer slots. This is the file to hand to reviewers. The separate [organizer bundle](projection-01/review_bundle.json) contains original identities, authored references, integrity bindings, coverage information, and **280 typed contrast proposals**. Keep it separate from reviewer handoff.

The proposals change one facet at a time, preserving typed contracts. They retain the original source without rewriting it and are explicitly unreviewed, unencoded, excluded from training and evaluation gold, and not proof verified. They were not used as the training negatives in this run. Preparing these files creates no reviewer attestation or independently adjudicated result.

## Consequences for the improvement plan

- AFI-04 preparation is available; independent annotation and adjudication remain pending. Add richer source material before claiming condition, exception, temporal, binder, or scope coverage.
- AFI-06 now has a working narrow projection/codec/checkpoint implementation. Full relevant dependency closure and broader profile support remain future evidence.
- AFI-09a now has an executed synthetic statement-alignment prototype and explicit duplicate-positive handling. Broader semantic false-negative checks and independently reviewed pairs remain required.
- Preserve the raw source control. Test a separate diversity-aware retrieval policy against the coverage signal, using inference-available source predictions rather than development references.
- Investigate factorized facet supervision and compositional formal representations before extending the current direct formal retriever. Register any new settings as another exposed-development experiment; the present results do not justify selecting these weights for production.
- Continue native 768D vector/checkpoint admission and the separately bounded Leanstral pooling probe as independent lanes. Verified proof-state alignment, generation, and repair still require their own trace and checker experiments.

## Validation

All **162 focused tests passed in 7.38 seconds**, exit 0. Ruff passed for the seven new Python files. The actual 12-trial CLI run exited 0. [projection-validation.json](projection-validation.json) records commands, file identities, checkpoint integrity, and outcome scope. Existing unrelated changes and earlier evidence generations were preserved.

Report canonical payload SHA256: `7e48665b6ba9e1417a9b1bfc4b48240061eec373032f55838681bf7c8d3fa2ff`.

The protected AF-002 protocol remains unchanged. Every output remains unqualified; no production admission, sealed-final-test access, independently adjudicated fidelity, or native proof success is asserted.
