# Formal logic alignment implementation backlog

Date: 2026-10-04. Status: proposed engineering work, with existing interfaces checked against local source. This companion makes the [comprehensive improvement plan](49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md) executable as bounded changes. It introduces no trained model, admitted labels, prover result or production default.

The first implementation slice should prepare review evidence, preserve statement scope, bind representation identities and separate fitting from inference and scoring. These changes can be tested without pretending that the pending reviews are complete. Semantic training and quality claims require their own admitted data. Keep the independent 8D spaCy, 384D GTE-small and 768D Alibaba GTE lanes, retained decoders, native family routes and Leanstral generation role.

The first independently reviewed pilot will cover logic families broadly, as selected by the user. Register all 40 current canonical family IDs, with exact profiles and source applicability assessed separately. Lean mathematics, legal rules, program specifications and other natural sources supply different strata; a prover name is not a logic family. Unsupported and unavailable cases remain visible. Languages, jurisdiction, source selection and the actual review process must be registered before an independent study.

ProofBridge motivates contrastive source/formal retrieval, compatible demonstrations and bounded repair. The interfaces and broader family contracts below are our proposed extensions, not a reproduction result. See [ProofBridge v3](https://arxiv.org/html/2510.15681v3).

## Existing implementation and important gaps

| Area | Existing implementation | Gap the next change must address |
| --- | --- | --- |
| Review recording | Exact source/context declaration recording and disagreement receipts for the 64-item packet. | Authentication, independent adjudication and semantic admission are separate operations. |
| Legal transport | Flat canonical rules, exact anchors and byte round trips. | The narrow rule contract sorts/deduplicates qualifiers; byte proposal v1 supports one rule and fixed operators. Rich review occurrences and scope cannot be silently lowered into it. |
| Context | Bound spans, context bundles, proposed bindings and link obligations. | These are hypotheses, not resolved meaning. The typed anchor decoder currently blocks supplied/required context. |
| Representations | Raw native vectors, retained learned384 endpoints and native span conditioning. | View identity, producer identity and source/context serialization need a common admission boundary. Equal widths do not establish compatibility. |
| Contrastive learning | Differentiable native384 dual heads, multi-positive loss and checkpoints. | Unknown-pair exclusion, new lane profiles and a runner that separates fitting, ranking and scoring. |
| Proof observations | Native Lean state capture and bounded local tactic replay. | Whole-source proof admission, dependency checks and source fidelity remain separate from capture or local closing. |
| Leanstral embeddings | A requested 4096D discovery profile, diagnostic response validators and saved numerical benchmark vectors. | Trusted native execution remains closed; saved batching and token-audit observations do not qualify the requested profile. |

The next contracts should extend existing owners. Preserve old schemas and checkpoint bytes. A new richer payload, loss or source profile receives its own version and explicit migration/loss assessment.

## Broad family pilot coverage

Planning packages: AFI-02, AFI-03, AFI-04 and AFI-22. Reuse the [canonical catalog](../../external/ipfs_datasets/ipfs_datasets_py/logic/families/canonical_catalog.py), [baseline registry](../../external/ipfs_datasets/ipfs_datasets_py/logic/families/registry.py), [publication registry](../../external/ipfs_datasets/ipfs_datasets_py/logic/families/registry_v3.py), [identity namespaces](../../external/ipfs_datasets/ipfs_datasets_py/logic/families/namespaces.py) and [provider matrix](../../external/ipfs_datasets/ipfs_datasets_py/logic/families/provider_matrix_v2.py). The static union contains 40 IDs: 35 baseline identities plus five additional publication identities. Catalog presence establishes identity, not production admission, host availability or faithful execution. The [planning coverage matrix](../../artifacts/autoformalization-alignment-20261003/implementation-backlog-02/pilot-family-coverage.json) derives its membership from those owners and supplies no new registry or authority.

The following six groups are proposed study strata, not changes to the catalog taxonomy. Their semantic checks must be instantiated and reviewed under the selected profiles and assumptions.

| Proposed stratum | Exact family IDs | Discriminants to register |
| --- | --- | --- |
| Core and structural | `propositional`, `first_order`, `higher_order`, `dependent_type`, `datalog`, `horn_chc`, `frame_logic`, `description_logic` | Connectives, binder/domain scope, type dependencies, rule restrictions, and open/closed-world assumptions where applicable. |
| Modal, normative and cognitive | `modal`, `deontic`, `tdfol`, `dcec`, `epistemic`, `doxastic`, `bdi`, `agency`, `intention_agency`, `epistemic_temporal` | Frame and agent assumptions; permission versus obligation; belief, knowledge, intention and agency distinctions; time/exception attachment. |
| Temporal and dynamics | `temporal`, `transition_system`, `event_calculus`, `situation_calculus`, `mu_calculus` | Time domain and bounds, event/action effects, state transitions, fixed-point choice and required model assumptions. |
| Program, resource and process | `program`, `refinement`, `separation_logic`, `linear_logic`, `concurrency`, `session_process`, `process_calculus` | Preconditions/postconditions, resource ownership/use, interference, protocol direction, scheduling and refinement assumptions. |
| Policy, security and relational | `authorization`, `cryptographic_protocol`, `hyperproperty`, `finite_field_constraint` | Principal/delegation scope, adversary model, multiple-trace quantifiers, field/bit-width assumptions and exact claimed security property. |
| Alternative consequence and quantitative | `argumentation`, `defeasible_logic`, `nonmonotonic_logic`, `relevance_paraconsistent`, `probabilistic`, `fuzzy_weighted` | Extension/priority choice, contradiction handling, probability versus truth grade, thresholds and unresolved outcomes. |

Proposed diagnostic floor: 12 requests per family in six related two-item groups, or 480 new request assignments before cross-family reuse. At least three originals per family should come from independently acquired natural sources; pair each with a declared controlled derivative. The remaining groups may be authored discrimination cases. Include ordinary supported statements, semantic boundary changes, context dependence and genuinely ambiguous or unrepresentable meaning. This gives at least 120 natural-original family assignments and 240 paired group assignments, not 480 independent sources. Reused sources and all derivatives share a global group identity. Review each member; a mutation is not automatically a negative, and its reviewed relation may remain unknown.

Keep the existing 64 exposed authored canonical requests as a separate legal diagnostic stratum with their original splits and zero admission masks. Together these panels propose 544 request assignments and 1,088 initial assessments if every request receives two independent reviews, before adjudication, intake verification and any additional profile cases. These are planning quantities, not collected data or a powered accuracy study. The older pending 34-item panel remains separate. A later confirmation cohort needs new source groups and a sample size based on pilot variance, clustering and review cost.

Each record binds source/context, acquisition and exposure, global derivative group, catalog generation, exact family/profile, assumptions, ordered semantic occurrences, coverage, alternative interpretations and reviewer/adjudication evidence. Use `family_not_applicable` or `no_applicable_statement` where appropriate rather than applying the legal packet's `no_normative_rule` label across families. An unavailable target representation may still have a reviewed coverage boundary; it receives no fabricated formula or semantic training mask. Source-meaning review, formal-target admission, contrastive relations and proof-training eligibility remain separate gates.

For each family/profile, record representation disposition, parser/transport status, semantic lowering and losses, backend/environment availability, requested property, checker result, evidence kind and satisfied trust policy. Keep `unsupported`, `unavailable`, `ambiguous`, `not_applicable`, `timeout` and `unchecked` distinct. The existing syntax/schema and domain qualification floors continue to apply, but passing an eight-fragment syntax floor does not establish forty-family semantic coverage. Register meaningful profile-specific suites before claiming support for more than one profile; twelve requests per family cannot qualify every published profile.

Use the same source/context cohort for the 8D, 384D and 768D comparison wherever their registered input policies apply. A supplied family/profile request must be public task information available to every arm, not private reference metadata. Preserve missing lanes in the ledger and report both matched-input comparisons and all-request outcomes. Keep the 8D diagnostic/routing contribution separately attributable. Leanstral embeddings join only after their own capability gate. Begin broad data collection and baseline assessment across all families; allocate expensive fitting, generation and proof runs to eligible profile slices under a fixed budget. Expand those runs based on observed gaps, while retaining every family in the coverage report. The existing legal 12-arm weak prototype is one diagnostic slice, not validation of this broad pilot.

Report equal-weight family means alongside request-weighted totals, sample counts and the weakest eligible family. Show semantic fidelity, useful checked coverage, false acceptance, abstention and cost by family/profile and by natural versus authored source. Useful checked coverage requires both independently faithful meaning and a successful check satisfying the requested trust policy, divided by all requests; report correct clarification and inapplicability dispositions separately. An unavailable checker does not make a statement semantically wrong, but it cannot contribute a useful checked success. Use grouped uncertainty estimates and expose small or empty strata instead of hiding them in a pooled score. Allocate a declared minimum baseline budget per family, then additional compute by measured uncertainty and benefit; avoid a full family-by-lane-by-decoder-by-prover cross-product.

## Review evidence intake

Planning package: AFI-04, following AFI-03. Reuse [review recording](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_binding_review.py), its [file workflow](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_binding_review_workflow.py) and the [evidence design](../../artifacts/autoformalization-alignment-20261003/label_admission_contract_design.md).

Proposed interface: `validate_label_evidence_intake(packet, recording, package, *, expected_bindings, selected_process_binding)`.

The intake binds the complete annotation, item/input identity, recording generation, organizer, cohort policy and review process selected outside the package. It records interpretation alternatives, formal target derivations, exposure and adjudication declarations. Return declared but unverified evidence with pending verification/admission and all supervision masks zero. It must have no operation that turns caller declarations into authenticated review or semantic gold.

Acceptance tests should reject a validly rehashed annotation substituted for another item, stale revisions, unknown processes, altered context and caller-written authentication claims. An empty package preserves all 64 pending items. Synthetic test fixtures remain synthetic; their names and signatures establish no real reviewer identity. The separate semantic admission gate needs actual process-owned verification and supported adjudication before it can enable a new data generation.

## Statement scope and coverage

Planning package: AFI-07a, with AFI-04 supplying reviewed interpretations and AFI-11 consuming diagnostics. Reuse [CanonicalTypedBridge and BridgeView](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_contracts.py), [source grounding](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_source_grounding.py) and [byte proposal validation](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_byte_codec.py).

Proposed interfaces: `validate_scope_declaration(request, declaration, *, expected_input_sha256)` and `assess_flat_profile_compatibility(declaration)`.

Introduce a separately versioned payload carried through existing family/bridge envelopes. Preserve rule identity, ordered occurrences, repeated qualifiers, operator structure, attachment, binders/domains where the family supports them, source/context spans, coverage and unresolved meaning. The bridge envelope supplies transport and construct disposition; it does not establish semantic correctness.

Assess compatibility before lowering into the legacy flat rule. Report which constructs are preserved, normalized under an approved policy, unavailable or lost. Sorting can preserve meaning in an admitted conjunction profile while still losing occurrence information; a reordered declaration is not automatically a logical negative. Reject unsupported lowering rather than dropping nested scope or extra rules.

Meaningful fixtures distinguish conjunction from disjunction, shared from local exceptions, duplicate occurrences, omitted clauses, binder capture and multi-rule attachment. Verify exact reconstruction within each declared transport profile. Independent review still decides source fidelity. The current bag-of-facets representation cannot stand in for this richer view.

## Context companions and agreement diagnostics

Planning packages: AFI-06 and AFI-11, using the registered input policy. Reuse [context bundles](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/context_resolution.py), [context bindings](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/context_slot_bindings.py), [link obligations](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/context_link_obligations.py) and [observed symbol bindings](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_symbol_bindings.py).

Proposed context interface: `prepare_canonical_context_companion(source_request, *, bundle, index, bindings)`. Bind exact context bytes, cited spans, roles, competing interpretations and outstanding assumptions. Keep source resolution false until the appropriate external or native obligations are discharged. Identical source wording with different context must have different input identities. Reject cross-source citations, byte/character offset confusion, missing required context and circular support.

Proposed agreement interface: `compare_typed_statement_views(candidate, references, *, profile, assumption_bindings, expected_bindings)`. Run only after target-free candidate artifacts are durable. Record reference access and report exact typed agreement, structural differences or unassessed scope with per-path details. Preserve accepted interpretation sets. Same anchors with wrong symbols, changed connectives, omitted qualifiers and changed assumptions must remain distinguishable. Structural difference does not establish logical non-equivalence; structural identity does not establish source fidelity.

Preserve the current [typed anchor decoder](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_typed_anchors.py) context block. Context-aware generation is a new profile with matched source/context information in retrieval and generation.

## Representation identity and lane profiles

Planning packages: AFI-01 and AFI-06. Reuse [native conditioning](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/legal_native_conditioning.py), [learned endpoint extraction](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_checkpoint_representations.py) and [multilingual GTE asset inspection](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/gte_multilingual_profile.py).

Proposed interface: `validate_lane_bundle(bundle, *, expected_bindings)`.

The bundle binds lane, representation stage, actual output width, producer/model/code/checkpoint identity, source and context digests, serialized encoder input, pooling, normalization, precision and vector digest. Each view remains separately named: raw vectors, learned latents, reconstruction, decoder condition and historical linguistic features. Fit-time and inference-time input recipes must agree. Unavailable vectors remain unavailable; a zero vector belongs only to an explicit ablation.

Reuse native conditioning's exact source/vector joins. Its historical8 features are not learned reconstruction outputs. Use extraction before target-assisted reconstruction safety or sample-memory lookup for the primary learned representation. Validate declared normalization without imposing a new normalization on preserved producers.

Test foreign profiles with the same dimension, source/vector swaps against bound producer receipts, context changes, nonfinite vectors and incorrect stage identities. Those checks establish contract integrity, not that a vector preserves source meaning. Native8/native768 projection heads require new checkpoint profiles; leave the exact GTE-small384 owner unchanged.

## Contrastive loss and separated numerical stages

Planning package: AFI-09a, following AFI-04 and AFI-06 for the semantic experiment. Reuse [alignment projection](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_projection.py) and the numerical ranking helper in [alignment experiment](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_experiment.py). Its complete legacy driver reads DEV before fitting and should not become the new isolated fit worker.

The existing owner provides TRAIN-fitted legal features, normalized dual heads, a symmetric multi-positive loss and checkpoint create/save/load. It requires exact native384 identity and shared dimensions 384 or 512. Its negative weights are at least one; they cannot exclude unknown pairs.

Proposed extension: `masked_multi_positive_contrastive_loss(source, formal, *, positive_mask, permitted_negative_mask, temperature, negative_weights)`. Masks bind the registered TRAIN relation policy. Unknown pairs are neither positives nor negatives. Reject overlapping masks and missing positives; report rows with no permitted negatives rather than implying meaningful separation. Reviewed equivalence supplies semantic positives. Author or document groups serve splitting and leakage controls, not equivalence.

Test parity with the old loss when all its negatives are permitted, isolation of excluded logit contributions, finite gradients into both heads, invalid masks and small batches with no separation signal. Preserve the old loss/checkpoint profile for historical replay.

Proposed stage interfaces are `fit_alignment(train_bundle, *, policy, budget, output_directory)`, `rank_alignment(target_free_queries, frozen_bank, checkpoint)` and a separate `score_alignment(saved_rankings, admitted_references)`. Fit sees only admitted TRAIN records. Ranking receives no reference IR, target tokens or organizer-only author grouping. Source text, declared context and inference-available profile metadata remain allowed. Save ranking artifacts before loading references.

Use deterministic candidate ordering and ID tie breaks, frozen bank identity, counted updates, measured resource use and disjoint checkpoint reloads. Tests should make reference files inaccessible during fitting/ranking, reject foreign banks and retain unavailable queries in the result ledger. Start with the existing [12-arm design](../../artifacts/autoformalization-alignment-20261003/contrastive_prototype_design.md). Its 960 requested updates are proposed, not executed. The original TRAIN16 contrastive masks remain zero; a weak diagnostic fit needs its own versioned policy before numerical work.

## Retrieval and decoder conditioning

Planning packages: AFI-10, AFI-12, AFI-16 and AFI-17. Preserve the [native span owner](../../external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/legal_span_dimensions.py), [preflight wrapper](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_span_decoder.py), [typed parent](../../external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/legal_formula_learning.py) and typed anchor lineage.

Add a training-only retrieval bank whose records bind source, family/profile, assumptions, typed view and admitted evidence. Exclude each training query's own target and source derivatives. Use profile eligibility before similarity ranking. Keep statement and proof-strategy retrieval separately attributable. Existing [representation ranking](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_representation_retrieval.py) supplies development controls; it should not supply query-reference data to inference.

Preserve real, disabled, zero and full-order rotated native span conditioning controls. Validate the complete input batch before source filtering; blocked requests can remain rotation donors under the declared control. Keep all request outcomes and retained checkpoint identities.

Retrieval conditioning for the typed decoder needs a new lineage because its current public interface takes source requests without an embedding condition. Feed retrieved TRAIN exemplars through a separate memory branch and bind their receipt separately. Do not concatenate exemplar text into the source whose offsets the anchor head predicts. Begin with a gate that contributes zero so source-only parity is testable, then fit the new branch under an admitted policy.

Test unchanged source offsets, no query-gold fields, source-only parity and exact retrieval joins. Advance on reviewed held-out whole-statement fidelity, including qualifiers and rule associations. Training memorization or copying a retrieved target does not qualify the new decoder.

## Native proof observations and verification

Planning packages: AFI-07b, AFI-08, AFI-13 and AFI-14. Reuse [Lean proof-state capture](../../JevOps/jevops/proof_state.py), [bounded tactic replay](../../JevOps/jevops/proof_replay.py), [family routes](../../external/ipfs_datasets/ipfs_datasets_py/logic/autoformal/legal_family_routes.py) and the [LegalIR proof router](../../external/ipfs_datasets/ipfs_datasets_py/logic/integration/reasoning/legal_ir_proof_router.py).

`capture_source` and `validate_trace` provide bound observations; their capture flags do not claim proof admission, kernel checking or dependency verification. `replay_candidate` checks a bounded local tactic attempt. A locally closed state does not establish whole-source correctness. `collect_replay_pairs` separately uses trusted replay/compile callbacks and structural admission; its evidence still requires the appropriate dependency and source-fidelity scope.

The proposed trace adapter binds original source/environment/exporter, event ID, typed before/after states, tactic, premises, dependencies and any whole-source checker receipt. Record which properties are unavailable. Preserve observation-only traces separately from admitted proof-training material. Mean pooling is the first baseline; ordered transitions and dependency graphs are later arms. Tests should catch changed environments, unmatched event IDs, missing post-states, local-close/whole-source disagreement and unverified dependency closure.

Canonical obligation/permission/prohibition rules use their supported deontic route. FOL, TDFOL and DCEC fragment transport is not a license to relabel a deontic obligation. The [qualified Lake owner](../../external/ipfs_datasets/ipfs_datasets_py/logic/autoformal/legal_qualified_lake.py) targets the qualified noncalendar profile. The [calendar compiler](../../external/ipfs_datasets/ipfs_datasets_py/logic/autoformal/legal_canonical_calendar.py) is separate; calendar-to-Lake integration needs a new qualified adapter.

The [generic backend templates](../../external/ipfs_datasets/ipfs_datasets_py/logic/integration/reasoning/_prover_backend_mixin.py) also need explicit compatibility exclusion for this pilot. Their Lean template defines obligation as the proposition itself and permission as double negation; their Rocq template assigns constant truth values to normative operators. These definitions do not preserve the intended distinction merely because the names are deontic. They must not serve as the pilot's faithful deontic semantics bridge. Other native routes remain separately assessable under their declared profiles.

Proposed direct verification interface: `verify_statement_candidate(candidate, premises, *, interpretation_binding, project_binding, policy, budget)`. Reuse [ProjectBinding and NativeLeanVerifier](../../JevOps/jevops/arena_lean.py), including request validation and generated-metaprogram isolation, and [axiom auditing](../../JevOps/jevops/proof_trust.py). Bind candidate statement/type, admitted premises, project/toolchain and actual checker result. The existing `native_lean_reconstruction` route is eligible only after a proved SMT/ATP portfolio candidate. Direct Lean candidates therefore need a new explicit verification route/profile or an independently invoked adapter, rather than reuse of that applicability rule. This adapter establishes formal properties under those assumptions; source fidelity remains a separate outcome. A caller-written trust level cannot manufacture a kernel receipt.

Route requests through existing eligibility, total/stage budgets and explicit trust policy. Record `trust_satisfied` separately from success. The current LegalIR router defaults to backend trust; configure and satisfy kernel trust for a kernel acceptance claim. Native execution support must be measured for the selected study environment. A proof of a lossy translation establishes only that translated obligation. Keep a checked statement fixed during proof repair; interpretation repair creates a new statement generation and repeats fidelity checks.

Store admitted traces in a separately versioned representation corpus linked to [trusted proof feedback](../../external/ipfs_datasets/ipfs_datasets_py/logic/integration/reasoning/legal_ir_proof_feedback.py). The existing categorical feedback boundary excludes raw proof states and scripts; a trace adapter must preserve that boundary. Tests should discriminate permission from obligation, reject unexpected axioms or changed theorem types, and exercise timeout/cancellation and descendant cleanup. Compilation alone must not set theorem acceptance or source fidelity.

## Leanstral embedding owner and canary

Planning packages: AFI-18 and AFI-19. Reuse [4096D profile discovery](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/source_embeddings_4096.py), [owner prerequisites](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/source_embeddings_4096_owner_diagnostic.py), the [bounded common runner](../../scripts/run_leanstral_ephemeral.py) and the [historical benchmark source](../../scripts/benchmark_leanstral_embeddings.py).

`Leanstral4096Profile` requests last pooling, L2 normalization, a 512-token maximum including special tokens, `parse_special=False` and one client operation. `inspect_embedding_capability` is GET-only discovery. Response validators supply diagnostic shape/accounting checks. `embed_rows` deliberately remains unavailable until trusted native owner integration; caller JSON and booleans cannot open that gate.

The [saved numerical inventory](../../artifacts/autoformalization-alignment-20261003/leanstral-embedding-inventory-01/inventory.json) demonstrates 4096D vectors under a different recorded workload. Its separate token-audit requests used `parse_special=True`; the embedding POST did not bind actual forwarded token IDs. The benchmark makes synchronous batched embedding calls. Its 16 backend slots do not mean 16 concurrent embedding clients: the thread pool clears slots, while embedding calls are serial. Bind client operation policy, input batch and backend slots independently. A width match cannot establish profile equivalence.

Proposed research interface: `run_embedding_canary(request_rows, *, model_profile, runtime_budget, output_directory)`. Integrate experimental embedding mode with the common runner's preflight, exclusive lock, child limits, cancellation and cleanup. Keep research observations separate from production owner admission. Preserve the existing production gate until same-operation native entry/close verification is implemented. Do not invoke the historical service-replacing benchmark as the new shared runtime.

Predeclare a small matrix crossing single/batched input, position, peer content, request order, cache state, token policy and overlength behavior. Measure the registered numerical tolerance, actual per-slot context and pooling index. The existing single/batch L2 result, 0.145932 versus a 0.001 tolerance, must be resolved or explicitly scoped. Mean pooling has its own complete-sequence physical-microbatch requirement. No saved source exactly joins the current panels, so a qualified owner must generate new comparison vectors.

Native owner integration must bind actual asset/build/launch/device, forwarded tokens, evaluated token count, native output and closing/cleanup to the same admitted operation. A declared full-weight hash or metadata prefix alone does not authenticate all weight bytes. Tests can exercise token response accounting, false caller witnesses, failed closing, cancellation and wrong profiles without admitting real inference. Actual capability and cost checks require a separately admitted numerical run. Measure cold load and warm encoding separately; retain GTE progress if this lane is unavailable or offers insufficient benefit.

## First implementation slice and advancement

| Order | Bounded deliverable | Acceptance before advancing |
| --- | --- | --- |
| 1 | Diagnostic review evidence intake and empty-package replay. | Exact bindings, pending verification, unchanged masks and meaningful substitution failures. |
| 2 | Scope/coverage payload and legacy compatibility assessment. | Preserve occurrences/attachment; disclose normalization and losses; representative profile fixtures pass. |
| 3 | Lane bundle boundary and separated fit/rank/score contracts. | Exact view identities; inaccessible query references; immutable banks and saved target-free outputs. |
| 4 | Versioned exclusion masks and private projection reload checks. | Finite gradients, legacy parity and counted/bounded numerical work under an explicit fit policy. |
| 5 | Reviewed data, baseline scoring and profile-filtered retrieval. | Independent interpretation and admitted labels; candidate-pool ceilings and all-request denominators. |
| 6 | New typed conditioning, admitted proof traces and bounded repair. | Held-out source fidelity and appropriately checked proof benefit under matched total cost. |
| Separate runtime track | Leanstral capability canary and trusted owner integration. | Qualified token/batch/context behavior and measured residency; no promotion from diagnostic response shapes. |

Scope/context contracts and lane boundaries can be developed in parallel once their input policies are registered. Broad family source collection and semantic reviews can proceed while those engineering changes are built. Model tuning, graph learning, cross-lane distillation and expansion of expensive prover runs depend on a measured gap. The broad coverage cohort begins with the first slice; expensive execution grows in qualified stages.

For evaluation, report independently assessed all-facet fidelity, useful checked coverage, false acceptance, abstention and cost. Separate exact-counterpart retrieval from useful TRAIN-demonstration retrieval. Preserve unsupported/unavailable/ambiguous/timeout requests, teacher-forced versus free-running outputs, whole-rule errors and qualifier scope. Register confirmation thresholds after pilot variance and review cost are known, before final outcomes are inspected.

This backlog is proposed work, not an activated supervisor board or assigned human review process. The [validation receipt](../../artifacts/autoformalization-alignment-20261003/implementation-backlog-02/validation.json) binds the document, family planning matrix and inspected owners, checks existing API names and local links, and records its planning scope. It establishes no new model or proof outcome.


## Frozen reconstruction evidence and revised execution order

The [published-autoencoder comparison](../../artifacts/autoformalization-publication-20261004/evaluation/frozen-development-summary-01.json) now restores all nine selected checkpoints from a fresh immutable Hugging Face download, reproduces original TRAIN outputs exactly, and compares six retrieval views. Across 16 source-only exposed development queries, all neural seeds beat the TRAIN mean but trail TRAIN-fitted PCA in reconstruction. On eight authored positive retrieval queries, native384 neural views improve slightly over raw; native768 neural views rank lower than raw; PCA latent means exceed neural-latent means in all three lanes. These are scoped development diagnostics, with all semantic masks zero and no optimizer updates in evaluation.

Execute the next source expansion before another TRAIN16 reconstruction fit. The 64 authored composition requests have no matching native cache and need exact-profile encoding plus a separate source-only policy. Broad 40-family source assignments and genuine reviews remain zero. Collect and group natural sources under traceable acquisition and learned-use rights; retain unsupported/unavailable profile outcomes and the permanent exclusion of the exact denied JusticeDAO pinset. More metadata counts do not create training rows.

Register a limited learning-curve/capacity matrix on larger grouped sources with raw, mean and TRAIN-only PCA controls. Track effective rank and context delivery alongside reconstruction and matched retrieval. The proposed authored TRAIN32 rank bound 31 remains below the768 bottleneck 64. New contrastive or proof training additionally requires admitted semantic pairs or native verified traces, respectively. Independent human review and new confirmation data remain the exits for M1/M2, rather than engineering replay or tiny exposed nDCG changes.
