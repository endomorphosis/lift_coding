# Autoformalization pinned stage workflows

Date: 2026-10-04. This continues AFI-09a in the [implementation backlog](50-autoformalization-alignment-implementation-backlog-2026-10-04.md), following the [representation and stage declarations](53-autoformalization-representation-and-stage-boundaries-2026-10-04.md). The [comprehensive improvement plan](49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md) and previous evidence generations remain unchanged.

ProofBridge combines joint natural/formal embeddings, retrieved demonstrations and verifier-guided repair. Its Lean results motivate these experiments; they do not establish transfer to our other logic families or certify our source interpretations. This slice establishes executable retrieval boundaries before introducing a new learned alignment loss. [ProofBridge v3](https://arxiv.org/html/2510.15681v3)

## Executable scope

The new [workflow owner](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_stage_workflow.py) supplies separate file-backed fit, rank and score entry points through `run_alignment_stage`. The [command-line entry point](../../external/ipfs_datasets/scripts/ops/autoencoder/run_alignment_stage.py) invokes that same owner. Inputs are independently selected file bindings with exact paths, byte counts and SHA256 digests. The previous dictionary validators remain the owners of closed stage declarations and ordered role associations.

Fit validates the selected TRAIN declaration and publishes a blocked readiness result. It executes no optimizer. Score checks a separately selected saved ranking generation before opening the score declaration or reference ledger, joins the selected values exactly and publishes a blocked readiness result. All current fidelity-evaluation masks are zero. Neither entry point admits a semantic label or computes a fidelity metric.

Rank additionally selects query and bank lane bundles and their external identity pins. It replays both lane validations and checks that their receipts are the exact receipts named by the rank declaration. The new [raw ranking owner](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_raw_ranking.py) computes diagnostic source-to-source cosine similarities from those saved vectors. It supports historical linguistic features and raw embedding views; learned projection, reconstruction, decoder conditioning and Leanstral embedding views require their own qualified executable contracts.

| Stage | Current operation | Admission and authority |
| --- | --- | --- |
| Fit | Pinned declaration validation and blocked readiness publication. | No admitted contrastive relations; zero updates. |
| Raw rank | Checked source-only bundles, cosine computation and durable saved rankings. | Diagnostic similarity; no source-fidelity or proof claim. |
| Score | Saved-generation integrity first, separate reference selection and blocked readiness publication. | No admitted fidelity references; zero scored queries. |

Available queries rank every available bank vector, retain the declared top-k count and order ties by candidate ID. Missing and explicit zero-ablation queries remain in the saved ledger with reasons and no hits. Missing and zero-ablation bank entries are ineligible. An available vector with zero norm rejects rather than becoming a successful representation. An entirely ineligible bank yields unavailable query results.

The executable raw boundary rejects overlap between query and bank IDs or exact source/context input hashes. Distinct declared contexts remain distinct inputs even when their source words match. These checks establish exact self-input exclusion. They do not authenticate TRAIN provenance or exclude every paraphrase, document derivative or contaminated source. Those broader provenance checks remain a separate admission requirement.

## File and process boundary

The workflow checks selected regular-file bytes, rejects symlink components, bounds JSON and aggregate inputs, rechecks implementation and input bindings, and publishes only to a fresh private output generation. Strict parsing rejects duplicate JSON keys and nonfinite constants. Output files retain exact byte bindings and canonical value seals separately. Existing artifact generations cannot be overwritten through the entry point.

Embedded `file_binding` fields do not grant authority to open a path. A nonnull role declaration needs a separately selected role file. Its detached payload omits the role's `file_binding` and `content_sha256`, avoiding a self-referential file checksum. The workflow checks both the declared file binding and the selected detached content. Saved ranking and scoring-reference selections instead bind their complete selected values and must equal the corresponding stage roles exactly.

Each execution uses a fresh trusted Python subprocess with a restricted environment, explicit implementation imports, CPU/address-space/output limits and a parent deadline. The child receives explicit file selections, verifies them and validates the stage and lane values needed for raw ranking. It does not invoke a model, encoder, decoder, projection checkpoint loader or prover. It publishes the complete saved rank declaration with each ranking generation so that later scoring can replay the same query, bank, policy and checkpoint associations.

This process arrangement is not an OS file-access sandbox. A trusted child is given no query-reference file selection during fitting or ranking, but OS-enforced inaccessibility has not been established. The stronger milestone-three criterion in the backlog remains open. Subprocess separation, durable rankings, exact self-input exclusion, derivative exclusion and semantic admission are reported as separate properties.

## Saved historical diagnostic

The [assay runner](../../artifacts/autoformalization-alignment-20261003/assay_stage_workflows.py) prepares new selections from the preceding saved representation generation. The bank uses the original 16 TRAIN IDs from the pinned weak-supervision manifest; the remaining 18 source/context requests are queries. Original vector values and profiles remain unchanged. Normalized producer receipts for the subsets are explicit historical association transcriptions, not runtime producer attestations.

The preparation process reads historical weak TRAIN proposals to retain their opaque formal-view identities. No query-reference panel or human-review package is loaded. The rank subprocess consumes source/context vectors and TRAIN formal-view digests without formal target bodies. This is a historical legal diagnostic; it supplies no new evaluation of the pending 40-family pilot.

The three raw views retain separate identities: 8D historical spaCy features, 384D GTE-small mean/L2 float32 embeddings and 768D Alibaba multilingual GTE CLS/L2 float32 embeddings. The [Alibaba model card](https://huggingface.co/Alibaba-NLP/gte-multilingual-base) identifies the requested embedding model; it is distinct from our decoder or autoencoder checkpoints. No weights are loaded, revised or trained here. Leanstral remains available in the plan for Lean generation and repair, while its optional final-hidden embedding role still requires pooling and batch-consistency qualification.

Saved diagnostic outcomes and file bindings are recorded in the [assay](../../artifacts/autoformalization-alignment-20261003/stage-workflow-01/assay.json). The separate fit request retains a bounded proposed budget and zero executed updates. The separate score request uses explicit unavailable reference rows, preserving every query without generating substitute reference truth.

The saved run ranked all 18 queries in each of the three lanes: 54 query/view outcomes, 864 cosine comparisons and 162 top-three hits against fixed 16-record banks. These are computations and completeness counts, not retrieval-quality measurements. Five workers used approximately 0.407 CPU seconds in total and each reported a 25,100 KiB peak RSS. Fit retained 960 proposed updates and executed zero; score retained 18 unavailable references and computed zero fidelity scores.

## Validation and next work

The [validation receipt](../../artifacts/autoformalization-alignment-20261003/stage-workflow-01/validation.json) rechecks the preceding 134 bound files, replays saved lane/stage/ranking values and records targeted test and lint evidence. The new [ranking tests](../../external/ipfs_datasets/tests/unit/logic/formalization/autoencoder/test_alignment_raw_ranking.py) exercise arithmetic, deterministic ties, exact profile joins, unavailable ledgers and cohort overlap. The new [workflow tests](../../external/ipfs_datasets/tests/unit/logic/formalization/autoencoder/test_alignment_stage_workflow.py) exercise selected file substitution, strict parsing, file kinds, publication and the scoring read-order boundary. Engineering fixtures are not semantic gold.

The combined targeted suite passed 540 tests: 67 new raw-ranking checks, 34 new workflow checks and the preceding 439 lane/stage/raw/context/checkpoint representation checks. Ruff passed all seven new Python files. Independent review checked the executable contracts and historical subset preparation. Validation recomputed all saved cosine rankings, replayed the five stage receipts, rebuilt the 20 source-only preparation inputs and separately rebuilt the three unavailable-reference scoring inputs.

The previously recorded legacy adapter-registry mismatch remains preserved. This slice does not claim that all legacy tests pass, rerun the older 554-file chain or establish a complete dependency closure. Original TRAIN16 masks and decoder checkpoints remain unchanged; all new semantic supervision and evaluation masks remain zero.

Next work is OS-enforced stage file confinement, authenticated TRAIN/derivative provenance, a separately versioned mask-aware multi-positive contrastive loss, admitted relation data and independently admitted scoring references. Learned source-to-formal retrieval also needs checked formal-vector banks and feature-codec/checkpoint joins. The broad pilot continues to cover all 40 catalog families, with per-family typed adapters and reviewed evidence required before semantic claims.
