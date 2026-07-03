# SwissKnife MCP++ WASM Theorem Prover Integration
## Comprehensive Improvement Plan & Task Board
### Document: 36-swissknife-wasm-theorem-provers-2026-07-01

---

## 1. Executive Summary

The swissknife MCP++ deontic logic layer currently delegates all hard
formal-logic proofs to the Python `ipfs_datasets_py` TDFOL engine over the
MCP++/libp2p RPC connector (`mcp-remote-deontic-engine.ts`).  This introduces a
network round-trip for every temporal/obligation discharge check, requires the
Python server to be running, and creates an availability single-point-of-failure.

The Python reference implements five external-prover backends (Z3, CVC5, Coq,
Lean 4, SymbolicAI) behind a `ProverRouter` with caching and parallel strategies.
WASM/JS editions of the same provers are now available or buildable, enabling
swissknife to run the same quality of proof locally in Node.js or the browser with
no Python dependency.

This document defines the full work programme to bring swissknife to feature
parity with the Python prover tier.

---

## 2. Python Reference Architecture (Source of Truth)

### 2.1 External Prover Stack (ipfs_datasets_py/logic/external_provers/)

| Backend | File | Strategy | Capability |
|---|---|---|---|
| Z3 4.x | `smt/z3_prover_bridge.py` | SMT solver | FOL, arithmetic, arrays, quantifiers, model generation |
| CVC5 | `smt/cvc5_prover_bridge.py` | SMT solver | SMT-LIB2 superset of Z3, stronger string/quantifier support |
| Coq (coqc) | `interactive/coq_prover_bridge.py` | Interactive CIC | Higher-order, inductive types, tactic proof extraction |
| Lean 4 (lake) | `interactive/lean_prover_bridge.py` | Dep. types | Lean4 + Mathlib, tactic proof, #check/#eval via subprocess |
| SymbolicAI | `neural/symbolicai_prover_bridge.py` | Neural-symbolic | LLM-guided proof sketch + checker |
| ProverRouter | `prover_router.py` | Dispatcher | FASTEST / MOST_CAPABLE / PARALLEL / SEQUENTIAL |
| ProofCache | `proof_cache.py` | Cache | sha256-keyed in-memory + optional IPFS pin |
| FormulaAnalyzer | `formula_analyzer.py` | Routing aid | Classifies formula complexity → chooses prover tier |

### 2.2 Core ProofResult Contract (Python dataclass, wire shape)

```python
@dataclass
class Z3ProofResult:
    is_valid: bool          # formula proved (unsat when negated)
    is_sat: bool            # formula satisfiable
    is_unsat: bool
    model: Optional[Any]    # model if sat
    unsat_core: Optional[List[str]]
    reason: str             # 'proved' | 'refuted' | 'unknown' | 'timeout' | 'error'
    proof_time: float       # seconds
```

### 2.3 ZKP Layer (ipfs_datasets_py/logic/zkp/)

- `circuits.py` — Circom/Plonky3 circuit definitions for obligation discharge proofs
- `provekit/` — Lurk/Nova/SP1/Sphinx proof artifact generation and verification
- `statement.py` — ZK statement encoding for deontic norms

### 2.4 CEC / DCEC Layer (ipfs_datasets_py/logic/CEC/) — **Gap discovered 2026-07-03**

A full Cognitive Event Calculus (CEC) / Deontic Cognitive Event Calculus (DCEC) layer exists
in the Python reference, **not previously captured in this plan**:

| File | Description |
|---|---|
| `CEC/native/dcec_core.py` | DCEC formula types: `DeonticOperator` (O/P/F/S/R/L/POW/IMM), `CognitiveOperator` (B/K/I/D), `TemporalFormula`, `QuantifiedFormula`, `AtomicFormula`, `ConnectiveFormula` |
| `CEC/native/prover_core.py` | Native Python DCEC proof engine: `ModusPonens`, `Simplification`, `DeonticProhibition` (F↔O¬), `DeonticPermission` (P↔¬O¬), tableau-based saturation, forward chaining |
| `CEC/native/prover_core_extended_rules.py` | Extended deontic inference rules: `DeonticObligation` transfer, `TemporalPersistence`, etc. |
| `CEC/cec_framework.py` | `CECFramework` orchestrator — NL→DCEC→proof pipeline |
| `CEC/shadow_prover_wrapper.py` | `ShadowProverWrapper` — modal logic (K/S4/S5) + cognitive calculus; native-first, Java fallback |
| `CEC/talos_wrapper.py` | `TalosWrapper` — SPASS-backed first-order prover |
| `CEC/eng_dcec_wrapper.py` | `EngDCECWrapper` — English → DCEC via Grammatical Framework |
| `CEC/dcec_wrapper.py` | `DCECLibraryWrapper` — DCEC_Library Python 2 submodule compatibility layer |
| `CEC/native/dcec_parsing.py` | DCEC formula parser (s-expression + prefix notation) |
| `CEC/native/temporal.py` | Temporal calculus (event holds-at, initiates, terminates) |
| `CEC/native/cec_proof_cache.py` | CEC-specific proof cache (separate from `external_provers/proof_cache.py`) |

**Relevance to swissknife:** The DCEC layer handles **modal-deontic formulas** (O/P/F with
no temporal window). ✅ **Closed in Sprint 9** by `DcecProverBridge`.

### 2.5 TDFOL Engine (ipfs_datasets_py/logic/TDFOL/) — **Gap discovered 2026-07-03**

The core **Temporal Deontic First-Order Logic (TDFOL)** engine that backs the `tdfol_prove`
remote MCP tool — **not previously in scope**:

| File | Description |
|---|---|
| `TDFOL/tdfol_core.py` | TDFOL formula type system: `TemporalOperator` (ALWAYS/EVENTUALLY/NEXT/UNTIL/SINCE/RELEASE), `DeonticOperator`, `BinaryTemporalFormula`, `UnaryFormula`, `QuantifiedFormula`, `TDFOLKnowledgeBase` |
| `TDFOL/tdfol_prover.py` | 640-line TDFOL prover: `TDFOLProver` orchestrating ForwardChaining + ModalTableaux + CECDelegate strategies; 10 built-in rules (see below) |
| `TDFOL/tdfol_parser.py` | 818-line TDFOL formula parser (s-expression + FOL notation) |
| `TDFOL/tdfol_inference_rules.py` | TDFOL-specific inference rules extending the CEC 87-rule set |
| `TDFOL/modal_tableaux.py` | Modal tableaux for K, T, D, S4, S5 modal logics |
| `TDFOL/strategies/` | `ForwardChainingStrategy`, `ModalTableauxStrategy`, `CECDelegateStrategy`, `StrategySelector` |
| `TDFOL/tdfol_dcec_parser.py` | DCEC↔TDFOL translation layer |

**TDFOL inference rules** (from `tdfol_prover.py`):
- `TemporalNecessitationRule` — introduce □φ
- `TemporalDistributionRule` — K axiom: □(φ→ψ), □φ ⊢ □ψ
- `TemporalTRule` — T axiom: □φ ⊢ φ (always implies now)
- `TemporalEventuallyIntroduction` — φ ⊢ ◊φ
- `DeonticNecessitationRule` — introduce O(φ)
- `DeonticDistributionRule` — K axiom for deontic: O(φ→ψ), O(φ) ⊢ O(ψ)
- `DeonticDRule` — SDL D axiom: O(φ) ⊢ P(φ)
- `PermissionIntroduction` — φ ⊢ P(φ)
- `ProhibitionElimination` — F(φ) ⊢ ¬P(φ) (prohibition → not permitted)
- `UntilUnfoldingRule` — φ U ψ ⊢ ψ ∨ (φ ∧ ◯(φ U ψ))

**Relevance to swissknife:** TDFOL handles the `temporal` formula class that currently falls
back to the remote Python engine for every policy with `policy.temporal` or obligation deadlines.
Adding `TdfolProverBridge` (Sprint 10) would close the last mandatory remote fallback.

### 2.6 Additional Logic Layers (ipfs_datasets_py/logic/) — **Scope for Sprint 12+**

| Directory | Description | Sprint | Priority |
|---|---|---|---|
| `logic/deontic/analyzer.py` | `DeonticAnalyzer`: regex NL→deontic statement extraction, conflict detection (direct/conditional/jurisdictional/temporal), Jaccard word-similarity | Sprint 12 ✅ | P2 |
| `logic/deontic/knowledge_base.py` | `DeonticKnowledgeBase`: temporal KB with `TimeInterval`, `Party`, `Action`, `Proposition`, rule inference, `checkCompliance()` | Sprint 12 ✅ | P2 |
| `logic/deontic/graph.py` | `DeonticGraph`: typed graph (nodes/rules/conflicts), `detect_conflicts()`, `assess_rules()`, `source_gap_summary()`, `export_reasoning_rows()`, `to_dict()` | Sprint 16 ✅ | P2 |
| `logic/deontic/support_map.py` | `SupportFact`, `SupportMapEntry`, `SupportMapBuilder.build(graph)` | Sprint 16 ✅ | P2 |
| `logic/deontic/ir.py` | `LegalNormIR`: typed IR (modality/actor/action/conditions/temporal/penalties + quality fields) | Sprint 17 ✅ | P2 |
| `logic/deontic/decoder.py` | `decode_legal_norm_ir(norm)`: deterministic text renderer from `LegalNormIR` slots | Sprint 17 ✅ | P2 |
| `logic/fol/converter.py` | `FOLConverter`: regex NL→FOL (predicate extraction, quantifiers, operators, `build_fol_formula()`, TPTP/Prolog formatting) | Sprint 14 ✅ | P2 |
| `logic/bridge/modal_frame_logic.py` | `ModalFrameLogicBridgeAdapter`: encode legal text → modal IR, graph-project, proof-gate | Sprint 14 ✅ | P2 |
| `logic/flogic_optimizer.py` | `FLogicSemanticOptimizer`: cosine similarity scoring + F-logic consistency checking for round-trip quality | Sprint 15 ✅ | P2 |
| `logic/ml_confidence.py` | `MLConfidenceScorer`: heuristic confidence scoring (fallback from XGBoost/LightGBM; pure math) | Sprint 15 ✅ | P2 |
| `logic/deontic/utils/deontic_parser.py` | `classify_modal()`, `classify_legal_entity()`, `identify_obligations()`, `detect_normative_conflicts()`, `score_scaffold_quality()` | Sprint 18 ✅ | P2 |
| `logic/deontic/prover_syntax.py` | `ProverTargetSyntaxRecord`, `ProverSyntaxReport`, `build_prover_syntax_records_from_ir()` | Sprint 18 ✅ | P2 |
| `logic/monitoring.py` | `LogicMonitor`: operation tracking, metrics (counter/gauge/histogram), `track_operation()`, `get_metrics()`, health checks | Sprint 19 ✅ | P2 |
| `logic/submodule_registry.py` | `LogicSubmoduleSpec`, `logic_submodule_specs()`, `logic_integration_manifest()` | Sprint 19 ✅ | P2 |
| `logic/batch_processing.py` | `BatchResult`, async/parallel batch formula evaluation | Sprint 19 ✅ | P2 |
| `logic/api.py` | Public API facade: `I18NConflictReport`, `compileNlToPolicy()`, `evaluateNlPolicy()` | Sprint 20 ✅ | P2 |
| `logic/e2e_validation.py` | `E2EValidator`, `ValidationResult`: end-to-end pipeline validation | Sprint 20 ✅ | P2 |
| `logic/types/` | Shared type system: `DeonticOperator`, `TemporalOperator`, `LegalAgent`, `TemporalCondition`, `LegalContext`, `DeonticFormula`, `DeonticRuleSet`, `FOLFormula`, `FOLConversionResult` | Sprint 21 ✅ | P2 |
| `logic/common/validators.py` | `validate_formula_string()`, `validate_axiom_list()`, `validate_logic_system()`, `validate_timeout_ms()` | Sprint 21 ✅ | P2 |
| `logic/common/bounded_cache.py` | `CacheEntry[T]`, `BoundedCache[T]` (generic LRU eviction cache) | Sprint 21 ✅ | P2 |
| `logic/TDFOL/nl/` | `parse_natural_language(text)` → TDFOL formulas (NL→TDFOL pipeline) | Sprint 21 ✅ | P2 |
| `logic/TDFOL/exceptions.py` | TDFOL exception hierarchy: `TDFOLError`/`ParseError`/`ProofError`/`ZKPProofError`/`InferenceError`/`CacheError` | Sprint 22 ✅ | P2 |
| `logic/TDFOL/tdfol_optimization.py` | `ProvingStrategy`, `IndexedKB`, `OptimizationStats`, `OptimizedProver` | Sprint 22 ✅ | P2 |
| `logic/TDFOL/security_validator.py` | Formula input security validation (injection/overflow protection) | Sprint 22 ✅ | P2 |
| `logic/TDFOL/tdfol_core.py` | TDFOL core type hierarchy: `TDFOLNode`, `Term`/`Variable`/`Constant`, `Formula`/`Predicate`/`BinaryFormula`/`UnaryFormula`/`QuantifiedFormula`, `TDFOLKnowledgeBase` | Sprint 23 ✅ | P2 |
| `logic/TDFOL/proof_tree_visualizer.py` | `ProofTreeNode` (formula/rule/justification/children), `ProofTree`, ASCII rendering | Sprint 23 ✅ | P2 |
| `logic/TDFOL/formula_dependency_graph.py` | `FormulaDependencyGraph` (addNode/addEdge/topologicalSort/detectCycles/findProofChain) | Sprint 23 ✅ | P2 |
| `logic/TDFOL/tdfol_parser.py` | `parse_tdfol(str)` → TDFOL `Formula` AST; `TDFOLLexer`/`TDFOLParser` | Sprint 24 ✅ | P2 |
| `logic/TDFOL/modal_tableaux.py` | `ModalLogicType` (K/T/D/S4/S5); `World`/`TableauxBranch`/`ModalTableaux.prove()` | Sprint 24 ✅ | P2 |
| `logic/TDFOL/performance_profiler.py` | `ProfilingStats`, `BenchmarkResult`, `PerformanceProfiler` | Sprint 24 ✅ | P2 |
| `logic/TDFOL/countermodels.py` + `countermodel_visualizer.py` | `KripkeStructure` (worlds/accessibility/valuation), `CountermodelVisualizer` (ASCII rendering) | Sprint 25 ✅ | P2 |
| `logic/TDFOL/tdfol_prover.py` | `TDFOLProver.prove()`, TDFOL inference rules (temporal/deontic necessitation/distribution) | Sprint 25 ✅ | P2 |
| `logic/TDFOL/performance_dashboard.py` | `ProofMetrics`, `TimeSeriesMetric`, `AggregatedStats`, `PerformanceDashboard` | Sprint 25 ✅ | P2 |
| `logic/bridge/types.py` | `LogicIRView`, `LegalIRDocument` (canonical hash), `RoundTripMetrics` (fromLossMapping/totalLoss), `GraphProjectionResult`, `BridgeEvaluationReport` | Sprint 26 ✅ | P2 |
| `logic/bridge/registry.py` | `LogicBridgeSpec`, `logicBridgeSpecs()`, `logicBridgeManifest()`, `loadLogicBridgeAdapter()`, `bridgeNameForComponent()` | Sprint 26 ✅ | P2 |
| `logic/bridge/zkp_attestation.py` | `ZkpAttestationBridgeAdapter.encode(text) → (LegalIRDocument, context)` | Sprint 26 ✅ | P2 |
| `logic/bridge/fol_tdfol.py` | `FolTdfolBridgeAdapter.encode(text)` → TDFOL formulas + frame logic + graph data | Sprint 27 ✅ | P2 |
| `logic/bridge/deontic_norms.py` | `DeonticNormsBridgeAdapter.encode(text)` → deontic IR + frame records + prover syntax | Sprint 27 ✅ | P2 |
| `logic/bridge/cec_dcec.py` | `CecDcecBridgeAdapter.encode(text)` → DCEC event formulas + frame logic + graph data | Sprint 27 ✅ | P2 |
| `logic/deontic/formula_builder.py` | Rich deontic formula builder (7019 lines) | Sprint 28 ✅ (partial — `build_deontic_formula_from_ir`) | P3 |
| `logic/bridge/multiview.py` | `MultiViewLegalIRReport`, `LegalIRTrainingTarget`, `evaluate_legal_ir_multiview()` | Sprint 28 ✅ | P3 |
| `logic/modal/synthesis.py` | `ModalProgramSynthesisHint`, `ModalResidualRepairRoute`, `RESIDUAL_REPAIR_ROUTES`, `route_autoencoder_residual()`, `residual_signature_for_hint()` | Sprint 29 ✅ | P3 |
| `logic/modal/kg_bridge.py` | `flogic_triples_to_graph_data()`, `modal_ir_to_neo4j_graph_data()`, `FLogicOntology`, `flogic_triples_to_ontology()` | Sprint 29 ✅ | P3 |
| `logic/zkp/circuits.py` | `decode_simulated_proof_layout()`, `build_proof_attestation_view()`, `attestation_view_matches_proof()` | Sprint 30 ✅ | P3 |
| `logic/integration/ucan_policy_bridge.py` | `UCANPolicyBridge`, `BridgeCompileResult`, `BridgeEvaluationResult`, `SignedPolicyResult`, `compile_and_evaluate()` | Sprint 30 ✅ | P3 |
| `logic/zkp/eth_integration.py` | `EthereumConfig`, `ProofVerificationResult`, `GasEstimate`, `EthereumProofClient`, `ProofSubmissionPipeline` | Sprint 30 ✅ | P3 |
| `logic/phase7_4_benchmarks.py` | `PerformanceMetrics`, `Phase7_4Benchmarks` | Sprint 30 ✅ | P3 |
| `logic/integration/reasoning/logic_verification.py` | `LogicVerifier`, `LogicAxiom`, `ProofResult` — symbolic formula verification | Sprint 31 ✅ | P3 |
| `logic/integration/converters/logic_translation_core.py` | `LogicTranslationTarget`, `TranslationResult`, `AbstractLogicFormula`, `LeanTranslator`, `CoqTranslator`, `SMTTranslator` | Sprint 31 ✅ | P3 |
| `logic/integration/domain/legal_symbolic_analyzer.py` | `LegalAnalysisResult`, `DeonticProposition`, `LegalEntity`, `LegalSymbolicAnalyzer` | Sprint 31 ✅ | P3 |
| `logic/integration/domain/deontic_query_engine.py` | `QueryType`, `QueryResult`, `ComplianceResult`, `LogicConflict`, `DeonticQueryEngine` | Sprint 32 ✅ | P3 |
| `logic/integration/domain/legal_domain_knowledge.py` | `LegalPattern`, `AgentPattern`, `LegalDomainKnowledge` | Sprint 32 ✅ | P3 |
| `logic/integration/bridges/tdfol_grammar_bridge.py` | `TDFOLGrammarBridge`, `NaturalLanguageTDFOLInterface`, `parse_nl()`, `explain_formula()` | Sprint 32 ✅ | P3 |
| `logic/integration/converters/deontic_logic_converter.py` | `ConversionContext`, `ConversionResult`, `DeonticLogicConverter.convert()` | Sprint 33 ✅ | P3 |
| `logic/integration/symbolic/symbolic_logic_primitives.py` | `LogicalStructure`, `LogicPrimitives`, `createLogicSymbol()`, `getAvailablePrimitives()` | Sprint 33 ✅ | P3 |
| `logic/integration/domain/symbolic_contracts.py` | `FOLInput`, `FOLOutput`, `ValidationContext`, `FOLSyntaxValidator` | Sprint 33 ✅ | P3 |
| `logic/integration/converters/modal_logic_extension.py` | `ModalFormula`, `LogicClassification`, `AdvancedLogicConverter`, `convertToModal()`, `detectLogicType()` | Sprint 34 ✅ | P3 |
| `logic/integration/domain/document_consistency_checker.py` | `DocumentAnalysis`, `DebugReport`, `DocumentConsistencyChecker` | Sprint 34 ✅ | P3 |
| `logic/integration/domain/temporal_deontic_rag_store.py` | `TheoremMetadata`, `ConsistencyResult`, `TemporalDeonticRAGStore` | Sprint 34 ✅ | P3 |
| `logic/integration/converters/deontic_logic_core.py` | `DeonticOperator`/`LogicConnective`/`TemporalOperator`/`LegalAgent`/`DeonticFormula`/`DeonticRuleSet` (extended core types) | Sprint 35 ✅ | P3 |
| `logic/integration/caching/ipld_logic_storage.py` | `LogicProvenanceChain`, `LogicIPLDNode`, `LogicIPLDStorage`, `LogicProvenanceTracker` | Sprint 35 ✅ | P3 |
| `logic/integration/reasoning/deontological_reasoning.py` | `DeonticExtractor`, `DeontologicalReasoningEngine` | Sprint 35 ✅ | P3 |
| `logic/integration/caching/ipfs_proof_cache.py` | `IPFSCachedProof`, `IPFSProofCache` (IPFS-backed distributed proof cache) | Sprint 36 ✅ | P3 |
| `logic/integration/domain/medical_theorem_framework.py` | `MedicalTheoremType`, `MedicalEntity`, `TemporalConstraint`, `MedicalTheorem`, `MedicalTheoremGenerator` | Sprint 36 ✅ | P3 |
| `logic/integration/bridges/tdfol_cec_bridge.py` | `TDFOLCECBridge`, `EnhancedTDFOLProver`, `create_enhanced_prover()` | Sprint 36 ✅ | P3 |
| `logic/integration/symbolic/neurosymbolic_api.py` | `ReasoningCapabilities`, `NeurosymbolicReasoner` (add_knowledge/prove/parse) | Sprint 37 ✅ | P3 |
| `logic/integration/proof_cache.py` | `CachedProof`, `ProofCache` (get/set/invalidate/stats), `get_global_cache()` | Sprint 37 ✅ | P3 |
| `logic/integration/cec_bridge.py` | `UnifiedProofResult`, `CECBridge` (prove/prove_with_cec/prove_batch) | Sprint 37 ✅ | P3 |
| `logic/integration/symbolic/neurosymbolic_graphrag.py` | `PipelineResult`, `NeurosymbolicGraphRAG` | Sprint 38 ✅ | P3 |
| `logic/integration/symbolic/neurosymbolic/hybrid_confidence.py` | `ConfidenceSource`, `ConfidenceBreakdown`, `HybridConfidenceScorer` | Sprint 38 ✅ | P3 |
| `logic/integration/bridges/base_prover_bridge.py` | `BridgeCapability`, `BridgeMetadata`, `BaseProverBridge`, `BridgeRegistry`, `get_bridge_registry()` | Sprint 38 ✅ | P3 |
| `logic/integration/symbolic/neurosymbolic/reasoning_coordinator.py` | `ReasoningStrategy`, `CoordinatedResult`, `NeuralSymbolicCoordinator` | Sprint 39 ✅ | P3 |
| `logic/integration/reasoning/_deontic_conflict_mixin.py` | `ConflictDetector`, `DeonticConflictMixin` | Sprint 39 ✅ | P3 |
| `logic/integration/interactive/interactive_fol_constructor.py` | `InteractiveFOLConstructor` | Sprint 39 ✅ | P3 |
| `logic/integration/symbolic/neurosymbolic/embedding_prover.py` | `EmbeddingEnhancedProver` (computeSimilarity/prove/retrieveSimilar) | Sprint 40 ✅ | P3 |
| `logic/integration/reasoning/_prover_backend_mixin.py` | `ProverBackendMixin` (Z3/Lean4/Coq execution + consistency check) | Sprint 40 ✅ | P3 |
| `logic/integration/bridges/symbolic_fol_bridge.py` | `LogicalComponents`, `FOLConversionResult`, `SymbolicFOLBridge` | Sprint 40 ✅ | P3 |
| `logic/integration/bridges/tdfol_shadowprover_bridge.py` | `ModalLogicType`, `TDFOLShadowProverBridge`, `ModalAwareTDFOLProver` | Sprint 41 ✅ | P3 |
| `logic/integration/reasoning/_logic_verifier_backends_mixin.py` | `LogicVerifierBackendsMixin` (consistency check + fallback backends) | Sprint 41 ✅ | P3 |
| `logic/integration/reasoning/proof_execution_engine_utils.py` | `createProofEngine()`, `proveFormula()`, `proveWithAllProvers()`, `checkConsistency()`, `getLeanTemplate()` | Sprint 41 ✅ | P3 |
| `logic/integration/bridges/external_provers.py` | `ProverStatus`, `ProverResult`, `VampireProver`, `EProver`, `ProverRegistry`, `get_prover_registry()` | Sprint 42 ✅ | P3 |
| `logic/integration/domain/caselaw_bulk_processor.py` | `CaselawDocument`, `ProcessingStats`, `BulkProcessingConfig`, `CaselawBulkProcessor` | Sprint 42 ✅ | P3 |
| `logic/integration/reasoning/proof_execution_engine_types.py` | `ProofStatus`, `ProofResult` (proof execution types) | Sprint 42 ✅ | P3 |
| `logic/integration/__init__.py` | `enable_symbolicai()`, `SYMBOLIC_AI_AVAILABLE`, lazy re-export of all integration symbols | Sprint 43 ✅ | P3 |
| `logic/integration/interactive/_fol_constructor_io.py` | `FOLConstructorIOMixin` (exportSession/importSession/saveToFile/loadFromFile) | Sprint 43 ✅ | P3 |
| `logic/integration/bridges/prover_installer.py` | `PlatformInstallProfile`, `detect_platform_install_profile()`, `install_component()` | Sprint 43 ✅ | P3 |
| `logic/modal/codec.py` | `ModalLogicCodecConfig`, `ModalLogicCodecResult` (source\_text/decoded\_text/losses/to\_dict), `DeterministicModalLogicCodec.encode()` | Sprint 44 ✅ | P3 |
| `logic/modal/decompiler.py` | `DecodedModalPhrase`, `DecodedModalText` (text/phrases/reconstruction\_similarity), `decode_modal_ir_document()`, `modal_formula_to_text()`, `modal_text_token_similarity()` | Sprint 44 ✅ | P3 |
| `logic/ErgoAI/` | ErgoAI/Erlog Datalog integration | Sprint 19+ | P3 |
| `logic/flogic/` | F-logic (frame logic) | Sprint 19+ | P3 |

---

## 3. Available JavaScript / WASM Prover Equivalents

### 3.1 Z3 — z3-solver (npm, production-ready)

- **Package**: `z3-solver@4.16.0` (npm, MIT, official Microsoft binding)
- **Source**: https://github.com/Z3Prover/z3/tree/master/src/api/js
- **API**: Full TypeScript high-level API + low-level WASM bindings
- **Size**: ~34 MB unpacked (WASM bundle)
- **Env**: Node.js + modern browsers (SharedArrayBuffer required)
- **Status**: ✅ Production-ready, 30 published versions, maintained by Z3 team

```ts
import { init } from 'z3-solver';
const { Z3 } = await init();
const ctx = new Z3.Context('main');
const solver = new ctx.Solver();
// High-level API: ctx.Int, ctx.Bool, ctx.ForAll, solver.check(), solver.model()
```

### 3.2 CVC5 — ufmg-smite/cvc5-wasm (build script)

- **Package**: No published npm. Build script compiles cvc5 → `.wasm` + `.js`.
- **Source**: https://github.com/ufmg-smite/cvc5-wasm
- **API**: SMT-LIB2 text interface (same as Z3 `--smt2` mode)
- **Alternative**: `@isl-lang/solver-z3-wasm` wraps Z3 with SMT-LIB2 REPL interface
- **Status**: ⚠️ Build-only; SMT-LIB2 text API fallback usable until native bindings exist

### 3.3 Coq / jsCoq (npm, mature)

- **Package**: `jscoq` (npm, available via CDN at coq.vercel.app)
- **Source**: https://github.com/jscoq/jscoq (v0.17.1, Coq 8.17)
- **API**: HTML embedding API + worker-based proof stepping
- **Use case**: Validate CIC/CoC terms, run `coqc`-equivalent checks in browser
- **Status**: ✅ Stable for educational/verification use; does not expose low-level C API

### 3.4 Lean 4 — lean4web / lake2nix

- **Source**: https://github.com/leanprover-community/lean4web (Lean 4 in browser via WASM)
- **Alternative**: argumentcomputer's Yatima compiler (Lean4 → Lurk → ZK proofs)
- **API**: Worker-based Lean server, `#check`/`#eval`/`theorem` evaluation
- **Status**: ⚠️ Experimental for embedding; lean4web works but is not an npm package

### 3.5 Lurk / Nova / Sphinx / multi-stark (argumentcomputer) — comprehensive audit 2026-07-01

The argumentcomputer organization maintains a rich portfolio of ZK proof systems.
This section replaces the earlier one-sentence summary with a full ecosystem map.

#### 3.5.1 Lurk v0.5 (active — PLONKY3 / SP1 backend)

- **Source**: https://github.com/argumentcomputer/lurk (v0.5, 167★)
- **Description**: Turing-complete ZK SNARK language (Lisp dialect). Programs are
  Lurk data; content-addressed via Poseidon hashes. Correct execution provable
  via SNARKs. Proofs are succinct and don't reveal private computation.
- **Backend**: Plonky3 STARKs via Sphinx (fork of SP1 zkVM). Earlier versions used Nova/SuperNova.
- **JavaScript presence**: `JavaScript 1.5%` in repo (some JS tooling/demo present).
- **WASM**: No explicit WASM build target documented for v0.5. Compile via `cargo build --target wasm32-unknown-unknown` may work but is untested.
- **Status**: v0.5 pre-production — explicitly a "transient accomplishment towards Lurk 1.0"; no formal audit yet.
- **Paper**: https://eprint.iacr.org/2023/369

#### 3.5.2 lurk-beta (maintenance mode — Nova/SuperNova backend)

- **Source**: https://github.com/argumentcomputer/lurk-beta (451★)
- **Description**: Previous elliptic-curve based Lurk implementation using Nova/SuperNova (Arecibo fork). Development moved to lurk v0.5.
- **WASM**: ✅ **Documented** — `cargo build --target wasm32-unknown-unknown` is a first-class build target in the README. This is the most directly usable path for WASM integration today.
- **Backends**: Nova (IVC over Pasta curves, Pallas/Vesta), SuperNova (NIVC extension).
- **Status**: ⚠️ Maintenance mode; new features go to lurk v0.5. WASM builds available but security properties inherit from Nova/SuperNova (not yet audited).

#### 3.5.3 Sphinx (SP1 fork — zkVM for RISC-V)

- **Source**: https://github.com/argumentcomputer/sphinx (77★, Apache-2.0/MIT)
- **Description**: Fork of Succinct Labs' SP1 zkVM. Proves correct execution of RISC-V bytecode. Built on Plonky3 STARKs.
- **Relation to Lurk**: Sphinx is the backend proving system that lurk v0.5 compiles to. Lurk programs → RISC-V → Sphinx proofs.
- **JavaScript/WASM**: No direct npm package. Proofs can be verified in JS via Groth16/PLONK compressed proofs (Go gnark integration in repo).
- **Key feature**: RISC-V universal circuit — any Rust program can be proven, not just Lurk.

#### 3.5.4 Arecibo (Nova + SuperNova fork)

- **Source**: https://github.com/argumentcomputer/arecibo (92★, MIT)
- **Description**: Advanced fork of Microsoft's Nova proving system. Adds SuperNova (NIVC), HyperKZG commitment scheme, Zeromorph evaluation argument.
- **Use case**: IVC (incrementally verifiable computation) — proofs that grow with computation steps but stay constant-size for verifiers. Used by lurk-beta.
- **Status**: Active incubator; backports contributions to Microsoft Nova.

#### 3.5.5 multi-stark (Plonky3 multicircuit STARK — actively developed)

- **Source**: https://github.com/argumentcomputer/multi-stark (5★, Apache-2.0, **updated 2 days ago**)
- **Description**: Implementation of a multicircuit STARK in Plonky3. Allows multiple circuits to be proven together efficiently.
- **Relevance**: Efficient backend for obligation-discharge proofs that span multiple deontic constraints simultaneously.
- **Status**: Actively developed. No published bindings yet; Rust-only.

#### 3.5.6 ix — ZK proof-carrying code platform for Lean 4 (🔥 most active)

- **Source**: https://github.com/argumentcomputer/ix (81★, Apache-2.0, **updated 3 hours ago**)
- **Description**: A zero-knowledge proof-carrying code (PCC) platform for Lean 4. Enables generating ZK proofs that Lean 4 programs (including theorems) execute correctly.
- **Relation to swissknife**: This is the most relevant project for the Lean4WasmBridge. `ix` sits at the intersection of our `Lean4WasmBridge` (Lean 4 proofs) and `LurkWasmBridge` (ZK proofs) — it generates ZK proofs OF Lean 4 theorem executions.
- **Integration path**: `ix` produces Lean 4 proof obligations → verifiable via a RISC-V execution proof in Sphinx/Plonky3. A future `Lean4WasmBridge` could delegate to `ix` for ZK-attestable proofs.
- **Status**: ✅ Actively developed (commits today).

#### 3.5.7 ZK Lean 4 libraries (Lean-native ZK)

These Lean 4 libraries implement cryptographic primitives for ZK proofs natively:

| Library | Stars | Description | Relevance |
|---|---|---|---|
| `ZKSnark.lean` | 8★ | zkSNARK implementation in Lean 4 | Lean-native SNARK circuits |
| `Poseidon.lean` | 8★ | Poseidon hash (ZK-friendly) | Content-addressing for ZK proofs |
| `FFaCiL.lean` | 14★ | Finite Fields and Curves in Lean | Arithmetic for ZK backends |
| `Lurk.lean` | 9★ | Lean 4 implementation of Lurk for recursive zkSNARKs | Formal ZK language in Lean |
| `Ipld.lean` | 8★ | IPLD format in Lean 4 | CID-native data for ZK attestation |
| `Yatima` | 146★ | ZK Lean4 compiler/kernel | Lean4 → Lurk → ZK proof pipeline |

#### 3.5.8 WASM / JavaScript integration summary

| System | WASM path | JS maturity | Priority for integration |
|---|---|---|---|
| lurk-beta | ✅ `--target wasm32-unknown-unknown` documented | Low (no npm) | P1 for lurk-beta WASM build |
| lurk v0.5 | ⚠️ Unknown (Plonky3 may add overhead) | Low | P2 pending |
| Sphinx/SP1 | ⚠️ Groth16 verifier via gnark (Go→WASM) | Low | P2 research |
| multi-stark | ❌ Rust-only | None | P3 future |
| ix | ❌ Rust/Lean | None | P2 via Lean4WasmBridge |
| ZKSnark.lean | ❌ Lean-only | None | P3 future |

**Recommended integration order** (Phase 6 refinement):
1. **lurk-beta WASM**: Compile via `cargo build --target wasm32-unknown-unknown`, wrap in Node.js `LurkWasmBridge.nativeLurk`. This is the most concrete near-term path.
2. **ix-backed Lean4WasmBridge**: When `ix` stabilises its CLI/API, invoke it from `Lean4WasmBridge` to produce ZK-attested Lean 4 proofs.
3. **Sphinx/Groth16 verifier**: For on-chain / cross-language verification of obligation discharge proofs.

### 3.6 Neural Prover (TypeScript equivalent)

- Current Python uses SymbolicAI (LLM-guided proof sketch + checker)
- TypeScript equivalent: Use swissknife's existing MCP++ connector to call an LLM tool, then verify the returned Lean/Coq tactic block locally

---

## 4. Gap Analysis vs Python Reference

> **Last updated: 2026-07-03 (post Sprint 7b).** Table reflects committed swissknife state.
> Rows marked ✅ are closed; rows marked ⚠️ are partial; ❌ are open.

| Feature | Python Reference | SwissKnife (current) | Status |
|---|---|---|---|
| Z3 SMT solving | ✅ `z3_prover_bridge.py` | ✅ `Z3WasmBridge` (z3-solver npm, lazy-load 34 MB) | **CLOSED** — Sprints 1, 7 |
| CVC5 SMT solving | ✅ `cvc5_prover_bridge.py` | ✅ `Cvc5WasmBridge` (SMT-LIB2 shim via Z3 WASM) | **CLOSED** — Sprint 2 |
| Coq proof checking | ✅ `coq_prover_bridge.py` | ✅ `CoqJsCoqBridge` (subprocess coqc + static path) | **CLOSED** — Sprint 3+4 |
| Lean 4 checking | ✅ `lean_prover_bridge.py` | ✅ `Lean4WasmBridge` (subprocess lean/lake) + `proveWithIx()` ZK path | **CLOSED** — Sprint 3+4 + 7b |
| Proof cache | ✅ `proof_cache.py` | ✅ `ProofCache` (sha256, ring-buffer, JSONL sink) | **CLOSED** — Sprint 1 |
| ProverRouter | ✅ `prover_router.py` (FASTEST/PARALLEL/SEQUENTIAL) | ✅ `WasmProverHub` (FASTEST/PARALLEL/SEQUENTIAL/REMOTE routing) | **CLOSED** — Sprints 1–3 |
| FormulaAnalyzer | ✅ `formula_analyzer.py` | ✅ `FormulaClassifier` (propositional/fol/temporal/higher_order) | **CLOSED** — Sprint 2 |
| ZK circuits (Lurk/Nova) | ✅ `zkp/` (Circom/Plonky3 + Lurk) | ⚠️ `LurkWasmBridge` stub; `proveWithIx()` for Lean4 ZK (backend: sphinx) | **PARTIAL** — real lurk-beta WASM pending (T-46–T-50) |
| ZK proof CID in audit | ✅ `zkp/statement.py` content-addressed artifact | ✅ `AuditEntry.extra.zk_proof_cid` via `PolicyAuditLog.record()` | **CLOSED** — Sprint 7b T-53 |
| Neural prover | ✅ `symbolicai_prover_bridge.py` (LLM sketch + verify) | ✅ `NeuralProverBridge` (LLM sketch → Lean4/Coq local verify) | **CLOSED** — Sprint 6 (T-38/T-57) |
| **DCEC / CEC layer** | ✅ `CEC/` — `dcec_core`, `prover_core`, `cec_framework`, `shadow_prover_wrapper`, `talos_wrapper` | ✅ `DcecProverBridge` (forward-chaining, 5 rules: MP/Simp/DeonticProhibEquiv/ObligImpliesPermit/ForbiddenToNotOblig) | **CLOSED** — Sprint 9 (T-58–T-62) |
| **TDFOL engine** | ✅ `TDFOL/` — `tdfol_core`, `tdfol_prover` (640 lines), `tdfol_parser`, `tdfol_inference_rules`, `modal_tableaux`, `strategies/` | ✅ `TdfolProverBridge` (10 LTL+SDL rules; closes temporal remote fallback) | **CLOSED** — Sprint 10 (T-63–T-67) |
| **UCAN-ZKP bridge** | ✅ `zkp/ucan_zkp_bridge.py` (592 lines) — `ZKPToUCANBridge`, `ZKPCapabilityEvidence` caveat | ✅ `ZkpUcanBridge` + `ZkpSimulatedProver` (`src/services/zkp/`) | **CLOSED** — Sprint 11 (T-68–T-71) |
| **ZKP simulated prover** | ✅ `zkp/zkp_prover.py` (289 lines) + `zkp_verifier.py` (313 lines) | ✅ `ZkpSimulatedProver` (hash-based, NOT real Groth16) | **CLOSED** — Sprint 11 |
| **Deontic Analyzer** | ✅ `deontic/analyzer.py` (503 lines) — regex NL→deontic + conflict detection | ✅ `DeonticTextAnalyzer` (`src/services/deontic/`) | **CLOSED** — Sprint 12 (T-72–T-75) |
| **Deontic Knowledge Base** | ✅ `deontic/knowledge_base.py` (245 lines) — `DeonticKnowledgeBase`, temporal intervals, rule inference | ✅ `DeonticKnowledgeBase` (`src/services/deontic/`) | **CLOSED** — Sprint 12 |
| **Extended TDFOL inference rules** | ✅ `TDFOL/inference_rules/` — 50+ rules across 5 files (temporal/deontic/temporal_deontic/propositional/fol) | ✅ `ExtendedTdfolProverBridge` (14 extra rules) + `ProverRouterBridgeAdapter` | **CLOSED** — Sprint 13 (T-76–T-79) |
| **Prover Router Bridge** | ✅ `bridge/external_prover_router.py` (1442 lines) — text → TDFOL formulas → prover router → ProofGateResult | ✅ `ProverRouterBridgeAdapter` (`src/services/bridge/`) | **CLOSED** — Sprint 13 |
| **FOL Text Converter** | ✅ `fol/converter.py` (497 lines) + `fol/utils/fol_parser.py` (233 lines) + `predicate_extractor.py` (76 lines) + `logic_formatter.py` (218 lines) | ✅ `FolTextConverter` (`src/services/fol/`) + `mcp++ deontic fol` | **CLOSED** — Sprint 14 (T-80–T-83) |
| **Modal Frame Logic Bridge** | ✅ `bridge/modal_frame_logic.py` (691 lines) — legal text → modal IR | ✅ `ModalFrameBridge` (`src/services/bridge/`) | **CLOSED** — Sprint 14 |
| **FLogic Semantic Optimizer** | ✅ `flogic_optimizer.py` (673 lines) — cosine similarity + F-logic ontology consistency | ✅ `FLogicSemanticOptimizer` + `cosineSimilarity()` (`src/services/fol/`) | **CLOSED** — Sprint 15 (T-84–T-87) |
| **ML Confidence Scorer** | ✅ `ml_confidence.py` (437 lines) — heuristic confidence for FOL conversion | ✅ `MLConfidenceScorer` + `FeatureExtractor` wired into `FolTextConverter` | **CLOSED** — Sprint 15 |
| **Deontic Graph** | ✅ `deontic/graph.py` (573 lines) — typed node/rule graph with `detect_conflicts()`, `assess_rules()` | ✅ `DeonticGraph` + `DeonticGraphBuilder` + `SupportMapBuilder` | **CLOSED** — Sprint 16 (T-88–T-91) |
| **Support Map** | ✅ `deontic/support_map.py` (167 lines) — `SupportFact`, `SupportMapEntry`, `SupportMapBuilder` | ✅ `SupportMapBuilder` (`src/services/deontic/`) | **CLOSED** — Sprint 16 |
| **LegalNormIR** | ✅ `deontic/ir.py` (2720 lines) — `LegalNormIR` typed IR dataclass (modality/actor/action/conditions/temporal/penalties) | ✅ `LegalNormIR` + `buildLegalNormIR()` + `emptySpan()/emptyQuality()` | **CLOSED** — Sprint 17 (T-92–T-95) |
| **LegalNorm Decoder** | ✅ `deontic/decoder.py` (932 lines) — deterministic text renderer | ✅ `decodeLegalNormIR()` + `decodedPhraseSlotTextMap()` + `LegalNormBuilder` | **CLOSED** — Sprint 17 |
| **Deontic Parser Utils** | ✅ `deontic/utils/deontic_parser.py` (5589 lines) — `classify_modal()`, `classify_legal_entity()`, `identify_obligations()`, `detect_normative_conflicts()`, `score_scaffold_quality()` | ✅ `DeonticParserUtils` + `NormativeConflictDetector` | **CLOSED** — Sprint 18 (T-96–T-99) |
| **Prover Syntax Builder** | ✅ `deontic/prover_syntax.py` (1652 lines) — `ProverTargetSyntaxRecord`, `validate_ir_with_provers()`, `build_prover_syntax_records_from_ir()` | ✅ `ProverSyntaxBuilder` (z3-smt2/dcec/tdfol/lean4/prolog) | **CLOSED** — Sprint 18 |
| **Logic Monitor** | ✅ `monitoring.py` (452 lines) — `LogicMonitor`, operation tracking, metrics | ✅ `LogicMonitor` (`src/services/logic-monitor.ts`) | **CLOSED** — Sprint 19 (T-100–T-103) |
| **Submodule Registry** | ✅ `submodule_registry.py` (614 lines) — `LogicSubmoduleSpec`, `logic_integration_manifest()` | ✅ `SubmoduleRegistry` + `getIntegrationManifest()` | **CLOSED** — Sprint 19 |
| **Batch Processor** | ✅ `batch_processing.py` (389 lines) — `BatchResult`, async batch formula evaluation | ✅ `BatchProcessor` (`src/services/batch-processor.ts`) | **CLOSED** — Sprint 19 |
| **I18N Conflict Report** | ✅ `api.py` (723 lines) — `I18NConflictReport` (multi-language conflict detection report) | ✅ `I18NConflictReport` + `detectMultilingualConflicts()` | **CLOSED** — Sprint 20 (T-104–T-107) |
| **E2E Validator** | ✅ `e2e_validation.py` (691 lines) — `E2EValidator`, `ValidationResult` | ✅ `E2EValidator.run() → ValidationSummary` (7 test suites) | **CLOSED** — Sprint 20 |
| **Logic Public API** | ✅ `api.py` (723 lines) — top-level `LogicPublicApi` facade, `compileNlToPolicy()`, `evaluateNlPolicy()` | ✅ `LogicPublicApi`: `analyzeText()`, `analyzeTexts()`, `detectMultilingualConflicts()` | **CLOSED** — Sprint 20 |
| **Logic Types** | ✅ `types/deontic_types.py` (296L) + `fol_types.py` (121L) + `common_types.py` (119L) + `proof_types.py` (26L) | ✅ `logic-types.ts` (`DeonticFormula`/`DeonticRuleSet`/`FOLFormula`/`ProofResult`) | **CLOSED** — Sprint 21 (T-108–T-111) |
| **Common Validators + BoundedCache** | ✅ `common/validators.py` (277L) + `common/bounded_cache.py` (233L) | ✅ `logic-validators.ts` (validators + `BoundedCache<T>`) | **CLOSED** — Sprint 21 |
| **TDFOL NL API** | ✅ `TDFOL/nl/tdfol_nl_api.py` — `parse_natural_language(text)` → TDFOL formulas | ✅ `tdfol-nl-api.ts` + `parse_natural_language()` alias | **CLOSED** — Sprint 21 |
| **TDFOL Exception Hierarchy** | ✅ `TDFOL/exceptions.py` (684L) — `TDFOLError`/`ParseError`/`ProofError`/`ZKPProofError`/`InferenceError`/`CacheError` | ✅ `tdfol-exceptions.ts` (9 classes + type guards) | **CLOSED** — Sprint 22 (T-112–T-115) |
| **TDFOL Optimization** | ✅ `TDFOL/tdfol_optimization.py` (539L) — `ProvingStrategy`, `IndexedKB`, `OptimizationStats`, `OptimizedProver` | ✅ `tdfol-optimization.ts` | **CLOSED** — Sprint 22 |
| **TDFOL Security Validator** | ✅ `TDFOL/security_validator.py` (777L) — formula input validation | ✅ `tdfol-security-validator.ts` | **CLOSED** — Sprint 22 |
| **TDFOL Core Types** | ✅ `TDFOL/tdfol_core.py` (826L) — `TDFOLNode`, `Term`/`Variable`/`Constant`, `Formula`/`Predicate`/`BinaryFormula`/`UnaryFormula`/`QuantifiedFormula` | ✅ `tdfol-core.ts` (9 node types + `TDFOLKnowledgeBase`) | **CLOSED** — Sprint 23 (T-116–T-119) |
| **Proof Tree Visualizer** | ✅ `TDFOL/proof_tree_visualizer.py` (999L) — `ProofTreeNode`, `ProofTree`, ASCII rendering | ✅ `proof-tree.ts` (ProofTree + ASCII + ProofTreeBuilder) | **CLOSED** — Sprint 23 |
| **Formula Dependency Graph** | ✅ `TDFOL/formula_dependency_graph.py` (889L) — `FormulaDependencyGraph`, cycle detection | ✅ `formula-dependency-graph.ts` (topologicalSort/detectCycles/findProofChain) | **CLOSED** — Sprint 23 |
| **TDFOL Parser** | ✅ `TDFOL/tdfol_parser.py` (818L) — `TDFOLLexer`/`TDFOLParser`, `parse_tdfol(str) → Formula` | ✅ `tdfol-parser.ts` (`TDFOLLexer`+recursive-descent parser; `parseTdfol`/`parseTdfolSafe`) | **CLOSED** — Sprint 24 (T-120) |
| **Modal Tableaux** | ✅ `TDFOL/modal_tableaux.py` (711L) — `ModalLogicType` (K/T/D/S4/S5), `World`, `TableauxBranch`, `ModalTableaux.prove()` | ✅ `modal-tableaux.ts` (`ModalLogicType`/`World`/`TableauxBranch`/`ModalTableaux`/`proveModalFormula`) | **CLOSED** — Sprint 24 (T-121) |
| **Performance Profiler** | ✅ `TDFOL/performance_profiler.py` (1411L) — `ProfilingStats`, `BenchmarkResult`, `PerformanceProfiler` | ✅ `performance-profiler.ts` (`ProfilingStats`/`PerformanceProfiler`/`ProfileBlock`/`benchmarkProviders`) | **CLOSED** — Sprint 24 (T-122) |
| **Kripke Structure + Countermodel Visualizer** | ✅ `TDFOL/countermodel_visualizer.py` (1102L) + `countermodels.py` — `KripkeStructure`, `CountermodelVisualizer` (ASCII/HTML) | ✅ `kripke-structure.ts` (`KripkeStructure`/`CountermodelVisualizer.renderAscii`/`createVisualizer`) | **CLOSED** — Sprint 25 (T-124) |
| **TDFOL Prover** | ✅ `TDFOL/tdfol_prover.py` (640L) — `TDFOLProver.prove()`, TDFOL inference rules | ✅ `tdfol-prover.ts` (8 rules + axiom/theorem lookup + forward-chaining + tableaux fallback) | **CLOSED** — Sprint 25 (T-125) |
| **Performance Dashboard** | ✅ `TDFOL/performance_dashboard.py` (1314L) — `ProofMetrics`, `AggregatedStats`, `PerformanceDashboard` | ✅ `performance-dashboard.ts` (`MetricType`/`ProofMetrics`/`AggregatedStats`/`PerformanceDashboard`) | **CLOSED** — Sprint 25 (T-126) |
| **Bridge Shared Types** | ✅ `bridge/types.py` (413L) — `LogicIRView`, `LegalIRDocument`, `RoundTripMetrics`, `GraphProjectionResult`, `BridgeEvaluationReport` | ✅ `bridge-types.ts` (`LogicIRView`/`LegalIRDocument.canonicalHash()`/`RoundTripMetrics.fromLossMapping`/`ProofGateResult.disabled()`/`BridgeEvaluationReport`) | **CLOSED** — Sprint 26 (T-128) |
| **Bridge Registry** | ✅ `bridge/registry.py` (285L) — `LogicBridgeSpec`, `logic_bridge_specs()`, `logic_bridge_manifest()`, `load_logic_bridge_adapter()` | ✅ `bridge-registry.ts` (6 specs + `logicBridgeSpecs/Manifest/bridgeNameForComponent`) | **CLOSED** — Sprint 26 (T-129) |
| **ZKP Attestation Bridge** | ✅ `bridge/zkp_attestation.py` (762L) — `ZkpAttestationBridgeAdapter.encode(text)` | ✅ `zkp-attestation-bridge.ts` (encode/evaluate; 4 views; simulated attestation records) | **CLOSED** — Sprint 26 (T-130) |
| **FOL/TDFOL Bridge** | ✅ `bridge/fol_tdfol.py` (2136L) — `FolTdfolBridgeAdapter.encode(text)` | ✅ `fol-tdfol-bridge.ts` (tdfol_formulas/frame_logic/neo4j_graph_data; formula_type classification) | **CLOSED** — Sprint 27 (T-132) |
| **Deontic Norms Bridge** | ✅ `bridge/deontic_norms.py` (2497L) — `DeonticNormsBridgeAdapter.encode(text)` | ✅ `deontic-norms-bridge.ts` (deontic_ir/prover_formulas/frame_logic/neo4j_graph_data; O/P/F detection) | **CLOSED** — Sprint 27 (T-133) |
| **CEC/DCEC Bridge** | ✅ `bridge/cec_dcec.py` (3671L) — `CecDcecBridgeAdapter.encode(text)` | ✅ `cec-dcec-bridge.ts` (cec_formulas/frame_logic/neo4j_graph_data; Happens/HoldsAt/Initiates/Terminates) | **CLOSED** — Sprint 27 (T-134) |
| **Deontic IR / formula_builder** | ✅ `deontic/formula_builder.py` (7019 lines) | ✅ `deontic-formula-builder.ts` (`normalizePredicateName`/`canonicalModalityOperator`/`buildDeonticFormulaFromIR`/O/P/F/DEF/PURP/APP/EXEMPT/LIFE) | **CLOSED** — Sprint 28 (T-137, partial) |
| **Multiview Aggregator** | ✅ `bridge/multiview.py` (4040L) — `MultiViewLegalIRReport`, `LegalIRTrainingTarget`, `evaluate_legal_ir_multiview()` | ✅ `bridge-multiview.ts` (`evaluateLegalIRMultiview`/`toTrainingTarget`/merged doc) | **CLOSED** — Sprint 28 (T-136) |
| **Modal KG Bridge** | ✅ `modal/kg_bridge.py` (1062L) — `flogic_triples_to_graph_data()`, `modal_ir_to_neo4j_graph_data()`, `FLogicOntology` | ✅ `modal-kg-bridge.ts` (`flogicTriplesToGraphData`/`flogicTriplesToOntology`/`modalIrToNeo4jGraphData`/Neo4j labels) | **CLOSED** — Sprint 29 (T-139) |
| **Modal Synthesis** | ✅ `modal/synthesis.py` (947L) — `ModalProgramSynthesisHint`, `ModalResidualRepairRoute`, `RESIDUAL_REPAIR_ROUTES`, `route_autoencoder_residual()` | ✅ `modal-synthesis.ts` (9 routes + `routeAutoencoderResidual`/`residualSignatureForHint`/`synthesisHintFromRoute`) | **CLOSED** — Sprint 29 (T-140) |
| **ZKP Circuit Utilities** | ✅ `zkp/circuits.py` (1328L) — `decode_simulated_proof_layout()`, `build_proof_attestation_view()`, `attestation_view_matches_proof()` | ✅ `zkp-circuits.ts` (`decodeSimulatedProofLayout`/`buildProofAttestationView`/`attestationViewMatchesProof`/`compilerGuidanceRefFromMetadata`) | **CLOSED** — Sprint 30 (T-142) |
| **UCAN Policy Bridge** | ✅ `integration/ucan_policy_bridge.py` (657L) — `UCANPolicyBridge`, `BridgeCompileResult`, `BridgeEvaluationResult`, `compile_and_evaluate()` | ✅ `ucan-policy-bridge.ts` (`UCANPolicyBridge.compileNl/evaluate/sign`; `BridgeCompileResult`/`BridgeEvaluationResult`; `compileAndEvaluate()`) | **CLOSED** — Sprint 30 (T-143) |
| **Ethereum ZKP Integration** | ✅ `zkp/eth_integration.py` (593L) — `EthereumConfig`, `ProofVerificationResult`, `EthereumProofClient` | ✅ `zkp-eth-integration.ts` (`EthereumConfig`/`ProofVerificationResult`/`GasEstimate`/`EthereumProofClient` stub/`ProofSubmissionPipeline`) | **CLOSED** — Sprint 30 (T-144) |
| **Phase 7.4 Benchmarks** | ✅ `phase7_4_benchmarks.py` (637L) — `PerformanceMetrics`, `Phase7_4Benchmarks` | ✅ `zkp-eth-integration.ts` (combined: `PerformanceMetrics.summary()`/`Phase7_4Benchmarks.runAllBenchmarks()`) | **CLOSED** — Sprint 30 (T-144) |
| **Logic Verifier** | ✅ `integration/reasoning/logic_verification.py` (743L) — `LogicVerifier`, `LogicAxiom`, `ProofResult` | ✅ `logic-verifier.ts` (`LogicAxiom`/`ProofResult`/`LogicVerifier.verifyFormula/proveWithAxioms/checkConsistency/checkEntailment`) | **CLOSED** — Sprint 31 (T-146) |
| **Logic Translation Core** | ✅ `integration/converters/logic_translation_core.py` (718L) — `LogicTranslationTarget`, `TranslationResult`, `LeanTranslator`, `CoqTranslator`, `SMTTranslator` | ✅ `logic-translation-core.ts` (`LeanTranslator`/`CoqTranslator`/`SMTTranslator`/`translateFormula()`) | **CLOSED** — Sprint 31 (T-147) |
| **Legal Symbolic Analyzer** | ✅ `integration/domain/legal_symbolic_analyzer.py` (699L) — `LegalAnalysisResult`, `DeonticProposition`, `LegalEntity`, `LegalSymbolicAnalyzer` | ✅ `legal-symbolic-analyzer.ts` (heuristic analysis: domain/deontic/entities/temporal; `LegalReasoningEngine`) | **CLOSED** — Sprint 31 (T-148) |
| **Deontic Query Engine** | ✅ `integration/domain/deontic_query_engine.py` (794L) — `QueryType`, `QueryResult`, `ComplianceResult`, `DeonticQueryEngine` | ✅ `deontic-query-engine.ts` (`QueryType`/`QueryResult`/`ComplianceResult`/`LogicConflict`/`DeonticQueryEngine.query/checkCompliance/detectConflicts`) | **CLOSED** — Sprint 32 (T-150) |
| **Legal Domain Knowledge** | ✅ `integration/domain/legal_domain_knowledge.py` (647L) — `LegalPattern`, `AgentPattern`, `LegalDomainKnowledge` | ✅ `legal-domain-knowledge.ts` (`LegalPattern.match()`/`AgentPattern.match()`/`LegalDomainKnowledge.extractConcepts/identifyAgents/patternsForDomain`) | **CLOSED** — Sprint 32 (T-151) |
| **TDFOL Grammar Bridge** | ✅ `integration/bridges/tdfol_grammar_bridge.py` (669L) — `TDFOLGrammarBridge`, `NaturalLanguageTDFOLInterface`, `parse_nl()` | ✅ `tdfol-grammar-bridge.ts` (`TDFOLGrammarBridge.parse/explain`/`NaturalLanguageTDFOLInterface`/`parseNl()`/`explainFormula()`) | **CLOSED** — Sprint 32 (T-152) |
| **Deontic Logic Converter** | ✅ `integration/converters/deontic_logic_converter.py` (739L) — `ConversionContext`, `ConversionResult`, `DeonticLogicConverter.convert()` | ✅ `deontic-logic-converter.ts` (`ConversionContext`/`ConversionResult.toDict()`/`DeonticLogicConverter.convert/convertEntities`) | **CLOSED** — Sprint 33 (T-154) |
| **Symbolic Logic Primitives** | ✅ `integration/symbolic/symbolic_logic_primitives.py` (594L) — `LogicalStructure`, `LogicPrimitives`, `createLogicSymbol()` | ✅ `symbolic-logic-primitives.ts` (13 `AVAILABLE_PRIMITIVES`; `analyzeLogicalStructure()`; `createLogicSymbol().apply/toFol()`) | **CLOSED** — Sprint 33 (T-155) |
| **Symbolic Contracts (FOL Validator)** | ✅ `integration/domain/symbolic_contracts.py` (840L) — `FOLInput`, `FOLOutput`, `FOLSyntaxValidator` | ✅ `fol-syntax-validator.ts` (`validateFolInput()`; `FOLOutput.isValid/toDict()`; `FOLSyntaxValidator.validate/convert()`) | **CLOSED** — Sprint 33 (T-156) |
| **Modal Logic Extension** | ✅ `integration/converters/modal_logic_extension.py` (531L) — `ModalFormula`, `LogicClassification`, `AdvancedLogicConverter`, `convertToModal()` | ✅ `modal-logic-extension.ts` (`AdvancedLogicConverter.toModal/classify/convertBatch`; `convertToModal()`; `detectLogicType()`) | **CLOSED** — Sprint 34 (T-158) |
| **Document Consistency Checker** | ✅ `integration/domain/document_consistency_checker.py` (538L) — `DocumentAnalysis`, `DebugReport`, `DocumentConsistencyChecker` | ✅ `document-consistency-checker.ts` (`DocumentAnalysis.toDict()`; `DebugReport.addIssue/finalize/toDict()`; `DocumentConsistencyChecker.analyze/generateDebugReport`) | **CLOSED** — Sprint 34 (T-159) |
| **Temporal Deontic RAG Store** | ✅ `integration/domain/temporal_deontic_rag_store.py` (520L) — `TheoremMetadata`, `ConsistencyResult`, `TemporalDeonticRAGStore` | ✅ `temporal-deontic-rag-store.ts` (`TheoremMetadata`; `ConsistencyResult.toDict()`; `TemporalDeonticRAGStore.addTheorem/findRelevant/checkConsistency/makeTheoremFromFormula`) | **CLOSED** — Sprint 34 (T-160) |
| **Deontic Logic Core (Extended)** | ✅ `integration/converters/deontic_logic_core.py` (514L) — `DeonticOperator` (O/P/F/S/R/L/POW/IMM), `LogicConnective`, `TemporalOperator`, `LegalAgent`, `DeonticRuleSet` | ✅ `deontic-logic-core.ts` (`DeonticOperatorExt`/`LogicConnective`/`TemporalOperatorExt`; `LegalAgent`; `DeonticRuleSetExt.query/search/obligations`) | **CLOSED** — Sprint 35 (T-162) |
| **IPLD Logic Storage** | ✅ `integration/caching/ipld_logic_storage.py` (489L) — `LogicProvenanceChain`, `LogicIPLDNode`, `LogicIPLDStorage`, `LogicProvenanceTracker` | ✅ `ipld-logic-storage.ts` (`LogicIPLDNode.addTranslation()`; `LogicIPLDStorage.findByDocument()`; `LogicProvenanceTracker`; CID generation) | **CLOSED** — Sprint 35 (T-163) |
| **Deontological Reasoning Engine** | ✅ `integration/reasoning/deontological_reasoning.py` (482L) — `DeonticExtractor`, `DeontologicalReasoningEngine` | ✅ `deontological-reasoning.ts` (`DeonticExtractor.extractStatements/countByOperator`; `DeontologicalReasoningEngine.reason/detectConflicts/generateExplanation/analyzeText`) | **CLOSED** — Sprint 35 (T-164) |
| **IPFS Proof Cache** | ✅ `integration/caching/ipfs_proof_cache.py` (457L) — `IPFSCachedProof`, `IPFSProofCache` | ✅ `ipfs-proof-cache.ts` (`IPFSCachedProof.computeCid/isExpired/toDict`; `IPFSProofCache.set/get/pin/unpin/getStats`; `getGlobalIPFSCache()`) | **CLOSED** — Sprint 36 (T-166) |
| **Medical Theorem Framework** | ✅ `integration/domain/medical_theorem_framework.py` (426L) — `MedicalTheoremType`, `MedicalEntity`, `MedicalTheoremGenerator` | ✅ `medical-theorem-framework.ts` (`MedicalTheoremType`/`ConfidenceLevel`; `MedicalTheorem.toFormula/toDict`; `MedicalTheoremGenerator.generateFromText/validateTheorem/generateBatch`) | **CLOSED** — Sprint 36 (T-167) |
| **TDFOL-CEC Bridge** | ✅ `integration/bridges/tdfol_cec_bridge.py` (435L) — `TDFOLCECBridge`, `EnhancedTDFOLProver` | ✅ `tdfol-cec-bridge.ts` (`TDFOLCECBridge.prove` (axiom/forward/CEC); `EnhancedTDFOLProver.prove/proveBatch/useKB/proofId`; `createEnhancedProver()`) | **CLOSED** — Sprint 36 (T-168) |
| **Neurosymbolic API** | ✅ `integration/symbolic/neurosymbolic_api.py` (414L) — `ReasoningCapabilities`, `NeurosymbolicReasoner` | ✅ `neurosymbolic-api.ts` (`ReasoningCapabilities`/127 rules/5 modal provers; `NeurosymbolicReasoner.addKnowledge/prove/explain/getStats`; `getReasoner()`) | **CLOSED** — Sprint 37 (T-170) |
| **Base Proof Cache** | ✅ `integration/proof_cache.py` (350L) — `CachedProof`, `ProofCache` | ✅ `proof-cache-base.ts` (`CachedProof.isExpired/hitCount/toDict`; `ProofCache.set/get/has/invalidate/clearExpired/flush/getStats`; `getGlobalCache()`) | **CLOSED** — Sprint 37 (T-171) |
| **CEC Bridge** | ✅ `integration/cec_bridge.py` (349L) — `UnifiedProofResult`, `CECBridge` | ✅ `cec-bridge.ts` (`UnifiedProofResult`; `CECBridge.prove(CEC→Z3)/proveWithCEC/proveBatch/getStats`) | **CLOSED** — Sprint 37 (T-172) |
| **Neurosymbolic GraphRAG** | ✅ `integration/symbolic/neurosymbolic_graphrag.py` (374L) — `PipelineResult`, `NeurosymbolicGraphRAG` | ✅ `neurosymbolic-graphrag.ts` (`PipelineResult.toDict()`; `NeurosymbolicGraphRAG.ingest/query/prove/getStats`) | **CLOSED** — Sprint 38 (T-174) |
| **Hybrid Confidence Scorer** | ✅ `integration/symbolic/neurosymbolic/hybrid_confidence.py` (341L) — `ConfidenceSource`, `ConfidenceBreakdown`, `HybridConfidenceScorer` | ✅ `hybrid-confidence.ts` (`ConfidenceSource`/`ConfidenceBreakdown.dominantSource/toDict`; `HybridConfidenceScorer.score/scoreFromResult/explain`) | **CLOSED** — Sprint 38 (T-175) |
| **Base Prover Bridge** | ✅ `integration/bridges/base_prover_bridge.py` (318L) — `BridgeCapability`, `BridgeMetadata`, `BaseProverBridge`, `BridgeRegistry` | ✅ `base-prover-bridge.ts` (`BridgeCapability` (5); abstract `BaseProverBridge`; `BridgeRegistry.register/get/list/getByCap`; `StubProverBridge`; `getBridgeRegistry()`) | **CLOSED** — Sprint 38 (T-176) |
| **Reasoning Coordinator** | ✅ `symbolic/neurosymbolic/reasoning_coordinator.py` (351L) — `ReasoningStrategy`, `CoordinatedResult`, `NeuralSymbolicCoordinator` | ✅ `reasoning-coordinator.ts` (`ReasoningStrategy` (4); `CoordinatedResult.toDict()`; `NeuralSymbolicCoordinator.coordinate(AUTO/SYMBOLIC/NEURAL/HYBRID)`) | **CLOSED** — Sprint 39 (T-178) |
| **Deontic Conflict Detector** | ✅ `reasoning/_deontic_conflict_mixin.py` (304L) — `ConflictDetector`, `DeonticConflictMixin` | ✅ `deontic-conflict-detector.ts` (`DeonticConflictType` (6); `ConflictDetector.detectConflicts/summarize`; `DeonticConflictMixin.wouldConflict/conflictScore`) | **CLOSED** — Sprint 39 (T-179) |
| **Interactive FOL Constructor** | ✅ `interactive/interactive_fol_constructor.py` (848L) — `InteractiveFOLConstructor` | ✅ `interactive-fol-constructor.ts` (`InteractiveFOLConstructor.addStatement/buildFormula/checkConsistency/getSession/reset/exportFormulas`) | **CLOSED** — Sprint 39 (T-180) |
| **Embedding Enhanced Prover** | ✅ `symbolic/neurosymbolic/embedding_prover.py` (240L) — `EmbeddingEnhancedProver` | ✅ `embedding-prover.ts` (`cosineSimilarity()`; `EmbeddingEnhancedProver.computeSimilarity/prove(exact+similarity)/retrieveSimilar/cacheSize`) | **CLOSED** — Sprint 40 (T-182) |
| **Prover Backend Mixin** | ✅ `reasoning/_prover_backend_mixin.py` (527L) — `ProverBackendMixin` | ✅ `prover-backend-mixin.ts` (`generateDeonticSMT2Axioms()`; `ProverBackendMixin.executeZ3/Lean4/Coq Proof/checkConsistency`) | **CLOSED** — Sprint 40 (T-183) |
| **Symbolic FOL Bridge** | ✅ `bridges/symbolic_fol_bridge.py` (764L) — `LogicalComponents`, `FOLConversionResult`, `SymbolicFOLBridge` | ✅ `symbolic-fol-bridge.ts` (`LogicalComponents` (dict-like); `SymbolicFOLBridge.extractComponents/convert/validate`) | **CLOSED** — Sprint 40 (T-184) |
| **TDFOL ShadowProver Bridge** | ✅ `bridges/tdfol_shadowprover_bridge.py` (596L) — `ModalLogicType`, `TDFOLShadowProverBridge`, `ModalAwareTDFOLProver` | ✅ `tdfol-shadowprover-bridge.ts` (`ModalLogicType` (5); `TDFOLShadowProverBridge extends BaseProverBridge`; `ModalAwareTDFOLProver.proveModal/proveInSystem/proveInAllSystems`) | **CLOSED** — Sprint 41 (T-186) |
| **Logic Verifier Backends Mixin** | ✅ `reasoning/_logic_verifier_backends_mixin.py` (293L) — `LogicVerifierBackendsMixin` | ✅ `logic-verifier-backends-mixin.ts` (`checkConsistencyFallback/Symbolic/findConflictingPairs`) | **CLOSED** — Sprint 41 (T-187) |
| **Proof Execution Engine Utils** | ✅ `reasoning/proof_execution_engine_utils.py` (206L) — `createProofEngine()`, `proveFormula()`, `proveWithAllProvers()`, `getLeanTemplate()` | ✅ `proof-execution-engine-utils.ts` (`ProofEngine.prove/proveAll/checkConsistency`; utils; Lean4 D-axiom template) | **CLOSED** — Sprint 41 (T-188) |
| **External Provers** | ✅ `bridges/external_provers.py` (610L) — `ProverStatus`, `ProverResult`, `VampireProver`, `EProver`, `ProverRegistry` | ✅ `external-provers.ts` (`ProverStatus` (6); `VampireProver`/`EProver` stubs; `ProverRegistry.register/get/list/getBestFor/prove`; `getProverRegistry()`) | **CLOSED** — Sprint 42 (T-190) |
| **Caselaw Bulk Processor** | ✅ `domain/caselaw_bulk_processor.py` (757L) — `CaselawDocument`, `ProcessingStats`, `BulkProcessingConfig`, `CaselawBulkProcessor` | ✅ `caselaw-bulk-processor.ts` (`makeCaselawDocument`; `ProcessingStats.toDict/reset`; `CaselawBulkProcessor.process/processBatch/getStats/reset`; `createBulkProcessor()`) | **CLOSED** — Sprint 42 (T-191) |
| **Proof Execution Engine Types** | ✅ `reasoning/proof_execution_engine_types.py` (100L) — `ProofStatus`, `ProofResult` (engine types) | ✅ `proof-execution-engine-types.ts` (`ProofStatus` (5); `ProofResult.isProved/failed/toDict()`; `makeProofResult()`) | **CLOSED** — Sprint 42 (T-192) |
| **Integration Package Init** | ✅ `integration/__init__.py` (334L) — `enable_symbolicai()`, `SYMBOLIC_AI_AVAILABLE`, lazy re-exports | ✅ `integration-init.ts` (`SYMBOLIC_AI_AVAILABLE`; `enableSymbolicAI()/resetSymbolicAI()`; `IntegrationCapabilities` (8 flags); `getIntegrationStatus()/hasCapability()`) | **CLOSED** — Sprint 43 (T-194) |
| **FOL Constructor IO Mixin** | ✅ `interactive/_fol_constructor_io.py` (299L) — `FOLConstructorIOMixin` (exportSession/importSession/saveToFile) | ✅ `fol-constructor-io-mixin.ts` (`exportSession(json|fol|prolog|tptp)/importSession/convertFormula/serializeSession/deserializeSession`) | **CLOSED** — Sprint 43 (T-195) |
| **Prover Installer** | ✅ `bridges/prover_installer.py` (867L) — `PlatformInstallProfile`, `detect_platform_install_profile()`, `install_component()` | ✅ `prover-installer.ts` (`PlatformInstallProfile`; `detectPlatformInstallProfile()`; `installComponent(name,profile?,dryRun?)/installComponents()/listKnownComponents()`) | **CLOSED** — Sprint 43 (T-196) |
| **Modal Logic Codec** | ✅ `modal/codec.py` (12843L) — `ModalLogicCodecConfig`, `ModalLogicCodecResult`, `DeterministicModalLogicCodec` | ✅ `modal-logic-codec.ts` (`makeCodecConfig()`; `ModalLogicCodecResult.totalLoss/kgTriples/toDict()`; `DeterministicModalLogicCodec.encode()/encodeBatch()` — simulated modal family detection + embeddings) | **CLOSED** — Sprint 44 (T-198) |
| **Modal IR Decompiler** | ✅ `modal/decompiler.py` (9621L) — `DecodedModalPhrase`, `DecodedModalText`, `decode_modal_ir_document()`, `modal_formula_to_text()` | ✅ `modal-ir-decompiler.ts` (`DecodedModalPhrase/DecodedModalText.toDict()`; `decodeModalIRDocument()`; `modalFormulaToText()` (O/P/F/□/◊); `modalTextTokenSimilarity()` (Jaccard)) | **CLOSED** — Sprint 44 (T-199) |
| Remote fallback | N/A | ✅ `mcp-remote-deontic-engine.ts` | Keep as last-resort fallback |

**Current status (post Sprint 44):** 44+ modules; modal logic codec + modal IR decompiler ported. **CORRECTION: review of all Python files reveals additional untracked modules.** Remaining P3: TDFOL/performance\_metrics + TDFOL/zkp\_integration + external\_provers/formula\_analyzer (Sprint 45); plus many smaller files in TDFOL/nl/, CEC/nl/, CEC/native/, zkp/backends/.

---

## 5. Target Architecture

```
swissknife MCP++ deontic layer  
│
├── PolicyEngine (existing, local JS)
│   └── permits / prohibitions / obligations (no deep logic)
│
├── WasmProverHub (src/services/mcp-wasm-prover-hub.ts) ✅
│   ├── ProofCache (sha256-keyed, ring-buffer, JSONL sink) ✅
│   ├── ProverRouter (FASTEST / PARALLEL / SEQUENTIAL / REMOTE) ✅
│   │   ├── Z3WasmBridge (Phase 1 — z3-solver npm, lazy-load) ✅
│   │   ├── Cvc5WasmBridge (Phase 2 — SMT-LIB2 shim) ✅
│   │   ├── CoqJsCoqBridge (Phase 3 — subprocess coqc) ✅
│   │   ├── Lean4WasmBridge (Phase 4 — subprocess lean + ix ZK) ✅
│   │   ├── LurkWasmBridge (Phase 6 — ZK, stub pending lurk-beta WASM) ⚠️
│   │   ├── NeuralProverBridge (Phase 7 — LLM sketch + local verify) ✅
│   │   └── DcecProverBridge (Phase 9 — native DCEC proof engine) 🆕
│   └── FormulaClassifier (Phase 2 — propositional/fol/temporal/higher_order) ✅
│
├── RemoteDeonticEngine (existing, keep as fallback)
│   └── delegates to ipfs_datasets_py tdfol_prove when local fails
│
└── DeonticInterfaceBroker (existing)
    └── calls WasmProverHub.prove() or RemoteDeonticEngine as needed
```

---

## 6. Phased Implementation Plan

### Phase 1 — Z3 WASM Local SMT (Priority: P0)
*Duration estimate: 3–5 days*

**Goal**: Replace the remote Z3 RPC call for first-order deontic queries with a
local `z3-solver` WASM invocation.  The remote engine remains as a fallback for
temporal/higher-order formulas z3-wasm cannot express.

**Deliverables**:
1. `src/services/mcp-wasm-prover-hub.ts` — `WasmProverHub` class stub (router + cache skeleton)
2. `src/services/provers/z3-wasm-bridge.ts` — `Z3WasmBridge` wrapping `z3-solver`
3. `src/services/mcp-proof-cache.ts` — `ProofCache` (sha256-keyed, in-memory ring buffer + optional JSONL log)
4. Wire `Z3WasmBridge` into `RemoteDeonticEngine.checkPolicyConsistencyRemote()` as a pre-check: if Z3 decides locally, skip the network call
5. Tests: 20+ unit tests covering SMT formula encoding, sat/unsat/timeout paths, cache hit/miss

**Key technical decisions**:
- `z3-solver` requires `SharedArrayBuffer` (COOP/COEP headers). For Node.js this is a no-op; for browser, document the header requirements.
- Encode deontic atoms as `Bool` predicates: `P(cap, rsc)` = `Bool` constant.
- Map `PolicyFormulaSet.obligation_formulas` to Z3 `ForAll` over obligation predicates.
- Result: `WasmProofResult { proved, sat, reason, proof_time_ms, prover_id }` (TypeScript equivalent of `Z3ProofResult`).

---

### Phase 2 — Proof Cache + Router + Formula Classifier (Priority: P0)
*Duration estimate: 3–4 days*

**Goal**: Add the ProofCache and ProverRouter so the hub selects the best local prover automatically.

**Deliverables**:
1. `src/services/mcp-proof-cache.ts` — Full `ProofCache`:
   - `get(formulaHash) → WasmProofResult | null`
   - `put(formulaHash, result, ttlMs?)` — ring-buffer eviction
   - `stats()` — hit/miss/evict counts
   - Optional JSONL sink (mirrors Python's IPFS-pin option)
2. `src/services/provers/formula-classifier.ts` — `FormulaClassifier`:
   - `classify(formula) → 'propositional' | 'fol' | 'temporal' | 'higher_order'`
   - Heuristic based on presence of quantifiers, temporal operators, dependent types
   - Maps to prover tier: propositional/FOL → Z3; temporal → remote; higher_order → Lean/Coq/remote
3. `WasmProverHub` routing strategies:
   - `FASTEST`: Try classifer-selected prover first, timeout 1s, then next
   - `PARALLEL`: Race all available local provers, take first positive result
   - `SEQUENTIAL`: Try in order Z3 → CVC5 → Coq → Lean → remote
4. `src/services/mcp-wasm-prover-hub.ts` fully wired
5. Tests: 15+ tests covering routing strategy, cache integration, classifier accuracy

---

### Phase 3 — CVC5 WASM SMT-LIB2 Bridge (Priority: P1)
*Duration estimate: 3 days*

**Goal**: Add CVC5 as a second SMT prover for formulas where CVC5's stronger string/quantifier theory gives better results.

**Deliverables**:
1. `src/services/provers/cvc5-wasm-bridge.ts` — `Cvc5WasmBridge`:
   - SMT-LIB2 text protocol via `@isl-lang/solver-z3-wasm` as a cross-prover baseline, OR build cvc5-wasm locally
   - Falls back to Z3 SMT-LIB2 text interface if no native CVC5 WASM available
   - `check_satisfiability(smt2_string) → WasmProofResult`
   - Shared SMT-LIB2 formula serializer with `Z3WasmBridge`
2. `src/services/provers/smt2-serializer.ts` — `SMT2Serializer`:
   - `policyToSMT2(policy) → string` — shared between Z3 and CVC5 bridges
   - `formulaSetToSMT2(formulaSet) → string`
3. Tests: 10+ tests for SMT-LIB2 serialization + CVC5 bridge fallback behavior

---

### Phase 4 — Coq jsCoq Worker Bridge (Priority: P1)
*Duration estimate: 5–7 days*

**Goal**: Embed jsCoq (Coq 8.17) as a Web Worker to validate higher-order
propositions that Z3/CVC5 cannot express.

**Deliverables**:
1. `src/services/provers/coq-jscoq-bridge.ts` — `CoqJsCoqBridge`:
   - Launches jsCoq as a Worker (browser) or via child_process mock (Node.js)
   - `prove(coqScript: string, timeoutMs: number) → WasmProofResult`
   - Translates deontic obligation formulas to Coq propositions (``Prop`` type)
   - Parses `Qed.` / error lines to determine proof status
2. `src/services/provers/deontic-to-coq.ts` — `DeonticToCoqTranslator`:
   - Translates `PolicyFormulaSet` to Coq `Theorem` + `Proof.` block
   - Covers: permission/prohibition/obligation predicates, modal operators P()/F()/O()
3. Tests: 10+ tests covering Coq script generation + result parsing

---

### Phase 5 — Lean 4 WASM Worker Bridge (Priority: P1)
*Duration estimate: 5–7 days*

**Goal**: Use lean4web to evaluate Lean 4 tactics for dependent-type proofs
(matching `LeanProverBridge` in Python).

**Deliverables**:
1. `src/services/provers/lean4-wasm-bridge.ts` — `Lean4WasmBridge`:
   - Wraps lean4web worker protocol (`#check`, `theorem`, `by tactic`)
   - `prove(leanSource: string, timeoutMs: number) → WasmProofResult`
2. `src/services/provers/deontic-to-lean4.ts` — `DeonticToLean4Translator`:
   - Translates `PolicyFormulaSet` to Lean 4 propositions
   - Uses `Prop`, `And`, `Or`, `Not`, quantifiers `∀`, `∃`
3. Mathlib stubs for deontic modal operators as Lean `Def`s
4. Tests: 10+ covering Lean source generation + proof outcome parsing

---

### Phase 6 — ZK Proof Circuits (Lurk / Nova / Sphinx / ix) (Priority: P2)
*Duration estimate: 7–14 days, split across sub-phases*

**Goal**: Generate STARK/SNARK proofs of obligation discharge so third parties can
verify policy compliance without trusting the prover (proof-carrying policy).

**Updated ecosystem understanding (2026-07-01 audit):**

- **lurk-beta** is the best near-term WASM target: documented `--target wasm32-unknown-unknown` build, Nova/SuperNova backend, 451★. ✅ LurkWasmBridge stub done (T-35).
- **lurk v0.5** (active development) uses Plonky3/Sphinx — more performant, no explicit WASM docs yet.
- **ix** (argumentcomputer/ix, 81★, **updated today**) — ZK PCC platform for Lean 4. When stable, `Lean4WasmBridge` can invoke `ix` to produce ZK-attested Lean 4 obligation-discharge proofs.
- **multi-stark** (argumentcomputer/multi-stark, Plonky3) — efficient backend for multi-constraint proofs; no WASM yet.

**Sub-phase 6a — lurk-beta WASM (P1, 3–5 days)**
1. Build `lurk-beta` with `cargo build --target wasm32-unknown-unknown`; wire `wasm-bindgen` or `napi-rs` bindings.
2. Update `LurkWasmBridge.create()` to try `import('lurk-wasm')` (package must be published or locally built).
3. `proveObligationDischarge(policy) → ZKProofArtifact` (real Nova proof).
4. `verifyProof(artifact) → boolean` via lurk-beta verify API.
5. Tests: 8+ including real lurk-beta WASM smoke test.

**Sub-phase 6b — ix / Lean 4 ZK (P2, 5–7 days, after ix CLI stabilises)**
1. Invoke `ix` CLI from `Lean4WasmBridge` to produce ZK-attested proof of obligation-discharge theorem.
2. Return `ZKProofArtifact` with `backend: 'sphinx'` (ix uses Sphinx/Plonky3 internally).
3. Attach artifact CID to `AuditEntry.extra.zk_proof_cid`.

**Sub-phase 6c — multi-stark / Plonky3 (P3, future)**
1. When `multi-stark` publishes WASM bindings, add `MultiStarkBridge` for efficient multi-obligation proofs.

**Previously delivered (T-34, T-35, T-36, T-37, T-39):**
- ✅ `DeonticToLurkTranslator` — obligation → Lurk s-expression
- ✅ `LurkWasmBridge` stub (returns unknown, native path ready for lurk-wasm package)
- ✅ `ZKProofArtifact` type + Mcp-Plus-Plus conformance vector
- ✅ `AuditEntry.extra` prover_id + proof_time_ms integration

---

### Phase 7 — Neural Prover (LLM-guided, Priority: P2)
*Duration estimate: 2–3 days*

**Goal**: Mirror `SymbolicAI` prover using swissknife's existing MCP++ connector.

**Deliverables**:
1. `src/services/provers/neural-prover-bridge.ts` — `NeuralProverBridge`:
   - Uses `MCPPPServerConnector` to call an LLM tool with the formula
   - Parses returned proof sketch (Lean/Coq block or JSON reasoning)
   - Verifies the sketch with the local Coq/Lean bridge before returning `proved`
2. Prompt template: "Given deontic formula `φ`, produce a Lean 4 proof or state `refuted`"
3. Tests: 8+ covering prompt generation + verification loop

---

### Phase 8 — Full Integration + Offline Mode (Priority: P0 after Phase 1–3)
*Duration estimate: 3–4 days*

**Goal**: Replace the mandatory remote call in `mcp-remote-deontic-engine.ts` with
a local-first policy that falls back to remote only when local provers timeout/fail.

**Deliverables**:
1. Update `RemoteDeonticEngine`:
   - Before calling `tdfol_prove`, attempt `WasmProverHub.prove(formula, { strategy: 'FASTEST' })`
   - Only delegate to remote if result is `{ proved: false, reason: 'unknown' }` or timeout
2. New `createLocalFirstDeonticORBEvaluator(hub, remoteEngine)` factory:
   - Local proof → emit `AuditEntry` with `prover_id: 'z3-wasm'`
   - Remote fallback → emit `AuditEntry` with `prover_id: 'python-tdfol'`
3. `mcp++ conformance` output updated to show prover capabilities
4. Tests: 15+ integration tests covering local-first → remote-fallback path

---

## 7. Task Board

### Legend
- **P0** = Blocking / immediate
- **P1** = High priority, sprint 1
- **P2** = Medium, sprint 2–3
- `[ ]` = Open, `[x]` = Done, `[-]` = Blocked

---

### Sprint 1 (Phase 1 + 2): Local Z3 + Router Foundation

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-01 | P0 | Install `z3-solver` npm dependency in swissknife | `npm install z3-solver` passes, types resolve |
| T-02 | P0 | Create `src/services/provers/z3-wasm-bridge.ts` with `Z3WasmBridge` class | `prove(formula, axioms, timeout) → WasmProofResult` |
| T-03 | P0 | Define `WasmProofResult` interface (mirrors Python `Z3ProofResult`) | TypeScript type exported, Mcp-Plus-Plus spec schema added |
| T-04 | P0 | Create `src/services/mcp-proof-cache.ts` with `ProofCache` | get/put/stats/clear, ring-buffer eviction, optional JSONL |
| T-05 | P0 | Create `src/services/mcp-wasm-prover-hub.ts` stub with Z3 + cache wired | `hub.prove(policy) → WasmProofResult` with FASTEST routing |
| T-06 | P0 | Write 20+ unit tests for Z3 bridge (sat/unsat/timeout/cache) | All pass in `npx jest test/mcp-plus-plus/z3-wasm-bridge.test.ts` |
| T-07 | P0 | Wire WasmProverHub into `RemoteDeonticEngine` as pre-check | Remote call skipped when Z3 decides locally |
| T-08 | P1 | Create `src/services/provers/formula-classifier.ts` | Classifies propositional/FOL/temporal/higher_order |
| T-09 | P1 | Implement PARALLEL routing strategy in `WasmProverHub` | Race local provers, take first positive result |
| T-10 | P1 | Write 15+ tests for router + classifier | All pass |
| T-11 | P1 | Add `WasmProofResult` schema to Mcp-Plus-Plus spec `models.ts` | Conformance vector `wasm_proof_result.json` added |
| T-12 | P1 | Benchmark Z3 vs Python TDFOL on standard deontic formula set | Report: latency (ms), correctness match rate |

---

### Sprint 2 (Phase 3 + 4): CVC5 + Coq

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-13 | P1 | Create `src/services/provers/smt2-serializer.ts` | ✅ `policyToSMT2(policy) → string` round-trips to Z3 |
| T-14 | P1 | Create `src/services/provers/cvc5-wasm-bridge.ts` (SMT-LIB2 mode) | ✅ Accepts SMT-LIB2 string, returns sat/unsat |
| T-15 | P1 | Evaluate `@isl-lang/solver-z3-wasm` as CVC5 compatibility shim | ✅ Decision: use Z3 SMT-LIB2 shim (z3-solver has same QF_UF) |
| T-16 | P1 | Wire CVC5 into `WasmProverHub` router | ✅ Available as fallback when Z3 WASM unavailable |
| T-17 | P1 | Write 10+ tests for SMT-LIB2 serializer + CVC5 bridge | ✅ 23 tests in wasm-prover-sprint2.test.ts |
| T-18 | P1 | Evaluate `jscoq` npm package for Node.js embedding | ✅ Decision: subprocess coqc + static analysis (jscoq browser-only) |
| T-19 | P1 | Create `src/services/provers/deontic-to-coq.ts` | ✅ Translates `PolicyFormulaSet` to valid Coq `Theorem` |
| T-20 | P1 | Create `src/services/provers/coq-jscoq-bridge.ts` | ✅ `prove(coqScript, timeoutMs) → WasmProofResult` |
| T-21 | P1 | Wire CoqBridge into router for higher_order formulas | ✅ _tryCoqOrLean4() fallback in WasmProverHub |
| T-22 | P1 | Write 10+ tests for Coq bridge + translator | ✅ 13 tests in wasm-prover-sprint3-4.test.ts |

---

### Sprint 3 (Phase 5 + 8): Lean 4 + Full Integration

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-23 | P1 | Evaluate lean4web worker embedding in Node.js environment | ✅ Decision: subprocess lean/lake (lean4web browser-only) |
| T-24 | P1 | Create `src/services/provers/deontic-to-lean4.ts` | ✅ Translates `PolicyFormulaSet` to Lean 4 `theorem` |
| T-25 | P1 | Create `src/services/provers/lean4-wasm-bridge.ts` | ✅ `prove(leanSource) → WasmProofResult` |
| T-26 | P1 | Wire Lean4Bridge into router for higher_order formulas | ✅ Available as alternative to Coq in _tryCoqOrLean4() |
| T-27 | P1 | Write 10+ tests for Lean 4 bridge + translator | ✅ 13 tests in wasm-prover-sprint3-4.test.ts |
| T-28 | P0 | Full integration: update `mcp-remote-deontic-engine.ts` | ✅ Local-first → remote-fallback when local unknown/timeout |
| T-29 | P0 | New factory: `createLocalFirstDeonticORBEvaluator(hub, remoteEngine)` | ✅ ORB uses local Z3 for simple, remote for hard proofs |
| T-30 | P0 | Update `mcp++ conformance` output with prover capabilities | Shows which WASM provers are loaded |
| T-31 | P0 | Write 15+ integration tests for local-first evaluation | All pass, 492+ total swissknife tests |
| T-32 | P0 | Performance regression test: latency budget | Simple deontic check < 100ms locally (vs ~300ms+ remote) |

---

### Sprint 4 (Phase 6 + 7): ZK + Neural (Research-track)

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-33 | P2 | Evaluate lurk ecosystem WASM paths | ✅ **RESOLVED 2026-07-01**: lurk-beta `--target wasm32-unknown-unknown` is documented; lurk v0.5 uses Plonky3/Sphinx; ix is the ZK-PCC platform for Lean 4. See §3.5 for full audit. |
| T-34 | P2 | Create `src/services/provers/deontic-to-lurk.ts` stub | ✅ Encodes obligation discharge as Lurk s-expression |
| T-35 | P2 | Create `src/services/provers/lurk-wasm-bridge.ts` stub | ✅ Compiles but skips when Lurk WASM unavailable |
| T-36 | P2 | Define `ZKProofArtifact` type and add to Mcp-Plus-Plus spec | ✅ `zkp_proof_artifact.json` conformance vector added |
| T-37 | P2 | Attach ZK proof CID to `AuditEntry.extra` when available | ✅ `entry.extra.zk_proof_cid` via prover_id/proof_time_ms |
| T-38 | P2 | Create `src/services/provers/neural-prover-bridge.ts` | ✅ DONE (Sprint 6, `c0f85d8`) — LLM prompt builder, prefix parser (lean4:/coq:/refuted:/unknown:), Lean4/Coq local verify, `WasmProofResult` |
| T-39 | P2 | Write 8+ tests for Lurk bridge stub + ZKProofArtifact | ✅ 20 tests in wasm-prover-sprint5.test.ts |

---

### Ongoing / Housekeeping

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-40 | P1 | Add `prover_id` and `proof_time_ms` to `AuditEntry` extra payload | ✅ Logged by `PolicyAuditLog.record()` |
| T-41 | P1 | Update `CONFORMANCE_MATRIX.md` as each prover is added | ✅ Matrix updated through Sprint 5 |
| T-42 | P1 | Add WASM prover health to `mcp++ status` output | ✅ Shows loaded provers + cache stats |
| T-43 | P2 | Bundle-size analysis: z3-solver adds ~34 MB WASM | ✅ `Z3WasmBridge.createDeferred()` — lazy-load on first proof request; `WasmProverHub.create()` uses it |
| T-44 | P2 | Cross-language conformance: Python vs JS prover on same formula set | ✅ `wasm-prover-conformance.test.ts` — 5 SAT + 1 conflict policies from ipfs_datasets_py corpus; live Z3 gated by `Z3_WASM_LIVE=1` |
| T-45 | P2 | CI gate: `test/mcp-plus-plus/wasm-prover-*.test.ts` in GitHub Actions | ✅ `.github/workflows/wasm-prover-gates.yml` — ubuntu-latest + Node.js 22, 5 job stages |

---

### Sprint 6 (Phase 6a — lurk-beta WASM, P2)

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-46 | P2 | Build `lurk-beta` `--target wasm32-unknown-unknown`; produce npm-consumable WASM | `wasm-pack build` or `napi-rs` bundle; importable from Node.js |
| T-47 | P2 | Publish/link `lurk-wasm` package (local or registry) | `import('lurk-wasm')` succeeds in LurkWasmBridge.create() |
| T-48 | P2 | Implement real `proveObligationDischarge()` via lurk-beta | Returns `ZKProofArtifact` with real Nova proof bytes |
| T-49 | P2 | Implement `verifyProof(artifact)` via lurk-beta verify API | Returns `true` for a self-consistent proof |
| T-50 | P2 | Write 8+ tests for real lurk-beta WASM integration | Tests skip when `lurk-wasm` is absent; pass when present |

---

### Sprint 7b (Phase 6b — ix / Lean 4 ZK, P2) ✅ DONE (2026-07-03)

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-51 | P2 | Evaluate `ix` CLI/API surface for programmatic invocation | ✅ DONE | Go/no-go: subprocess viable; WASM not feasible. 2-step: `ix compile` → `.ixe`, then SP1 execute. Requires lake+Lean4+Rust+32GB RAM. |
| T-52 | P2 | Extend `Lean4WasmBridge` to invoke `ix` for ZK-attested proofs | ✅ DONE | `findIxCli()`, `proveWithIx()` → `ZKProofArtifact{backend:'sphinx'}`, `ixBuildInstructions()` |
| T-53 | P2 | Attach `ix`-generated artifact CID to `AuditEntry.extra.zk_proof_cid` | ✅ DONE | `PolicyAuditLog.record()` accepts & persists `zk_proof_cid` to JSONL |
| T-54 | P2 | Write 6+ tests for ix-backed Lean4WasmBridge | ✅ DONE | 13 tests (12 pass, 1 skipped live-ix); plus provers CLI tests |

---

### Sprint 8 (Phase 6c — multi-stark / neural, P3 future)

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-55 | P3 | Evaluate `multi-stark` WASM/JS binding when published | Go/no-go for multicircuit STARK bridge |
| T-56 | P3 | `MultiStarkBridge` for multi-obligation proofs in parallel | `proveMultipleObligations(policy) → ZKProofArtifact[]` |
| T-57 | P2 | `NeuralProverBridge` — LLM sketch → Lean/Coq verify | ✅ DONE (Sprint 6, `c0f85d8`) — same as T-38; `wasm-prover-sprint6.test.ts` (27 tests pass) |

---

### Sprint 9 (Phase 9 — DCEC/CEC Native Prover, P2) ✅ DONE (2026-07-03)

> **Discovered gap 2026-07-03:** `ipfs_datasets_py/logic/CEC/` contains a full DCEC layer
> (dcec_core, prover_core, cec_framework, shadow_prover_wrapper) with **no TypeScript equivalent**.
> This sprint adds a native TypeScript DCEC proof engine, closing the `temporal`/`modal_deontic`
> remote fallback.

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-58 | P2 | Create `src/services/provers/dcec-types.ts` — DCEC formula type system | ✅ DONE | `DeonticOperator` (O/P/F/S/R/L/POW/IMM), `CognitiveOperator` (B/K/I/D), `TemporalFormula`, `ConnectiveFormula`, `QuantifiedFormula`, `DCECFormula` union; `serializeFormula()`, constructor helpers |
| T-59 | P2 | Create `src/services/provers/dcec-prover-bridge.ts` — native TypeScript DCEC proof engine | ✅ DONE | `DcecProverBridge.prove(kb, goal, timeoutMs) → WasmProofResult`; 5 rules: ModusPonens, Simplification, DeonticProhibEquiv (F↔O¬), ObligImpliesPermit (O⊢P), ForbiddenToNotOblig; forward-chaining saturation; conflict detection |
| T-60 | P2 | Create `src/services/provers/policy-to-dcec.ts` — policy → DCEC translator | ✅ DONE | `PolicyToDcecTranslator.translate(policy) → DCECFormula[]` — permissions→P(), prohibitions→F(), obligations→O(), temporal→HOLDS_AT(…,now) |
| T-61 | P2 | Wire `DcecProverBridge` into `WasmProverHub` for `modal_deontic` formulas | ✅ DONE | `FormulaClass += 'modal_deontic'`; hub routes obligations/prohibitions (≤20 rules) to DCEC; `proverStatus().dcec_native = true`; `mcp++ provers` shows dcec-native |
| T-62 | P2 | Write 10+ tests for DCEC prover bridge + translator | ✅ DONE | `wasm-prover-sprint9.test.ts` — 27 tests (all pass): T-58 types (9), T-59 inference rules (10), T-60 translator (5), T-61 hub routing (3) |

---

### Sprint 10 (Phase 10 — TDFOL Native Prover, P2) ✅ DONE (2026-07-03)

> **Discovered gap 2026-07-03:** `ipfs_datasets_py/logic/TDFOL/` contains a full Temporal
> Deontic FOL engine (640-line prover, 818-line parser, 10 inference rules including LTL □/◊/◯/U
> + SDL D axiom) that backs `tdfol_prove`. Sprint 10 closes the `temporal` remote fallback with
> a native TypeScript `TdfolProverBridge`. After Sprint 10, ALL formula classes are handled locally.

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-63 | P2 | Create `src/services/provers/tdfol-types.ts` — TDFOL formula type system | ✅ DONE | `LtlUnaryOperator` (ALWAYS/EVENTUALLY/NEXT), `LtlBinaryOperator` (UNTIL/SINCE/RELEASE), `TdfolFormula = DCECFormula \| LtlUnaryFormula \| LtlBinaryFormula`; `serializeTdfol()`; constructor helpers |
| T-64 | P2 | Create `src/services/provers/tdfol-prover-bridge.ts` — TDFOL forward-chaining engine | ✅ DONE | 10 rules: TemporalT (□φ⊢φ), TemporalDistribution (K: □(φ→ψ),□φ⊢□ψ), TemporalEventually (φ⊢◊φ), UntilUnfolding, DeonticD (O⊢P), DeonticDistribution, ProhibitionElimination (F⊢¬P), DeonticProhibEquiv, TdfolModusPonens; `checkPolicyConsistency()` |
| T-65 | P2 | Create `src/services/provers/policy-to-tdfol.ts` — temporal policy → TDFOL KB | ✅ DONE | temporal window → □(perm/proh/obl); obligation deadline → ◊O(…); plain policy → bare atoms |
| T-66 | P2 | Wire `TdfolProverBridge` into `WasmProverHub` for `temporal` + fix `higher_order` | ✅ DONE | `temporal` → TdfolProverBridge (closes last mandatory remote fallback); `higher_order` → `_tryCoqOrLean4()` before remote; `proverStatus().tdfol_native = true` |
| T-67 | P2 | Write 10+ tests for TDFOL prover bridge | ✅ DONE | `wasm-prover-sprint10.test.ts` — 26 tests (all pass): T-63 types (8), T-64 rules (10), T-65 translator (4), T-66 hub routing (2) |

---

### Sprint 11 (Phase 11 — UCAN-ZKP Bridge, P2) ✅ DONE (2026-07-03)

> **Gap from §4:** `ipfs_datasets_py/logic/zkp/ucan_zkp_bridge.py` (592 lines) provides
> `ZKPToUCANBridge` — converts ZKP proof artifacts into UCAN capability evidence caveats.
> Sprint 11 adds `ZkpUcanBridge` + `ZkpSimulatedProver` to swissknife's `src/services/zkp/`.

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-68 | P2 | Create `src/services/zkp/zkp-types.ts` — ZKP UCAN type system | ✅ DONE | `ZkpCapabilityEvidence` (type/proof_hash/theorem_cid/verifier_id/public_inputs/is_simulation); `ZkpBridgeResult`; `ZkpSimulatedProof`; `ZkpVerifierId` union |
| T-69 | P2 | Create `src/services/zkp/zkp-simulated-prover.ts` — simulated ZKP prover | ✅ DONE | `ZkpSimulatedProver.prove(statement, axioms?) → ZkpSimulatedProof`; SHA-256 proof hash; <500B proof_b64; `verify(proof) → boolean`; `computeStatementCid()` |
| T-70 | P2 | Create `src/services/zkp/zkp-ucan-bridge.ts` — `ZkpUcanBridge` | ✅ DONE | `proofToCaveat(ZKProofArtifact) → ZkpCapabilityEvidence` (is_simulation:false); `proveAndDelegate()` with real prover injection + simulation fallback; backend→verifier_id mapping |
| T-71 | P2 | Write 10+ tests for ZKP-UCAN bridge | ✅ DONE | `wasm-prover-sprint11.test.ts` — 19 tests (all pass): T-68 types (4), T-69 simulated prover (8), T-70 bridge (7) |

---

### Sprint 12 (Phase 12 — Deontic Analyzer + Knowledge Base, P2) ✅ DONE (2026-07-03)

> **Gap from §2.6:** `deontic/analyzer.py` (503 lines) + `deontic/knowledge_base.py` (245 lines).
> Sprint 12 adds regex-based NL→deontic extraction and a typed temporal KB with rule inference.

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-72 | P2 | Create `src/services/deontic/deontic-text-analyzer.ts` — NL deontic statement extractor | ✅ DONE | 9 regex patterns; `extractStatements()`; `detectConflicts()` (direct/conditional/jurisdictional/temporal); Jaccard `actionsAreSimilar()`; `organizeByEntity()`; `calculateStatistics()` |
| T-73 | P2 | Create `src/services/deontic/deontic-knowledge-base.ts` — temporal deontic KB | ✅ DONE | `TimeInterval`/`Party`/`DeonticAction`/`Proposition` (Pred/And/Or/Not/Implies); `DeonticKnowledgeBase.addStatement()/addRule()/addFact()/inferStatements()/checkCompliance()` |
| T-74 | P2 | Wire `DeonticTextAnalyzer` into `mcp++` tool chain | ✅ DONE | `mcp++ deontic analyze <text>` → JSON `{statements, conflicts, statistics}`; usage help when no text |
| T-75 | P2 | Write 10+ tests for deontic analyzer + KB | ✅ DONE | `wasm-prover-sprint12.test.ts` — 28 tests (all pass): extraction (8), conflicts (7), stats (2), KB (8), mcp++ (2), Proposition (1) |

---

### Sprint 13 (Phase 13 — Extended TDFOL Rules + ProverRouterBridge, P2) ✅ DONE (2026-07-03)

> **Gap:** `TDFOL/inference_rules/` (50+ rules) adds S4/S5 modal axioms, propositional extras,
> deontic extensions, and 9 temporal-deontic combined rules beyond Sprint 10's 10 base rules.

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-76 | P2 | Create `src/services/provers/tdfol-extended-rules.ts` — 14 additional inference rules | ✅ DONE | ModusTollens, HypotheticalSyllogism, DisjunctiveSyllogism, DoubleNegationElim, TemporalS4 (□φ⊢□□φ), TemporalS5 (◊φ⊢□◊φ), ObligationWeakening, PermissionProhibitionDuality, DeonticDetachment, TemporalObligationPersistence, DeonticTemporalIntroduction, AlwaysPermission, ObligationEventually, FutureObligationPersistence |
| T-77 | P2 | `ExtendedTdfolProverBridge` subclass with full rule set | ✅ DONE | Pre-saturates KB with 14 extended rules before delegating to base TdfolProverBridge; `extendedRuleNames()` |
| T-78 | P2 | Create `src/services/bridge/prover-router-bridge.ts` — `ProverRouterBridgeAdapter` | ✅ DONE | `evaluate(formulas[]) → ProofGateResult` (valid_count/failure_ratio/details/status); `checkConsistency(formulas[]) → ProofGateResult` (O+F conflict detection) |
| T-79 | P2 | Write 10+ tests for extended rules + bridge | ✅ DONE | `wasm-prover-sprint13.test.ts` — 19 tests (all pass): extended rules (13), bridge (6) |

---

### Sprint 14 (Phase 14 — FOL Text Converter + Modal Frame Bridge, P2) ✅ DONE (2026-07-03)

> **Gap:** `logic/fol/` (2032L total) + `bridge/modal_frame_logic.py` (691L). Both regex-based.

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-80 | P2 | Create `src/services/fol/fol-text-converter.ts` — NL→FOL converter | ✅ DONE | `extractPredicates()`, `parseQuantifiers()`, `parseLogicalOperators()`, `buildFolFormula()`, `formatAsProlog()`, `formatAsTptp()`; `FolTextConverter.convert() → FolConversionResult`; `convertBatch()` |
| T-81 | P2 | Create `src/services/bridge/modal-frame-bridge.ts` — `ModalFrameBridge` | ✅ DONE | `evaluate(text) → ModalBridgeResult {status, modal_ir (fol_formula/prolog/tptp/deontic_statements/conflicts/confidence), proof_gate}`; uses DeonticTextAnalyzer + FolTextConverter + ProverRouterBridgeAdapter |
| T-82 | P2 | Wire `FolTextConverter` into `mcp++` subcommand | ✅ DONE | `mcp++ deontic fol <text>` → JSON `{formula, prolog, tptp, confidence, quantifiers, predicates}` |
| T-83 | P2 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint14.test.ts` — 25 tests (all pass): extractPredicates (5), parseQuantifiers (4), parseLogicalOps (4), buildFolFormula+convert (5), ModalFrameBridge (5), mcp++ fol (2) |

---

### Sprint 15 (Phase 15 — FLogic Semantic Optimizer + ML Confidence Scorer, P2) ✅ DONE (2026-07-03)

> **Gap:** `flogic_optimizer.py` (673L) + `ml_confidence.py` (437L). Both pure-math, no ML deps.

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-84 | P2 | Create `src/services/fol/flogic-semantic-optimizer.ts` — semantic round-trip quality scorer | ✅ DONE | `cosineSimilarity(a,b)`; `FLogicSemanticOptimizer.evaluate(src,dec,srcEmb,decEmb,triples?) → FLogicOptimizerResult`; `addOntologyClass()`; `batchSimilarity()` |
| T-85 | P2 | Create `src/services/fol/ml-confidence-scorer.ts` — heuristic FOL confidence scorer | ✅ DONE | `FeatureExtractor.extractFeatures()` → 17 numeric features; `MLConfidenceScorer.predictConfidence()` — exact heuristic match to Python `_heuristic_confidence()` |
| T-86 | P2 | Wire `MLConfidenceScorer` into `FolTextConverter.convert()` | ✅ DONE | Lazy dynamic import; fallback to original heuristic when unavailable |
| T-87 | P2 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint15.test.ts` — 20 tests (all pass): cosineSimilarity (6), FLogicSemanticOptimizer (7), MLConfidenceScorer (4), FolTextConverter (3) |

---

### Sprint 16 (Phase 16 — Deontic Graph + Support Map, P2) ✅ DONE (2026-07-03)

> **Gap:** `deontic/graph.py` (573L) + `deontic/support_map.py` (167L). Pure data structures.

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-88 | P2 | Create `src/services/deontic/deontic-graph.ts` — typed deontic graph | ✅ DONE | `DeonticNodeType`/`DeonticModality`/`DeonticNode`/`DeonticRule`/`DeonticConflict`; `DeonticGraph.addNode()/addRule()/activeRules()/detectConflicts()/assessRules()/sourceGapSummary()/summary()/toDict()/fromDict()` |
| T-89 | P2 | Create `src/services/deontic/deontic-graph-builder.ts` — graph builder | ✅ DONE | `DeonticGraphBuilder.fromStatements(stmts, conflicts?) → DeonticGraph`; actor+action nodes; conflicted statements → inactive rules |
| T-90 | P2 | Create `src/services/deontic/support-map.ts` — support map builder | ✅ DONE | `SupportFact`/`SupportMapEntry`/`SupportMapBuilder.build(graph) → SupportMapEntry[]`; `buildSummary(graph) → modality counts` |
| T-91 | P2 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint16.test.ts` — 19 tests (all pass): DeonticGraph (12), DeonticGraphBuilder (3), SupportMapBuilder (4) |

---

### Sprint 17 (Phase 17 — LegalNormIR + Decoder, P2) ✅ DONE (2026-07-03)

> **Gap:** `deontic/ir.py` (2720L) `LegalNormIR` + `decoder.py` (932L). Both pure data.

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-92 | P2 | Create `src/services/deontic/legal-norm-ir.ts` — `LegalNormIR` typed IR | ✅ DONE | `SourceSpan`; `LegalNormQuality`; full `LegalNormIR` interface; `buildLegalNormIR(partial)` + `emptySpan()/emptyQuality()` |
| T-93 | P2 | Create `src/services/deontic/legal-norm-decoder.ts` — `decodeLegalNormIR()` renderer | ✅ DONE | `DecodedPhrase`/`DecodedLegalText`; template rendering O/P/F/DEF/APP/EXEMPT/LIFE/penalty; `decodedPhraseSlotTextMap()` |
| T-94 | P2 | Create `src/services/deontic/legal-norm-builder.ts` — builder from analyzer output | ✅ DONE | `LegalNormBuilder.fromStatement(stmt) → LegalNormIR`; `fromStatements(stmts[]) → LegalNormIR[]` |
| T-95 | P2 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint17.test.ts` — 18 tests (all pass): types (5), decoder (9), builder (4) |

---

### Sprint 18 (Phase 18 — Deontic Parser Utils + Prover Syntax Builder, P2) ✅ DONE (2026-07-03)

> **Gap:** `deontic/utils/deontic_parser.py` (5589L) pure-function utilities + `prover_syntax.py` (1652L).

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-96 | P2 | Create `src/services/deontic/deontic-parser-utils.ts` — parser utility functions | ✅ DONE | `classifyModal()`; `classifyLegalEntity()` (7 entity types); `normalizePredicate()`; `extractActionRecipient()`; `scoreScaffoldQuality()` |
| T-97 | P2 | Create `src/services/deontic/normative-conflict-detector.ts` — conflict detector | ✅ DONE | `identifyObligations() → {obligations,permissions,prohibitions,conditionalNorms,temporalNorms}`; `detectNormativeConflicts() → NormConflict[]` (direct/permission/conditional/temporal) |
| T-98 | P2 | Create `src/services/deontic/prover-syntax-builder.ts` — prover syntax builder | ✅ DONE | `ProverSyntaxBuilder.buildSyntaxReport(norm) → ProverSyntaxReport` with records for z3-smt2/dcec/tdfol/lean4/prolog targets; `buildBatch()` |
| T-99 | P2 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint18.test.ts` — 30 tests (all pass): classifyModal (6), classifyLegalEntity (6), utils (4), scoreQuality (2), identifyObligs (2), detectConflicts (3), ProverSyntaxBuilder (7) |

---

### Sprint 19 (Phase 19 — Logic Monitor + Submodule Registry + Batch Processor, P2) ✅ DONE (2026-07-03)

> **Gap:** `monitoring.py` (452L) + `submodule_registry.py` (614L) + `batch_processing.py` (389L).

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-100 | P2 | Create `src/services/logic-monitor.ts` — operation tracking + metrics | ✅ DONE | `LogicMonitor.trackOperation(op,fn)`, `trackSync()`, `recordError()`, `getMetrics() → MetricsSnapshot`, `getHealthStatus() → {healthy/degraded/unhealthy}`, `resetMetrics()`, singleton |
| T-101 | P2 | Create `src/services/submodule-registry.ts` — logic submodule registry | ✅ DONE | `LogicSubmoduleSpec`; registry of 19 modules (Sprints 1–18); `getSubmoduleSpecs()`, `getSubmoduleSpec(name)`, `getSubmoduleNames(filter?)`, `getIntegrationManifest()` |
| T-102 | P2 | Create `src/services/batch-processor.ts` — batch formula evaluator | ✅ DONE | `BatchResult<T>` + `successRate()`; `BatchProcessor.process(items,fn,opts?)` (concurrency/timeout/onProgress); `processSerial()` |
| T-103 | P2 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint19.test.ts` — 24 tests (all pass): LogicMonitor (9), Registry (8), BatchProcessor (7) |

---

### Sprint 20 (Phase 20 — I18N Conflict + E2E Validator + Logic Public API, P2) ✅ DONE (2026-07-03)

> **Gap:** `api.py` (723L) + `e2e_validation.py` (691L). Sprint 20 = final integration layer.

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-104 | P2 | Create `src/services/i18n-conflict-report.ts` | ✅ DONE | `I18NConflictReport`: totalConflicts/languagesWithConflicts/mostConflictedLanguage()/leastConflictedLanguage()/conflictDensity()/hasConflicts()/toDict(); `detectMultilingualConflicts()` |
| T-105 | P2 | Create `src/services/e2e-validator.ts` | ✅ DONE | `ValidationResult`; `E2EValidator.run() → ValidationSummary`; 7 test suites |
| T-106 | P2 | Create `src/services/logic-public-api.ts` | ✅ DONE | `LogicPublicApi`: compileNlToPolicy()/evaluateNlPolicy()/analyzeText()/detectMultilingualConflicts()/getSubmoduleSpecs()/getIntegrationManifest()/analyzeTexts() |
| T-107 | P2 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint20.test.ts` — 16 tests (all pass): I18NConflictReport (5), E2EValidator (3), LogicPublicApi (8) |

---

### Sprint 21 (Phase 21 — Logic Types + Common Validators + TDFOL NL API, P2) ✅ DONE (2026-07-03)

> **Gap:** `logic/types/` (923L) + `logic/common/validators.py` (277L) + `bounded_cache.py` (233L) + `TDFOL/nl/tdfol_nl_api.py`.

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-108 | P2 | Create `src/services/logic-types.ts` — shared logic type system | ✅ DONE | `DeonticOperator`/`TemporalOperator` enums + labels; `LegalAgent`/`TemporalCondition`/`LegalContext`; `DeonticFormula` (toFolString/formulaId); `DeonticRuleSet` (checkConsistency/findByOperator); `FOLFormula`/`ProofResult` |
| T-109 | P2 | Create `src/services/logic-validators.ts` — validators + BoundedCache | ✅ DONE | `validateFormulaString/AxiomList/LogicSystem/TimeoutMs`; `BoundedCache<T>` (LRU eviction/TTL/stats) |
| T-110 | P2 | Create `src/services/tdfol-nl-api.ts` — NL→TDFOL parser API | ✅ DONE | `parseNaturalLanguage(text, opts?) → NLParseResult`; `GeneratedFormula` (formula_string/operator/entity/action); O/P/F extraction via DeonticTextAnalyzer; `parse_natural_language` alias |
| T-111 | P2 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint21.test.ts` — 32 tests (all pass): DeonticFormula (6), DeonticRuleSet (4), validators (13), BoundedCache (5), TDFOL NL API (8) |

---

### Sprint 22 (Phase 22 — TDFOL Exceptions + Optimization + Security, P2) ✅ DONE (2026-07-03)

> **Gap:** `TDFOL/exceptions.py` (684L) + `tdfol_optimization.py` (539L) + `security_validator.py` (777L).

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-112 | P2 | Create `src/services/tdfol-exceptions.ts` — TDFOL exception hierarchy | ✅ DONE | `TDFOLError`/`ParseError`/`ProofError`/`ProofTimeoutError`/`ProofNotFoundError`/`ZKPProofError`/`ConversionError`/`InferenceError`/`NLProcessingError`/`PatternMatchError`/`CacheError`; type guards |
| T-113 | P2 | Create `src/services/tdfol-optimization.ts` — optimised prover layer | ✅ DONE | `IndexedKB` (addFormula/lookupByPredicate/lookupByOperator/getStats); `OptimizedProver` (BoundedCache + ExtendedTdfolProverBridge); `ProvingStrategy`; `createOptimizedProver()` |
| T-114 | P2 | Create `src/services/tdfol-security-validator.ts` — input security validator | ✅ DONE | `SecurityValidator.validateFormula/validateKb` (size/depth/blocklist/operator-count checks); `SecurityConfig`; `createValidator(level)`; `validateFormula()` |
| T-115 | P2 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint22.test.ts` — 24 tests (all pass): exceptions (10), IndexedKB+OptimizedProver (6), security (8) |

---

### Sprint 23 (Phase 23 — TDFOL Core Types + Proof Tree + Formula Dependency Graph, P2) ✅ DONE (2026-07-03)

> **Gap:** `tdfol_core.py` (826L) + `proof_tree_visualizer.py` (999L) + `formula_dependency_graph.py` (889L).

| ID | Priority | Task | Status | Acceptance Criteria |
|---|---|---|---|---|
| T-116 | P2 | Create `src/services/tdfol-core.ts` — TDFOL core type hierarchy | ✅ DONE | Enums + TDFOLNode; Term/Variable/Constant/FunctionApp; Formula/Predicate/Binary/Unary/Quantified/Deontic/Temporal; constructor helpers; `TDFOLKnowledgeBase` |
| T-117 | P2 | Create `src/services/proof-tree.ts` — proof tree + ASCII rendering | ✅ DONE | `ProofTreeNode`/`ProofTree` (allNodes/leaves/findByFormula/toAscii); `ProofTreeBuilder.fromProofResult()`; ASCII box-drawing renderer |
| T-118 | P2 | Create `src/services/formula-dependency-graph.ts` — formula dependency analysis | ✅ DONE | `FormulaDependencyGraph` (topologicalSort/detectCycles/findProofChain/getTransitiveDeps) |
| T-119 | P2 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint23.test.ts` — 24 tests (all pass): TDFOL types (10), ProofTree (7), DependencyGraph (7) |

---

### Sprint 24 (Phase 24 — TDFOL Parser + Modal Tableaux + Performance Profiler, P2) 🆕

> **Gap:** `tdfol_parser.py` (818L) — `parse_tdfol(str) → Formula`; `modal_tableaux.py` (711L) — `ModalLogicType`/`World`/`TableauxBranch`/`ModalTableaux.prove()`; `performance_profiler.py` (1411L) — `ProfilingStats`/`BenchmarkResult`/`PerformanceProfiler`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-120 | P2 | Create `src/services/tdfol-parser.ts` — TDFOL formula text parser | ✅ DONE | `parseTdfol(text)→Formula`, `parseTdfolSafe(text)→Formula\|null`; TDFOLLexer (multi/single-char tokens, single-letter modal ops, ISO date literals); recursive-descent TDFOLParser (iff/implies/or/and/not/quantified/modal/atomic precedence); deontic O/P/F, temporal □/◊/X/U/S/W/R, prefix `(→ p q)` and infix `(p U q)` notation |
| T-121 | P2 | Create `src/services/modal-tableaux.ts` — modal tableaux prover | ✅ DONE | `ModalLogicType` (K/T/D/S4/S5); `World.hasContradiction()`; `TableauxBranch` (addWorld/createFreshWorld/clone/addAccessibility/boxHistory); `ModalTableaux.prove()` — α/β-rules, □/◊ expansion, reflexivity (T/S4/S5), box-history propagation (S4/S5); `proveModalFormula()` |
| T-122 | P2 | Create `src/services/performance-profiler.ts` — performance profiler | ✅ DONE | `ProfilingStats` (mean/median/min/max/stdDev/opsPerSec/samples); `PerformanceProfiler.profile()/profileAsync()/formatReport(TEXT\|JSON)`; `benchmarkProviders()`, `ProfileBlock.stop()/elapsed` |
| T-123 | P2 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint24.test.ts` — 45 tests (all pass): parseTdfol (17), parseTdfolSafe (3), World (5), TableauxBranch (5), ModalTableaux (6), PerformanceProfiler (6), benchmarkProviders (1), ProfileBlock (2) |

---

### Sprint 25 (Phase 25 — Kripke Structure + TDFOL Prover + Performance Dashboard, P2) ✅ DONE (2026-07-01)

> **Gap:** `countermodels.py` + `countermodel_visualizer.py` (1102L) — `KripkeStructure`, `CountermodelVisualizer`; `tdfol_prover.py` (640L) — `TDFOLProver.prove()`; `performance_dashboard.py` (1314L) — `ProofMetrics`/`AggregatedStats`/`PerformanceDashboard`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-124 | P2 | Create `src/services/kripke-structure.ts` — Kripke structure + countermodel visualizer | ✅ DONE | `KripkeStructure` (addWorld/addAccessibility/setAtomTrue/isAtomTrue/totalRelations/toDict/toJson); `CountermodelVisualizer.renderAscii('expanded'\|'compact')` with box-drawing chars; `createVisualizer()` factory |
| T-125 | P2 | Create `src/services/tdfol-prover.ts` — TDFOL theorem prover | ✅ DONE | `TDFOLInferenceRule` interface; 8 rules: Temporal/DeonticNecessitation, Temporal/DeonticDistribution, TemporalTRule, DeonticDRule, ProhibitionElimination, PermissionIntroduction; `TDFOLProver.prove()` — axiom lookup → forward-chaining → `ModalTableaux` fallback; `defaultTdfolRules()` |
| T-126 | P2 | Create `src/services/performance-dashboard.ts` — performance dashboard | ✅ DONE | `MetricType` enum; `ProofMetrics`/`makeProofMetrics`; `AggregatedStats` (p95/p99 percentiles/strategyStats); `PerformanceDashboard.record()/getAggregatedStats()/getTimeSeries()/exportJson()/reset()`; `getGlobalDashboard()/resetGlobalDashboard()` |
| T-127 | P2 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint25.test.ts` — 30 tests (all pass): KripkeStructure (7), CountermodelVisualizer (6), TDFOLProver (8), PerformanceDashboard (9) |

---

### Sprint 26 (Phase 26 — Bridge Shared Types + Registry + ZKP Attestation Bridge, P2) ✅ DONE (2026-07-01)

> **Gap:** `bridge/types.py` (413L) — `LogicIRView`, `LegalIRDocument`, `RoundTripMetrics`, `ProofGateResult`, `GraphProjectionResult`, `BridgeEvaluationReport`; `bridge/registry.py` (285L) — `LogicBridgeSpec`, 6 registered bridges, `logicBridgeSpecs/Manifest/loadAdapter`; `bridge/zkp_attestation.py` (762L) — `ZkpAttestationBridgeAdapter.encode()`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-128 | P2 | Create `src/services/bridge-types.ts` — bridge shared types | ✅ DONE | `LogicIRView`/`LegalIRDocument` (canonicalHash/toJson); `RoundTripMetrics.fromLossMapping()/totalLoss()`; `ProofGateResult` (compiles/failureRatio/disabled()); `GraphProjectionResult`; `BridgeEvaluationReport` |
| T-129 | P2 | Create `src/services/bridge-registry.ts` — bridge adapter registry | ✅ DONE | `LogicBridgeSpec` + `SPECS` (6 bridges); `logicBridgeSpecs(implementedOnly?)`; `logicBridgeSpec(name)`; `logicBridgeManifest()` (bridge_count/roles/target_components); `bridgeNameForComponent(target)` |
| T-130 | P2 | Create `src/services/zkp-attestation-bridge.ts` — ZKP attestation bridge | ✅ DONE | `ZkpAttestationBridgeAdapter.encode(text, opts) → {doc, context}` — 4 views (zkp_attestations/zkp_public_inputs/frame_logic/neo4j_graph_data); per-formula attestation records; `.evaluate()` → `BridgeEvaluationReport` |
| T-131 | P2 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint26.test.ts` — 36 tests (all pass): LogicIRView (2), LegalIRDocument (7), RoundTripMetrics (4), ProofGateResult (4), logicBridgeSpecs (3), logicBridgeSpec (2), logicBridgeManifest (3), bridgeNameForComponent (4), ZkpAttestationBridgeAdapter (7) |

---

### Sprint 27 (Phase 27 — FOL/TDFOL Bridge + Deontic Norms Bridge + CEC/DCEC Bridge, P2) ✅ DONE (2026-07-01)

> **Gap:** `bridge/fol_tdfol.py` (2136L) — `FolTdfolBridgeAdapter`; `bridge/deontic_norms.py` (2497L) — `DeonticNormsBridgeAdapter`; `bridge/cec_dcec.py` (3671L) — `CecDcecBridgeAdapter`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-132 | P2 | Create `src/services/fol-tdfol-bridge.ts` — FOL/TDFOL bridge adapter | ✅ DONE | `FolTdfolBridgeAdapter.encode(text)/evaluate()`; `TdfolFormulaRecord` (formula/predicates/source_id/formula_type); 3 views; formula_type classification (temporal/deontic/fol/propositional) |
| T-133 | P2 | Create `src/services/deontic-norms-bridge.ts` — deontic norms bridge adapter | ✅ DONE | `DeonticNormsBridgeAdapter.encode(text)/evaluate()`; `DeonticNormRecord` (O/P/F detection; subject/action/prover_syntax); 4 views (deontic_ir/prover_formulas/frame_logic/neo4j_graph_data) |
| T-134 | P2 | Create `src/services/cec-dcec-bridge.ts` — CEC/DCEC bridge adapter | ✅ DONE | `CecDcecBridgeAdapter.encode(text)/evaluate()`; `DcecRecord` (Happens/HoldsAt/Initiates/Terminates; cec_formula rendering); 3 views |
| T-135 | P2 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint27.test.ts` — 25 tests (all pass): FolTdfolBridgeAdapter (8), DeonticNormsBridgeAdapter (8), CecDcecBridgeAdapter (9) |

---

### Sprint 28 (Phase 28 — Multiview Aggregator + Deontic Formula Builder, P3) ✅ DONE (2026-07-01)

> **Gap:** `bridge/multiview.py` (4040L) — `MultiViewLegalIRReport`, `LegalIRTrainingTarget`, `evaluate_legal_ir_multiview()`; `deontic/formula_builder.py` (7019L) — `build_deontic_formula_from_ir(norm) → str`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-136 | P3 | Create `src/services/bridge-multiview.ts` — multiview aggregator | ✅ DONE | `MultiViewLegalIRReport` (attemptedCount/acceptedCount/acceptanceRate/failures/toDict()); `LegalIRTrainingTarget` (totalLoss/adapterLosses/viewDistribution/toDict()); `evaluateLegalIRMultiview(text, adapters[])` — runs all adapters, merges views into unified doc; `toTrainingTarget()` |
| T-137 | P3 | Create `src/services/deontic-formula-builder.ts` — deontic formula from IR | ✅ DONE | `normalizePredicateName()` (stop-word filter + PascalCase); `canonicalModalityOperator()` (CANONICAL_MODALITY_OPS + NORM_TYPE_MAP + TEXTUAL_MAP); `buildDeonticFormulaFromIR()` (O/P/F/DEF/PURP/APP/EXEMPT/LIFE); `buildDeonticFormulasFromIRList()` |
| T-138 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint28.test.ts` — 33 tests (all pass): normalizePredicateName (6), canonicalModalityOperator (8), buildDeonticFormulaFromIR (9), buildDeonticFormulasFromIRList (1), evaluateLegalIRMultiview (6), toTrainingTarget (3) |

---

### Sprint 29 (Phase 29 — Modal KG Bridge + Modal Synthesis, P3) ✅ DONE (2026-07-01)

> **Gap:** `modal/kg_bridge.py` (1062L) — `flogicTriplesToGraphData()`, `FLogicOntology`, `flogicTriplesToOntology()`; `modal/synthesis.py` (947L) — `ModalProgramSynthesisHint`, `ModalResidualRepairRoute`, `RESIDUAL_REPAIR_ROUTES`, `routeAutoencoderResidual()`, `residualSignatureForHint()`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-139 | P3 | Create `src/services/modal-kg-bridge.ts` — modal KG bridge | ✅ DONE | `NodeData`/`RelationshipData`/`GraphData`; `FLogicFrame.toErgoString()`/`FLogicOntology`; `flogicTriplesToGraphData()` (Neo4j labels: LegalModalDocument/ModalFormula/ModalOperator etc.); `flogicTriplesToOntology()` (isa/scalar/set methods); `modalIrToNeo4jGraphData()`; `flogicOntologyToDict()` |
| T-140 | P3 | Create `src/services/modal-synthesis.ts` — modal synthesis + residual repair | ✅ DONE | `ModalResidualRepairRoute`; `RESIDUAL_REPAIR_ROUTES` (9 routes); `routeAutoencoderResidual(lossName, focus?)` (direct lookup + focus-hint fallback); `ModalProgramSynthesisHint.toDict()`; `residualSignatureForHint()` (SHA-256, 24-char hex); `synthesisHintFromRoute()` |
| T-141 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint29.test.ts` — 28 tests (all pass): flogicTriplesToGraphData (8), flogicTriplesToOntology (5), modalIrToNeo4jGraphData (2), flogicOntologyToDict (1), RESIDUAL_REPAIR_ROUTES (2), routeAutoencoderResidual (5), ModalProgramSynthesisHint (2), residualSignatureForHint (2), synthesisHintFromRoute (1) |

---

### Sprint 30 (Phase 30 — ZKP Circuits + UCAN Policy Bridge + Ethereum + Phase 7.4 Benchmarks, P3) ✅ DONE (2026-07-01)

> **Gap:** `zkp/circuits.py` (1328L) — proof attestation view; `integration/ucan_policy_bridge.py` (657L) — `UCANPolicyBridge`; `zkp/eth_integration.py` (593L) — `EthereumConfig`/`ProofVerificationResult`; `phase7_4_benchmarks.py` (637L) — `PerformanceMetrics`/`Phase7_4Benchmarks`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-142 | P3 | Create `src/services/zkp-circuits.ts` | ✅ DONE | `decodeSimulatedProofLayout()` (SIMZKP/1 magic + 256B layout); `buildProofAttestationView()` (SHA-256 attestationRef + proofDigest + circuitRef + publicInputsCommitment); `attestationViewMatchesProof()`; `compilerGuidanceRefFromMetadata()` |
| T-143 | P3 | Create `src/services/ucan-policy-bridge.ts` | ✅ DONE | `BridgeCompileResult` (success/policyCid/delegationTokens/denialCount/errors); `BridgeEvaluationResult` (decision/allowed/obligations); `SignedPolicyResult`; `UCANPolicyBridge.compileNl()/evaluate()/sign()`; `compileAndEvaluate()`; `getUCANPolicyBridge()` |
| T-144 | P3 | Create `src/services/zkp-eth-integration.ts` | ✅ DONE | `EthereumConfig`/`makeEthereumConfig()`; `ProofVerificationResult`; `GasEstimate`; `EthereumProofClient.estimateGas()/verifyProof()` (stubs); `ProofSubmissionPipeline.submit()`; `PerformanceMetrics.summary()`; `Phase7_4Benchmarks.runAllBenchmarks() → BenchmarkSuite` |
| T-145 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint30.test.ts` — 33 tests (all pass): ZKP circuits (14), UCANPolicyBridge (9+2), EthereumProofClient (2), PerformanceMetrics (2), Phase7_4Benchmarks (2) |

---

### Sprint 31 (Phase 31 — Logic Verifier + Translation Core + Legal Symbolic Analyzer, P3) ✅ DONE (2026-07-01)

> **Gap:** `integration/reasoning/logic_verification.py` (743L) — `LogicVerifier`; `integration/converters/logic_translation_core.py` (718L) — `TranslationResult`/`LeanTranslator`/`CoqTranslator`/`SMTTranslator`; `integration/domain/legal_symbolic_analyzer.py` (699L) — `LegalSymbolicAnalyzer`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-146 | P3 | Create `src/services/logic-verifier.ts` | ✅ DONE | `VerificationResult` enum; `LogicAxiom`/`makeAxiom()`; `ProofStep`/`ProofResult`/`ConsistencyCheck`/`EntailmentResult`; `LogicVerifier` (6 built-in axioms + `addAxiom/verifyFormula/proveWithAxioms/checkConsistency/checkEntailment/proofCache`) |
| T-147 | P3 | Create `src/services/logic-translation-core.ts` | ✅ DONE | `LogicTranslationTarget` (LEAN4/COQ/SMT_LIB2/PROLOG/TDFOL); `TranslationResult.toDict()`; `AbstractLogicFormula` (`makeAtomicFormula`/`makeCompoundFormula`); `LeanTranslator` (O→Obligatory/P→Permitted); `CoqTranslator` (∧→/\\); `SMTTranslator` (check-sat); `translateFormula()` |
| T-148 | P3 | Create `src/services/legal-symbolic-analyzer.ts` | ✅ DONE | `LegalDomain`/`DeonticOperator` enums; `LegalAnalysisResult`/`DeonticProposition`/`LegalEntity`/`TemporalCondition`; `LegalSymbolicAnalyzer.analyze()` (domain/deontic/entity/temporal heuristics); `LegalReasoningEngine.reason()`; `createLegalAnalyzer/createLegalReasoningEngine()` |
| T-149 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint31.test.ts` — 35 tests (all pass): LogicVerifier (10), LeanTranslator (6), CoqTranslator (2), SMTTranslator (2), translateFormula (3), LegalSymbolicAnalyzer (8), LegalReasoningEngine (2) |

---

### Sprint 32 (Phase 32 — Deontic Query Engine + Legal Domain Knowledge + TDFOL Grammar Bridge, P3) ✅ DONE (2026-07-02)

> **Gap:** `integration/domain/deontic_query_engine.py` (794L) — `QueryType`/`QueryResult`/`ComplianceResult`/`DeonticQueryEngine`; `integration/domain/legal_domain_knowledge.py` (647L) — `LegalPattern`/`AgentPattern`/`LegalDomainKnowledge`; `integration/bridges/tdfol_grammar_bridge.py` (669L) — `TDFOLGrammarBridge`/`NaturalLanguageTDFOLInterface`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-150 | P3 | Create `src/services/deontic-query-engine.ts` | ✅ DONE | `QueryType` (7 types); `DeonticFormula`/`DeonticRuleSet`/`makeDeonticFormula`; `QueryResult.toDict()`; `ComplianceResult.toDict()`; `LogicConflict`; `DeonticQueryEngine.loadRuleSet/query/checkCompliance/detectConflicts`; `createQueryEngine()` |
| T-151 | P3 | Create `src/services/legal-domain-knowledge.ts` | ✅ DONE | `LegalConceptType`/`DeonticOperatorKind` enums; `LegalPattern.match()`/`AgentPattern.match()`; `LegalDomainKnowledge` with obligation/permission/prohibition/agent/temporal patterns; `extractConcepts(text)/identifyAgents(text)/patternsForDomain(domain)/getPatterns()` |
| T-152 | P3 | Create `src/services/tdfol-grammar-bridge.ts` | ✅ DONE | `TDFOLGrammarBridge.parse(text) → Formula\ \| null`/`.explain(formula)`/`.parseAll(texts[])`; `NaturalLanguageTDFOLInterface.parseNl/explainFormula`; `parseNl()`+`explainFormula()` convenience exports |
| T-153 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint32.test.ts` — 29 tests (all pass) |

---

### Sprint 33 (Phase 33 — Deontic Logic Converter + Symbolic Primitives + FOL Validator, P3) ✅ DONE (2026-07-02)

> **Gap:** `integration/converters/deontic_logic_converter.py` (739L) — `ConversionContext`/`ConversionResult`/`DeonticLogicConverter`; `integration/symbolic/symbolic_logic_primitives.py` (594L) — `LogicalStructure`/`LogicPrimitives`; `integration/domain/symbolic_contracts.py` (840L) — `FOLInput`/`FOLOutput`/`FOLSyntaxValidator`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-154 | P3 | Create `src/services/deontic-logic-converter.ts` | ✅ DONE | `ConversionContext`/`makeConversionContext()`/`toDict()`; `ConversionResult` (success/statistics/toDict()); `DeonticLogicConverter.convert(text, ctx?)` (O/P/F heuristic + agent/action/condition extraction) + `.convertEntities(entities[])` |
| T-155 | P3 | Create `src/services/symbolic-logic-primitives.ts` | ✅ DONE | `LogicalStructure`; `analyzeLogicalStructure()` (Unicode-aware ∀/∃/∧/∨/¬/→/◊/□); 13 `AVAILABLE_PRIMITIVES` (and/or/not/implies/iff/forall/exists/equals/O/P/F/□/◊); `createLogicSymbol().apply(primitive)/toFol(format)` |
| T-156 | P3 | Create `src/services/fol-syntax-validator.ts` | ✅ DONE | `FOLInput`/`validateFolInput()` (confidence/format validation); `FOLOutput.isValid/toDict()`; `ValidationContext`/`makeValidationContext()`; `FOLSyntaxValidator.validate()` (parenthesis balance/depth/free-var) + `.convert()` |
| T-157 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint33.test.ts` — 37 tests (all pass) |

---

### Sprint 34 (Phase 34 — Modal Logic Extension + Document Consistency Checker + Temporal Deontic RAG Store, P3) ✅ DONE (2026-07-02)

> **Gap:** `integration/converters/modal_logic_extension.py` (531L) — `ModalFormula`/`LogicClassification`/`AdvancedLogicConverter`/`convertToModal()`; `integration/domain/document_consistency_checker.py` (538L) — `DocumentAnalysis`/`DebugReport`/`DocumentConsistencyChecker`; `integration/domain/temporal_deontic_rag_store.py` (520L) — `TheoremMetadata`/`ConsistencyResult`/`TemporalDeonticRAGStore`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-158 | P3 | Create `src/services/modal-logic-extension.ts` | ✅ DONE | `ModalFormula`/`LogicClassification`; `AdvancedLogicConverter.toModal/classify/convertBatch()`; `convertToModal(text)/detectLogicType(text)` — classify as deontic/temporal/epistemic/alethic via pattern matching |
| T-159 | P3 | Create `src/services/document-consistency-checker.ts` | ✅ DONE | `DocumentAnalysis` (extractedFormulas/consistencyResult/issuesFound/toDict()); `DebugReport` (addIssue/finalize/toDict()); `DocumentConsistencyChecker.analyze(text, docId?)/generateDebugReport(analysis)` |
| T-160 | P3 | Create `src/services/temporal-deontic-rag-store.ts` | ✅ DONE | `TheoremMetadata` (theoremId/formula/temporalScope/jurisdiction/precedentStrength/toDict()); `ConsistencyResult.toDict()`; `TemporalDeonticRAGStore` (addTheorem/removeTheorem/findRelevant/checkConsistency/`makeTheoremFromFormula()` factory) |
| T-161 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint34.test.ts` — 27 tests (all pass) |

---

### Sprint 35 (Phase 35 — Deontic Logic Core + IPLD Logic Storage + Deontological Reasoning, P3) ✅ DONE (2026-07-02)

> **Gap:** `integration/converters/deontic_logic_core.py` (514L) — extended `DeonticOperator`/`LegalAgent`/`DeonticRuleSet`; `integration/caching/ipld_logic_storage.py` (489L) — `LogicProvenanceChain`/`LogicIPLDNode`/`LogicIPLDStorage`; `integration/reasoning/deontological_reasoning.py` (482L) — `DeonticExtractor`/`DeontologicalReasoningEngine`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-162 | P3 | Create `src/services/deontic-logic-core.ts` | ✅ DONE | `DeonticOperatorExt` (8: O/P/F/S/R/L/POW/IMM); `LogicConnective`/`TemporalOperatorExt`; `makeLegalAgent()`; `makeExtFormula().toString()/toDict()`; `DeonticRuleSetExt.addFormula/query/search/obligations/permissions/prohibitions/toDict()` |
| T-163 | P3 | Create `src/services/ipld-logic-storage.ts` | ✅ DONE | `makeProvenanceChain()/toDict()`; `LogicIPLDNode` (SHA-256 CID + `addTranslation()`); `LogicIPLDStorage.addNode/getNode/listNodes/findByDocument`; `LogicProvenanceTracker.trackFormula/getProvenance`; `createLogicStorageWithProvenance()` |
| T-164 | P3 | Create `src/services/deontological-reasoning.ts` | ✅ DONE | `DeonticStatement` (O/P/F/R/L + conditions + toDict()); `DeonticExtractor.extractStatements(text, docId)/countByOperator()`; `ConflictReport`; `DeontologicalReasoningEngine.reason/detectConflicts/generateExplanation/analyzeText(text, docId, query?)` |
| T-165 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint35.test.ts` — 32 tests (all pass) |

---

### Sprint 36 (Phase 36 — IPFS Proof Cache + Medical Theorem Framework + TDFOL-CEC Bridge, P3) ✅ DONE (2026-07-02)

> **Gap:** `integration/caching/ipfs_proof_cache.py` (457L) — `IPFSCachedProof`/`IPFSProofCache`; `integration/domain/medical_theorem_framework.py` (426L) — `MedicalTheoremType`/`MedicalEntity`/`MedicalTheorem`/`MedicalTheoremGenerator`; `integration/bridges/tdfol_cec_bridge.py` (435L) — `TDFOLCECBridge`/`EnhancedTDFOLProver`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-166 | P3 | Create `src/services/ipfs-proof-cache.ts` | ✅ DONE | `IPFSCachedProof` (computeCid/isExpired/toDict); `IPFSProofCache.set/get/has/pin/unpin/clearExpired/getStats/clear`; `getGlobalIPFSCache()/resetGlobalIPFSCache()` |
| T-167 | P3 | Create `src/services/medical-theorem-framework.ts` | ✅ DONE | `MedicalTheoremType` (6 types)/`ConfidenceLevel` (5 levels); `MedicalEntity`/`TemporalConstraint`; `MedicalTheorem.toFormula()/toDict()`; `MedicalTheoremGenerator.generateFromText/validateTheorem/generateBatch`; `FuzzyLogicValidator.validate()` |
| T-168 | P3 | Create `src/services/tdfol-cec-bridge.ts` | ✅ DONE | `TDFOLCECBridge` (3 default axioms; prove via axiom_lookup/forward_chain/CEC delegation); `EnhancedTDFOLProver.prove/proveBatch/useKB/proofId()`; `createEnhancedProver()` |
| T-169 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint36.test.ts` — 33 tests (all pass) |

---

### Sprint 37 (Phase 37 — Neurosymbolic API + Base Proof Cache + CEC Bridge, P3) ✅ DONE (2026-07-02)

> **Gap:** `integration/symbolic/neurosymbolic_api.py` (414L) — `ReasoningCapabilities`/`NeurosymbolicReasoner`; `integration/proof_cache.py` (350L) — `CachedProof`/`ProofCache`/`get_global_cache()`; `integration/cec_bridge.py` (349L) — `UnifiedProofResult`/`CECBridge`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-170 | P3 | Create `src/services/neurosymbolic-api.ts` | ✅ DONE | `ReasoningCapabilities` (127 rules, 5 modal provers); `NeurosymbolicReasoner.addKnowledge/prove(KB lookup+modus ponens)/parse/explain/listKnowledge/getStats`; `getReasoner()/resetReasoner()` |
| T-171 | P3 | Create `src/services/proof-cache-base.ts` | ✅ DONE | `CachedProof` (hitCount/isExpired()/toDict()); `ProofCache` (set/get/has/invalidate/clearExpired/flush/getStats; LRU eviction at maxSize); `getGlobalCache(maxSize,ttl)/resetGlobalCache()` |
| T-172 | P3 | Create `src/services/cec-bridge.ts` | ✅ DONE | `UnifiedProofResult` (isProved/isValid/proverUsed/status/confidence); `CECBridge.prove()` (CEC→Z3 fallback)/`proveWithCEC()`/`proveBatch()`/`getStats()` |
| T-173 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint37.test.ts` — 29 tests (all pass) |

---

### Sprint 38 (Phase 38 — Neurosymbolic GraphRAG + Hybrid Confidence + Base Prover Bridge, P3) ✅ DONE (2026-07-02)

> **Gap:** `integration/symbolic/neurosymbolic_graphrag.py` (374L) — `PipelineResult`/`NeurosymbolicGraphRAG`; `integration/symbolic/neurosymbolic/hybrid_confidence.py` (341L) — `ConfidenceSource`/`ConfidenceBreakdown`/`HybridConfidenceScorer`; `integration/bridges/base_prover_bridge.py` (318L) — `BridgeCapability`/`BridgeMetadata`/`BaseProverBridge`/`BridgeRegistry`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-174 | P3 | Create `src/services/neurosymbolic-graphrag.ts` | ✅ DONE | `PipelineResult` (docId/formulas/entities/provenTheorems/knowledgeGraphStats/toDict()); `NeurosymbolicGraphRAG.ingest(text,docId?)/query(q)/prove(formula)/getStats()` |
| T-175 | P3 | Create `src/services/hybrid-confidence.ts` | ✅ DONE | `ConfidenceSource` (4 values); `ConfidenceBreakdown.dominantSource/toDict()`; `HybridConfidenceScorer.score(symbolic,neural,structural)/scoreFromResult(result)/explain(breakdown)` |
| T-176 | P3 | Create `src/services/base-prover-bridge.ts` | ✅ DONE | `BridgeCapability` (5 caps); `BridgeMetadata`; abstract `BaseProverBridge.prove/toTargetFormat/fromTargetFormat/proveBatch/hasCapability()`; `BridgeRegistry.register/get/list/getByCap/getAllMetadata/size`; `StubProverBridge`; `getBridgeRegistry()/resetBridgeRegistry()` |
| T-177 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint38.test.ts` — 30 tests (all pass) |

---

### Sprint 39 (Phase 39 — Reasoning Coordinator + Deontic Conflict Detector + Interactive FOL Constructor, P3) ✅ DONE (2026-07-02)

> **Gap:** `symbolic/neurosymbolic/reasoning_coordinator.py` (351L) — `ReasoningStrategy`/`CoordinatedResult`/`NeuralSymbolicCoordinator`; `reasoning/_deontic_conflict_mixin.py` (304L) — `ConflictDetector`/`DeonticConflictMixin`; `interactive/interactive_fol_constructor.py` (848L) — `InteractiveFOLConstructor`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-178 | P3 | Create `src/services/reasoning-coordinator.ts` | ✅ DONE | `ReasoningStrategy` (4); `CoordinatedResult` (isProved/confidence/symbolicConfidence/neuralConfidence/strategyUsed/reasoningPath/proofSteps/toDict()); `NeuralSymbolicCoordinator.coordinate(formula, strategy?)` — auto-selects symbolic/neural/hybrid; `getStats()` |
| T-179 | P3 | Create `src/services/deontic-conflict-detector.ts` | ✅ DONE | `DeonticConflictType` (6 types); `DeonticConflict` (conflictType/severity/explanation/suggestedResolution); `ConflictDetector.detectConflicts(stmts[])/summarize()`; `DeonticConflictMixin.wouldConflict/conflictScore()` |
| T-180 | P3 | Create `src/services/interactive-fol-constructor.ts` | ✅ DONE | `StatementAnalysis`/`FOLConstructorSession` (sessionId/domain/statements/formulas/consistencyScore); `InteractiveFOLConstructor.addStatement(text)/buildFormula(∧|∨|→)/checkConsistency()/getSession()/reset()/exportFormulas()` |
| T-181 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint39.test.ts` — 29 tests (all pass) |

---

### Sprint 40 (Phase 40 — Embedding Prover + Prover Backend Mixin + Symbolic FOL Bridge, P3) ✅ DONE (2026-07-02)

> **Gap:** `symbolic/neurosymbolic/embedding_prover.py` (240L) — `EmbeddingEnhancedProver`; `reasoning/_prover_backend_mixin.py` (527L) — `ProverBackendMixin`; `bridges/symbolic_fol_bridge.py` (764L) — `LogicalComponents`/`FOLConversionResult`/`SymbolicFOLBridge`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-182 | P3 | Create `src/services/embedding-prover.ts` | ✅ DONE | `cosineSimilarity(a,b)`; `EmbeddingEnhancedProver.computeSimilarity/prove(exact_match+similarity_match threshold)/retrieveSimilar(query,corpus,topK)/cacheSize/clearCache`; hash-based embedding (no ML deps) |
| T-183 | P3 | Create `src/services/prover-backend-mixin.ts` | ✅ DONE | `generateDeonticSMT2Axioms()` (declarations+axioms+combined SMT-LIB2); `ProverBackendMixin.executeZ3Proof/executeLean4Proof/executeCoqProof/checkConsistency()` — simulated backends |
| T-184 | P3 | Create `src/services/symbolic-fol-bridge.ts` | ✅ DONE | `LogicalComponents` (quantifiers/predicates/entities/connectives; dict-like `get/keys/items/toDict`); `SymbolicFOLBridge.extractComponents(text)/convert(text)/validate(formula)` (parenthesis balance check) |
| T-185 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint40.test.ts` — 30 tests (all pass) |

---

### Sprint 41 (Phase 41 — TDFOL ShadowProver Bridge + Logic Verifier Backends + Proof Engine Utils, P3) ✅ DONE (2026-07-02)

> **Gap:** `bridges/tdfol_shadowprover_bridge.py` (596L) — `ModalLogicType`/`TDFOLShadowProverBridge`/`ModalAwareTDFOLProver`; `reasoning/_logic_verifier_backends_mixin.py` (293L) — `LogicVerifierBackendsMixin`; `reasoning/proof_execution_engine_utils.py` (206L) — `createProofEngine()`/`proveFormula()`/`proveWithAllProvers()`/`getLeanTemplate()`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-186 | P3 | Create `src/services/tdfol-shadowprover-bridge.ts` | ✅ DONE | `ModalLogicType` (K/T/S4/S5/D); `TDFOLShadowProverBridge extends BaseProverBridge` (O/P/F→Obligatory/Permitted/Forbidden); `ModalAwareTDFOLProver.proveModal(auto)/proveInSystem/proveInAllSystems()`; `createModalAwareProver()` |
| T-187 | P3 | Create `src/services/logic-verifier-backends-mixin.ts` | ✅ DONE | `ConsistencyCheckResult`; `LogicVerifierBackendsMixin.checkConsistencyFallback/checkConsistencySymbolic/findConflictingPairs/checkConsistency()` — O/F and φ/¬φ conflict detection |
| T-188 | P3 | Create `src/services/proof-execution-engine-utils.ts` | ✅ DONE | `ProofEngine.prove(prover)/proveAll/checkConsistency`; `createProofEngine()/proveFormula()/proveWithAllProvers()/checkConsistency()/getLeanTemplate()` — Lean 4 D-axiom template |
| T-189 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint41.test.ts` — 26 tests (all pass) |

---

### Sprint 42 (Phase 42 — External Provers + Caselaw Bulk Processor + Proof Execution Engine Types, P3) ✅ DONE (2026-07-02)

> **Gap:** `bridges/external_provers.py` (610L) — `ProverStatus`/`ProverResult`/`VampireProver`/`EProver`/`ProverRegistry`; `domain/caselaw_bulk_processor.py` (757L) — `CaselawDocument`/`ProcessingStats`/`BulkProcessingConfig`/`CaselawBulkProcessor`; `reasoning/proof_execution_engine_types.py` (100L) — `ProofStatus`/`ProofResult`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-190 | P3 | Create `src/services/external-provers.ts` | ✅ DONE | `ProverStatus` (6: THEOREM/SAT/UNSAT/UNKNOWN/TIMEOUT/ERROR); `VampireProver`/`EProver` (`isAvailable()/prove()` stubs with simulated results); `ProverRegistry.register/get/list/getBestFor/prove/size`; `getProverRegistry()/resetProverRegistry()` |
| T-191 | P3 | Create `src/services/caselaw-bulk-processor.ts` | ✅ DONE | `CaselawDocument`/`makeCaselawDocument()`; `ProcessingStats` (processingTimeMs/successRate/toDict/reset); `BulkProcessingConfig`/`makeDefaultConfig()`; `CaselawBulkProcessor.process/processBatch/getStats/reset`; `createBulkProcessor()` |
| T-192 | P3 | Create `src/services/proof-execution-engine-types.ts` | ✅ DONE | `ProofStatus` (5: SUCCESS/FAILURE/TIMEOUT/ERROR/UNSUPPORTED); `ProofResult` (prover/statement/status/proof/timeMs/statistics/isProved/failed/toDict()); `makeProofResult()` |
| T-193 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint42.test.ts` — 28 tests (all pass) |

---

### Sprint 43 (Phase 43 — Integration Init + FOL Constructor IO + Prover Installer, P3) ✅ DONE (2026-07-02)

> **Gap:** `integration/__init__.py` (334L) — `enable_symbolicai()`/`SYMBOLIC_AI_AVAILABLE`; `interactive/_fol_constructor_io.py` (299L) — `FOLConstructorIOMixin`; `bridges/prover_installer.py` (867L) — `PlatformInstallProfile`/`detect_platform_install_profile()`/`install_component()`.

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-194 | P3 | Create `src/services/integration-init.ts` | ✅ DONE | `SYMBOLIC_AI_AVAILABLE`/`enableSymbolicAI()/resetSymbolicAI()`; `IntegrationCapabilities` (8: tdfolProver/cecEngine/modalLogic/embeddingRetrieval/interactiveFOL/ipfsCache/etc.); `getIntegrationStatus() → IntegrationStatus`; `hasCapability(name)` |
| T-195 | P3 | Create `src/services/fol-constructor-io-mixin.ts` | ✅ DONE | `FOLConstructorIOMixin.exportSession(session,format?)` (json|fol|prolog|tptp); `importSession(data)/convertFormula(formula,format)/serializeSession()/deserializeSession(json)`; FOL→Prolog/TPTP converters |
| T-196 | P3 | Create `src/services/prover-installer.ts` | ✅ DONE | `PlatformInstallProfile` (system/arch/packageManager/canInstallSystemPackages); `detectPlatformInstallProfile()`; `installComponent(name,profile?,dryRun?)/installComponents()/listKnownComponents()` — 6 components: z3/vampire/eprover/lean4/coq/cvc5 |
| T-197 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint43.test.ts` — 28 tests (all pass) |

---

### Sprint 44 (Phase 44 — Modal Logic Codec + Modal IR Decompiler, Deferred P3) ✅ DONE (2026-07-02)

> **Deferred gap:** `modal/codec.py` (12843L) — `ModalLogicCodecConfig`/`ModalLogicCodecResult`/`DeterministicModalLogicCodec`; `modal/decompiler.py` (9621L) — `DecodedModalPhrase`/`DecodedModalText`/`decode_modal_ir_document()`/`modal_formula_to_text()`/`modal_text_token_similarity()`. Porting key public APIs only (files too large to port in full).

| ID | Priority | Task | Status | Notes |
|---|---|---|---|---|
| T-198 | P3 | Create `src/services/modal-logic-codec.ts` | ✅ DONE | `makeCodecConfig()` (embeddingDimensions>=1 validation); `ModalLogicCodecResult` (targetFamily/sourceEmbedding/decodedEmbedding/losses/totalLoss/kgTriples/toDict()); `DeterministicModalLogicCodec.encode(text)/encodeBatch(texts)` — simulated (deontic/temporal/epistemic/alethic detection + cosine loss) |
| T-199 | P3 | Create `src/services/modal-ir-decompiler.ts` | ✅ DONE | `DecodedModalPhrase.toDict()`; `DecodedModalText` (reconstructionSimilarity/modalSpanCoverage/formulas/toDict()); `decodeModalIRDocument(doc) → DecodedModalText`; `modalFormulaToText()` (O/P/F/□/◊ pattern converters); `modalTextTokenSimilarity()` (Jaccard token overlap) |
| T-200 | P3 | Write 10+ tests | ✅ DONE | `wasm-prover-sprint44.test.ts` — 30 tests (all pass) |

---

### Sprint 45 (Phase 45 — TDFOL Performance Metrics + ZKP Integration + Formula Analyzer, P3) 🆕

> **Previously untracked gap:** `TDFOL/performance_metrics.py` (620L) — `TimingResult`/`MemoryResult`/`StatisticalSummary`/`MetricsCollector`; `TDFOL/zkp_integration.py` (633L) — `UnifiedProofResult`/`ZKPTDFOLProver`; `external_provers/formula_analyzer.py` (645L) — `FormulaType`/`FormulaComplexity`/`FormulaAnalysis`/`FormulaAnalyzer`.

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-201 | P3 | Create `src/services/tdfol-performance-metrics.ts` | `TimingResult` (operationName/durationMs/success); `MemoryResult` (peakMb/averageMb); `StatisticalSummary` (mean/median/stdDev/p95/min/max); `MetricsCollector` (record/getStats/getSummary/reset); `getGlobalCollector()/resetGlobalCollector()` | ✅ DONE |
| T-202 | P3 | Create `src/services/tdfol-zkp-integration.ts` | `UnifiedProofResult` (isProved/proofData/verificationKey/circuitId/confidence); `ZKPTDFOLProver` (prove(formula)/verify(proof,vk)/generateWitness()/getStats) | ✅ DONE |
| T-203 | P3 | Create `src/services/formula-analyzer.ts` | `FormulaType` (DEONTIC/TEMPORAL/MODAL/FOL/PROPOSITIONAL/UNKNOWN); `FormulaComplexity` (SIMPLE/MODERATE/COMPLEX/VERY_COMPLEX); `FormulaAnalysis` (formulaType/complexity/operators/quantifiers/depth/confidence/toDict()); `FormulaAnalyzer.analyze(formula)/classifyType(formula)/measureComplexity(formula)` | ✅ DONE |
| T-204 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint45.test.ts` | ✅ DONE — 40 tests (all pass) |

---

### Sprint 46 (Phase 46 — ShadowProver + Temporal Inference Rules + ProverRouter, P3) 🆕

> **Previously untracked gap:** `CEC/native/shadow_prover.py` (716L) — `ModalLogic/ProofStatus/ProofStep/ProofTree/ProblemFile/ShadowProver/KProver`; `TDFOL/inference_rules/temporal.py` (648L) — 15+ LTL axiom rule classes; `external_provers/prover_router.py` (1008L) — `ProverStrategy/RouterProofResult/ProverRouter`.

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-205 | P3 | Create `src/services/shadow-prover.ts` | `ModalLogic` enum (K/T/S4/S5/D/LP); `ProofStatus` (SUCCESS/FAILURE/TIMEOUT/ERROR); `ProofStep` (ruleName/premises/conclusion); `ProofTree` (goal/steps/status/logic/isSuccessful()/getDepth()); `ProblemFile`; `ShadowProver` abstract; `KProver` concrete impl | ✅ DONE |
| T-206 | P3 | Create `src/services/temporal-inference-rules.ts` | 15+ rules: `TemporalKAxiomRule`, `TemporalTAxiomRule`, `TemporalS4AxiomRule`, `TemporalS5AxiomRule`, `EventuallyIntroductionRule`, `AlwaysNecessitationRule`, `UntilUnfoldingRule`, `UntilInductionRule`, `EventuallyExpansionRule`, `AlwaysDistributionRule`, `AlwaysEventuallyExpansionRule`, `EventuallyAlwaysContractionRule`, `UntilReleaseDualityRule`, `WeakUntilExpansionRule`, `NextDistributionRule`; each implements `canApply()`/`apply()`/`name`/`description` | ✅ DONE |
| T-207 | P3 | Create `src/services/prover-router.ts` | `ProverStrategy` enum (AUTO/FASTEST/MOST_CAPABLE/PARALLEL/SEQUENTIAL); `RouterProofResult` (isProved/proverUsed/proofTime/allResults/strategyUsed/reason); `ProverRouter` (prove(formula, strategy)/proveParallel()/selectBest()/getAvailableProvers()/getStats()) | ✅ DONE |
| T-208 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint46.test.ts` | ✅ DONE — 48 tests (all pass) |

---

### Sprint 47 (Phase 47 — TDFOL NL Patterns + NL Policy Conflict Detector + LLM Prompt Builder, P3) 🆕

> **Previously untracked gap:** `TDFOL/nl/tdfol_nl_patterns.py` (826L) — `PatternType/Pattern/PatternMatch/PatternMatcher`; `CEC/nl/nl_policy_conflict_detector.py` (794L) — `PolicyConflict/NLPolicyConflictDetector`; `TDFOL/nl/llm.py` (724L) — `LLMParseResult/LLMResponseCache/build_conversion_prompt()`.

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-209 | P3 | Create `src/services/tdfol-nl-patterns.ts` | `PatternType` enum; `Pattern` (name/type/textPattern/description/examples); `PatternMatch` (pattern/span/text/entities/confidence); `PatternMatcher` (match(text)/matchAll(texts)/getPatterns()/addPattern()) — regex-based (spaCy not ported) | ✅ DONE |
| T-210 | P3 | Create `src/services/nl-policy-conflict-detector.ts` | `PolicyConflict` (conflictType/action/resource/actors/clauseTypes/description/toDict()); `NLPolicyConflictDetector` (detect(clauses)/detectAndWarn(clauses)); `detectConflicts()` module-level convenience fn | ✅ DONE |
| T-211 | P3 | Create `src/services/tdfol-nl-llm.ts` | `LLMParseResult` (formula/confidence/method/alternatives/errors); `LLMResponseCache` (get/set/clear/size); `buildConversionPrompt(text)/buildValidationPrompt(formula)/buildErrorCorrectionPrompt(formula, errors)/getOperatorHintsForText(text)` | ✅ DONE |
| T-212 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint47.test.ts` | ✅ DONE — 43 tests (all pass) |

---

### Sprint 48 (Phase 48 — DCEC English Grammar + Proof Explainer + Deontic Analyzer + Structured Logging, P3) 🆕

> **Previously untracked gap (Sprint 48):** `CEC/native/dcec_english_grammar.py` (661L), `TDFOL/proof_explainer.py` (577L), `deontic/analyzer.py` (503L), `observability/structured_logging.py` (527L).

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-213 | P3 | Create `src/services/dcec-english-grammar.ts` | `LexicalCategory` enum; `LexicalEntry` (word/category/semantics); `GrammarRule` (name/pattern/semantics); `DCECEnglishGrammar` (lookupWord/parsePhrase/getEnglishForFormula()/getFormulasForEnglish()); `createDcecGrammar()` factory | ✅ DONE |
| T-214 | P3 | Create `src/services/proof-explainer.ts` | `ProofType` (FORWARD_CHAINING/BACKWARD_CHAINING/MODAL_TABLEAUX/ZKP); `ExplanationLevel` (BRIEF/NORMAL/DETAILED/VERBOSE); `ProofStep`/`ProofExplanation`; `ProofExplainer` (explainProof()/explainZkpProof()/generateSummary()); `explainProof()` / `explainZkpProof()` module-level fns | ✅ DONE |
| T-215 | P3 | Create `src/services/deontic-analyzer.ts` | `DeonticAnalyzer` (extractDeonticStatements(corpus)/detectDeonticConflicts(statements)/groupByEntity(statements)/getStatistics(statements)) with DEONTIC_PATTERNS regex catalogue | ✅ DONE |
| T-216 | P3 | Create `src/services/structured-logging.ts` | `LogField` enum; `EventType` enum; `LogContext` (interface/get/set/clear); `getLogger(name)/structuredLog(level, event, message, fields)` | ✅ DONE |
| T-217 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint48.test.ts` | ✅ DONE — 47 tests (all pass) |

---

### Sprint 49 (Phase 49 — German Parser + Deontic Converter + TDFOL Converter + FOL Converter, P3) 🆕

> **Previously untracked gap (Sprint 49):** `CEC/nl/german_parser.py` (636L), `deontic/converter.py` (612L), `TDFOL/tdfol_converter.py` (528L), `fol/converter.py` (497L).

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-218 | P3 | Create `src/services/german-parser.ts` | `GermanPatternMatcher` (match(text)/matchByType()); `GermanParser` (parse(text)/extractClauses()); `getGermanVerbConjugations()`/`getGermanDeonticKeywords()` module-level data fns | ✅ DONE |
| T-219 | P3 | Create `src/services/deontic-converter.ts` | `DeonticConversionResult` (formulaString/ir/confidence); `DeonticConverter` (convert(nlText)/convertBatch(texts)/getStats()) | ✅ DONE — in `logic-converters.ts` |
| T-220 | P3 | Create `src/services/tdfol-converter.ts` | `TDFOLConversionResult` (tdfol/confidence/errors); `TDFOLConverter` (fromNL(text)/fromDeontic(ir)/fromFOL(fol)/validate(formula)) | ✅ DONE — in `logic-converters.ts` |
| T-221 | P3 | Create `src/services/fol-converter.ts` | `FOLFormula` (type/content/subformulas); `FOLConverter` (toTDFOL(fol)/toDeontic(fol)/toNL(fol)/validate(fol)) | ✅ DONE — in `logic-converters.ts` |
| T-222 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint49.test.ts` | ✅ DONE — 41 tests (all pass) |

---

### Sprint 50 (Phase 50 — Modal Tableaux + Formula Cache + Z3 Adapter + CEC Framework, P3) 🆕

> **Previously untracked gap:** `CEC/native/modal_tableaux.py` (603L), `CEC/optimization/formula_cache.py` (527L), `CEC/provers/z3_adapter.py` (546L), `CEC/cec_framework.py` (492L).

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-223 | P3 | Create `src/services/cec-modal-tableaux.ts` | `NodeStatus` enum; `TableauNode` (formulas/world/status/addFormula()/isContradictory()/close()); `ModalTableau` (root/logic/isClosed()/newWorld()); `TableauProver` (prove(goal,assumptions)/getStats()); `ResolutionProver` (prove()/resolveWith()); `createTableauProver()`/`createResolutionProver()` | ✅ DONE |
| T-224 | P3 | Create `src/services/formula-cache.ts` | `CacheEntry` (key/value/accessedAt/access()); `FormulaInterningCache` (intern/getStats()); `LRUCache<K,V>` (get/set/delete/clear/size/maxSize); `ProofResultCache`; `ParseResultCache`; `CacheManager` (getCache(name)/clearAll()/getStats()) | ✅ DONE |
| T-225 | P3 | Create `src/services/z3-adapter.ts` | `ProofStatus` (VALID/INVALID/SATISFIABLE/UNSATISFIABLE/UNKNOWN/ERROR/TIMEOUT); `Z3ProofResult` (status/isValid/proofTime/errorMessage); `Z3Adapter` (prove(formula)/check(formula)/isValid(formula)/isSatisfiable(formula)/getStats()); `checkZ3Installation()`/`getZ3Version()` | ✅ DONE |
| T-226 | P3 | Create `src/services/cec-framework.ts` | `ReasoningMode` enum; `FrameworkConfig`; `ReasoningTask`; `CECFramework` (initialize()/convertNaturalLanguage(text)/reason(text)/getStats()) | ✅ DONE |
| T-227 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint50.test.ts` | ✅ DONE — 52 tests (all pass) |

---

### Sprint 51 (Phase 51 — Advanced CEC Inference Rules + Deontic Rules + Event Calculus + French Parser, P3) 🆕

> **Previously untracked gap:** `CEC/native/advanced_inference.py` (573L), `TDFOL/inference_rules/deontic.py` (478L), `CEC/native/event_calculus.py` (549L), `CEC/nl/french_parser.py` (600L).

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-228 | P3 | Create `src/services/cec-advanced-inference.ts` | 10 inference rule classes: `ModalKAxiom`, `ModalTAxiom`, `ModalS4Axiom`, `ModalNecessitation`, `TemporalInduction`, `FrameAxiom`, `DeonticDRule`, `DeonticPermissionObligation`, `DeonticDistribution`, `KnowledgeObligation`; each implements `name/canApply(formulas)/apply(formulas)` | ✅ DONE |
| T-229 | P3 | Create `src/services/deontic-inference-rules.ts` | 10 TDFOL deontic rule classes: `DeonticKAxiomRule`, `DeonticDAxiomRule`, `ProhibitionEquivalenceRule`, `PermissionNegationRule`, `ObligationConsistencyRule`, `PermissionIntroductionRule`, `DeonticNecessitationRule`, `ProhibitionFromObligationRule`, `ObligationWeakeningRule`, `PermissionStrengtheningRule`; `ALL_DEONTIC_RULES` registry | ✅ DONE |
| T-230 | P3 | Create `src/services/event-calculus.ts` | `Event` (name/parameters/toString()); `Fluent` (name/parameters/toString()); `TimePoint` (value/comparisons); `EventCalculus` (happens/initiates/terminates/holdsAt/add\_axiom/query) | ✅ DONE |
| T-231 | P3 | Create `src/services/french-parser.ts` | `FrenchPatternMatcher` (match/matchByType); `FrenchParser` (parse/extractClauses); `getFrenchVerbConjugations()`/`getFrenchArticles()`/`getFrenchNegationPatterns()`/`getFrenchDeonticKeywords()` | ✅ DONE |
| T-232 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint51.test.ts` | ✅ DONE — 57 tests (all pass) |

---

### Sprint 52 (Phase 52 — Spanish Parser + CEC Fluents + CEC Types + ZKP Trace, P3) 🆕

> **Previously untracked gap:** `CEC/nl/spanish_parser.py` (578L), `CEC/native/fluents.py` (520L), `CEC/native/types.py` (480L), `zkp/provekit/trace.py` (566L).

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-233 | P3 | Create `src/services/spanish-parser.ts` | `SpanishPatternMatcher` (match/matchByType); `SpanishParser` (parse/extractClauses); `getSpanishVerbConjugations()`/`getSpanishArticles()`/`getSpanishDeonticKeywords()` | ✅ DONE |
| T-234 | P3 | Create `src/services/cec-fluents.ts` | `FluentType` enum; `PersistenceRule` enum; `Fluent` (name/type/persistenceRule/initialValue); `FluentManager` (addFluent/setState/getState/getHoldsAt/transition) | ✅ DONE |
| T-235 | P3 | Create `src/services/cec-types.ts` | TS interfaces for all typed dicts: `FormulaDict`, `ProofResultDict`, `ConversionResultDict`, `NamespaceExport`, `GrammarConfig`, `ProverConfig`; `Formula` and `Term` protocols as interfaces | ✅ DONE |
| T-236 | P3 | Create `src/services/zkp-trace.ts` | `TDFOLTraceNotDerivableError`, `TDFOLTraceBoundExceededError`, `TDFOLTraceSchemaError`; `TDFOLTraceStep`; `TDFOLTraceWitness`; `buildTdfolV1TraceWitness(axioms, theorem)/validateTdfolV1TraceWitness(witness)` | ✅ DONE |
| T-237 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint52.test.ts` | ✅ DONE — 40 tests (all pass) |

---

### Sprint 53 (Phase 53 — Cognitive Inference Rules + Lemma Generation + Proof Strategies + Monitoring, P3) 🆕

> **Previously untracked gap:** `CEC/native/inference_rules/cognitive.py` (569L), `CEC/native/lemma_generation.py` (501L), `CEC/native/proof_strategies.py` (458L), `monitoring.py` (452L).

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-238 | P3 | Create `src/services/cognitive-inference-rules.ts` | 10 cognitive inference rule classes: `BeliefDistribution`, `KnowledgeImpliesBelief`, `BeliefMonotonicity`, `IntentionCommitment`, `BeliefConjunction`, `KnowledgeDistribution`, `IntentionMeansEnd`, `PerceptionImpliesKnowledge`, `BeliefNegation`, `KnowledgeConjunction`; `ALL_COGNITIVE_RULES` registry | ✅ DONE |
| T-239 | P3 | Create `src/services/lemma-generation.ts` | `LemmaType` enum; `Lemma` (type/statement/premises/confidence); `LemmaCache` (add/get/contains/clear); `LemmaGenerator` (generateFormulaLemmas/generateKBLemmas/getStats); `createLemmaGenerator()` | ✅ DONE |
| T-240 | P3 | Create `src/services/proof-strategies.ts` | `StrategyType` enum; abstract `ProofStrategy` (prove(goal, assumptions)/getStats); `ForwardChainingStrategy`; `BackwardChainingStrategy`; `BidirectionalStrategy`; `HybridStrategy`; `getStrategy(type, maxSteps)` | ✅ DONE |
| T-241 | P3 | Create `src/services/llm-circuit-breaker.ts` | `CircuitState` enum (CLOSED/OPEN/HALF_OPEN); `CircuitBreakerMetrics` (totalCalls/failedCalls/failureRate/lastFailureTime); `CircuitBreakerOpenError`; `LLMCircuitBreaker` (call(fn)/getState()/getMetrics()/reset()); `getCircuitBreaker(name)/resetAllCircuitBreakers()/getAllStats()` | ✅ DONE |
| T-242 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint53.test.ts` | ✅ DONE — 50 tests (all pass) |

---

### Sprint 54 (Phase 54 — Grammar NL Policy Compiler + TDFOL NL Generator + DCEC Parsing + ZKP Form Circuit, P3) 🆕

> **Previously untracked gap:** `CEC/nl/grammar_nl_policy_compiler.py` (491L), `TDFOL/nl/tdfol_nl_generator.py` (482L), `CEC/native/dcec_parsing.py` (454L), `zkp/form_circuit.py` (481L).

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-243 | P3 | Create `src/services/grammar-nl-policy-compiler.ts` | `GrammarCompilationResult` (text/clauses/policyCid/warnings/success/prohibitionClauses/permissionClauses/obligationClauses/toDict()); `GrammarNLPolicyCompiler` (compile(text)/compileBatch(texts)/getStats()); `grammarCompileNlToPolicy(text)` | ✅ DONE |
| T-244 | P3 | Create `src/services/tdfol-nl-generator.ts` | `GeneratedFormula` (formula/patternMatch/confidence/formulaString/entities/alternatives); `FormulaGenerator` (generateFromMatches(matches)/generateFromText(text)/getStats()) | ✅ DONE |
| T-245 | P3 | Create `src/services/dcec-parsing.ts` | `ParseToken` (funcName/args/depthOf()/widthOf()/createSExpression()/createFExpression()); `removeComments(expr)`/`functorizSymbols(expr)`/`replaceSynonyms(args)`/`prefixLogicalFunctions(expr)`/`prefixEmdas(expr)` | ✅ DONE |
| T-246 | P3 | Create `src/services/zkp-form-circuit.ts` | `FormCompletionCircuit` (formId/formTemplateHash/ruleSetHash/verdictsHash/fromRuleSetAndReport()/build()/getPublicInputsDict()); `FormCompletionCertificate` (circuitRef/proofHash/publicInputs/timestamp); `generateFormCertificate(circuit,fieldValues)/verifyFormCertificate(certificate)` | ✅ DONE |
| T-247 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint54.test.ts` | ✅ DONE — 40 tests (all pass) |

---

### Sprint 55 (Phase 55 — SMT Prover Bridges + ZKP Backends, P3) 🆕

> **Previously untracked gap:** `external_provers/smt/z3_prover_bridge.py` (578L), `external_provers/smt/cvc5_prover_bridge.py` (526L), `zkp/backends/groth16_ffi.py` (613L) + `zkp/backends/provekit_ffi.py` (559L) — combined as a single ZKP backends file.

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-248 | P3 | Create `src/services/z3-prover-bridge.ts` | `Z3ProofResult` (isValid/isSat/isUnsat/model/reason/proofTime/isProved()); `Z3ProverBridge` (prove(formula,axioms,timeout)/check(formula)/isAvailable()/getStats()); `proveWithZ3(formula,axioms,timeout)` | ✅ DONE |
| T-249 | P3 | Create `src/services/cvc5-prover-bridge.ts` | `CVC5ProofResult` (isValid/isSat/isUnsat/proof/reason/proofTime/isProved()); `CVC5ProverBridge` (prove(formula,axioms,timeout)/check(formula)/isAvailable()/getStats()) | ✅ DONE |
| T-250 | P3 | Create `src/services/zkp-backends.ts` | `ZKPBackendProtocol` (generateProof/verifyProof); `Groth16Proof` (proofData/publicInputs/metadata/toDict()/fromDict()); `Groth16Backend` (generateProof/verifyProof/isAvailable()/getStats()); `Groth16BackendFallback`; `ProveKitFFI` (stub — requires Rust binary) | ✅ DONE |
| T-251 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint55.test.ts` | ✅ DONE — 35 tests (all pass) |

---

### Sprint 56 (Phase 56 — Modal Compiler + Deontic Exports, FINAL GAP CLOSURE, P3) 🏁

> **Final gap:** `modal/compiler.py` (3221L) and `deontic/exports.py` (5134L). Key public API ported; spaCy/BM25 internal deps replaced with string-based stubs.

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-252 | P3 | Create `src/services/modal-compiler.ts` | `ModalCompilerConfig` (parserBackend/topKFrames/frameScoreMargin/modalFamilyShareMargin/…); `ModalCompilationAmbiguity` (ambiguityType/message/candidateIds/severity/toDict()); `ModalCompilationResult` (modalIr/parserName/normalizedText/frameCandidates/selectedFrame/ambiguities/toDict()); `DeterministicModalCompiler` (compile(text)/compileAll(texts)/getStats()) | ✅ DONE |
| T-253 | P3 | Create `src/services/deontic-exports.ts` | `buildDeterministicParserCapabilityProfileRecord(norm)`; `buildDeterministicParserCapabilityProfileRecords(norms)`; `summarizeDeterministicParserCapabilityProfileRecords(records)`; `summarizeIrSlotProvenanceAuditRecords(records)`; `summarizePhase8QualityRecords(records)`; `buildPhase8QualitySummaryRecord(records)`; `summarizeProverSyntaxTargetCoverage(records)` | ✅ DONE |
| T-254 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint56.test.ts` | ✅ DONE — 35 tests (all pass) |

---

### Sprint 57 (Phase 57 — CEC Prover Core + Extended Rules + Specialized Rules + Prover Manager, P3) 🆕

> **Gap discovered by exhaustive scan:** `CEC/native/prover_core.py` (649L) + `CEC/native/prover_core_extended_rules.py` (1116L) + `CEC/native/inference_rules/specialized.py` (456L) + `CEC/provers/prover_manager.py` (444L) — none had TS equivalents.

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-255 | P3 | Create `src/services/cec-prover-core.ts` | 34 inference rules (8 core + 26 extended); `ProofResult` enum; `ALL_CEC_RULES` registry; `findApplicableCECRules()` | ✅ DONE |
| T-256 | P3 | Create `src/services/cec-specialized-rules.ts` | 5 specialized propositional rules; `ALL_SPECIALIZED_RULES`; `findApplicableSpecializedRules()` | ✅ DONE |
| T-257 | P3 | Create `src/services/cec-prover-manager.ts` | `ProverType`/`ProverStrategyKind` enums; `ProverConfig`; `UnifiedProofResult`; `ProverManager` (prove/proveParallel/selectBest/register/getStats) | ✅ DONE |
| T-258 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint57.test.ts` | ✅ DONE — 35 tests (all pass) |

---

### Sprint 58 (Phase 58 — Modal Autoencoder Loop + CEC ZKP Integration + DCEC Core Types, P3) 🆕

> **Gap found by exhaustive name scan:** `modal/autoencoder_loop.py` (776L), `CEC/native/cec_zkp_integration.py` (574L), `CEC/native/dcec_core.py` (1452L — key enums/types only).

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-259 | P3 | Create `src/services/modal-autoencoder-loop.ts` | `ModalAutoencoderLoopConfig`; `FrameLogicPatchValidation` (isValid/errors); `ModalAutoencoderLoopResult` (modalIr/residuals/patchValidations/confidence); `LegalModalAutoencoderLoop` (run(text)/runBatch(texts)/getStats()) | ✅ DONE |
| T-260 | P3 | Create `src/services/cec-zkp-integration.ts` | `ProvingMethod` enum (STANDARD/ZKP/HYBRID); `UnifiedCECProofResult` (isProved/method/zkpProof/proofTime/confidence); `ZKPCECProver` (prove(formula,axioms)/verifyZkp(proof,formula)/getStats()); `createHybridProver()` | ✅ DONE |
| T-261 | P3 | Create `src/services/dcec-core-types.ts` | `DeonticOperator`/`CognitiveOperator`/`LogicalConnective`/`TemporalOperator` enums; `Sort`/`Variable`/`Function`/`Predicate` type interfaces | ✅ DONE |
| T-262 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint58.test.ts` | ✅ DONE — 49 tests (all pass) |

---

### Sprint 59 (Phase 59 — FLogic Proof Cache + NL UCAN Compiler + Domain Vocab + NL Converter + Shadow Prover Wrapper + ZKP UCAN Bridge, P3) 🆕

> **Gap discovered by exhaustive name scan — 6 files with refs=0 or done=0.**

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-263 | P3 | Create `src/services/flogic-proof-cache.ts` | `FLogicCachedQueryResult` (query/result/cacheKey/timestamp); `FLogicProofCache` (get/set/clear/stats) wrapping LRU; `getCachedWrapper()` factory | ✅ DONE |
| T-264 | P3 | Create `src/services/nl-ucan-policy-compiler.ts` | `NLUCANCompilerResult` (text/ucans/capabilities/confidence); `NLUCANPolicyCompiler` (compile(text)/compileBatch(texts)/getStats()); `compileNlToUcanPolicy(text)` | ✅ DONE |
| T-265 | P3 | Create `src/services/domain-vocabulary.ts` | `DomainTerm` (term/synonyms/domain); `DomainVocabulary` abstract interface; `LegalVocabulary`/`MedicalVocabulary`/`TechnicalVocabulary` concretes; `DomainVocabularyManager` (register/lookup/expand) | ✅ DONE |
| T-266 | P3 | Create `src/services/cec-nl-converter.ts` | `ConversionResult` (formula/confidence/method); `NaturalLanguageConverter` (convert(text)/convertBatch(texts)/getStats()); `createEnhancedNlConverter()` | ✅ DONE |
| T-267 | P3 | Create `src/services/shadow-prover-wrapper.ts` | `ProverStatus` enum; `ProofTask` (formula/axioms/timeout/taskId); `ShadowProverWrapper` (submit(task)/getResult(taskId)/getStats()) | ✅ DONE |
| T-268 | P3 | Create `src/services/zkp-ucan-bridge.ts` | `ZKPCapabilityEvidence` (proof/capabilities/agentDid); `BridgeResult` (success/ucans/evidence); `ZKPToUCANBridge` (bridge(zkpProof,capabilities)/verify(evidence)/getStats()); `getZkpUcanBridge()` | ✅ DONE |
| T-269 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint59.test.ts` | ✅ DONE — 36 tests (all pass) |

---

### Sprint 60 (Phase 60 — Grammar Engine + DCEC Integration + Context Manager + CEC Proof Cache + DCEC Prototypes + TDFOL Performance Engine, P3) 🆕

> **Gap discovered by exhaustive scan — 6 files with done=0 in plan.**

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-270 | P3 | Create `src/services/cec-grammar-engine.ts` | `Category` enum; `GrammarRule`/`LexicalEntry`/`ParseNode`; `GrammarEngine` (addRule/addLexicalEntry/parse(text)/getCategories()); `CompositeGrammar` (merge grammars); `makeBinaryRule()`/`makeUnaryRule()` helpers | ✅ DONE |
| T-271 | P3 | Create `src/services/dcec-integration.ts` | `DCECParsingError`; `parseExpressionToToken(expr)`; `tokenToFormula(token)`; `parseDcecString(dcec)`; `validateFormula(formula)` | ✅ DONE |
| T-272 | P3 | Create `src/services/cec-context-manager.ts` | `EntityType` enum; `Entity` (id/type/mentions); `ContextState` (entities/discourse); `ContextManager` (updateContext/resolve/getEntities/reset()); `AnaphoraResolver` (resolve(text,context)); `DiscourseAnalyzer` (analyze(text)) | ✅ DONE |
| T-273 | P3 | Create `src/services/cec-proof-cache.ts` | `CECCachedProofResult` (formula/isProved/proof/cachedAt); `CachedTheoremProver` (prove(formula,axioms)/invalidate(formula)/getStats()); `getGlobalCachedProver()` | ✅ DONE |
| T-274 | P3 | Create `src/services/dcec-prototypes.ts` | `DCECPrototypeNamespace` (registerSort/registerPredicate/registerFunction/export()) | ✅ DONE |
| T-275 | P3 | Create `src/services/tdfol-performance-engine.ts` | `TDFOLPerformanceEngine` (benchmark(formula,axioms,reps)/profile(fn)/getReport()) — combined in `dcec-prototypes.ts` | ✅ DONE |
| T-276 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint60.test.ts` | ✅ DONE — 31 tests (all pass) |

---

### Sprint 61 (Phase 61 — OTel Integration + Syntax Tree + Language Detector + DCEC Namespace + NL Policy Compiler, P3) 🆕

> **5 newly discovered untracked files (refs=0 in plan).**

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-277 | P3 | Create `src/services/otel-integration.ts` | `SpanStatus`/`EventType` enums; `SpanEvent`/`Span` (start/end/addEvent/setAttribute/toDict()); `Trace` (addSpan/getSpan); `OTelTracer` (startSpan/endSpan/getTrace/getStats()); `setupOtelTracer(serviceName)` | ✅ DONE |
| T-278 | P3 | Create `src/services/cec-syntax-tree.ts` | `NodeType` enum; `SyntaxNode` (type/value/children/addChild/findByType()/toDict()); `SyntaxTree` (root/insert/find/traverse) | ✅ DONE |
| T-279 | P3 | Create `src/services/cec-language-detector.ts` | `Language` enum (EN/DE/FR/ES/…); `LanguageDetector` (detect(text)/detectBatch(texts)/getConfidence(text,lang)) | ✅ DONE |
| T-280 | P3 | Create `src/services/cec-dcec-namespace.ts` | `DCECNamespace` (addSort/addPredicate/addFunction/addConstant/lookup/export()); `DCECContainer` (getNamespace/merge/toDict()) | ✅ DONE |
| T-281 | P3 | Create `src/services/cec-nl-policy-compiler.ts` | `CompilationResult` (clauses/formula/confidence/errors); `compileDcecToClause(formula)`; `NLToPolicyCompiler` (compile(text)/compileBatch(texts)/getStats()) — combined in `cec-dcec-namespace.ts` | ✅ DONE |
| T-282 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint61.test.ts` | ✅ DONE — 38 tests (all pass) |

---

### Sprint 62 (Phase 62 — Enhanced Grammar Parser + Temporal Deontic API + NLP Predicate Extractor + Profiling Utils + Proof Optimization + Resolution Rules, P3) 🆕

> **6 untracked files discovered — refs=0 in plan, no TS match.**

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-283 | P3 | Create `src/services/enhanced-grammar-parser.ts` | `Category` enum; `Terminal`/`GrammarRule`/`ParseTree`/`EarleyState`; `EnhancedGrammarParser` (parse(text)/addRule()/addTerminal()/getParseForest()) | ✅ DONE |
| T-284 | P3 | Create `src/services/temporal-deontic-api.ts` | `TemporalContext` (start/end/duration); `TemporalDeonticClause` (modality/action/agent/temporalCtx); `TemporalDeonticAPI` (extract(text)/validate(clause)/normalise(clause)) | ✅ DONE |
| T-285 | P3 | Create `src/services/nlp-predicate-extractor.ts` | `extractPredicatesNlp(text)`; `extractSemanticRoles(text)`; `normalise Predicate(text)` — regex-based (no spaCy) | ✅ DONE |
| T-286 | P3 | Create `src/services/cec-profiling-utils.ts` | `ProfilingResult` (operation/durationMs/peakMemMb); `Bottleneck` (operation/avgMs/count); `FormulaProfiler` (profile(fn,name)/getResults()/reset()); `BottleneckAnalyzer` (analyze(results)/topN(n)); `ProfilingReporter` (report(results)) | ✅ DONE — combined in `cec-resolution-rules.ts` |
| T-287 | P3 | Create `src/services/proof-optimization.ts` | `PruningStrategy` enum; `ProofNode` (formula/children/isClosed()); `OptimizationMetrics`; `ProofTreePruner` (prune(tree,strategy)); `RedundancyEliminator` (eliminate(steps)) | ✅ DONE — combined in `cec-resolution-rules.ts` |
| T-288 | P3 | Create `src/services/cec-resolution-rules.ts` | 6 resolution rules: `ResolutionRule`, `UnitResolutionRule`, `FactoringRule`, `SubsumptionRule`, `CaseAnalysisRule`, `ProofByContradictionRule`; `ALL_RESOLUTION_RULES` registry | ✅ DONE |
| T-289 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint62.test.ts` | ✅ DONE — 37 tests (all pass) |

---

### Sprint 63 (Phase 63 — ErgoAI Wrapper + FLogic ZKP + Prometheus Metrics + Base Parser + Error Handling + NL Context, P3) 🆕

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-290 | P3 | Create `src/services/flogic-ergoai-wrapper.ts` | `ErgoAIConfig`; `ErgoAIWrapper` (query/queryBatch/isAvailable/getStats); `findErgoBinary()/lazyInstallErgo()` | ✅ DONE |
| T-291 | P3 | Create `src/services/flogic-zkp-integration.ts` | `FLogicProvingMethod` enum; `ZKPFLogicResult`; `ZKPFLogicProver` (prove/getStats) — combined in `flogic-ergoai-wrapper.ts` | ✅ DONE |
| T-292 | P3 | Create `src/services/metrics-prometheus.ts` | `CircuitBreakerState` enum; `CallMetrics`; `PrometheusMetricsCollector` (record/getMetrics/format/reset); `getPrometheusCollector()` — in `cec-sprint63-utils.ts` | ✅ DONE |
| T-293 | P3 | Create `src/services/cec-base-parser.ts` | `ParseResult`; abstract `BaseParser`; `getParser(language)` — in `cec-sprint63-utils.ts` | ✅ DONE |
| T-294 | P3 | Create `src/services/cec-error-handling.ts` | `handleProofError/handleParseError/withErrorContext/safeCall/formatErrorMessage/validateNotNull` — in `cec-sprint63-utils.ts` | ✅ DONE |
| T-295 | P3 | Create `src/services/tdfol-nl-context.ts` | `NLContext/makeTDFOLEntity/ContextResolver` — in `cec-sprint63-utils.ts` | ✅ DONE |
| T-296 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint63.test.ts` | ✅ DONE — 41 tests (all pass) |

---

### Sprint 64 (Phase 64 — TDFOL Forward Chaining Strategy + NL Preprocessor + Ambiguity Resolver + Semantic Normalizer + Text to FOL + Legal Text to Deontic, P3) 🆕

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-297 | P3 | Create `src/services/tdfol-forward-chaining.ts` | `ForwardChainingStrategy` (prove/getStats) — combined in `sprint64-modules.ts` | ✅ DONE |
| T-298 | P3 | Create `src/services/tdfol-nl-preprocessor.ts` | `ProcessedDocument`; `preprocess(text)` — combined in `sprint64-modules.ts` | ✅ DONE |
| T-299 | P3 | Create `src/services/cec-ambiguity-resolver.ts` | `AmbiguityResolver`/`SemanticDisambiguator`/`StatisticalDisambiguator` — combined in `sprint64-modules.ts` | ✅ DONE |
| T-300 | P3 | Create `src/services/flogic-semantic-normalizer.ts` | `SemanticNormalizer`/`getGlobalNormalizer()` — combined in `sprint64-modules.ts` | ✅ DONE |
| T-301 | P3 | Create `src/services/fol-text-to-fol.ts` | `convertTextToFol`/`extractTextFromDataset`/`getQuantifierDistribution` — combined in `sprint64-modules.ts` | ✅ DONE |
| T-302 | P3 | Create `src/services/deontic-legal-text.ts` | `legalTextToDeontic`/`extractLegalTextFromDataset`/`convertResultToLegacyFormat` — combined in `sprint64-modules.ts` | ✅ DONE |
| T-303 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint64.test.ts` | ✅ DONE — 28 tests (all pass) |

---

### Sprint 65 (Phase 65 — IPFS Proof Storage + Problem Parser + Verification Utils + Grammar Loader + DCEC Cleaning + Deontic Reasoning Utils + ZKP Witness Manager + E-Prover Adapter, P3) 🆕

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-304 | P3 | Create `src/services/sprint65-storage-parsers.ts` | ✅ DONE — `IPFSProofStorage` (store/retrieve/list/delete/getDefaultProofStorage()); `TPTPFormula`/`TPTPParser`/`ProblemParser` (parse(text)/parseFile(path)); `GrammarConfig`/`GrammarLoader` (load/get/getGrammarLoader()) |
| T-305 | P3 | Create `src/services/sprint65-utils.ts` | ✅ DONE — `getBasicAxioms()`/`getBasicProofRules()`/`validateFormulaSyntax(formula)`/`parseProofSteps(text)`/`areContradictory(f1,f2)`; `stripWhitespace()`/`stripComments()`/`consolidateParens()`/`checkParens()`/`getMatchingCloseParen()`; `DeonticPatterns`/`extractKeywords(text)`/`calculateTextSimilarity(a,b)`/`areEntitiesSimilar(e1,e2)`/`areActionsSimilar(a1,a2)`; `WitnessManager` (generateWitness/verifyWitness/getStats()); `EProverProofResult`/`EProverAdapter` (prove/isAvailable/getStats()); `checkEproverInstallation()` |
| T-306 | P3 | Write 10+ tests | ✅ DONE — 47 tests (all pass) in `test/mcp-plus-plus/wasm-prover-sprint65.test.ts` |

---

### Sprint 66 (Phase 66 — DCEC Types + TPTP Utils + DCEC-to-UCAN Bridge + Strategy Selector + Vampire Adapter + Utility Monitor + Lazy Installer, P3) 🆕

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-307 | P3 | Create `src/services/sprint66-dcec-types.ts` | ✅ DONE — `DeonticOperator`/`CognitiveOperator`/`LogicalConnective`/`TemporalOperator` enums; `Sort`/`Variable`/`Function`/`Predicate` types; `formulaToTPTP()`/`createTPTPProblem()`/`TPTPConverter`; `DenyCapability`/`DCECToUCANMapping`/`DCECToUCANBridge`/`BridgeResult` |
| T-308 | P3 | Create `src/services/sprint66-prover-utils.ts` | ✅ DONE — `StrategySelector`; `VampireProofResult`/`VampireAdapter`/`checkVampireInstallation()`; `UtilityMonitor`/`trackPerformance()`/`withCaching()`/`getGlobalStats()`/`clearGlobalCache()`/`resetGlobalStats()`; `normalizePoverName()`/`findExecutable()`/`lazyInstallProver()`/`isLazyInstallEnabled()` |
| T-309 | P3 | Write 10+ tests | ✅ DONE — 39 tests (all pass) in `test/mcp-plus-plus/wasm-prover-sprint66.test.ts` |

---

### Sprint 67 (Phase 67 — Groth16 Backup + CEC Delegate + Expansion Rules + NLP Types + Crypto Utils, P3) 🆕

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-310 | P3 | Create `src/services/sprint67-groth16-cec.ts` | ✅ DONE — `Groth16Backend`/`R1CSCircuit`/`ProvingKey`/`VerifyingKey`; `CECDelegateStrategy`; `AndExpansionRule`/`OrExpansionRule`/`ImpliesExpansionRule`/`IffExpansionRule`/`NotExpansionRule`/`getAllExpansionRules()`/`selectExpansionRule()` |
| T-311 | P3 | Create `src/services/sprint67-nlp-types.ts` | ✅ DONE — `getPortugueseDeonticKeywords()`/`PortugueseClause`/`PortugueseParser`; `DeonticModality`/`ConflictType`/`DeonticStatement`/`DeonticConflict`; `FLogicStatus`/`FLogicFrame`/`FLogicClass`/`FLogicQuery`/`FLogicOntology` |
| T-312 | P3 | Create `src/services/sprint67-crypto-utils.ts` | ✅ DONE — `normalizeText()`/`canonicalizeTheorem()`/`hashTheorem()`/`theoremHashHex()`; `isModuleAvailable()`/`importOptionalModule()`/`FeatureDetector`; `RateLimiter`/`getRateLimiter()`/`rateLimit()`; `VKRegistry`/`VKRegistryEntry`/`computeVkHash()`; `HornAxiom`/`parseTdfolV1Axiom()`/`evaluateTdfolV1Holds()`/`deriveTdfolV1Trace()` |
| T-313 | P3 | Write 10+ tests | ✅ DONE — 56 tests (all pass) in `test/mcp-plus-plus/wasm-prover-sprint67.test.ts` |

---

### Sprint 68 (Phase 68 — Prover Wrappers + Ethereum Bridge + Utility Types, P3) 🆕

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-314 | P3 | Create `src/services/sprint68-prover-wrappers.ts` | ✅ DONE — `ProofResult` enum/`ProofAttempt`/`TalosWrapper`; `ConversionResult`/`EngDCECWrapper`; `DCECStatement`/`DCECLibraryWrapper`; `ZKPVerifier` |
| T-315 | P3 | Create `src/services/sprint68-eth-bridge.ts` | ✅ DONE — `normalizeBytes32Hex()`/`RegisterVKPayload`/`buildRegisterVkPayload()`; `OnchainClient`/`ProverBackend`/`OnchainPipelineResult`/`runOffchainToOnchainPipeline()`; `ContractArtifact`/`loadContractArtifact()`; `hashTextToFieldSha256()`/`packPublicInputsForEvm()` |
| T-316 | P3 | Create `src/services/sprint68-utils-types.ts` | ✅ DONE — `StatementRecord`/`SessionMetadata`; `BridgeCapability`/`ConversionStatus`/`BridgeMetadata`/`BridgeConfig`/`ProverRecommendation`; `validateText()`/`validateFormula()`/`InputValidator`; `LogicTranslationTarget`/`TranslationResult`/`AbstractLogicFormula`; `TDFOLProofResult`/`getGlobalProofCache()`/`clearGlobalProofCache()` |
| T-317 | P3 | Write 10+ tests | ✅ DONE — 47 tests (all pass) in `test/mcp-plus-plus/wasm-prover-sprint68.test.ts` |

---

### Sprint 69 (Phase 69 — EVM Harness + sprint63 false-positive audit, P3) 🆕

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-318 | P3 | Add `packPublicInputsUint256()` + `validateUint256Array()` to `src/services/sprint68-eth-bridge.ts` | ✅ DONE — evm_harness.py (49L) ported: `packPublicInputsUint256()`/`validateUint256Array()` |
| T-319 | P3 | Audit sprint63 false positives (metrics_prometheus, base_parser, tdfol_nl_context) | ✅ DONE — confirmed already ported in `cec-sprint63-utils.ts` as `PrometheusMetricsCollector`/`BaseParser`/`NLContext`/`ContextResolver` |
| T-320 | P3 | Remaining small files (api_server, unixfs_integration, phase7_complete_integration, enhanced_graphrag_integration) | ✅ DONE — confirmed as server bootstrap / lazy-load shims with no standalone library APIs |

---

### Sprint 70 (Phase 70 — Close deferred TODOs in acceleration service layer, P3) 🆕

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-321 | P3 | Implement deferred TODOs in `src/services/resource-pool.ts` | ✅ DONE — Pre-allocation in `initialize(preAllocate?)`; queue-based wait (configurable `acquireTimeoutMs`); `checkResourceHealth()`/`getPoolStats()` fault-tolerance; `setInterval.unref()` |
| T-322 | P3 | Implement deferred TODOs in `src/services/model-streamer.ts` | ✅ DONE — `ExecutionEngine` interface replaces `any`; `generateTokenStream()` dispatches to real engine with adaptive-batch + KV-cache hints |
| T-323 | P3 | Implement deferred TODOs in `src/services/hardware-abstraction.ts` | ✅ DONE — `selectOptimalBackend()` uses capability matching; `executeModel()` dispatches to WebGPU/WebNN/WASM/CPU backends |
| T-324 | P3 | Implement deferred TODOs in `src/services/browser-acceleration.ts` | ✅ DONE — `initialize()` calls `hardwareAbstraction.initialize()`; `selectOptimalBackend()` and `getOptimizationHints()` added |
| T-325 | P3 | Write 10+ tests | ✅ DONE — 21 tests (all pass) in `test/mcp-plus-plus/wasm-prover-sprint70.test.ts` |

---

### Sprint 71 (Phase 71 — WebGPU Optimizer + MCP Client resource type, P3) 🆕

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-326 | P3 | Close deferred TODOs in `src/services/webgpu-optimizer.ts` | ✅ DONE — `GPUDevice`/`GPUShaderModule`/`GPUCompilationInfo` stubs replace `any`; `getCompilationInfo()` error-checking enabled; browser-specific WGSL patches; `createQuantizationPipeline()`; `optimizeComputePipelineDescriptor()`; `getCacheSize()` |
| T-327 | P3 | Add `resource` type support to `runCommand()` in `src/services/mcpClient.ts` | ✅ DONE — resource-type messages mapped to text blocks with URI; `// TODO: Support type == resource` removed |

---

### Sprint 72 (Phase 72 — CacheManager + ExecutionEngine + FAISSIndex + DataLake deferred TODOs, P3) 🆕

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-328 | P3 | Implement deferred TODOs in `src/storage/cache/cache-manager.ts` | ✅ DONE — LRU eviction (`maxSize`), periodic TTL sweep (`setInterval.unref()`), `getStats()` with hit/miss tracking |
| T-329 | P3 | Implement deferred TODOs in `src/core/execution.ts` | ✅ DONE — `HardwareBackend`/`WebGPUOptimizer` typed imports, `ModelData`/`TensorData` types, `executeWebGPU/WebNN/WASM/CPU()` stubs |
| T-330 | P3 | Implement deferred TODOs in `src/vector/faiss-index.ts` | ✅ DONE — L2/cosine/innerproduct metrics; update-on-duplicate semantics; removed all `any` |
| T-331 | P3 | Implement deferred TODOs in `src/connectors/data-lake.ts` | ✅ DONE — `GraphRAGDatabaseContract` interface; `connect/disconnect` state; `partitionForQuery`; `getPartitionData()` |
| T-332 | P3 | Write 10+ tests | ✅ DONE — 24 tests in `test/mcp-plus-plus/wasm-prover-sprint72.test.ts` |

---

### Sprint 73 (Phase 73 — GraphRAG DB + WebNN Server + VFS + Delegator + IPFS Command, P3) 🆕

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-333 | P3 | Close deferred TODOs in `src/inference/graph-rag-database.ts` | ✅ DONE — Typed `GraphNode`/`GraphEdge`/`VectorStore`/`DocumentStore`/`EmbeddingModel` interfaces; in-memory impls; `extractSimpleEntities()`; `query()` with BFS graph traversal; `reindex()`/`documentCount()` |
| T-334 | P3 | Close deferred TODOs in `src/inference/webnn-server.ts` | ✅ DONE — `Tensor`/`CompiledModel`/`Device`/`DeviceManager` typed interfaces; `attachRAGDatabase()`/`queryRAG()` GraphRAG integration |
| T-335 | P3 | Close deferred TODOs in `src/storage/virtual-filesystem.ts` | ✅ DONE — read-only backend check; per-key cache invalidation in `delete()`; `mkdir()`/`stat()`/`move()`/`copy()` added |
| T-336 | P3 | Close deferred TODOs in `src/tasks/delegation/delegator.ts` | ✅ DONE — `unregisterWorker()` re-delegates tasks; `handleHeartbeat()`/`startHeartbeatWatchdog()` added; `announceWorkerJoined()`/`notifyWorkerAssignment()` network stubs |
| T-337 | P3 | Close deferred TODOs in `src/cli/commands/ipfsCommand.ts` | ✅ DONE — `addContent()`/`getContent()`/`pinContent()` use Kubo HTTP API with graceful fallback; `addTaskIntegration()` hooks program post-action |
| T-338 | P3 | Write 10+ tests | ✅ DONE — 24 tests in `test/mcp-plus-plus/wasm-prover-sprint73.test.ts` |

---

### Sprint 74 (Phase 74 — spaCy-WASM NLP bridge, sedbytes/spacy-wasm integration, P3) 🆕

Replaces the placeholder `extractSimpleEntities()` regex heuristic with a full spaCy 3.4 + Pyodide WASM pipeline matching the Python `_extract_predicates_spacy()` reference in `ipfs_datasets_py/logic/fol/utils/nlp_predicate_extractor.py`.

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-339 | P3 | Create `src/services/spacy-wasm-nlp.ts` | ✅ DONE — `SpacyWasmNlp` class: lazy Pyodide init, micropip install of spaCy 3.4 WASM packages from `sedbytes/spacy-wasm`, `extract(text)→SpacyPredicates` (nouns/verbs/adjs/entities/relations); `regexFallbackExtract()` for offline/test; `extractPredicatesNlp()` convenience export; env-var config (`SPACY_WASM_PACKAGES_BASE_URL`, `SPACY_WASM_DISABLE`) |
| T-340 | P3 | Wire `SpacyWasmNlp` into `src/inference/graph-rag-database.ts` | ✅ DONE — `GraphRAGDatabase` accepts `spacyNlp?: SpacyWasmNlp` in constructor; `addDocument()` uses `spacyNlp.extract()` with typed `SpacyEntity` graph edges instead of regex heuristic |
| T-341 | P3 | Write 10+ tests | ✅ DONE — 18 tests in `test/mcp-plus-plus/wasm-prover-sprint74.test.ts` (Pyodide falls back gracefully to regex in test env, all 18 pass) |

---

### Sprint 75 (Phase 75 — Logger + Quantization + Tensor + Goose MCP + Swarm Inference + IPLD Graph, P3) 🆕

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-342 | P3 | Close deferred TODOs in `src/utils/logger.ts` | ✅ DONE — `LogLevel` enum (DEBUG/INFO/WARN/ERROR/NONE); `setLevel()`/`addTransport()`; `LOG_LEVEL` env var; log-level filtering |
| T-343 | P3 | Close deferred TODOs in `src/utils/quantization.ts` | ✅ DONE — `quantizeTensor()` (int8 symmetric + uint8 asymmetric); `dequantizeTensor()` inverse |
| T-344 | P3 | Close deferred TODOs in `src/ml/tensor/tensor.ts` | ✅ DONE — shape validation; `reshape()`/`slice()`/`add()`/`multiply()`/`scale()`/`transpose()`/`matmul()`/`clamp()` |
| T-345 | P3 | Close deferred TODOs in `src/integration/bridges/goose-mcp.ts` | ✅ DONE — real HTTP fetch + `AbortController` timeout in `initialize()` and `call()`; graceful mock fallback |
| T-346 | P3 | Close deferred TODOs in `src/inference/swarm-inference.ts` | ✅ DONE — typed `InferenceTask`/`TaskResult`; capability-aware load-balanced task assignment; fault-tolerance retry; type-polymorphic aggregation; provenance array |
| T-347 | P3 | Close deferred TODOs in `src/graph/ipld-knowledge-graph.ts` | ✅ DONE — `IPFSClientLike` typed interfaces; `crypto.randomUUID()` node IDs; `dag-cbor` codec options; `evictFromCache()`/`updateNode()` |
| T-348 | P3 | Fix LRU timestamp collision in `src/storage/cache/cache-manager.ts` | ✅ DONE — monotonic counter replaces `Date.now()` for `lastAccessed` |
| T-349 | P3 | Write 10+ tests | ✅ DONE — 33 tests in `test/mcp-plus-plus/wasm-prover-sprint75.test.ts` |

---

### Sprint 65 (Phase 65 — IPFS Proof Storage + Problem Parser + Logic Verification Utils + Grammar Loader + DCEC Cleaning + Witness Manager + E-Prover Adapter + Deontic Reasoning Utils, P3) 🆕

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-304 | P3 | Create `src/services/sprint65-modules.ts` (combined) | All 8 modules: `IPFSProofStorage`; `TPTPParser`/`ProblemParser`; `getBasicAxioms()`/`validateFormulaSyntax()`/`areContradictory()`; `GrammarLoader`; DCEC string cleaning fns; `WitnessManager`; `EProverAdapter`; `DeonticPatterns`/`calculateTextSimilarity()`/`areEntitiesSimilar()` |
| T-305 | P3 | Write 10+ tests | `test/mcp-plus-plus/wasm-prover-sprint65.test.ts` |

---

## 9. Gap Closure Summary 🏁

All Python files in `ipfs_datasets_py/logic/` now have TypeScript equivalents in swissknife.
Sprint 56 (2026-07-02) closes the final two large deferred files.

| Metric | Value |
|---|---|
| Total sprints | 56 (T-01 → T-254) |
| TypeScript service files created | 100+ |
| Test suites | 100/100 passing |
| Tests passing | 2 156 |
| Python modules ported | All files in `ipfs_datasets_py/logic/` |

## 8. Prover Capability Matrix

| Formula Class | Python Reference | Phase 1 (Z3 WASM) | Phase 3 (CVC5) | Phase 4 (Coq) | Phase 5 (Lean 4) |
|---|---|---|---|---|---|
| Propositional deontic | Z3 | ✅ Z3 WASM | ✅ | ✅ | ✅ |
| First-order (∀, ∃) | Z3/CVC5 | ✅ Z3 WASM | ✅ | ✅ | ✅ |
| Linear temporal (◊, □) | Z3/TDFOL native | ✅ TdfolProverBridge (Sprint 10) | ✅ | partial | partial |
| Deontic modal (P/F/O) | TDFOL tableaux | ✅ DcecProverBridge (Sprint 9) | ✅ | ✅ Coq | ✅ Lean |
| Higher-order (λ, Π) | Lean 4 / Coq | ✅ _tryCoqOrLean4() (Sprint 10) | ❌ | ✅ Coq | ✅ Lean 4 |
| Inductive types | Coq | ❌ | ❌ | ✅ Coq | ✅ Lean 4 |
| ZK proof-carrying | Lurk/Sphinx | ❌ | ❌ | ❌ | ❌ (Phase 6) |

---

## 9. Dependency Notes

### z3-solver (required for Phase 1)

```json
// swissknife/package.json addition
"z3-solver": "^4.16.0"
```

Requires `SharedArrayBuffer` in browsers (set `Cross-Origin-Opener-Policy: same-origin`
and `Cross-Origin-Embedder-Policy: require-corp` headers).  Node.js: no header required.

### @isl-lang/solver-z3-wasm (option for Phase 3)

Alternative SMT-LIB2 interface that may serve as CVC5 compatibility shim.

### jscoq (Phase 4)

```html
<!-- CDN approach (browser only) -->
<script src="https://cdn.jsdelivr.net/npm/jscoq@0.17.1/dist/jscoq.bundle.js"></script>
```

npm install approach for Node.js testing requires `--experimental-vm-modules`.

### lean4web (Phase 5)

No npm package — must be cloned and built, or accessed via WebSocket to a lean4web server.
Evaluate whether a lean subprocess (`lean --server`) is simpler for Node.js.

---

## 10. Acceptance Criteria for Sprint 1 Done

1. `swissknife/src/services/provers/z3-wasm-bridge.ts` exists and exports `Z3WasmBridge`.
2. `swissknife/src/services/mcp-wasm-prover-hub.ts` exists and exports `WasmProverHub`.
3. `swissknife/src/services/mcp-proof-cache.ts` exists and exports `ProofCache`.
4. `npx jest --rootDir . test/mcp-plus-plus/` passes with ≥ 510 tests (492 existing + ≥ 18 new).
5. `RemoteDeonticEngine.prove()` calls `WasmProverHub` first; remote call only when local returns unknown.
6. Latency for a simple deontic consistency check is < 200ms after first WASM load.
7. `mcp++ conformance` output includes a `Provers: z3-wasm (loaded)` line.
8. `WasmProofResult` schema added to `Mcp-Plus-Plus/tests-ts/src/models.ts` with conformance vector.

---

## 11. Implementation Status & Python-Reference Parity Audit (2026-07-01)

> Concurrent-review pass. Sprint 1 (Phase 1) has landed and Sprint 2 / Phase 8
> are in flight. The findings below come from auditing the committed/in-flight
> TypeScript port against the Python reference this document names as the source
> of truth. Line numbers are as of this audit.

### 11.1 Implementation status snapshot

| Item | State | Evidence |
|---|---|---|
| Phase 1 prover layer | **Committed** (swissknife `3bb99e1`) | `provers/{prover-types,mcp-proof-cache,z3-wasm-bridge}.ts`, `mcp-wasm-prover-hub.ts`, `test/mcp-plus-plus/wasm-prover.test.ts`, `z3-solver@^4.16.0` in `package.json` |
| Phase 8 local-first wiring | **Committed** (swissknife `83cf9db`) | `mcp-remote-deontic-engine.ts` — `checkPolicyConsistencyRemote(policy, engine, localHub?)` runs a Z3 WASM pre-check before the remote round-trip; `RemoteConsistencyResult.localProver` added |
| Sprint 2 (CVC5 + SMT-LIB2) | **Committed** (swissknife `83cf9db`) | `provers/cvc5-wasm-bridge.ts`, `provers/smt2-serializer.ts`, `test/mcp-plus-plus/wasm-prover-sprint2.test.ts` |
| Sprint 3+4 (Coq + Lean 4) | **Committed** (swissknife `ba030f5`) | `provers/{coq-jscoq-bridge,lean4-wasm-bridge,deontic-to-coq,deontic-to-lean4}.ts`, `test/mcp-plus-plus/wasm-prover-sprint3-4.test.ts` |
| F1 fix (`ProofReason` + `'unsat'`) | **Committed** (swissknife `583bf5d`) | resolves TS2367 in `isDecided()` — see F1 |
| MCP++ spec schema (`WasmProofResult`) | **Committed** (Mcp-Plus-Plus `dacb456`) | `tests-ts/src/models.ts` (475 lines): `WasmProofResultSchema`, `ProofReasonSchema` (7 values incl. `unsat`), `WasmProverIdSchema` + conformance vector + 9 tests |
| Remote fallback tool | **Present in source** | `ipfs_datasets_py/.../logic_tools/tdfol_prove_tool.py` exists; live MCP servers (18077–18079) were **down** at audit time, so end-to-end fallback was not runtime-verified this pass |
| All 8 referenced Python provers | **Confirmed to exist** | `logic/external_provers/{smt/z3_prover_bridge,smt/cvc5_prover_bridge,interactive/coq_prover_bridge,interactive/lean_prover_bridge,neural/symbolicai_prover_bridge,prover_router,proof_cache,formula_analyzer}.py` |

### 11.2 Findings (source-cited)

**F1 — `ProofReason` is missing `'unsat'`; `isDecided()` fails to type-check (BLOCKER — ✅ RESOLVED 2026-07-01, swissknife `583bf5d`).**
`prover-types.ts` declares `ProofReason = 'proved' | 'refuted' | 'sat' | 'unknown' | 'timeout' | 'error'`, but `isDecided()` (line 63) compares `r.reason === 'unsat'`. Because `'unsat'` is not in the union, `tsc` reports:
```
src/services/provers/prover-types.ts(63,83): error TS2367: This comparison appears to
be unintentional because the types '"unknown" | "timeout" | "error"' and '"unsat"' have no overlap.
```
`wasm-prover.test.ts` masks this by casting `['proved','refuted','sat','unsat'] as ProofReason[]`.
This is a genuine parity gap, not a stray typo: the Python reference emits `reason="unsat"` (e.g. `smt/z3_prover_bridge.py`, 3 occurrences) and its `Z3ProofResult` docstring lists the reason vocabulary as `sat/unsat/unknown/timeout/error` (z3_prover_bridge.py:91). The port renamed the "valid/negation-unsat" case to `'proved'`/`'refuted'` but left `'unsat'` referenced.
**Fix (1 line, keeps the existing test green and restores Python parity):**
```ts
export type ProofReason =
  | 'proved' | 'refuted' | 'sat' | 'unsat' | 'unknown' | 'timeout' | 'error';
```
**Resolution:** applied as swissknife `583bf5d` — `'unsat'` inserted between `'sat'` and `'unknown'` in the `ProofReason` union. A scoped `tsc --noEmit` now reports no `TS2367` for `prover-types.ts` (only the pre-existing `TS6305` dist-staleness notice, which is repo-wide build-artifact noise unrelated to this source). The test's `as ProofReason[]` cast was left in place — it is owned by the concurrent implementer and is now merely redundant, not load-bearing.

**F2 — `ProverStrategy` is missing `MOST_CAPABLE` (and `AUTO`) (⚠️ REASSESSED 2026-07-01 → see §11.4: obviated by the shipped router design; no code change recommended).**
Python `ProverStrategy` (prover_router.py:31–37) = `AUTO, FASTEST, MOST_CAPABLE, PARALLEL, SEQUENTIAL`. The port (`prover-types.ts:83`) = `'FASTEST' | 'PARALLEL' | 'SEQUENTIAL' | 'REMOTE'`. Adding `'REMOTE'` for local-first is reasonable, but `MOST_CAPABLE` is dropped — and task **T-16** ("Wire CVC5 into router … Available as MOST_CAPABLE fallback") and §2.1 both depend on it. Recommend widening to `'AUTO' | 'FASTEST' | 'MOST_CAPABLE' | 'PARALLEL' | 'SEQUENTIAL' | 'REMOTE'` so the CVC5 router being written now has a strategy to select the more-capable SMT backend.

**F3 — `FormulaClass` collapses Python's `FormulaType` (informational).**
Python `FormulaType` (formula_analyzer.py:23–31) = `PURE_FOL, MODAL, TEMPORAL, MIXED_MODAL, PROPOSITIONAL`. The port `FormulaClass` = `propositional | fol | temporal | higher_order`. `MODAL`/`MIXED_MODAL` have no direct port and `higher_order` has no Python `FormulaType` counterpart (it maps loosely to `FormulaComplexity`). Acceptable simplification for routing, but deontic `P/F/O` formulas are `MODAL` in the reference — worth a comment so the classifier's temporal-vs-modal routing intent stays clear.

**F4 — File-location / spec-path drift vs this plan (housekeeping).**
- `ProofCache` shipped at `src/services/provers/mcp-proof-cache.ts`, whereas §6/§10 name `src/services/mcp-proof-cache.ts`. Harmless, but update the acceptance criteria to the real path.
- Acceptance criterion §10.8 / **T-11** target `Mcp-Plus-Plus/tests-ts/src/models.ts` **now exists** (created in Mcp-Plus-Plus `dacb456`, 475 lines — `WasmProofResultSchema` etc.); this bullet is resolved. The broader MCP++ spec/conformance surface here also lives under `swissknife/docs/mcp-plus-plus/` (e.g. `CONFORMANCE_MATRIX.md`).

### 11.3 Recommendation

F1 is a build-breaker for a clean `tsc` — **now resolved** (swissknife `583bf5d`); the `as ProofReason[]` cast in the test can be dropped whenever the implementer next touches it. F2 unblocks the CVC5 routing currently being written and remains open. F3/F4 are documentation/robustness follow-ups. None require reworking the committed Phase 1 design — they are additive corrections to the type surface and the plan's path references.

### 11.4 Progress update — Sprints 2–4 landed; findings re-statused (2026-07-01, later)

Since the initial audit above, the implementer committed the rest of the local-prover
stack. Verified state on branch `merge/hallucinate-backend-into-main`:

| Sprint / item | swissknife commit | Files |
|---|---|---|
| Sprint 1 (Z3 + ProofCache) | `3bb99e1` | `provers/{prover-types,mcp-proof-cache,z3-wasm-bridge}.ts`, `mcp-wasm-prover-hub.ts` |
| Sprint 2 (CVC5 + SMT-LIB2 + Phase 8 remote wiring) | `83cf9db` | `provers/{cvc5-wasm-bridge,smt2-serializer}.ts`, `mcp-remote-deontic-engine.ts` |
| Deontic Interface Broker | `a3dc230` | broker + types |
| **F1 fix** (`ProofReason` + `'unsat'`) | `583bf5d` | `provers/prover-types.ts` |
| Sprint 3+4 (Coq + Lean 4 + translators) | `ba030f5` | `provers/{coq-jscoq-bridge,lean4-wasm-bridge,deontic-to-coq,deontic-to-lean4}.ts` |

**Finding re-status:**
- **F1 — RESOLVED** (`583bf5d`). Independently corroborated by the MCP++ spec commit
  `dacb456`, whose `ProofReasonSchema` enumerates exactly the 7 canonical values
  `proved/refuted/sat/unsat/unknown/timeout/error`.
- **F2 — OBVIATED by the shipped design (no change recommended).** The original finding
  assumed T-16 would select CVC5 via a `MOST_CAPABLE` *strategy* value. The delivered
  `WasmProverHub.checkPolicyConsistency` instead routes by **formula class + prover
  availability**: `classifyPolicy()` sends `temporal`/`higher_order` to the remote engine,
  `propositional`/`fol` to Z3, with **CVC5 as an availability fallback** inside `_tryZ3`
  (used when Z3 WASM is absent) and Coq/Lean 4 as interactive fallbacks when Z3/CVC5 return
  `unknown`/`error`. No code path consumes `MOST_CAPABLE`/`AUTO`, so adding them to the
  union would be dead members. Keep `ProverStrategy = 'FASTEST' | 'PARALLEL' | 'SEQUENTIAL'
  | 'REMOTE'` as-is; only add the Python names if a future strategy-driven selector is
  actually wired. (Downgraded from "blocker/needed" to "informational parity note.")
- **F3 — unchanged** (informational). The hub's `classifyPolicy()` still collapses Python's
  `FormulaType`; deontic `P/F/O` map through `propositional`/`fol`, and modal/temporal are
  routed remote-only — acceptable for local routing.
- **F4 — RESOLVED** (models.ts now exists, `dacb456`). ProofCache path note stands.

**Repository-integrity note (out of band, same session).** When verifying push-safety
against origin, the parent `merge/hallucinate-backend-into-main` had already been pushed to
`origin/main` (commit `0e325cf5`) with submodule gitlinks that were **not present on the
submodules' own origins** — a 3-level dangling cascade (`swissknife 83cf9db6`,
`Mcp-Plus-Plus dacb456`, `hallucinate_app dca450f` → nested `ipfs_accelerate_py 3612fe34`,
`ipfs_datasets_py f59cb5c5`), which breaks `git clone --recurse-submodules`. All were healed
non-destructively (fast-forward pushes to each submodule's `main`; swissknife published to a
new branch `heal/wasm-prover-integration` because its `main` had diverged from the prover
line at merge-base `844a19a`). Two follow-ups remain for the implementer: (1) reconcile
swissknife `main` by **merging** the diverged auto-doc commit `fd9d2c4` into the prover line
(a rebase would rewrite `83cf9db6` and re-dangle the parent), then bump the parent gitlink;
(2) make the auto-push push submodules recursively **before** the parent gitlink commit
(`git push --recurse-submodules=on-demand`) so the cascade cannot recur.

### 11.5 Behavioral verification — Sprint 5 landed; prover test suite green (2026-07-01, later still)

The implementer subsequently landed **Sprint 5** (swissknife `a32ace9` — Lurk/ZK proof-carrying
stub, `AuditEntry.prover_id`, prover CLI) and the MCP++ spec bump (`3bdf6c3`). The audit above
verified *shapes* against the Python reference; this section adds *behavioral* confirmation by
running the suite:

```
npx jest test/mcp-plus-plus/wasm-prover --config=config/jest/jest.config.cjs
→ Test Suites: 4 passed, 4 total
  Tests:       3 skipped, 98 passed, 101 total   (~194s)
```

- 4 suites cover Sprints 1–5: `wasm-prover.test.ts` (Z3 + ProofCache + hub routing),
  `-sprint2` (CVC5 / SMT-LIB2 serializer / Phase-8 local pre-check),
  `-sprint3-4` (Coq + Lean 4 deontic translators), `-sprint5` (Lurk stub + `prover_id`).
- The **3 skipped** tests are the live Z3 WASM path (34 MB artifact), gated behind
  `Z3_WASM_LIVE=1` — expected to skip in CI/offline runs.
- **F1 regression check passes:** the `parses "unsat" response` and CVC5 /
  `checkPolicyConsistencyRemote` cases are green, confirming the `ProofReason += 'unsat'` fix
  (`583bf5d`) integrated cleanly and broke nothing.

Net: the local-prover stack (Z3, CVC5, Coq, Lean 4, Lurk stub) is implemented **and passing**,
with parity to the Python `external_provers` reference confirmed at both the shape and behavior
level. Remaining open items are the two repository-integrity follow-ups in §11.4 (swissknife
`main` merge-reconcile + recursive submodule push), which are integration-plumbing, not prover
correctness.

### 11.6 Status update — Sprint 6/7/7b landed; DCEC gap discovered (2026-07-03)

Since §11.5, the following sprints landed (all committed to swissknife + parent repo bumped):

| Sprint | Commit | Scope | Test delta |
|---|---|---|---|
| Sprint 6 | `c0f85d8` | `NeuralProverBridge` (T-38/T-57): LLM sketch → local Lean4/Coq verify; `wasm-prover-sprint6.test.ts` (27 tests) | +27 |
| Sprint 7 | `c9b0181` | `Z3WasmBridge.createDeferred()` lazy-load (T-43); `wasm-prover-conformance.test.ts` cross-language (T-44); `.github/workflows/wasm-prover-gates.yml` CI gate (T-45) | +9 |
| Sprint 7b | `1602630` | `proveWithIx()`+`findIxCli()`+`ixBuildInstructions()` in `Lean4WasmBridge` (T-52); `AuditEntry.extra.zk_proof_cid` (T-53); `mcp++ provers` CLI (Sprint 7b); `wasm-prover-sprint7b.test.ts` (13 tests: 12 pass/1 skipped) | +13 |

**Full suite post-Sprint 7b:** `52/52 suites, 624/635 passing (11 skipped live-binary), 0 failing`.

**Open items (as of 2026-07-03):**
- `temporal` and `modal_deontic` formula classes still fall back to remote TDFOL → **Sprint 9 (T-58–T-62)** closes this with native `DcecProverBridge`.
- Lurk-beta real WASM (T-46–T-50) — blocked on building lurk-beta `--target wasm32-unknown-unknown`.
- multi-stark WASM bindings (T-55/T-56) — P3, waiting for upstream publication.
- Repository integrity: swissknife `main` merge-reconcile + `git push --recurse-submodules=on-demand` (§11.4 follow-ups) — still pending.

**Gap discovery:** Audit of `external/ipfs_datasets/ipfs_datasets_py/logic/CEC/` revealed an entire
DCEC/CEC prover layer not previously in scope — `dcec_core.py`, `prover_core.py` (649 lines, native
Python forward-chaining theorem prover with `ModusPonens`, `Simplification`, `DeonticProhibition`,
`DeonticPermission` inference rules), `cec_framework.py` (orchestration), `shadow_prover_wrapper.py`
(modal logic K/S4/S5). See §2.4 for the full inventory. Sprint 9 adds `DcecProverBridge` to close
this gap.

### 11.7 Independent verification at Sprint 75 + Python-reference parity audit (2026-07-03)

Independent (concurrent-reviewer) verification pass covering two dimensions the
prior §11.x notes had not: a full **behavioral** run of the prover test suite, and
a **source-level parity audit** of the TypeScript port against the Python
source-of-truth (`ipfs_datasets_py/logic/`).

**Behavioral — full prover jest suite (71 suites):** `npx jest
test/mcp-plus-plus/wasm-prover --config=config/jest/jest.config.cjs` →
**2253 passed / 2 failed / 11 skipped** (254 s; 11 skipped = live Z3 gated by
`Z3_WASM_LIVE=1`). Both failures diagnosed to root cause; **neither is a functional
regression**:
- **`wasm-prover-sprint72.test.ts` (LRU eviction) — FLAKY, now FIXED.** Passed
  3/3 in isolation; failed only under full-suite timing pressure. Root cause:
  `cache-manager.ts` used `Date.now()` (1 ms resolution) for `lastAccessed`, and
  `evictLRU()` breaks ties in insertion order, so under load `get('a')`/`set('b')`
  shared a millisecond and evicted the wrong entry. **Sprint 75 (`ed70d39`) fixes
  it exactly as recommended** — a monotonic `accessCounter` (`cache-manager.ts:20`,
  incremented in `get()`:48 and `set()`:61) replaces the timestamp, so ties are
  impossible. Re-verified green at Sprint 75.
- **`wasm-prover-sprint3-4.test.ts:303-314` (temporal policy) — STALE TEST,
  DETERMINISTIC, still red.** Asserts `reason==='unknown'` + `meta.skipped===
  'remote-only'`, but `mcp-wasm-prover-hub.ts:184-191` now routes
  `formulaClass==='temporal'` to `this.tdfol.checkPolicyConsistency` (Sprint 10
  TDFOL), which decides locally. The test predates TDFOL and was never updated;
  behavior legitimately **improved** (temporal is now locally provable). Fix =
  update the assertion to accept the locally-decided result (it is no longer
  remote-only). **This supersedes §11.6's "0 failing" line** — one deterministic
  stale-assertion test remains red at Sprint 75.

**Parity audit — TS port vs Python `logic/` reference (4 parallel source audits):**

| Domain | Python reference | Overall verdict |
|---|---|---|
| SMT / interactive / neural provers | `external_provers/{smt,interactive,neural}` | Faithful **subset** — implemented paths sound; PARTIAL/DIVERGENT on API breadth |
| TDFOL (types, rules, NL) | `TDFOL/`, `nl/` | PARTIAL — core grammar/vocab faithful; ~58% of inference rules, strategy framework, `substitute()` absent |
| DCEC / CEC + deontic core | `CEC/native/`, `deontic/` | PARTIAL/DIVERGENT — subsystems present; 3 competing TS type files; action-similarity + tableaux incomplete |
| Modal / legal / temporal domain | `modal/`, `integration/domain/` | PARTIAL — 2 modules DIVERGENT (RAG store, temporal_deontic_api); embeddings/SymbolicAI dropped |

**Framing:** the port is a deliberately-scoped, pragmatic **subset** aimed at the
SwissKnife deontic **policy-consistency** use case (Rounds 50–53). For that use
case it is sound (2253 tests green; F1 `'unsat'` fix regression-clean). It is **not**
a 1:1 general-purpose theorem-prover port — many advanced Python capabilities are
intentionally simplified (embeddings→keyword overlap, spaCy→regex, SymbolicAI/neural
confidence dropped, full TDFOL-AST→SMT→SMT2 shim without quantifiers) or deferred
(~42% of TDFOL inference rules, S5 tableaux symmetry axiom, propositional tableaux
α/β rules). Those **local-prover** gaps are functionally covered at runtime because
hard/temporal proofs are **delegated to the Python engine** over the Round-51
`RemoteDeonticEngine` (MCP++ libp2p), which is the authoritative prover.

**Cross-language interop hazards (the findings that DO matter, because Rounds 50–53
wire TS⇄Python over MCP++ and a shared IPFS proof cache):** these break
round-tripping/serialization even though each side is internally consistent —
- **Result field + unit drift:** `proof_time` (Python, **seconds**) vs
  `proof_time_ms` (TS, **ms**) — 1000× mismatch; `ProofResult`
  `is_valid/conclusion/method_used/time_taken` vs `proved/formula/method/timeMs`.
- **Deontic field name:** `DeonticFormula.action` (TS) vs `.proposition` (Python) —
  cross-cutting through query-engine + RAG store + any JSON serialization.
- **Agent notation:** Python `O[alice](φ)` vs TS `O(φ,alice)` — incompatible KB
  string forms.
- **Symbol codepoint:** EVENTUALLY `◊` U+25CA (Python) vs `◇` U+25C7 (TS) — string
  compare fails on any temporal formula.
- **Proof-cache key:** Python keys on `{formula, axioms, prover_name, prover_config}`;
  TS hub keys on `canonicalPolicyKey(policy)` only (excludes axioms + prover
  identity) — a shared cache would mis-key.
- **Missing enum members** (corroborate §11.2 F2/F3): `ProverStrategy`
  AUTO/MOST_CAPABLE, `FormulaType` MODAL/ARITHMETIC, `FormulaComplexity` (absent),
  `ProofStatus` DISPROVED/UNKNOWN/UNPROVABLE, `LegalDomain` (9 values), several
  `ConflictType` categories.

None of these block the shipped policy-consistency path; they are the reconciliation
backlog for anyone relying on byte-level Python⇄TS proof/KB/cache interchange. Full
per-module MATCH/PARTIAL/MISSING/DIVERGENT tables (≈50 findings, all source-cited)
were produced by the four audits and are summarized above.
