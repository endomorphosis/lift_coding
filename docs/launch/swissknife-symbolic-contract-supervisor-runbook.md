# SwissKnife Symbolic Contract Assurance — Operator Runbook

**Program:** SCA (`SCA-` task prefix)  
**Profile:** `config/swissknife_symbolic_contract_assurance_supervisor.json`  
**Board:** `implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md`  
**Runtime root:** `data/agent_supervisor/swissknife_contract_assurance/`  
**Phase (current):** `symbolic_repair` (formal enablement closed via `SCA-ENABLE-CLOSE`)

This runbook is the SCA-160 operator surface for start/status/stop, promotion
gates, rollback, and evidence retention. **Shadow is the default.** Automatic
promotion is **not** enabled by this document alone.

---

## 1. Authority model (read first)

| Source | Authority |
|--------|-----------|
| Kernel / exact proof receipts | Authoritative when snapshot-bound |
| Real ZK (`verified_receipt` only) | Attestation only under capability + approved predicate |
| Simulated / unavailable ZK | **Never ATTESTED**; may block only if marked required |
| Static analysis / tests | Observation |
| LLM / provider output | **proposal_only** — never completion authority |

Completion never follows from an empty task queue. Goal exhaustion requires a
**current healthy scan** and **child completion proofs** (or typed blocked
evidence).

---

## 2. Key paths

| Path | Role |
|------|------|
| `config/swissknife_symbolic_contract_assurance_supervisor.json` | Supervisor profile (mode, lanes, selectionPolicy) |
| `config/swissknife_symbolic_contract_scope.json` | Index scope + skipPrefixes |
| `authoritative` → `generations/…` | Published healthy index generation |
| `baseline/handoff.json` | Handoff receipt (symlink into authoritative) |
| `baseline/runtime_components/` | SCA-180 four-component baseline |
| `evaluation/runtime_report.json` | SCA-181 mutation / ZK / release eval |
| `evaluation/production-composition.json` | SCA-614 production composition |
| `formal_first_enablement_closeout.json` | ENABLE-CLOSE receipt |
| `completion_gate.json` | SCA-160 promotion / health gate receipt |
| `rpr_admission_ready.json` | Proof-gated repair admission |
| `generated/ipfs_accelerate_contract_repairs.todo.md` | Non-authoritative repair board |

---

## 3. Preflight

```bash
cd /path/to/lift_coding
export PYTHONPATH="external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets:Mcp-Plus-Plus:${PYTHONPATH:-}"

# Phase / closeout
python3 scripts/sca_formal_first_ready.py --expect-closeout
python3 scripts/sca_formal_first_ready.py --expect-phase symbolic_repair

# Authoritative health
python3 -c "import json; s=json.load(open('data/agent_supervisor/swissknife_contract_assurance/baseline/summary.json')); print(s['health_status'], s.get('handoff'))"
test -L data/agent_supervisor/swissknife_contract_assurance/authoritative

# Runtime baseline + evaluation
python3 -c "import json; print(json.load(open('data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_components/summary.json'))['health_status'])"
python3 -c "import json; print(json.load(open('data/agent_supervisor/swissknife_contract_assurance/evaluation/runtime_report.json'))['passed'])"

# Completion gate
python3 -m json.tool data/agent_supervisor/swissknife_contract_assurance/completion_gate.json >/dev/null
```

All of the above should be green before any assist/automatic discussion.

---

## 4. Start / status / stop (supervisor)

Profile fields of record:

- `mode` / `selectionPolicy.phase`: `symbolic_repair`
- `parallelRuntime.laneCount` / `bounds.supervisorLanes`: **8**
- `selectionPolicy.requireCounterexampleBindingForLlmTasks`: **true**
- `selectionPolicy.requireDoctorAbstentionOrTransformForLlmTasks`: **true**
- `selectionPolicy.preferDeterministicOnly`: **true**
- `selectionPolicy.maxOpenLlmImplementationTasks`: **1** (raise only deliberately)

### Status

```bash
# PID / lease / logs (adjust to your launch script)
ls -la data/agent_supervisor/swissknife_contract_assurance/state 2>/dev/null
tail -n 50 data/agent_supervisor/swissknife_contract_assurance/supervisor.log 2>/dev/null

# Board ready summary
python3 scripts/sca_formal_first_ready.py --list-ready-summary
```

### Start (illustrative)

Use the project’s SCA multi-lane launcher or:

```bash
# Prefer the checked-in launch path if present; otherwise:
python3 -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor \
  --todo-path implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md \
  --objective-path implementation_plan/docs/44-swissknife-symbolic-contract-assurance.objectives.md \
  # ... plus profile-bound state/worktree/merge flags from the supervisor JSON
```

Confirm `selectionPolicy.phase=symbolic_repair` and packet gates before enabling
implement lanes.

### Stop

1. Stop implement daemons / supervisor process group.
2. Leave `generations/`, `baseline/`, `evaluation/`, and proof caches intact.
3. Record the stopping snapshot IDs from `baseline/summary.json`.

### Reclaim / recovery

- Dead claims with open worktrees: reclaim via supervisor recovery tooling;
  do not delete worktrees that still own snapshot or incident locks.
- Stale index: re-run authoritative index only with
  `--require-healthy --require-provider-authority --publish-handoff` (see SCA-225).
- Never promote while `parser_failure_budget_exceeded` or handoff unpublished.

---

## 5. Query evidence

```bash
# Index identity
python3 -c "import json,os; r='data/agent_supervisor/swissknife_contract_assurance'; print(os.readlink(f'{r}/authoritative')); print(json.load(open(f'{r}/baseline/handoff.json'))['index_id'])"

# Runtime evaluation safety gates
python3 -c "import json; print(json.load(open('data/agent_supervisor/swissknife_contract_assurance/evaluation/runtime_report.json'))['safety_gates'])"

# Completion gate
python3 -c "import json; g=json.load(open('data/agent_supervisor/swissknife_contract_assurance/completion_gate.json')); print(g['passed'], g['promotion']['mode'])"
```

---

## 6. Promotion gates

| Mode | When | Mutation |
|------|------|----------|
| **shadow** (default) | Always until explicitly changed | No source mutation from models |
| **assist** | Human-approved packets only | Bounded CodeEditPacket implement |
| **automatic** | Not enabled by this runbook | Requires separate sign-off |

### Hard requirements for any promotion discussion

1. Authoritative analyzer health **healthy** and handoff **published**.
2. Runtime components baseline **healthy**, `llm_call_count=0`.
3. SCA-181 runtime evaluation **passed** (`simulated_zk_never_attests`,
   zero false authority, release fail-closed on bad children).
4. Formal-first closeout **gate_closed** (or successor phase receipt).
5. RPR admission **ready** for any LLM implement path.
6. Every LLM task bound to counterexample + doctor transform/abstention.
7. `completion_gate.json` `passed=true` and `promotion.mode` still `shadow`
   unless a human edits the gate after review.

Empty backlog ≠ done.

---

## 7. Rollback

Goal: **disable model mutation**, **retain all evidence**.

1. Set `selectionPolicy.maxOpenLlmImplementationTasks` to `0`.
2. Ensure `preferDeterministicOnly=true` and counterexample/doctor gates remain on.
3. Stop implement lanes; optional: keep index/analysis.
4. Do **not** delete:
   - `generations/`
   - `baseline/` (including `runtime_components/`)
   - `evaluation/`
   - `proof-cache` / CAS blobs
5. Optionally flip `mode` back to `formal_first_enablement` only with a new
   board receipt — prefer leaving `symbolic_repair` and zeroing LLM budget.

---

## 8. Retention

Retain at least:

- Last N authoritative generations under `generations/`
- `completion_gate.json`, `formal_first_enablement_closeout.json`
- `evaluation/runtime_report.json` and production composition receipts
- Supervisor logs sufficient to reconstruct lease/PID/incident state

Content-addressed blobs are the audit trail; log-only claims are not.

---

## 9. Related validation commands

```bash
# Authoritative handoff tests
python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_repository_index_handoff.py -q

# Runtime evaluation (SCA-181)
python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_evaluation.py -q

# Repair projection (SCA-221)
python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_integrity_repair_projection.py -q

# Production composition (SCA-614)
python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_production_contract_composition.py -q
```

---

## 10. Document control

| Field | Value |
|-------|--------|
| SCA task | SCA-160 |
| Companion gate | `data/agent_supervisor/swissknife_contract_assurance/completion_gate.json` |
| Formal plan | `implementation_plan/docs/47-sca-formal-first-improvement-plan-2026-08-06.md` |
| LLM calls to produce this runbook | 0 (operator/deterministic) |


---

## 11. Symbolic repair pipeline (SCA-225 → 180 → 221 → provers)

Use this path to drive residual SCA work with **accelerate agent supervisor**
plus **datasets logic / hammers / theorem-prover IR**, without free-form LLM
authority.

```text
SCA-225 authoritative index (healthy, handoff published)
    → SCA-180 runtime baseline findings (healthy, llm=0)
    → mismatch / vulnerability classification
    → SCA-221 CodeEditPacket projection (non-authoritative board)
    → sca_doctor_bridge: transform_receipt | analytical_abstention (0 model calls)
    → sca_rpr_admission: require snapshot + counterexample + reproof
    → obligation compile (mcp_contract_obligations → datasets logic IRClaim)
    → McpContractProver + ipfs_datasets_logic_provider hammers
    → TrustAwareProofCache rebind + re-index / re-prove fixed point
```

### Operator preflight for symbolic repair

```bash
export PYTHONPATH="external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets:Mcp-Plus-Plus:${PYTHONPATH:-}"
python3 scripts/sca_symbolic_repair_ready.py
# expects: OK symbolic-repair stack ready
# receipt: data/agent_supervisor/swissknife_contract_assurance/symbolic_repair_ready.json
```

### Normative rules

1. LLM implement is **proposal_only** and rejected unless RPR-admitted.
2. Doctor never mints kernel proof; transforms require re-index/re-prove.
3. Simulated ZK never attests.
4. Empty repair board is valid when no admitted counterexample packets exist.
5. Phase remains `symbolic_repair` with counterexample + doctor packet gates on.


---

## 12. Project live repairs (operator)

```bash
export PYTHONPATH="external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets:Mcp-Plus-Plus:${PYTHONPATH:-}"
python3 scripts/sca_project_live_repairs.py --max-tasks 12 --merge-live
```

Writes non-authoritative `SCA-REPAIR-*` tasks into
`generated/ipfs_accelerate_contract_repairs.todo.md` from SCA-180
`observed_contract_incomplete` findings (doctor → RPR → CodeEditPacket).

CEC/hammer backends are registered for deontic claims; solver output remains
**candidate** until trusted kernel reconstruction. Repair tasks never complete
from solver alone.

### Package interop (MCP protocol)

Cross-package interop between `ipfs_accelerate_py`, `ipfs_kit_py`, and
`ipfs_datasets_py` **must** use MCP mediation:

| Path | Allowed? |
|------|----------|
| `tools/call` / JSON-RPC to peer MCP URL | Yes (preferred) |
| `tools_dispatch` within unified MCP registry | Yes (same server) |
| `package_mcp_interop.call_package_mcp_tool` | Yes |
| Direct `import ipfs_kit_py` / `import ipfs_datasets_py` for new surfaces | No (compat only) |

Env endpoints: `IPFS_KIT_MCP_URL`, `IPFS_DATASETS_MCP_URL`,
`IPFS_ACCELERATE_MCP_URL`. Helper:
`ipfs_accelerate_py.mcp_server.package_mcp_interop`.

SCA path classes keep **MCP++** and **direct** distinct; do not collapse them.

### Start live MCP endpoints + symbolic repair loop

```bash
export PYTHONPATH="external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit:Mcp-Plus-Plus"
python3 scripts/sca_start_mcp_endpoints.py          # acc:8000 datasets:3002 kit:8004
set -a; source data/agent_supervisor/swissknife_contract_assurance/evaluation/mcp_endpoints/endpoints.env; set +a
python3 scripts/sca_start_mcp_endpoints.py --status
python3 scripts/sca_symbolic_auto_repair_loop.py --max-tasks 5
```

Kit uses MCP++ Hypercorn HTTP (`python -m ipfs_kit_py.mcp_server.server
--transport http`), not the legacy `UnifiedMCPServer` stdio harness. All three
package endpoints can be live for `package_mcp_interop` / `tools/call`.

Logic backends (CEC/HAMMER/SMT/TDFOL/IR) register into the agent-supervisor
prover via `create_mcp_contract_prover_with_datasets_logic_backends`. Candidates
stay non-authoritative until kernel reconstruction.

### Multi-family symbolic repair (not CEC-only)

```bash
python3 scripts/sca_multi_family_symbolic_repair.py --max-tasks 8
# report: …/evaluation/multi_family_symbolic_repair_report.json
```

Applies **all** useful families from `ipfs_datasets_py.logic` to each residual
finding and synthesizes an ordered repair plan:

| Family | Role in contract repair |
|--------|-------------------------|
| IR | Canonical identity / disambiguation keys |
| software_contracts / AST | Registration & handler sites |
| graph / schema | Local MCP proof routes |
| deontic / CEC | Policy-before-effect, obligations |
| modal | Necessary mediation vs possible direct |
| TDFOL / event_calculus | Temporal/workflow ordering |
| flogic | Category/frame uniqueness |
| SMT | Uniqueness & schema constraints |
| HAMMER | Premise selection / candidate portfolio |

Also invoked from `sca_symbolic_auto_repair_loop.py` (registers **all** backend
kinds into the supervisor prover).

**Prover matrix + protocol (ProVerif/Tamarin):** the same script probes the
supervisor prover matrix (Z3, CVC5, Vampire, E, Lean, Coq, Isabelle, Hammer,
ProVerif, Tamarin, …) and attaches **protocol** families to auth/mediation
findings (`ambiguous_path_class`, `tools_dispatch`, UCAN/session, kit interop).
Protocol tools may be *guidance-only* until binaries are installed
(`ipfs_prover_installer --proverif` / formal_verification_toolchains).

### Full prover integration (matrix + protocol + MultiProverRouter)

End-to-end binding of the full symbolic stack for residual SCA findings:

```bash
export PYTHONPATH="external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit:Mcp-Plus-Plus"
# Optional override if installs live elsewhere:
# export IPFS_THEOREM_PROVERS_BIN=~/.local/share/ipfs_datasets_py/theorem-provers/bin
python3 scripts/sca_full_prover_integration.py --max-tasks 8 --execute
# report: …/evaluation/full_prover_integration_report.json
```

| Layer | Role |
|-------|------|
| Managed PATH | `theorem-provers/bin` prepended so ProVerif/Tamarin/Vampire/… resolve |
| Datasets backends | IR · TDFOL · CEC · SMT · HAMMER → MCP contract prover routes |
| Prover matrix | Capability snapshot for all matrix IDs (smoke/version/reconstruction) |
| Protocol layer | ProVerif + Tamarin **end-to-end conformance** + CORE protocol model |
| MultiProverRouter | Maps findings → `PropertyKind` portfolios; fail-closed execute |
| Portfolio runner | Returns **CANDIDATE** for available tools — never mints KERNEL_VERIFIED |

Property kinds routed: `finite_constraint`, `state_machine`, `authorization`,
`protocol`, `hyperproperty`, `runtime_trace`, `kernel_check`, `typed_planning`,
`temporal_deontic`, `first_order_theorem`.

Protocol POLICY lanes: **tamarin** (`protocol_trace_property`) + **proverif**
(`protocol_reachability`). DatasetsLogicBackendKind stays closed at five kinds;
protocol/ATP/kernel attach via the portfolio layer, not the MCP backend enum.

Also invoked from `sca_symbolic_auto_repair_loop.py`.

### Typed obligations + kernel reconstruction gate

Compile residual findings into reviewed `McpContractObligation` records, prove
via datasets backends, and fail-close the kernel boundary:

```bash
export PATH="$HOME/.local/share/ipfs_datasets_py/theorem-provers/bin:$HOME/.elan/bin:$PATH"
export PYTHONPATH="external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit:Mcp-Plus-Plus"
python3 scripts/sca_obligation_kernel_pipeline.py --max-tasks 6
# report: …/evaluation/obligation_kernel_pipeline_report.json

# Live Lean independent kernel (toolchain readiness bound to obligation ids):
python3 scripts/sca_kernel_reconstruction_pipeline.py --max-tasks 6
# report: …/evaluation/kernel_reconstruction_pipeline_report.json

# Full multi-family portfolio (every analyzer):
python3 scripts/sca_multi_family_symbolic_repair.py --max-tasks 4 --all-families --protocol-conformance

# Or nested under full integration / auto-repair loop:
python3 scripts/sca_full_prover_integration.py --max-tasks 6 --execute --with-obligations
python3 scripts/sca_symbolic_auto_repair_loop.py --max-tasks 4 --skip-mcp-require
```

| Step | Behavior |
|------|----------|
| Finding → claim family | all residual kinds map to schema/deontic/relation parity families |
| Catalog | `make_source_record` + `build_contract_from_sources` + `register_contract` |
| Compile | `compile_contract_claim` (SCA-060 bindings; claim stays **OPEN**) |
| Prove | `McpContractProver.prove` (CEC/SMT/TDFOL/local schema); candidates only |
| Empty kernel packet | `verify_kernel_reconstruction({},{},{})` **must fail-closed** |
| Live Lean toolchain | `IndependentKernelVerifier.verify_lean_proof_text` → ACCEPTED for True smoke **bound to obligation id** |
| Claim discharge (IR→Lean) | `sca_mcp_claim_lean_codec` → `scaClaimHolds`; Lean `by decide` |
| Claim discharge (IR→Coq) | Same observations → coqc + `verify_kernel_reconstruction` |
| Claim discharge (IR→Isabelle) | Same observations → `isabelle build` session ScaClaim |
| Residual deontic facts | Mediation + doctor + **live protocol CONFORMANCE receipts** (strict; not mere PATH) |
| Residual relation facts | Z3 unsat of negated identity equality (when SMT is candidate-only) |
| Environment lock | `lock:sca:<itp>:sha256:…` bound to snapshot_id + executable |
| Board + RPR bind | `sca_bind_kernel_receipts_to_board.py` → claim receipts, board notes, RPR ready extra |
| Authority scope | `observation_bound_operator_semantics@1` — not full live MCP re-execution |

```bash
# Full kernel stack (Lean + Coq + Isabelle + strict protocol)
# Prefer board-aligned residual ops; cap expensive ITPs for speed when needed:
python3 scripts/sca_kernel_reconstruction_pipeline.py \
  --max-tasks 12 --skip-hammer --max-isabelle-claims 4 --max-coq-claims 20

# Bind claim KERNEL_VERIFIED receipts into repair board + RPR readiness
python3 scripts/sca_bind_kernel_receipts_to_board.py
# receipts: …/evaluation/claim_kernel_receipts/
# board: …/generated/ipfs_accelerate_contract_repairs.todo.md
# rpr: …/rpr_admission_ready.json

# Supervisor-native stack (preferred — agent_supervisor.sca_symbolic_repair)
# Includes multi_family + kernel + board_bind + **symbolic planning**
# + Intent/Legal/Security IR + UI interface bridge inventory
python3 scripts/sca_agent_supervisor_symbolic_repair.py --max-tasks 6
# report: …/evaluation/supervisor_symbolic_repair_stack_report.json

# IR integration probe only (intent_ir / legal_ir / security_ir / ui_ir)
python3 scripts/sca_ir_integration_probe.py
# report: …/evaluation/supervisor_ir_integration_report.json

# Apply IR logic to intermediate representations (normalize → compile → evaluate)
python3 scripts/sca_ir_logic_apply.py --max-surfaces 4
# optional fail-closed plan admission over compiled IR constraints:
python3 scripts/sca_ir_logic_apply.py --max-surfaces 2 --with-admission
# report: …/evaluation/supervisor_ir_logic_apply_report.json

# Symbolic planning only (DefaultPlannerFactory + MultiProverRouter + all families)
python3 scripts/sca_agent_supervisor_symbolic_planning.py --max-tasks 8
# report: …/evaluation/supervisor_symbolic_planning_stack_report.json

# Full symbolic auto-repair (defaults to supervisor orchestrator)
python3 scripts/sca_symbolic_auto_repair_loop.py --max-tasks 4 --skip-mcp-require
python3 scripts/sca_multi_family_symbolic_repair.py --max-tasks 8 --all-families --protocol-conformance

# Readiness (includes supervisor policy + all backends + kernel + planning + IR)
python3 scripts/sca_symbolic_repair_ready.py
```

Supervisor profile fields in
`config/swissknife_symbolic_contract_assurance_supervisor.json`:

| Field | Module |
|-------|--------|
| `symbolicRepairPolicy` | `agent_supervisor.sca_symbolic_repair` |
| `symbolicPlanningPolicy` | `agent_supervisor.sca_symbolic_planning` |
| `irIntegrationPolicy` | `agent_supervisor.sca_ir_integration` |
| `irLogicApplyPolicy` | `agent_supervisor.sca_ir_logic_applicator` |

Both repair and planning bind **33 analysis families** (29 logic/prover +
`intent_ir` · `legal_ir` · `security_ir` · `ui_ir`), **5 datasets backends**,
MultiProverRouter property kinds, protocol conformance, and kernel ITP
inventory.

**Apply logic to intermediate representations** (planner + doctor + symbolic repair):

```
residual finding / op
  → project_candidate_plan (actions/effects graph)
  → deterministic_ir_fixture + IRRegistry.load/verify
  → IRAdapterRegistry.normalize (family-exact)
  → compile_intent_constraints / compile_legal_constraints /
    compile_security_constraints
  → evaluate_security_authorization (fail-closed)
  → ui_ir interface projection (descriptor nodes + action contract render)
  → AST body-free index + symbol/call/path query
  → deterministic code-symbol vector index + search
  → semantic knowledge graph + mandatory closure
  → optional compile_plan_admission (grant sources empty → no execution)
```

| Surface | Apply path | Role |
|---------|------------|------|
| `intent_ir` | load → normalize → `compile_intent_constraints` | required work IR (never authorizes) |
| `legal_ir` | load → normalize → `compile_legal_constraints` | applicability IR (never grants) |
| `security_ir` | load → normalize → compile + evaluate | authorization decision IR |
| `ui_ir` | project UI IR nodes + interface_contract render | interface intermediate IR |
| `ast` | `build_analysis_ast_index` + query | AST intermediate IR (body-free) |
| `knowledge_graph` | `build_semantic_dependency_graph` + closure | dependency IR for plan/doctor |
| `vector_index` | `build_code_symbol_vector_index` + search | retrieval IR (fixture embeddings only) |

**General (not SCA-taskboard-only)**

Canonical modules (any domain: planner / doctor / repair / contract_repair / sca / generic):

| Module | Role |
|--------|------|
| `proof.ir_logic_application` | Shared + structural IR apply (`IrWorkSurface`) |
| `proof.ir_structural_application` | AST / KG / vector |
| `planning.ir_logic_consumers` | Planner enrich + doctor diagnose helpers |
| `sca_ir_logic_applicator` | Thin SCA re-export (`domain="sca"` default) |

**Consumers**

| Consumer | Entry |
|----------|--------|
| Symbolic repair | stage `ir_apply` + multi-family analyzers (`domain=sca`) |
| Planner (general) | `AdaptivePlanner.plan_symbolically` + context surfaces / `enrich_planning_context_with_ir_logic` |
| Planner (SCA) | portfolio field `ir_logic_apply` |
| Doctor (general) | `planning.ir_logic_consumers.diagnose_with_ir_logic` |
| Doctor (SCA) | `diagnose_finding_with_ir` (disposition + general IR apply) |
| Default planner factory | `handles.to_dict()["ir_logic"]` capability probe |

Example non-SCA apply:

```python
from ipfs_accelerate_py.agent_supervisor.proof.ir_logic_application import (
    IrWorkSurface, apply_logic_to_ir,
)
apply_logic_to_ir(IrWorkSurface(
    operation="tools.deploy", kind="missing_guard",
    domain="contract_repair", consumer="planner", path="pkg/deploy.py",
))
```

### Deep hooks (`planning.ir_logic_hooks`)

| Hook | Where | Effect |
|------|--------|--------|
| `prepare_planning_context` | `SymbolicCandidatePlanner.plan`, `AdaptivePlanner.plan_symbolically` | Freezes IR receipts into planning context |
| `compose_hard_gate_with_ir` | adaptive hard gates | Fail-closed when `require_ir_logic` |
| `inject_ir_into_formal_plan_source` | `FormalPlanCompiler.compile` | Projects IR into AST/policy/evidence/task channels |
| `ir_validation_findings` | `FormalPlanValidator.validate` | Required IR missing → validation finding |
| `attach_ir_logic_to_doctor_request` | `DoctorSynthesizer.synthesize` | Binds IR into doctor request metadata |
| `symbolic_repair_ir_portfolio_bind` | SCA `planning` stage | Cross-binds `ir_apply` into plan portfolios |

Set `apply_ir_logic: true` / `require_ir_logic: true` on planning context or compile source to opt into / require deep IR.

### Autonomous repair (no LLM, reusable)

Canonical package: `agent_supervisor.autonomous_repair`

| Piece | Role |
|-------|------|
| `InterfaceAliasRegistry` | MCP/ORB/IDL name aliases (extend per product) |
| `resolve_mcp_surfaces` | Package-agnostic `register_tool` resolution |
| `AutonomousRepairEngine` | IR + doctor + surface → disposition plan |

```bash
# SCA board (SwissKnife GUI ↔ MCP)
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit \
  python3 scripts/autonomous_supervisor_repair.py --source sca-board --swissknife-idl

# Any domain / ops
python3 scripts/autonomous_supervisor_repair.py --domain contract_repair \
  --op tools_dispatch --op ipfs_add
```

Dispositions: `single_path_ready` · `multi_path_collapse` · `missing_surface` ·
`idl_gap` · `analysis_only` · `blocked`. Never marks board completion
authoritative; `model_call_count` must stay 0.

**Body-free admitted edit plans** (second stage):

```bash
python3 scripts/autonomous_supervisor_repair.py --source sca-board --swissknife-idl \
  --allow-code-edit-materialize
# writes data/agent_supervisor/autonomous_repair/edit_plans/*.json + index.json
```

| Field | Meaning |
|-------|---------|
| `body_free` | No source body text embedded |
| `materialize_ready` | Single-path + IR/doctor ok + flag; still not implementable |
| `implementable` | Always false until external re-proof admits materialize |
| `doctor_proposal` | Optional body-free closed-set proposal (`proof_admitted=false`) |

Multi-path items get collapse plans (`materialize_ready=false`). Missing surfaces
get no edit plan (registration required first).

**Materialize stage** (third stage — gated tree writes):

```bash
# Plan + materialize single-path bindings (no LLM)
python3 scripts/autonomous_supervisor_repair.py --source sca-board --swissknife-idl \
  --allow-code-edit-materialize --materialize --write-package-bindings

# Re-apply existing edit plans only
python3 scripts/autonomous_supervisor_repair.py --materialize-only --write-package-bindings

# Gate check without writes
python3 scripts/autonomous_supervisor_repair.py --materialize-only --dry-run
```

Gates before write: `materialize_ready` · revalidated single-path · path exists ·
handler/`register_tool` evidence in source. Writes **identity binding catalogs**
only (not free-form source rewrites):

| Output | Path |
|--------|------|
| Data catalog | `data/agent_supervisor/autonomous_repair/bindings/surface_identity_bindings.json` |
| Domain copy | `…/surface_identity_bindings.<domain>.json` |
| Package catalog | `external/ipfs_accelerate/.../mcp_server/surface_identity_bindings.json` |
| Loader | `mcp_server.surface_identity_bindings.resolve_preferred_surface` |
| Receipt | `edit_plans/materialize_receipt.json` |

`implementable` / board completion remain non-authoritative until re-proof.

**Live mediation** uses the package loader:

* `mcp_server.surface_identity_bindings.resolve_dispatch_target` — `tools_dispatch`
* `mcp_server.package_mcp_interop` — resolves tool names before `tools/call`
* `resolve_preferred_surface` / `preferred_path_for` — shared lookup

After materialize, re-run:

```bash
python3 scripts/sca_symbolic_repair_ready.py
python3 scripts/sca_bind_kernel_receipts_to_board.py
```

Supervisor stages include `ir_integration` (capability probe) and **`ir_apply`**
(actual logic on IR). SCA is one domain tag, not a hard dependency of the IR stack.

`requireUiIr` stays **false** until `ipfs_datasets_py.logic.ui_ux_ir` exists;
`requireUiInterfaceBridge` remains true. No IR apply path grants execution
authority without real Security grant sources. Planning is deterministic-first
(`AdaptivePlanner.plan_symbolically` available; residual LLM only under sealed
RPR packets).

`required_assurance` for residual work is `SOLVER_CHECKED`. Schema-local
**proved**, residual deontic (strict protocol conformant), and residual relation
observations can discharge claim-level KERNEL_VERIFIED under the observation-
bound encoding on **Lean, Coq, and Isabelle**. CEC/SMT provider results remain
non-authoritative candidates. Board/RPR binding attaches evidence only —
completion stays non-authoritative; LLM implement remains **proposal_only**.

### Kit MCP HTTP

Kit MCP++ exposes Hypercorn HTTP (not the legacy `UnifiedMCPServer` stdio
harness):

```bash
python3 scripts/sca_start_mcp_endpoints.py   # kit uses --transport http on :8004
# equivalent:
python3 -m ipfs_kit_py.mcp_server.server --transport http --host 127.0.0.1 --port 8004
```

### Auto-repair incomplete surfaces (AST + registration)

```bash
export PYTHONPATH="external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets:Mcp-Plus-Plus:${PYTHONPATH:-}"
python3 scripts/sca_auto_repair_incomplete_surfaces.py --probe-kernel
# report: data/agent_supervisor/swissknife_contract_assurance/evaluation/auto_repair_incomplete_surfaces_report.json
```

Classifies `observed_contract_incomplete` ops against static MCP surfaces
(after registration aliases + multi-match collapse). Kernel probe imports
`verify_kernel_reconstruction` and fail-closes empty candidates — it does
**not** mint KERNEL_VERIFIED receipts.

Focused observation recompile (updates findings without full handoff):

```bash
python3 scripts/sca_recompile_observed_incomplete.py --update-findings
python3 scripts/sca_project_live_repairs.py --max-tasks 12 --merge-live
# empty SCA-REPAIR board is success when incompletes are zero
```

Authoritative runtime baseline refresh (slow; allow-dirty while repairs are uncommitted):

```bash
python3 external/ipfs_accelerate/scripts/index_repository_contracts.py \
  --repo-root . \
  --scope-config config/swissknife_symbolic_contract_scope.json \
  --output-root data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_components \
  --shadow --allow-dirty --require-healthy \
  --max-parser-failures 10 --max-parser-failure-ratio 0.01
```
