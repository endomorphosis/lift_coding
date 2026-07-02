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
| `logic/deontic/formula_builder.py` | Rich deontic formula builder (7019 lines) | Sprint 27+ | P3 |
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
| **Deontic IR / formula_builder** | ✅ `deontic/formula_builder.py` (7019 lines) | ⚠️ Only `Policy` type | **PARTIAL** — Sprint 27+ P3 |
| Remote fallback | N/A | ✅ `mcp-remote-deontic-engine.ts` | Keep as last-resort fallback |

**Current status (post Sprint 26):** 26+ modules; complete bridge layer (shared types/registry/ZKP attestation); complete TDFOL stack; all provers local; ZKP→UCAN; full NL→prover pipeline. Remaining P3: formula_builder (Sprint 27+).

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
