# ProofGroundedIRLearningFabric current implementation inventory

Inventory date: 2026-08-16 UTC  
Repository inspected: `/home/barberb/lift_coding/hallucinate_app/ipfs_datasets_py`  
Mode: read-only inspection of the checked-out filesystem; no repository files were changed.

This document identifies the existing implementations that should be extended or adapted. It does not designate a new logic family, semantic-state system, proof cache, prover, scheduler, or MCP++ profile.

## Preflight revision and worktree facts

- Reviewed revision: `7f0fe2bbad3c70928234c6e2312ee3182fd7681f`.
- Checked-out `HEAD`: `d144be65ffe4c6423e4e1c30cd692812607343eb`.
- `HEAD` is the merge base and an ancestor of the reviewed revision.
- `git rev-list --count HEAD..7f0fe2b` returned `1717`; `git rev-list --count 7f0fe2b..HEAD` returned `0`.
- The checkout is therefore 1,717 commits behind the reviewed baseline, not the reviewed baseline plus intervening changes.
- The inspected worktree already had 6,839 modified/untracked status entries. Representative logic files contained real working-tree diffs, not only file-mode changes.
- The inventory below treats the actual checked-out filesystem as implementation evidence, as requested. It must not be interpreted as evidence that the reviewed revision is present.

This is a fail-closed preflight condition for implementation: create a clean isolated worktree at an explicitly admitted revision, preserve the existing dirty tree, and rerun this inventory before changing code or admitting training data. In particular, commit subjects between `HEAD` and the reviewed revision refer to `FormalizationArtifact@3`, `DomainLogicSlice@2`, and UI/UX IR work that is absent from the inspected filesystem.

## Classification vocabulary

- **canonical**: current declared semantic or trust authority.
- **canonical component**: reviewed part of a canonical pipeline, but not the whole authority.
- **generated**: machine-produced source or derived artifact.
- **compatibility facade**: stable compatibility import or adapter over another owner.
- **legacy**: retained older implementation or wire surface.
- **experimental**: advisory, benchmark, or research implementation.
- **artifact-only**: persisted evidence/output rather than a semantic implementation.
- **declaration-only**: schema declarations without a complete execution path.
- **duplicate**: overlapping implementation whose authority must be reconciled.
- **obsolete**: explicitly deprecated.
- **unresolved**: required role not found in the inspected checkout.

The machine-readable starting point for the logic authority map is `ipfs_datasets_py/logic/submodule_registry.py`.

## Canonical foundations and source grounding

| Classification | Current owner and role |
|---|---|
| canonical | `ipfs_datasets_py/logic/ir_core/canonical.py`: deterministic canonical JSON and collection semantics. |
| canonical | `logic/ir_core/identity.py`: SHA-256 and CIDv1 canonical identities. |
| canonical | `logic/ir_core/provenance.py`: `SourceRef`, `SourceSpan`, producer/config bindings, and closed provenance graphs. |
| canonical | `logic/ir_core/schema_registry.py`: explicit compatibility, deterministic migrations, and structured loss reports. |
| canonical | `logic/ir_core/claims.py`, `protocols.py`, and `evidence.py`: assumptions, obligations, claims, bounded backend results, evidence, authority, and proof/result receipts. |
| canonical | `logic/ir_core/artifacts.py`: content/integrity artifacts, run manifests, reviewed decisions, and verification. |
| canonical | `logic/formalization/samples.py`, `views.py`, and `compiler.py`: source-grounded `FormalizationSample@v1`, view/symbol/formula/cross-view contracts, compiler protocol, unsupported-semantics diagnostics, and `FormalizationArtifact@v1`. |
| canonical component | `logic/formalization/constraint_contracts.py`: typed constraint statements, applicability, premise sets, world policies, coverage gaps, translation receipts, and reconstruction receipts. |
| canonical component | `logic/integration/reasoning/legal_ir_source_maps.py`: lossless legal source-document/span/transformation graph and artifact traceability. |
| canonical component | `logic/integration/reasoning/legal_ir_build_manifest.py`: deterministic compiler build/replay manifest binding source/output digests, code, passes, models, tools, and runtime configuration. |

`SourceRef` is the correct reusable lineage primitive, but it does not itself close the required corpus-release contract. It lacks required first-class Hugging Face configuration/split/file/shard/row identity, publisher, jurisdiction, authority level, legal-document type, citation/effective dates, retrieval date, and transformation-rights fields. `processors/legal_data/canonical_legal_corpora.py` is a canonical dataset-ID registry, but it stores mutable repository IDs and filenames rather than exact Hub revisions.

No general source-versus-derived record distinction, `IRLineageGraph@1`, corpus build manifest, or source-lineage grouping contract was found. `ArtifactRole` distinguishes pipeline input/parent/output/diagnostic, which is not equivalent to legal source record versus derivative row.

## Current IRs and logic-family implementations

| Role | Classification | Current implementation |
|---|---|---|
| legal measured bridge | canonical | `logic/legal_ir/canonical_contracts.py`, `canonical_compiler.py`, `canonical_decompiler.py`, `canonical_roundtrip.py` |
| formalization adapter | compatibility facade | `logic/legal_ir/adapter.py` |
| multiview bridge registry | canonical component | `logic/bridge/types.py`, `registry.py`, `multiview.py`, and family adapters |
| deontic legal IR | canonical component | `logic/deontic/ir.py`, `converter.py`, `decoder.py`, `exports.py`, `graph.py`, `prover_syntax.py` |
| deterministic modal IR | canonical component | `logic/modal/compiler.py`, `codec.py`, `decompiler.py`, `kg_bridge.py`, with IR records in `optimizers/logic_theorem_optimizer/modal_ir.py` |
| first-order logic | canonical component | `logic/fol/converter.py`, `text_to_fol.py`, and `logic/types/fol_types.py` |
| temporal deontic FOL | canonical component | `logic/TDFOL/tdfol_core.py`, `tdfol_parser.py`, `tdfol_prover.py`, inference rules, strategies, NL bridge, countermodels |
| cognitive/event calculus | canonical component | `logic/CEC/native/` plus current wrappers and prover adapters |
| frame logic | canonical component | `logic/flogic/flogic_types.py`, `semantic_normalizer.py`, `ergoai_wrapper.py` |
| Intent IR | canonical | `logic/intent_ir/schema.py`, `canonicalize.py`, `decoder.py`, `formalize/`, evaluation and GraphRAG adapters |
| Security IR | declaration-only canonical schema | `logic/security_ir/model.py`; result authority and domain/legacy adapters are adjacent |
| crypto-exchange security IR | canonical domain component | `logic/security_models/crypto_exchange/ir/schema.py`, `canonicalize.py`, compiler/runners/reports |
| hybrid legal reasoner IR | legacy / duplicate | `processors/legal_data/reasoner/hybrid_legal_ir.py` |
| next-generation hybrid sketch | experimental / declaration-only | `processors/legal_data/reasoner/hybrid_v2_blueprint.py` |
| Python-2-era DCEC and external assets | legacy/vendor | `logic/CEC/DCEC_Library/`, Talos/ShadowProver wrappers; `logic/ErgoAI/` is a placeholder/vendor location |
| old integration namespace | obsolete compatibility | `logic/tools`, explicitly deprecated in favor of `logic.integration` |
| software-verification IR | unresolved | No current dedicated implementation found |
| UI/UX IR | unresolved | No current dedicated implementation found |
| generic cryptographic IR | unresolved | Only the crypto-exchange security-domain IR was found |

There is no module named `syntax_core`. Typed syntax is distributed across deontic IR, modal IR, TDFOL, native DCEC, formalization formulas/constraints, and the hammer translation term AST. No `DomainLogicSlice` implementation or generation was found. No datasets-owned `SemanticState` or `SemanticCapsule` contract was found.

## Bridge, compiler, decompiler, and translation authority

### Measured canonical path

`logic/legal_ir/canonical_compiler.py` owns `TypedDeonticCanonicalCompiler`, which invokes the existing deterministic `logic.deontic.DeonticConverter` and projects typed `LegalNormIR` records into `CanonicalRoundTripIR@1`. `canonical_decompiler.py` owns the source-withheld deterministic controlled reconstruction. `canonical_roundtrip.py` composes the two.

This is the strongest current canonical round-trip boundary, but its measured grammar is deliberately narrow: canonical O/P/F rules with bounded actor/action/object/condition/exception/temporal facets. It is not the requested shared typed bridge for arbitrary binders, quantifiers, equality, modal/temporal/event/frame structures, assumptions, provenance, and family extensions.

### Existing parallel surfaces

- `logic/bridge/` is a canonical component and adapter registry for modal/frame, deontic, FOL/TDFOL, CEC/DCEC, external prover, and ZKP views. `LegalIRDocument` is an envelope over view payloads, not a closed shared typed bridge AST.
- `logic/integration/reasoning/legal_ir_compiler_api.py` exposes daemon-free `compile_legal_ir`, `decompile_legal_ir`, validation, diff, explain, benchmark, export, and LSP operations. It is a useful public component but contains a separate lowering path that must be consolidated behind the selected canonical bridge.
- `logic/modal/compiler.py` and `decompiler.py` are the expert-auditable modal path. The decompiler retains source-backed reconstructed text and audit phrases, which must not be confused with source-withheld controlled decompilation.
- `logic/integration/reasoning/legal_ir_interop.py` handles JSON/XML/RDF/KG/proof/decompiler interchange.

Translation meaning is currently split among `formalization.views.CrossViewRelation`, a boolean `lossy` field in `constraint_contracts.TranslationReceipt`, `LogicTranslationTarget/TranslationResult`, and interop `lossless/lossy/unsupported`. There is no single closed preservation classification for `lossless`, `equisatisfiable`, sound over/under approximation, `heuristic`, and `unsupported`. Translation currently lacks a universal rule preventing evidence-authority increase.

## Proof, tactician, hammer, and provider roles

| Classification | Current owner and boundary |
|---|---|
| canonical | `logic/hammers/`: content-addressed theorem corpus, deterministic and gated learned premise selection, Lean/Coq/Isabelle frontends, typed TPTP/SMT-LIB translation, bounded Z3/CVC5/Vampire/E portfolio, candidate provenance, native reconstruction, and content-addressed receipts. `VERIFIED` requires a kernel-accepted reconstruction. |
| canonical | `logic/proof_corpus/`: content-addressed proof store/index/query, attestations, applicability, manifests, append-only lineage, revocation, trust policy, audit, and independent verification. |
| canonical component | `logic/external_provers/`: lazy Z3, CVC5, Lean, Coq, and SymbolicAI adapters and deterministic routing. |
| compatibility / duplicate | `logic/integration/reasoning/hammer.py`, `legal_ir_hammer.py`, older proof execution/cache surfaces. They should adapt to `logic/hammers` rather than establish another trust contract. |
| canonical component for evidence retrieval only | `processors/legal_data/proof_tactician.py`: docket/evidence-source search plans and escalation. It is not a proof-state tactician and does not rank theorem-prover tactics or premises against formal proof states. |
| experimental candidate adapter | `logic/modal/leanstral.py`, verifier/audit/reporting modules: model proposals, proof drafts, compiler hints, and local validation. Module contracts explicitly keep canonical IR and proof authority outside the model. |
| canonical benchmark/provider boundary | `benchmarks/logic_pipeline/adapters.py`: strict, source-bound provider requests, fixed theorem/context, model identity, budgets, candidate receipts, and independent kernel handoff. It imports `ProofContextCapsule` from `ipfs_accelerate_py.agent_supervisor.proof_context`. |
| compatibility facade | `ipfs_datasets_py/llm_router.py` aliases the accelerator-owned canonical router. |
| operational adapter | `optimizers/logic_theorem_optimizer/llm_backend.py`: router/accelerator/local/mock inference compatibility; it is not semantic or proof authority. |

There is no closed `IRTacticTrace@1` or unified proof-attempt trace covering every requested state, premise, tactic, model/tool identity, disposition, and resource field. `optimizers/logic_theorem_optimizer/proof_trace.py` is a simpler legacy JSON serialization. Hammer receipts are the stronger current trust/evidence model.

## Model, loss, example, split, and evaluation implementations

### Learned representation

`optimizers/logic_theorem_optimizer/modal_autoencoder.py` is the actual current learned representation implementation:

- `ModalAutoencoderBaseline` deterministically copies a precomputed embedding through encode/decode and evaluates family distributions.
- `AdaptiveModalAutoencoder` is explicitly an adaptive diagnostic/advisor, not canonical legal representation.
- The current architecture version is `proof_aware_auxiliary_heads_v2`, with compatibility for `legacy_dense_v1`.
- State is primarily sparse feature embeddings/logits, family/view heads, decompiler-plan heads, and proof auxiliary heads.
- `legal_ir_grammar_decoder.py` supplies structure-level grammar admission.

This is not yet either requested encoder-decoder architecture. There is no pinned token-sequence model with tokenizer/vocabulary identity, teacher-forcing/free-running protocol, binder/type-constrained decoding, typed decoder heads, or a shared latent model experiment contract.

### Losses

Current loss functions include normalized cosine, embedding MSE, family/distribution cross entropy, entropy/KL excess, frame ranking, symbolic validity, bridge losses, source-copy penalties, and semantic/proof guardrails. `train_generalizable_projection` applies guarded feature-level updates with rollback.

Missing or incomplete:

- no `IRLossConfiguration@1`;
- no canonical fixed-point/decimal durable weights;
- no masked token CE by logical token class;
- no pinned tokenizer/vocabulary;
- no recorded teacher-forcing or scheduled-sampling policy;
- no reproducible supervised-contrastive/InfoNCE sampler and memory-bank identity;
- no complete cycle/structure/relation/semantic/proof/source-span/calibration multi-task objective under one versioned configuration.

### Examples, positives, negatives, and splits

- `optimizers/logic_theorem_optimizer/legal_samples.py` defines a reproducible U.S.-Code-specific `LegalSample`; it does not carry complete release, split, compiler/decompiler, translation, proof, or label-authority lineage.
- No closed `IRTrainingExample`, compiler/decompiler/translation/round-trip trace, proof-grounding, or positive-pair contract was found.
- `legal_ir_hard_negatives.py` and `legal_ir_fuzzing.py` provide verified-negative curriculum, mutation, and minimization components. The verification gate accepts loose boolean fields, including `leanstral_verified`, rather than a closed evidence-authority vocabulary. Unknown relationships do not have the required universal `unknown` disposition contract.
- `legal_ir_eval_splits.py` provides deterministic train/validation/canary/holdout/statute-family/jurisdiction/temporal/external-test partitions with example/content/citation/source-span/amendment/near-duplicate leakage keys.

The split implementation does not yet group every source CID derivative, graph/vector projection, proof-target sibling, alternate notation, or generated paraphrase. Required holdout dimensions for publication, legal domain, logic family, notation, document type, compiler, proof library, unseen premises, length, rare operators, exception density, and cross-reference density are incomplete.

### Evaluation

Current components are distributed across:

- `legal_ir_semantic_metrics.py`;
- `legal_ir_family_evaluator.py`;
- `legal_ir_metric_lineage.py`;
- `legal_ir_evaluation_artifacts.py` and cache;
- `legal_ir_uncertainty.py` and drift monitoring;
- `logic/modal/introspection_{metrics,analysis,export}.py`;
- `benchmarks/semantic_roundtrip/` and `benchmarks/logic_pipeline/`.

There is no unified `IREvaluationSuite@1`. Current coverage does not provide all requested per-token-class CE, latent effective-rank diagnostics, retrieval measures, structural/semantic/proof metrics, calibration curves, paired bootstrap confidence intervals, and OOD dimensions under one immutable suite. `logic.bridge.types.ProofGateResult.disabled()` and bridge-level soft-pass metadata are acceptable diagnostic shortcuts but must be inadmissible for checkpoint promotion.

## Checkpoints and publication

Two complementary manifests currently share the name `CheckpointManifest`:

1. `logic/formalization/checkpoints.py`: domain-separated advisor model/weights/training-config/ontology/view/feature identities with fail-closed compatibility.
2. `optimizers/logic_theorem_optimizer/modal_autoencoder_checkpoint.py`: non-executable checksummed full/delta state containers, precision, metric lineage, component digests, and torn-tail recovery.

Neither is `IRCheckpointManifest@1`. The current state checkpoint does not bind all required tokenizer, vocabulary, corpus root, split root, curriculum, optimizer, scheduler, data cursor, random state, environment, code, compiler, and decompiler identities. No complete created-to-promoted lifecycle or unified compare-and-swap promotion authority exists in this repository.

Hugging Face components:

- `huggingface/repository.py` is the canonical read-only immutable repository-revision receipt and injected fetcher.
- `huggingface/bucket.py` is a bounded bucket inventory/store component.
- `huggingface/snapshot.py` is a compatibility facade over the SkillCenter snapshot implementation and retains the legacy wire spelling.
- `huggingface/release.py` is the canonical generic deterministic Parquet/shard/CID helper.
- `huggingface/publisher.py` implements strong append-only, approval-gated publication and pinned redownload verification, but its schemas, defaults, and evidence anchors are Abby-voice-specific.
- `logic/intent_ir/graphrag/skillcenter_hf_release.py` and `benchmarks/logic_pipeline/custodian_release.py` are domain/benchmark-specific release components.

There is no datasets-root `publish_ir_release` API, IR dataset/checkpoint card builder, or versioned IR release configuration owner.

## Public API gap

Stable imports currently exist for `logic.ir_core`, `logic.formalization`, `logic.legal_ir`, `logic.intent_ir`, `logic.security_ir`, `logic.hammers`, `logic.proof_corpus`, and read-only `huggingface` contracts. `logic.integration.reasoning.legal_ir_compiler_api` also exposes useful lower-level functions.

No inspected module defines the requested public functions:

`build_ir_corpus`, `build_ir_split_manifest`, `create_ir_training_examples`, `compile_to_ir`, `decompile_from_ir`, `translate_ir`, `mine_ir_positive_pairs`, `mine_ir_hard_negatives`, `evaluate_ir_checkpoint`, `verify_ir_checkpoint_manifest`, or `publish_ir_release`.

These should be thin stable APIs over the authorities above. Importing them must not start trainers, daemons, providers, or network access.

## Security and recovery coverage

Strong reusable controls already exist:

- bounded canonical JSON/CID and source-reference validation;
- closed proof/result authority in `ir_core.protocols`;
- hammer candidate-versus-kernel authority separation;
- proof-corpus revocation and append-only manifest verification;
- source-map, proof-carrying artifact, premise-security, and schema-migration validation;
- safe, non-pickle checkpoint framing, finite-number checks, size bounds, checksums, lineage, delta ordering, and torn-tail recovery;
- Hugging Face path safety, digest/CID checks, immutable revisions, credential rejection, append-only writes, and pinned redownload verification.

Missing is one integrated fail-closed Q suite for malicious Parquet paths, arbitrary dataset scripts or `trust_remote_code`, decompression bombs, oversized rows, embedded secrets, prompt-injection policy text, rights conflicts, cross-statement/stale proof attachment, tokenizer/data-cursor mismatch, split leakage, gradient failures, lease-fenced checkpoint writes, crash injection at every pipeline stage, and publication recovery.

## Consolidation direction

The smallest coherent implementation should:

1. extend `ir_core` provenance/artifact contracts for release, source, derivative, lineage, and split identities;
2. extend the reviewed formalization contracts rather than add another semantic-state or logic-family system;
3. consolidate the measured canonical legal bridge, multiview registry, and daemon-free compiler API behind one typed bridge contract;
4. adapt `logic/hammers`, `logic/proof_corpus`, external prover adapters, and accelerator proof context without adding a proof cache or prover;
5. wrap the current modal autoencoder as the first experimental advisor baseline, then compare the two requested smallest compatible architectures;
6. unify existing loss, split, semantic metric, checkpoint, and HF release components through versioned IR contracts;
7. leave campaign scheduling, leases, resources, checkpoint promotion workflow, daemon execution, and supervisor state in `ipfs_accelerate_py`.

## Focused current test anchors

- Foundations/formalization: `tests/unit/logic/ir_core`, `tests/unit/logic/formalization`.
- Canonical compiler/decompiler: `tests/unit/logic/legal_ir`, `tests/integration/logic/test_canonical_semantic_roundtrip.py`.
- Family conformance: `tests/integration/logic/test_ir_family_conformance.py`, `test_ir_compatibility_exports.py`, and focused deontic/TDFOL/CEC/FLogic suites.
- Provider and capsule boundary: `tests/integration/benchmarks/logic_pipeline/test_leanstral_adapter.py`, `test_leanstral_runtime.py`, `test_live_runtime.py`, plus router-provider unit tests.
- Proof corpus: `tests/unit/logic/proof_corpus`.
- Hammer: `tests/unit_tests/logic/hammers`, `tests/integration/logic/hammers`, and benchmark hammer adapter/replay tests.
- Tactician: `tests/unit/processors/test_docket_dataset.py -k tactician`.
- Model/checkpoint/split/negative curriculum: focused files under `tests/unit/optimizers/logic_theorem_optimizer/` for modal autoencoder, checkpoint, eval splits, and hard negatives.
- Publication/security: `tests/unit/voice/test_abby_voice_hf_publish.py`, SkillCenter HF release tests, custodian-release integration, premise-security, and adversarial hammer tests.

These tests must be rerun in the clean admitted worktree before any implementation task is leased.
