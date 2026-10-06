# Runtime compatibility review, 2026-10-06

Published datasets commit `795d960170214d03e2eaf4c0a13ad4eb922c5c08` includes the contextual LegalIR384/768 runtime, while the canonical workspace checkout at `d5238def256d1c352793ee7d977e6b17b6d8cbee` lacks its three modules. The bounded useful integration is to bring those already published modules, their four dedicated tests and their guide into the canonical workspace, with the exact training-import relocation in `source_value_decoder_experiment.py`. The audit inspected pinned Git source and live source bytes. It made no source/Git changes and loaded no model, weights, encoder, database or checker.

The exact addition/dependency hashes, live preimages, API contracts, previous test receipts and proposed checks are in [runtime-compatibility.json](runtime-compatibility.json). [build_runtime_compatibility.py](build_runtime_compatibility.py) reproduces that static survey; [source_value_lazy_import.diff](source_value_lazy_import.diff) retains the only existing-file delta. The parent agent owns materialization and actual verification.

## Compatible source closure

The runtime names thirteen pinned owners. Its facade and numerical owner are absent locally. Ten of the eleven existing numerical owners are byte-identical to published main. The remaining owner, `source_value_decoder_experiment.py`, differs only by moving `reference_weights` from module scope into `reference_source_values()`, with a three-line comment. This preserves every calculation: static AST comparison after removing that import confirms exact equality. The move prevents restoration from importing the historical training/reference owner through the source-value chain; an explicit training reference call retains its original dependency.

The output owner's direct dependencies—`decoder_source_fidelity.py`, `canonical_contracts.py` and `canonical_decompiler.py`—and relevant package initializers are also byte-identical to published main. Existing canonical compiler/decompiler files show changes relative to the old shared HEAD but already contain published bytes. They need no replacement.

| Entry point | Contract | Practical boundary |
| --- | --- | --- |
| `prepare_contextual_legal_ir_runtime` | Closed five-field LegalIR request, explicit 384/768 input width, `semantic_IR_reconstruction`, selected checkpoint and exact thirteen source pins | Metadata preparation; no numerical imports, model, store or network execution |
| `open_contextual_legal_ir_autoencoder` | Original cached source paragraphs/ordered clauses, selected state, saved preprocessing, raw384 donor | Explicit lazy CPU float32 restoration; caller configures one thread |
| `describe()` / `infer_cached()` | Fixed retained source selection, complete tensor inventory, source fences, raw token/status/EOS candidates | At most64 selected rows/eight clauses/512 output tokens; no fresh sources or training |
| Output owner | Generated token parsing through actual `CanonicalRoundTripIR`, separate ordered/canonical/text scores | References only enter evaluation; missing candidates and incomplete EOS stay failed rows |

The selected32-entry state and13-entry donor retain their original numerical geometry and codec. No target, reference IR, gold prefix or target-derived clause count enters generation. The output owner preserves generated rule order independently of canonical sorting and measures source-withheld text reconstruction separately. All teacher, native format/profile, production runtime, fresh holdout, long-span and proof authority flags remain false.

## Interfaces that remain separate

`ir_model_manager_import` registers authenticated metadata through an injected genuine manager and requires fresh persisted readback. It does not select or open the contextual runtime. Its concrete lane identities support8/384/768, while source-token/unbound components retain null external width. A ModelManager row or immutable Hub location confers no serving readiness.

The common `autoencoder_runtime_registry` supports version-explicit historical8D/current384D legal features, attached latent formula heads, published384 packages, a separately trained source-text formula lineage and native structural formula lineages. It has no contextual384/768 state or exact-resume adapter. The native decoder profile inventory supports the preserved Intent/Security384 fragment contracts; the contextual Legal native profile/schema/format is deliberately unknown. Adding published source availability should not invent a registry alias or route through a mismatched class.

The original8D `LegacyLinguisticTeacher` remains a guided/compiler-observation adapter over the preserved linguistic model. The separate4096 sidecar requires a live full native embedding owner, reuses only donor token embedding/GRU/readout and adds new source paths. Its projection is explicitly identity, so zero reconstruction MSE does not demonstrate trained reconstruction or stronger formalization. Validated native-v7 training consumes actual compiler projections and source-disjoint batches; it has no raw-source text decoder objective.

Shared prepared targets, Arrow features and sparse modal updates support the owned feature campaigns. The formula fleet has its own exact checkpoint exchange, one DuckDB owner, scoped Quack leases and owner replay of actual decoded-output Lake checks. Neither route accepts contextual states merely because they contain GRU weights. The contextual runtime does not open those stores. Public checkpoint publication is separate from shared training state synchronization.

## Verification for this integration

1. Materialize only absent files from the pinned published commit. Check each hash and refuse existing-file clobber. Apply the source-value import move only under its exact observed preimage; retain before/after hashes.
2. Run the published metadata, adversarial and output tests in the canonical workspace, with minimal imports, auto-install disabled, offline flags and pytest plugin autoload disabled. These cover closed selectors, exact source pins, malformed/restored asset metadata, file changes, cache provenance, token/EOS completeness, genuine canonical contract conformance and independent text scoring. Their numerical restoration/inference calls are injected inert controls.
3. Add a fresh-process import probe invoking only the numerical owner's `_owners()` helper with historical training/reference modules, ModelManager, databases, encoders and network imports blocked. No model constructor or original assets are needed. This directly verifies the lazy import relocation.
4. Retain the dedicated numerical tests with the source; their synthetic Torch model execution is separate from the requested no-model materialization checks. Original asset replay and its archived qualification receipts remain prior evidence.

The earlier isolated closure receipts already record129 canonical profile tests,774 original-wrapper tests and25 existing checkpoint-Hub controls, for928 distinct tests. These are historical5171a632-era closure results, with no models or Lean admission. They do not validate this newer runtime, and no rerun of those suites is needed without a dependency change.

The original contextual regression reports48/48 ordered and canonical semantic IR matches for each width and0/48 original-text byte matches. These are exposed authored data, empty qualifiers and a deterministic prose baseline. Separate paraphrase modality findings and normative TRAIN/DEVELOPMENT controls use different states and source populations. Preserve each experiment's asset joins. Current source-bound family coverage and actual Lake gates remain required for formalization or proof admission.
