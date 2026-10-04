# Source preflight and grounded decoder contract

Date: 2026-10-04. Status: implemented opt-in development contracts, with deterministic execution and tests. Source fidelity, runtime qualification and proof authority remain unestablished.

This stage adds concrete contracts for the output gaps found in the [retained decoder replay](decoder-replay-report.md). Literal anchors and canonical symbols now occupy separate fields, so repeated mentions and multiple qualifier atoms can be recorded without changing the old decoder checkpoints or references. Source preflight remains a narrow warning mechanism; proposal transport is a separate check, and neither accepts a generated artifact.

## Implemented interfaces

The new [source preflight](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_decoder_preflight.py) accepts exact source text and optional declared context, with no vocabulary, targets, row kinds or models. It diagnoses bounded normative patterns for universal/cardinality binding, linked variables, negated obligation, unsupported suffix connectives, attributed actor ambiguity and relative calendar references. Quotes are masked. No warning produces `unassessed`, which supplies no assurance of representability or meaning. Context is retained and unapplied; supplied or required context produces clarification, including a distinct missing-context diagnostic.

The new [source grounding](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_source_grounding.py) invokes the existing opt-in complete qualifier compiler only after an unassessed preflight. It uses the request's declared vocabulary and preserves the existing controlled-English interpretation. Every canonical facet value receives its own exact half-open source-character anchor and field path. An object mention of “application” and a condition containing the same word have different offsets. A canonical `application_complete` atom remains separate from the literal phrase “the application is complete.” Conditions and temporal lists declare `all`; exception lists declare `any`. This flat single-rule scope does not encode general binders, nested operators or graphs.

Grounding and transport validators recompute the complete source construction and return detached receipts. Changed offsets, source, symbols, operators, profile identities or authority flags are rejected even after recomputing a payload hash. Transport checks compare a source-constructed proposal with three independently named output contracts:

- Retained literal-span transport requires unique, exact case-sensitive token-aligned canonical strings, disjoint fields, and at most one atom per qualifier facet.
- Retained fixed-codec transport checks whether the complete compact JSON proposal can be assembled from saved content tokens. It accounts for BOS/content/EOS under the configured output cap and supports symbols assembled from smaller token pieces.
- Anchored canonical proposal transport preserves canonical symbols with exact source anchors. It defines a static representation, without a trained decoder or an acceptance decision.

Existing compiler, source guard, checkpoint-bound decoder owners, selected catalogs and runtime entry points are unchanged. The new modules are explicit imports, not a replacement default pipeline.

## Executed development assay

The [request manifest](grounding-01/request_manifest.json), [constructed receipts](grounding-01/constructed_receipts.json) and [report](grounding-01/report.json) bind all 34 original input identities. Exact contexts come from the earlier declared-context manifest. Source preflight consumes no vocabulary; grounding uses the frozen parser study's **TRAIN-supervised vocabulary**, whose preparation used training references. The grammar was designed on exposed development diagnostics. No query references entered construction or transport. All source results were saved before the authored reference panel was read for posthoc comparison.

| Stage | Outcome on all 34 requests |
| --- | --- |
| Source preflight | 24 unassessed, 6 unsupported-profile warnings, 4 clarification requests |
| Grammar grounding | 22 grounded proposals, 10 source-blocked, 2 unavailable under the declared vocabulary |
| Retained literal-span transport | 0 compatible, 22 unsupported transport, 10 blocked, 2 unavailable |
| Retained fixed-codec transport | 0 compatible, 22 unsupported transport, 10 blocked, 2 unavailable |
| Anchored proposal transport | 22 statically compatible, 10 blocked, 2 unavailable |

The 22 proposals contain 172 exact anchors: 22 each for actor, action, modality and object, and 28 each for conditions, exceptions and temporal facets. Two unmatched condition atoms remain unavailable; the vocabulary was not widened from development targets. Both explicit-context inputs remain unresolved.

Posthoc agreement is 22/22 among constructed candidates, or 22/24 among authored positives. This reproduces the earlier parser's exploratory agreement; it is not new independent semantic accuracy. All 34 human review items remain pending. Unsupported, unresolved and unavailable requests remain visible in the full 34-request accounting.

The [saved-output overlay](grounding-01/posthoc_source_span_overlay.json) associates all ten decoded output occurrences across the nine previous real-vector state runs with source-preflight blocks. Those occurrences concern four distinct sources. The old outputs were neither modified nor reexecuted. This is a posthoc association on exposed diagnostics, not a deployed prevention rate or acceptance experiment. Unassessed inputs were never counted as accepted.

The assay used no model, encoder, prover or training call. It completed in 2.658 seconds with measured peak RSS 32,492 KiB and preserved all 245 prior checked file bindings. A process import guard observed no optional model/numerical-stack import attempts. Source/CPU/wall limits and cooperative memory checks are bound in the report; the import inventory is not a complete environment manifest.

## Verification and next work

The combined [preflight tests](../../external/ipfs_datasets/tests/unit/logic/legal_ir/test_canonical_decoder_preflight.py), [grounding tests](../../external/ipfs_datasets/tests/unit/logic/legal_ir/test_canonical_source_grounding.py), existing qualifier tests and existing source-guard tests passed **275 tests in 4.04 seconds**. Ruff passed the four new implementation/test files and the assay runner. An independent read-only review checked source anchors, resealed tampering and codec reachability, including 1,890 small exhaustive tokenization comparisons. The [stage validation](source-grounding-validation-01/validation.json) replays saved deterministic contracts, checks identities and arithmetic, and binds this report and the updated plan.

Next, evaluate the contracts on independently reviewed natural sources and contextual examples. Integrate preflight as an opt-in wrapper while retaining the old raw decoder controls; do not turn `unassessed` or static transport compatibility into acceptance. Add a separately versioned open vocabulary or canonical-symbol decoder arm that consumes inference-available inputs and emits anchors, then measure all-facet fidelity under the same request denominator. Multi-rule association, context interpretation and richer typed ASTs remain separate extensions. Source/formal contrastive learning should use admitted supervision rather than treating compiler-generated proposals as independent truth.
