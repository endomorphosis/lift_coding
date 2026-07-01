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

### 3.5 Lurk / Nova WASM (argumentcomputer)

- **Source**: https://github.com/argumentcomputer/lurk-beta (`lurk-beta` has preliminary WASM support)
- **Yatima**: https://github.com/argumentcomputer/yatima — Lean4 → Lurk → ZK proof
- **Wasm.lean**: WASM runtime implemented in Lean4 (for verified WASM execution, not a prover)
- **Use case**: Proof-carrying code — generate a STARK proof that a Lean4 theorem holds, verify in JS
- **Status**: ⚠️ Research-stage; not production-ready but architecturally sound

### 3.6 Neural Prover (TypeScript equivalent)

- Current Python uses SymbolicAI (LLM-guided proof sketch + checker)
- TypeScript equivalent: Use swissknife's existing MCP++ connector to call an LLM tool, then verify the returned Lean/Coq tactic block locally

---

## 4. Gap Analysis vs Python Reference

| Feature | Python | SwissKnife (current) | Gap |
|---|---|---|---|
| Z3 SMT solving | ✅ Full (z3-python) | ❌ Remote only | HIGH — z3-solver npm exists |
| CVC5 SMT solving | ✅ Full (cvc5-python) | ❌ Remote only | MED — SMT-LIB2 API usable |
| Coq proof checking | ✅ Full (coqc subprocess) | ❌ None | MED — jscoq embedding |
| Lean 4 checking | ✅ Full (lake subprocess) | ❌ None | MED — lean4web |
| Proof cache | ✅ proof_cache.py | ❌ None | HIGH — pure TypeScript |
| ProverRouter | ✅ PARALLEL / FASTEST | ❌ None | HIGH — pure TypeScript |
| FormulaAnalyzer | ✅ Complexity-based routing | ❌ None | MED — heuristic |
| ZK circuits (Lurk) | ✅ zkp/ (Circom/Plonky3) | ❌ None | LOW — research-stage |
| Neural prover | ✅ SymbolicAI | ❌ None | LOW — MCP++ LLM call |
| Remote fallback | N/A | ✅ mcp-remote-deontic-engine | Keep as fallback |

---

## 5. Target Architecture

```
swissknife MCP++ deontic layer
│
├── PolicyEngine (existing, local JS)
│   └── permits / prohibitions / obligations (no deep logic)
│
├── WasmProverHub (NEW — src/services/mcp-wasm-prover-hub.ts)
│   ├── ProofCache (NEW — sha256-keyed, TTL, optional IPFS pin)
│   ├── ProverRouter (NEW — FASTEST / PARALLEL / SEQUENTIAL)
│   │   ├── Z3WasmBridge (Phase 1 — z3-solver npm)
│   │   ├── Cvc5WasmBridge (Phase 2 — SMT-LIB2 text protocol)
│   │   ├── CoqWasmBridge (Phase 3 — jscoq worker)
│   │   ├── LeanWasmBridge (Phase 4 — lean4web worker)
│   │   └── LurkWasmBridge (Phase 6 — ZK proof-carrying code)
│   └── FormulaClassifier (Phase 2 — complexity heuristic)
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

### Phase 6 — ZK Proof Circuits (Lurk/Nova WASM) (Priority: P2)
*Duration estimate: 7–10 days, after Lurk WASM matures*

**Goal**: Generate STARK/SNARK proofs of obligation discharge so third parties can
verify policy compliance without trusting the prover (proof-carrying policy).

**Deliverables**:
1. `src/services/provers/lurk-wasm-bridge.ts` — `LurkWasmBridge`:
   - Wrap `lurk-beta` WASM preview API (pending upstream stability)
   - `proveExecution(lurkExpr: string) → ZKProofArtifact`
   - `verifyProof(proof: ZKProofArtifact) → boolean`
2. `src/services/provers/deontic-to-lurk.ts` — `DeonticToLurkTranslator`:
   - Encode obligation discharge as Lurk s-expression
3. `ZKProofArtifact` type in `Mcp-Plus-Plus` spec (new conformance vector)
4. Integration with `PolicyAuditLog` — attach proof CID to `AuditEntry.extra`
5. Tests: 8+ covering Lurk expression encoding + proof verification stub

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
| T-13 | P1 | Create `src/services/provers/smt2-serializer.ts` | `policyToSMT2(policy) → string` round-trips to Z3 |
| T-14 | P1 | Create `src/services/provers/cvc5-wasm-bridge.ts` (SMT-LIB2 mode) | Accepts SMT-LIB2 string, returns sat/unsat |
| T-15 | P1 | Evaluate `@isl-lang/solver-z3-wasm` as CVC5 compatibility shim | Decision: use as CVC5 stand-in or build cvc5-wasm from source |
| T-16 | P1 | Wire CVC5 into `WasmProverHub` router | Available as MOST_CAPABLE fallback |
| T-17 | P1 | Write 10+ tests for SMT-LIB2 serializer + CVC5 bridge | All pass |
| T-18 | P1 | Evaluate `jscoq` npm package for Node.js embedding | Decision: use jsCoq worker or build lighter Coq subprocess |
| T-19 | P1 | Create `src/services/provers/deontic-to-coq.ts` | Translates `PolicyFormulaSet` to valid Coq `Theorem` |
| T-20 | P1 | Create `src/services/provers/coq-jscoq-bridge.ts` | `prove(coqScript, timeoutMs) → WasmProofResult` |
| T-21 | P1 | Wire CoqBridge into router for higher_order formulas | FormulaClassifier routes correctly |
| T-22 | P1 | Write 10+ tests for Coq bridge + translator | All pass |

---

### Sprint 3 (Phase 5 + 8): Lean 4 + Full Integration

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-23 | P1 | Evaluate lean4web worker embedding in Node.js environment | Decision: usable or not; alternative Lean subprocess |
| T-24 | P1 | Create `src/services/provers/deontic-to-lean4.ts` | Translates `PolicyFormulaSet` to Lean 4 `theorem` |
| T-25 | P1 | Create `src/services/provers/lean4-wasm-bridge.ts` | `prove(leanSource) → WasmProofResult` |
| T-26 | P1 | Wire Lean4Bridge into router for higher_order formulas | Available as alternative to Coq |
| T-27 | P1 | Write 10+ tests for Lean 4 bridge + translator | All pass |
| T-28 | P0 | Full integration: update `mcp-remote-deontic-engine.ts` | Local-first → remote-fallback when local unknown/timeout |
| T-29 | P0 | New factory: `createLocalFirstDeonticORBEvaluator(hub, remote)` | ORB uses local Z3 for simple, remote for hard proofs |
| T-30 | P0 | Update `mcp++ conformance` output with prover capabilities | Shows which WASM provers are loaded |
| T-31 | P0 | Write 15+ integration tests for local-first evaluation | All pass, 492+ total swissknife tests |
| T-32 | P0 | Performance regression test: latency budget | Simple deontic check < 100ms locally (vs ~300ms+ remote) |

---

### Sprint 4 (Phase 6 + 7): ZK + Neural (Research-track)

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-33 | P2 | Evaluate `lurk-beta` WASM preview API stability | Go/no-go decision document |
| T-34 | P2 | Create `src/services/provers/deontic-to-lurk.ts` stub | Encodes obligation discharge as Lurk s-expression |
| T-35 | P2 | Create `src/services/provers/lurk-wasm-bridge.ts` stub | Compiles but skips when Lurk WASM unavailable |
| T-36 | P2 | Define `ZKProofArtifact` type and add to Mcp-Plus-Plus spec | `zkp_proof_artifact.json` conformance vector |
| T-37 | P2 | Attach ZK proof CID to `AuditEntry.extra` when available | `entry.extra.zk_proof_cid` set on ZK-proved entries |
| T-38 | P2 | Create `src/services/provers/neural-prover-bridge.ts` | LLM sketch → Lean verify → WasmProofResult |
| T-39 | P2 | Write 8+ tests for Lurk bridge stub + ZKProofArtifact | All pass (tests skip when Lurk unavailable) |

---

### Ongoing / Housekeeping

| ID | Priority | Task | Acceptance Criteria |
|---|---|---|---|
| T-40 | P1 | Add `prover_id` and `proof_time_ms` to `AuditEntry` extra payload | Logged by `PolicyAuditLog.record()` |
| T-41 | P1 | Update `CONFORMANCE_MATRIX.md` as each prover is added | Matrix stays current after each sprint |
| T-42 | P1 | Add WASM prover health to `mcp++ status` output | Shows which provers are loaded / healthy |
| T-43 | P2 | Bundle-size analysis: z3-solver adds ~34 MB WASM | Lazy-load strategy: load only when first proof requested |
| T-44 | P2 | Cross-language conformance: Python vs JS prover on same formula set | Match rate ≥ 95% on shared test corpus |
| T-45 | P2 | CI gate: `test/mcp-plus-plus/wasm-prover-*.test.ts` in GitHub Actions | Passes in ubuntu-latest Node.js 22 |

---

## 8. Prover Capability Matrix

| Formula Class | Python Reference | Phase 1 (Z3 WASM) | Phase 3 (CVC5) | Phase 4 (Coq) | Phase 5 (Lean 4) |
|---|---|---|---|---|---|
| Propositional deontic | Z3 | ✅ Z3 WASM | ✅ | ✅ | ✅ |
| First-order (∀, ∃) | Z3/CVC5 | ✅ Z3 WASM | ✅ | ✅ | ✅ |
| Linear temporal (◊, □) | Z3/TDFOL native | ❌ (remote fallback) | ❌ (remote) | partial | partial |
| Deontic modal (P/F/O) | TDFOL tableaux | ✅ Z3 encoding | ✅ | ✅ Coq | ✅ Lean |
| Higher-order (λ, Π) | Lean 4 / Coq | ❌ (remote) | ❌ | ✅ Coq | ✅ Lean 4 |
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
