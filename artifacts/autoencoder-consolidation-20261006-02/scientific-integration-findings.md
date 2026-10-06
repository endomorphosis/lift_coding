# Autoencoder and legal decoder consolidation: scientific evidence

This review supports an additive integration of the grouped decoder into the
existing effort. It does not select a production model, combine incompatible
checkpoints, or start another experiment. The machine-readable
[inventory](scientific-provenance-inventory.json) binds the source APIs,
checkpoint bytes, retained experiment reports and publication receipts.

The reviewed GitHub main commits, refreshed by the parent agent, are
`795d960170214d03e2eaf4c0a13ad4eb922c5c08` for datasets and
`b0ba1aaa9c8a3f1d0e42bca31aa710f1108c686e` for the workspace.
All 16 reports from the earlier integration matrix remain reachable and have
identical bytes on these newer mains. All original report hashes matched.
Among the 20 inspected API owners, the six grouped-coordination/decoder modules
are absent from pinned datasets main; the other 14 match it exactly. The parent
owns broader branch/worktree review and integration.

No model was imported or executed. This review streamed hashes for the complete
398,209,746-byte teacher checkpoint, two retained 384D feature-student examples,
36 formula-sidecar state files, 72 expanded source-AE model/Adam files, and both
selected grouped checkpoints. All 113 artifact hashes and sizes matched their
recorded bindings. This establishes retained-byte integrity, not a new numerical
replay or complete training ancestry. Hub verification below is authenticated
retained evidence; no fresh Hub fetch or upload ran here.

| Model or owner | Actual contract and evidence | Integration disposition |
| --- | --- | --- |
| Historical 8D teacher | Sparse `AdaptiveModalAutoencoder` feature model, full checkpoint SHA `7236de26…`. Its original embedding provenance and all ten constituent producer commits are not established. The `ddf6b794…` runtime is distinct from the weights' preparation commit. | Preserve exact lineage and runtime; do not label the grouped decoder a retrained teacher. Old target-aware safety-projected reconstruction is not comparable to free-running formula accuracy. |
| Current 384D feature student | Separate sparse residual feature lineage; verified GTE-small example checkpoints remain historical smoke artifacts, not an implicit campaign selection. Neither base feature checkpoint alone is a learned formula decoder. | Retain explicit parent, source/vector and runtime identities. Attach or select formula heads through their existing separate contracts. |
| 8D/384D/768D Legal formula sidecars | Ordered restricted-vocabulary rule generation from cached width-specific source inputs. Actual head fitting and generated-field losses exist. Later 384D/768D selected original development scores reach 48/48, while exposed wording behavior differs. Many final attempts were rejected by unchanged gates. | Reuse frozen selected states and field-level diagnostics as controls. Do not promote rejected endpoints or turn repeated development panels into fresh holdouts. The 36-state inventory is a bounded older subset, not every later sidecar. |
| 8D/384D/768D source-only MLPs | Nine TRAIN32 reconstruction models, widths 8→16→4, 384→128→32 and 768→128→64; 1,800 selected-model updates plus 27 private numerical checks. Every model trails TRAIN-only PCA on the exposed development reconstruction panel. | Reuse raw, mean, PCA, learned latent and reconstruction views under explicit identities. These are source-vector models, not the formula sidecars. |
| Registered `source_conditioned_formula_v1` | Separate source-GRU/attention/formula-GRU model. The common registry already supports source-only generation and a different checkpoint/resume schema. | Keep this profile as an existing source-only baseline. A new grouped profile can join the same discovery interface without replacing it. |
| Native768 single-rule span decoder | Source tokens plus an explicitly profiled 768D condition; raw/PCA/AE interventions use unchanged raw-trained weights. Joint span search raises proposals from 10 to 183/192, retaining known actor/modality/attachment errors. | Reuse target-free source preparation, conditioning controls and bounded joint-search methodology. The one-rule grammar and checkpoint schema are incompatible with grouped 2–8-member heads. |
| Grouped v1/v2 source heads | Raw source plus caller-supplied modal scope; ordered actor/action spans, O/P/F, member count and scope. V2 adds local byte convolutions and learned support refusal. It has no vector input or latent bottleneck. | Add a separately named experimental Legal profile and expose its actual closed request schema. No 8D/384D/768D claim and no default/runtime promotion. |
| Native 4096D heads | Actual two-clause training succeeds; broader exposed development remains 0/12 in both arms. Saved Leanstral embedding workloads have separate token/batch/profile limitations. | Preserve as a separate capacity/runtime track. Width and a successful tiny fit do not establish a superior encoder. |
| Intent/UI/Security domain owners | Native feature, formula, structured-ridge and domain-384 v1/v2/v3 models have distinct contracts. Some wrong generated candidates still pass scoped Lake checks. Domain-384 v3 is not a Legal grouped-decoder version. | Reuse validator ownership, complete-family accounting and output-before-scoring separation, not cross-domain checkpoint relabeling. |

The grouped v2 selected state is epoch 3, 480 updates, from a completed
2,400-update recipe. Its authored fresh final set has 64 exact positive requests
out of 64, 55 learned refusals out of 64 unsupported-profile cases, seven
incidental structural blocks and two unsupported requests emitted. The strict
mixed score is 119/128, with 38 correlated source-parent groups. The in-sample
score is 2537/2560. The same fresh final panel gives v1 40/64 exact positives,
45 safe refusals and 19 unsupported emissions; v1 has no learned support head.
The v1/v2 comparison changes encoder, augmentation, negative supervision and
positive presentation count, so it is not an architecture-only ablation.

Seven real official US Code paragraphs yield 14 learned refusals under the two
caller-supplied scopes and zero requests. These are real source-only model calls,
but have no independently reviewed reference IR. The experiment establishes
neither real-law formalization coverage nor legal semantic accuracy. Its two
generated eight-member native examples pass actual `lake build legal`, and an
incorrect scope claim is rejected; that result does not admit every prediction
or verify the legal interpretation of the input.

## Existing contracts to reuse

1. Add the grouped v2 reader beside the explicit source-only runtime. Require an
   exact local checkpoint hash and its producer closure, raw source and explicit
   `modal_scope`; unavailable scope remains an abstention. Describe the input as
   source conditioned, the target as ordered grouped deontic IR, and the scope
   as caller supplied. Keep loading/inference opt-in and avoid a width alias.
2. Use `CoordinationDecodeRequest` as the shared prediction boundary, followed by
   `legal_coordination_evaluation.evaluate_coordination_outputs` and the existing
   native deontic renderer. The source parser may supply attributed candidate
   groups; it must not repair a learned prediction or supply target spans to
   inference. Preserve separate malformed, blocked, missing and extra outputs.
3. Connect richer target design to `canonical_statement_scope` rather than
   silently flattening groups into single rules. Its occurrence/attachment
   declarations preserve information but do not implement universal logic or
   authorize executable lowering. Any grouped-to-canonical adapter needs an
   explicit capability check for modal scope, ordered duplicate occurrences,
   inherited actors, qualifiers, binders and unsupported constructs.
4. Reuse `alignment_lane_bundle` for future raw/latent/reconstructed vector
   identity, not as runtime attestation. Add a separately versioned conditioning
   branch only when needed; preserve zero-gate source-only parity. Do not append
   retrieved demonstrations to the source string used for character offsets.
5. Reuse the existing source-only review recorder, label-evidence intake and
   provenance workflow. Their declarations/signatures do not authenticate human
   identity, independent judgment or semantic truth. The retained authentic
   review/admitted-label counts are zero. Independently reviewed source/context
   targets remain the prerequisite for a legal-fidelity claim.
6. Reuse the implemented masked contrastive arithmetic and relation handoff.
   The numerical assay tests synthetic masks and gradients; it runs no semantic
   fitting. Unknown pairs remain excluded. The current native384 dual-head owner
   and 27D one-rule formal features cannot be called a trained 8D/768D or grouped
   source/formal/proof model. New view profiles and admitted relations are needed.
7. Reuse proof-state capture and bounded replay for observation, and actual
   family-specific checking for formal evidence. Preserve the source-free trusted
   proof-feedback store: raw states/scripts belong in a separately admitted
   trace corpus. Local tactic closure, syntax validity, arbitrary backend modal
   templates and compiler agreement cannot substitute for source fidelity or
   whole-source native proof/dependency admission.

Docs 49/50 contain earlier descriptions of masked contrastive, statement scope,
review intake and stage separation as proposed work. Current source and retained
validation show these engineering slices now exist. Their missing pieces are
authentic review/admission, richer compatible representations, actual admitted
fits and evaluation—not another implementation of the same arithmetic or
declaration wrappers. The owners' APIs and exact current hashes are in the
inventory. The eight-family Legal requirement and 40-family planning catalog
remain broader than the grouped decoder's supported deontic profile.

## Shared scoring protocol for the next experiment

Register input profile, output grammar, source/context identity, label origin,
exposure history and source-parent groups before fitting. Keep authored
engineering references, compiler proposals and reviewed legal targets as
different strata. The JusticeDAO span caches are source/proposal resources,
not independent semantic gold by their dataset names; preserve any exact
existing pinset exclusions and do not generalize them to unrelated sources.

Use a shared target-free inference record and score saved outputs afterward.
Measure exact ordered IR, individual roles/modalities/actions/count/scope,
character occurrence spans, whole-rule associations, unsupported emissions,
learned refusal and incidental validation blocks separately. Report every
request, missing/extra output and clustered source-group denominator. Explicit
scope preservation is not inferred-scope accuracy. Tests of normalization must
retain the distinction between wire identity and normalized semantic labels.

For a representation comparison, use matched targets, architectures, starting
weights, completed updates, positive/negative presentations, selection rules and
decoding budgets, then report resource costs. Raw/PCA/AE inverse reconstructions
entering an unchanged raw-trained decoder measure interventions; they do not
measure equally trained representation-conditioned decoders or compressed
inference. Keep source-only and disabled/zero/rotated conditioning controls
distinct. A lower CE or vector MSE is not sufficient for selection when generated
fidelity or unsupported acceptance regresses.

Seal new independent final source groups after the target profile is set. The
old R6/v3/composition cohorts and both examined grouped final sets are now
diagnostic material. Grouped source-identical scope pairs and derived negatives
stay together. The semantic admission requirements for real-law conclusions
remain separate from permission to train on explicitly fictional fixtures.

## Publication and duplicate evidence

The retained Legal initial publication is immutable revision
`a87cc2303776319385c9c2855886e4410a8a3d08`. Expanded source reconstruction weights
are at `d624057cf58e0090a0db9a3ad25857aaa91357de`, under
`releases/20261005-authored32-source-reconstruction-aes-v1` (36 checkpoint
triplets; nine selected). The all-project archive is
`081c55a0635dacc443192de7562ea4cfe8bc06c8`; its 1,640 selected files are archive
coverage, not 1,640 independently useful models. This review did not rehash that
whole remote archive or download its payloads.

Grouped v1 is at `80087f53b1dff4811623079dd7d642347d6232bb`, under
`experiments/grouped-span-head-20261006/run-03`. Grouped v2 is at
`726386d3cb0ef068f275d4ded97fef71fdfeebf0`, under
`experiments/grouped-span-head-v2-20261006/run-02`. V2's retained verification
covers 98 appended files, downloaded selected checkpoint bytes, model/Adam
resave and reproduced source-only prediction. It preserves prior model/evidence
files and explicitly records the server-managed LFS tracking exception.

The joint-conditioning publication commits `8c02d655…` and `3b39519d…` have
identical artifact trees and represent one study. Greedy and joint policies
reuse the same forwards; repeated seeds, publication copies and stress examples
do not create independent source observations. Our grouped model adds a new
grammar and refusal experiment; it does not supersede those conditioning
controls or close their unmeasured semantic-fidelity gap.

Integration should therefore preserve existing owners and evidence, add the
explicit grouped profile and shared scoring connections, and advance the
reviewed-target and matched-comparison work already specified in the main plan.
No model or scientific result needs to be renamed or retrained merely to make
its contribution visible on main.
