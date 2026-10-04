# Initial autoformalization alignment study — 2026-10-03

The first implementation increment of the [improvement plan](../../implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md) is runnable. It inventories the three encoder/autoencoder lanes, logic and prover declarations, and Leanstral metadata, and measures the deterministic compiler and raw 384D retrieval on an existing exposed development panel. The [final measured manifest](baseline-02/manifest.json) preserves individual outcomes and source/input identities. The [runbook](../../external/ipfs_datasets/docs/autoencoders/alignment_study.md) explains how to reproduce this scope in a fresh directory.

This increment provides development diagnostics. Independent source fidelity, native useful-proof coverage, learned alignment, and Leanstral embedding quality remain unmeasured. No weights were loaded or trained, no provider or prover was called, and no sealed final-test inputs were accessed.

## Measured results

The Legal IR panel has 360 training rows in 15 groups and 120 development rows in five groups. Sources and targets come from the same synthetic authoring fixture; targets have no independent review attestation. Cached embedding bytes are bound, but their encoder execution is not authenticated by this study. These results cannot establish natural-document fidelity or broad system performance.

| Diagnostic | Result | Meaning |
| --- | --- | --- |
| B0 exact authored-target agreement | 80/120 (66.7%) | Current deterministic compiler, using training-only vocabulary and source-only requests. |
| B0 failures | 40 `empty_output` | All failures are retained in the denominator; each development group has eight. |
| B1 nearest actor agreement | 104/120 (86.7%) | Training source vectors often retrieve the same actor. |
| B1 nearest action agreement | 16/120 (13.3%) | Action distinctions are frequently lost in the nearest demonstration. |
| B1 best-of-five core-facet agreement | Mean 3/4 (75%) | Oracle diagnostic over modality, actor, action, and object. |
| B1 best-of-five seven-facet agreement | Mean 6/7 (85.7%) | Shared empty condition, exception, and temporal fields inflate the average. |
| B1 exact nearest-target copy | 0/120 | Expected: complete development targets are excluded from training. |

B1 ranks source vectors and returns paired training demonstrations. It does not execute retrieval-conditioned generation, embed formal targets, or measure counterpart recall. The best-of-five diagnostic uses authored references after retrieval; it is not an inference-time selector. Five development groups also mean these 120 rows should not be treated as 120 independent observations.

Two representative compiler gaps are “The custodian is allowed to register the certificate.” and “For the clerk, the action to certify the certificate is required.” Both produce the recorded `empty_output` outcome. This points to specific source-construction coverage to investigate while preserving ambiguity and semantic checks.

Baseline computation took 2.33 seconds in this run: 1.49 seconds for compilation and 0.60 seconds for retrieval. Those are local diagnostic timings and exclude encoder generation, LLM inference, native proving, and cold-start costs.

## Inventory and implementation

The user-confirmed [Alibaba-NLP/gte-multilingual-base](https://huggingface.co/Alibaba-NLP/gte-multilingual-base) is the 768D encoder identity already represented by the pinned local profile. A trained autoencoder or source-decoder checkpoint has its own identity and readiness evidence. The inventory does not infer that an unconfigured or uninspected asset is absent.

The canonical catalog exposes 35 baseline families, 40 namespace identities, 33 profiles, 15 executable-provider declarations, and 17 canonical providers. These are different declaration counts. Discovery and saved receipts remain separate from current native execution and certificate verification. The inspected Legal IR router defaults to backend trust; kernel claims require their explicit policy and reconstruction evidence.

A bounded metadata read identifies the local Leanstral GGUF hidden width as 4096D. Its current runner is configured for chat. Final hidden-state pooling, tokenizer/template handling, numerical consistency, latency, and retrieval quality still need a separate embedding experiment. The large model's full hash was not recomputed during inventory.

The added [CLI](../../external/ipfs_datasets/scripts/ops/legal_ir/prepare_alignment_study.py) and four study helpers reject input drift, split leakage, unsupported evaluation roles, and mismatched code origins. They retain failures and partial results on a cooperative deadline, and refuse overwriting prior evidence. The deadline does not preempt one synchronous compiler call. Source bindings cover listed study/core files; they are explicitly not a complete dependency manifest. Earlier `inventory-01` and `baseline-01` evidence is preserved; use `baseline-02` for the final implementation in this increment.

## Plan progress and next dependencies

| Work package | Evidence now available | Still required |
| --- | --- | --- |
| AFI-01 | Bounded asset/profile inventory and exact listed-source identities. | Numerical checkpoint replay and complete relevant dependency bindings. |
| AFI-02 | Declarations, PATH discovery, historical receipts, trust policy, Leanstral metadata. | Current bounded backend execution and scoped certificate replay. |
| AFI-03 | Versioned exposed-development configuration, protected-protocol digest, and split/resource checks. | Full study preregistration for independent reviewed evaluation. |
| AFI-05 | Component-level B0 and B1 development diagnostics. | AFI-04 reviewed facets and semantic mutants, then full fidelity/proof/cost evaluation. |

The next priority is AFI-04: candidate-blind source-facet annotations, disputed-case adjudication, and semantic mutants that alter actors, actions, modality, scope, conditions, exceptions, and time. Those labels enable a meaningful fidelity endpoint. In parallel, AFI-06 can add independently versioned projection heads while preserving the sparse donor cores. AFI-09a should first compare frozen 384D source/typed-statement heads at shared widths 384 and 512 against the raw-vector baseline, with training-only fitting and semantic false-negative masks. Action-sensitive hard negatives are especially motivated by this retrieval diagnostic.

Native 768D vector/checkpoint admission and the separately bounded 4096D Leanstral pooling probe remain parallel prerequisites. Verified proof-state alignment and retrieval-conditioned repair follow their own trace, statement-fidelity, and native-checker requirements. All unexecuted experiment arms remain `unrun`, and no production qualification is asserted.

## Validation evidence

The four focused test files passed: **94 passed in 0.66 seconds**, exit 0. Ruff passed for all nine new Python files. The actual CLI baseline also exited 0. [validation.json](validation.json) records commands, checkout references, file digests, and outcome scope. Existing unrelated changes were preserved.

Manifest canonical payload SHA256: `0248ef52f5c66e62fd6bf2067af8a4034541363df31129bc202db59ef87976c9`.

The protected AF-002 protocol remains at SHA256 `8f81d8d7c46de327f14b93100a24b97f18194518d18220ad459521e849f51401`. Independent fidelity is `unavailable`, native useful-proof coverage is `unrun`, and `qualified`, `production_admitted`, and `training_performed` remain false.
