# Supervisor Worker Planner–Doctor Integration Plan

Status: implementation-ready successor plan  
Program prefix: `WPD-`  
Board namespace: `agent-supervisor-worker-planner-doctor-v1`  
Task prefix: `## WPD-`  
Goal prefix: `WPD-G`  
Date: 2026-08-06  

Companion machine inputs:

- `implementation_plan/docs/47-supervisor-worker-planner-doctor-integration.objectives.md`
- `implementation_plan/docs/47-supervisor-worker-planner-doctor-integration.todo.md`
- `config/supervisor_worker_planner_doctor_integration_scheduler.json` (WPD-000)

## 1. Outcome

Make the **live** agent supervisor and implementation workers use the existing
**Planner** and **Deterministic Doctor** as the primary reasoning path, so that:

1. task claim → plan compile/validate/admit happens **before** any LLM provider call;
2. validation/merge failures invoke **Doctor inspect → plan → repair packet** before
   re-prompting a model;
3. deterministic analytical transforms and proof-carrying stages close as much
   work as evidence permits without language models;
4. an LLM receives only a **minimal residual packet** (exact paths, obligations,
   counterexamples, authority roots, validation commands)—never free-form repo
   rediscovery;
5. supervisor selection, retry, rescue, and refill prefer typed planner/doctor
   dispositions over “try the model again”; and
6. metrics prove reduced provider tokens/calls per completed task without
   weakening authority floors.

This program **does not** reimplement analysis, formal planning, Hammer, or
Doctor stages. It **wires** them into the default production composition of:

| Live surface | Primary path today | Target path |
| --- | --- | --- |
| `todo_daemon.implementation_daemon._run_implementation` | Provider (Codex/Grok/…) after claim | Pre-flight planner/doctor → residual provider only |
| Implementation supervisor selection / retry | Attempt + provider backoff | Doctor disposition + plan failure memory |
| Rescue / recovery | Provider-centric preview | Doctor inspect + formal replan first |
| Prompt / plan create services | Optional factories often unset | Default factories always bound |
| Deterministic Doctor CLI/service | Stage slots often unbound | Production factory binds live checkout |

## 2. Relationship to existing programs

| Program | What it delivered | What WPD reuses | What WPD must not reopen |
| --- | --- | --- | --- |
| **RPR** (proof-gated contract repair) | Impact, transforms, transactions, fixed point | Stage APIs | Task identities RPR-* |
| **LPR** (tactician–hammer logic repair + doctor stages) | Doctor contracts, service, transforms, policy, rollout | Stage modules under `analysis/`, `planning/`, `control/`, `validation/` | LPR-000…042 identities |
| **PDR** (proof-directed planner/doctor) | Snapshots, admission, parallel plan, portfolios, benchmarks | Contracts and completed receipts after revalidation | Completed PDR task rows as sole evidence |
| **CPD** (control-plane planner/doctor v2) | Prompt→control-plane design | Design constraints | CPD task IDs if later sealed |
| **PTR** (proof-backed test reuse) | Completion/closeout patterns | Board/validator style only | PTR identities |

WPD is an **integration and production-default** program. A historical
`Status: completed` on PDR/LPR is not current-tree proof; each WPD task that
imports a prior capability must **revalidate** behavior against the live forest.

## 3. Audited residual gaps (why this program exists)

From live architecture docs and code inspection (`PLANNING_AND_ASSURANCE.md`,
`EXECUTION_AND_RECOVERY.md`, PDR residual table, Doctor service, implementation daemon):

1. **Components exist; default path does not call them.**  
   `ProofCarryingPlanner`, `FormalReplanner`, `AdaptivePlanner`,
   `DeterministicDoctorService`, context compiler, and proof caches are
   present, but `_run_implementation` still centers provider execution after
   claim/worktree setup.

2. **Doctor factory/CLI often bind empty stage slots.**  
   Injected backends for inspect/plan/repair/replay are optional; normal
   construction and CLI can leave them unbound, so “Doctor” becomes a shell
   that always abstains or accepts caller-supplied evidence.

3. **Prompt/plan services leave analysis factories off by default.**  
   Optional `build_analysis_factory` / `admission_request_factory` unset means
   the advertised planner path does not run.

4. **Failure handling re-enters the model without a typed residual.**  
   Counterexample-guided `CodexRepairPacket` exists, but the default retry
   path does not require FormalReplanner + packet admission before another
   full implementation attempt.

5. **No single public “pre-implementation kernel” receipt.**  
   Workers need one content-addressed record: evidence roots, plan admission,
   doctor disposition, residual class, and whether an LLM call is authorized.

6. **Metrics do not attribute LLM-avoidance.**  
   Without denominators for “closed by doctor/planner vs residual LLM,”
   rollout cannot prove reduced model dependence.

## 4. Normative principles

1. **Planner and Doctor are dual views of one kernel.**  
   Planner: desired behavior → obligations → plan.  
   Doctor: observed mismatch → same obligations → repair plan.  
   Same records: `PlanBranch`, edit packet, validation commands, fixed-point gate.

2. **Deterministic-first; LLM residual-only.**  
   Order: static facts → impact → goals/premises → plan/doctor → analytical
   transform → (optional) residual LLM → validate → fixed point.  
   Deterministic Doctor mode remains hard-off for LLM/network/remote models.

3. **Discovery nominates; independent checks admit.**  
   Vectors, GraphRAG, tests, and model text never authorize writes or completion.

4. **Preview ≠ apply.**  
   Inspect/explain/plan are read-only. Repair/apply requires permit, lease,
   fence, exact roots, checkpoint, and rollback.

5. **Unknown is not pass.**  
   Missing backends, incomplete frontiers, or unbound factories produce typed
   abstention—not silent provider fallback that pretends Doctor ran.

6. **Worker authority stays below completion.**  
   Provider exit 0, merge, and board `completed` rows are not objective
   completion. Existing authoritative completion gates remain.

7. **Import hygiene.**  
   Cold import of Doctor/planner worker modules must not load network clients
   or optional providers until capability probes run.

## 5. Target architecture (live loop)

```text
  claim task + worktree lease
           │
           ▼
  WPD PreImplementationKernel.evaluate(task, forest, policy)
           │
           ├─ Doctor inspect (if failure residual / contract gap)
           ├─ Evidence factory (AST/graph/cache snapshot)
           ├─ Formal/adaptive plan compile + validate
           ├─ Proof-carrying / analytical transform attempt
           │
           ▼
     disposition ∈ {
       closed_deterministic,   # no LLM
       residual_llm_authorized, # CodexRepairPacket / minimal capsule
       abstain_review,         # typed residual for operator
       defer_capability        # missing optional backend
     }
           │
           ▼
  if closed_deterministic → validate → merge admit → completion gates
  if residual_llm_authorized → provider(packet only) → validate → …
  if abstain/defer → record receipt; do not free-form re-prompt
```

### 5.1 New owned modules (proposed)

| Module | Package | Role |
| --- | --- | --- |
| `pre_implementation_kernel.py` | `planning/` or `todo_daemon/` | Single evaluate() for workers |
| `worker_doctor_bridge.py` | `todo_daemon/` | Map validation failures → DoctorOperationRequest |
| `residual_llm_packet.py` | `planning/` | Seal CodexRepairPacket / context bounds |
| `implementation_disposition.py` | `todo_daemon/` | Durable disposition + metrics |
| `default_doctor_factory.py` | `control/` | Bind live checkout stages |
| `default_planner_factory.py` | `planning/` | Bind compiler/validator/replanner |
| `llm_avoidance_metrics.py` | `validation/` or `self_improvement/` | Token/call attribution |

Exact paths are finalized in WPD-001 contracts; placement must keep the
package DAG acyclic (`docs/architecture/agent_supervisor/PACKAGE_MAP.md`).

## 6. Goal tree

```text
WPD-G000  Deterministic-first planner/doctor in live supervisor & workers
|-- WPD-G010  Contracts, authority ladder, dual-view kernel
|-- WPD-G020  Default evidence + Doctor + planner factories
|-- WPD-G030  Pre-implementation kernel on the worker path
|-- WPD-G040  Failure → doctor replan → residual packet (no free re-prompt)
|-- WPD-G050  Supervisor selection, retry, rescue, refill integration
|-- WPD-G060  Metrics, paired benchmark, and LLM-avoidance proof
`-- WPD-G070  Adversarial floors, rollout, and terminal release
```

## 7. Parallel waves

```text
W0   WPD-000                         control plane seal
W1   WPD-001 | WPD-002 | WPD-003     contracts / threat / metrics schema
W2   WPD-010 | WPD-011 | WPD-012     default factories (doctor, planner, evidence)
W3   WPD-020 | WPD-021               pre-implementation kernel + daemon hook
W4   WPD-022 | WPD-023               analytical close path + residual packet seal
W5   WPD-030 | WPD-031 | WPD-032     failure bridge, formal replan, retry policy
W6   WPD-040 | WPD-041 | WPD-042     supervisor selection / rescue / refill
W7   WPD-050 | WPD-051               metrics + live paired benchmark
W8   WPD-060 | WPD-061               adversarial + operations
W9   WPD-070                         terminal release gate
```

Lanes (file-disjoint ownership where possible):

| Lane | Owns |
| --- | --- |
| `wpd-control` | Plan/objectives/todo/scheduler/validator |
| `wpd-contracts` | Authority, disposition, residual packet schemas |
| `wpd-factory` | Default Doctor/planner/evidence factories |
| `wpd-worker` | `todo_daemon` pre-impl hook and failure bridge |
| `wpd-supervisor` | Selection, rescue, refill adapters |
| `wpd-metrics` | Metrics, benchmark, rollout |
| `wpd-release` | Terminal gate only |

## 8. Safety floors (must remain zero)

- Unauthorized LLM call when disposition ≠ `residual_llm_authorized`
- Deterministic Doctor path that loads network/LLM clients
- Write without mutation permit / lease / exact roots
- Completion from provider prose or synthetic Doctor success flags
- Free-form re-prompt that omits residual packet after a typed failure
- Candidate code editing protected WPD control artifacts post-seal

## 9. Success criteria

1. Hermetic tests prove: with analytical fixtures, workers complete tasks with
   **zero** provider invocations.
2. With residual-only fixtures, providers receive only sealed packets (size and
   field bounds enforced).
3. Cold import of worker/doctor bridges loads no `requests`/remote clients.
4. Live integration test: validation failure → Doctor plan → replan → second
   attempt uses packet, not full task prose re-injection.
5. Benchmark report: token and provider-call rates drop vs baseline on the
   fixed fixture corpus without safety-floor violations.
6. Terminal release receipt binds current forest, policy, and zero floors.

## 10. Non-goals

- Replacing Codex/Grok providers entirely
- New assurance lattice or completion authority
- Reopening sealed LPR/PDR task identities
- Unbounded autonomous self-modification of policy/benchmarks
- Production Groth16 ceremony or warm test-skip authority (see PTR)

## 11. Operator notes

- Deterministic Doctor remains report-only until elevated policy admits repair.
- Hybrid residual LLM is a **named** path distinct from deterministic mode.
- Prefer monorepo worktree on a dedicated branch
  `agent/worker-planner-doctor-integration` with accelerate submodule pin.

## 12. Source anchors

| Concern | Path |
| --- | --- |
| Implementation loop | `todo_daemon/implementation_daemon.py` |
| Doctor service | `control/deterministic_doctor_service.py` |
| Doctor policy | `validation/deterministic_doctor_policy.py` |
| Formal replan | `planning/formal_replanner.py` |
| Proof-carrying planner | `planning/proof_carrying_planner.py` |
| Adaptive planner | `planning/adaptive_planner.py` |
| Context compiler | `context/context_compiler.py` |
| Planning narrative | `docs/architecture/agent_supervisor/PLANNING_AND_ASSURANCE.md` |
| Execution narrative | `docs/architecture/agent_supervisor/EXECUTION_AND_RECOVERY.md` |
| LPR plan | `docs/architecture/AGENT_SUPERVISOR_TACTICIAN_HAMMER_LOGIC_REPAIR_PLAN.md` |
| PDR plan | `docs/architecture/AGENT_SUPERVISOR_PROOF_DIRECTED_PLANNER_DOCTOR_PLAN.md` |
