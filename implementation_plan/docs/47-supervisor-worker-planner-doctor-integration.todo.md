# Supervisor Worker Planner–Doctor Integration Taskboard

Consumable by `ipfs_accelerate_py.agent_supervisor` with task prefix `WPD-`.

Companion artifacts:

- objective heap:
  `implementation_plan/docs/47-supervisor-worker-planner-doctor-integration.objectives.md`
- architecture:
  `implementation_plan/docs/47-supervisor-worker-planner-doctor-integration-plan-2026-08-06.md`

Successor integration program over completed RPR/LPR/PDR foundations. It does
not reopen sealed RPR/LPR/PDR task identities. Prior `completed` labels are not
current-tree evidence without revalidation.

Normative execution order on every implementation attempt:

```text
claim + lease
  -> PreImplementationKernel (evidence + plan/doctor)
  -> disposition
  -> closed_deterministic | residual_llm_authorized | abstain | defer
  -> validate / merge admit / completion gates
```

On failure:

```text
typed failure
  -> Doctor inspect/plan
  -> FormalReplanner + failure memory
  -> sealed residual packet (optional LLM)
  -> never free-form full-task re-prompt as sole context
```

## Parallel waves

```text
W0  WPD-000
W1  WPD-001 | WPD-002 | WPD-003
W2  WPD-010 | WPD-011 | WPD-012
W3  WPD-020 | WPD-021
W4  WPD-022 | WPD-023
W5  WPD-030 | WPD-031 | WPD-032
W6  WPD-040 | WPD-041 | WPD-042
W7  WPD-050 | WPD-051
W8  WPD-060 | WPD-061
W9  WPD-070
```

## WPD-000 Bootstrap and seal the worker planner–doctor control plane

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: control
- Depends on:
- Goal id: WPD-G000
- Outputs: implementation_plan/docs/47-supervisor-worker-planner-doctor-integration-plan-2026-08-06.md, implementation_plan/docs/47-supervisor-worker-planner-doctor-integration.objectives.md, implementation_plan/docs/47-supervisor-worker-planner-doctor-integration.todo.md, config/supervisor_worker_planner_doctor_integration_scheduler.json, config/supervisor_worker_planner_doctor_supervisor.json, scripts/validate_supervisor_worker_planner_doctor_board.py, scripts/supervisor_worker_planner_doctor_supervisor.sh, test/test_supervisor_worker_planner_doctor_bootstrap.py
- Validation: python3 -m pytest -q test/test_supervisor_worker_planner_doctor_bootstrap.py && python3 scripts/validate_supervisor_worker_planner_doctor_board.py --check-all
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/control
- Parallel lane: wpd-control
- Resource class: cpu-small
- Resource stage: analysis
- Token class: small
- Estimated tokens: 12000
- Implementation timeout seconds: 1800
- Predicted files: implementation_plan/docs/47-supervisor-worker-planner-doctor-integration-plan-2026-08-06.md, implementation_plan/docs/47-supervisor-worker-planner-doctor-integration.objectives.md, implementation_plan/docs/47-supervisor-worker-planner-doctor-integration.todo.md, config/supervisor_worker_planner_doctor_integration_scheduler.json, scripts/validate_supervisor_worker_planner_doctor_board.py, test/test_supervisor_worker_planner_doctor_bootstrap.py
- Interfaces: WorkerPlannerDoctorPlan@1
- Conflict policy: After commit, the six control artifacts are protected; workers must not edit them.
- Preconditions: Accelerate agent_supervisor planning, control Doctor, and todo_daemon packages exist on the pin under test.
- Effects: Parseable objective/goal/task program with DAG validator and scheduler stub; unlocks foundation tasks.
- Evidence subset: architecture, goals, task DAG, ownership, acceptance
- Acceptance: Validator proves unique WPD tasks, all goals, acyclicity, and that WPD-001–003 become ready after WPD-000; scheduler disables objective refill into protected paths; no LLM/Doctor/provider is claimed as completion authority.
- Embedding query: seal worker planner doctor objective goal taskboard control plane

## WPD-001 Define implementation disposition and dual-view kernel contracts

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: contracts
- Depends on: WPD-000
- Goal id: WPD-G010
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_disposition.py, external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_disposition.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_disposition.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/contracts
- Parallel lane: wpd-contracts
- Resource class: cpu-small
- Resource stage: analysis
- Implementation timeout seconds: 3600
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_disposition.py, external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_disposition.py
- Interfaces: ImplementationDisposition@1, PreImplementationKernelReceipt@1
- Conflict policy: Own new disposition module only.
- Preconditions: WPD-000 sealed.
- Effects: Closed disposition enum and content-addressed receipt schema shared by worker and supervisor.
- Evidence subset: disposition schema, content identity, reject unknown
- Acceptance: Dispositions include closed_deterministic, residual_llm_authorized, abstain_review, defer_capability; receipt binds task_cid, forest roots, plan/doctor CIDs; forged fields fail closed.
- Embedding query: ImplementationDisposition closed_deterministic residual_llm_authorized receipt

## WPD-002 Define residual LLM packet and bounds

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: contracts
- Depends on: WPD-000
- Goal id: WPD-G010
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/residual_llm_packet.py, external/ipfs_accelerate/test/api/test_agent_supervisor_residual_llm_packet.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_residual_llm_packet.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/contracts
- Parallel lane: wpd-contracts
- Resource class: cpu-small
- Resource stage: analysis
- Implementation timeout seconds: 3600
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/residual_llm_packet.py, external/ipfs_accelerate/test/api/test_agent_supervisor_residual_llm_packet.py
- Interfaces: ResidualLlmPacket@1
- Conflict policy: Align with CodexRepairPacket; do not weaken redaction.
- Preconditions: FormalReplanner CodexRepairPacket exists.
- Effects: Single sealed residual packet type for provider invocation.
- Evidence subset: size bounds, path exactness, redaction, no source body dump
- Acceptance: Packet excludes secrets and unbounded source dumps; requires exact write paths, obligations, counterexample capsule, validation commands; identity is content-addressed.
- Embedding query: ResidualLlmPacket CodexRepairPacket bounds redaction exact paths

## WPD-003 Publish threat model and non-compensable safety floors

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: trust
- Depends on: WPD-000
- Goal id: WPD-G010
- Outputs: external/ipfs_accelerate/docs/architecture/agent_supervisor_worker_planner_doctor_threat_model.md, config/supervisor_worker_planner_doctor_authority_policy.json, external/ipfs_accelerate/test/api/test_agent_supervisor_worker_planner_doctor_authority_policy.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_worker_planner_doctor_authority_policy.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/contracts
- Parallel lane: wpd-contracts
- Resource class: cpu-small
- Resource stage: analysis
- Implementation timeout seconds: 3600
- Predicted files: external/ipfs_accelerate/docs/architecture/agent_supervisor_worker_planner_doctor_threat_model.md, config/supervisor_worker_planner_doctor_authority_policy.json, external/ipfs_accelerate/test/api/test_agent_supervisor_worker_planner_doctor_authority_policy.py
- Interfaces: WorkerPlannerDoctorAuthorityPolicy@1
- Conflict policy: Policy root is protected after review.
- Preconditions: Existing doctor and formal planning policies inventoried.
- Effects: Immutable floor list for unauthorized LLM, false fixed point, scope escape.
- Evidence subset: threat table, zero floors, forbidden transitions
- Acceptance: Policy forbids unauthorized LLM, deterministic-mode network, completion-from-prose, free re-prompt after typed failure, and candidate self-certification; tests encode floors as machine checks.
- Embedding query: threat model safety floors unauthorized LLM free re-prompt

## WPD-010 Production default Deterministic Doctor factory

- Status: active
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: factories
- Depends on: WPD-001, WPD-003
- Goal id: WPD-G020
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/default_doctor_factory.py, external/ipfs_accelerate/test/api/test_agent_supervisor_default_doctor_factory.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_default_doctor_factory.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/factories
- Parallel lane: wpd-factory
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 5400
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/default_doctor_factory.py, external/ipfs_accelerate/scripts/ops/agent_supervisor/deterministic_doctor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_default_doctor_factory.py
- Interfaces: DefaultDoctorFactory@1
- Conflict policy: Compose LPR stages; do not rewrite DoctorService contracts.
- Preconditions: DeterministicDoctorService and stage modules exist.
- Effects: CLI/API defaults bind live checkout stages; empty slots are explicit capability gaps.
- Evidence subset: factory binds inspect/plan backends, checkout-root snapshot, no LLM load
- Acceptance: `build_default_doctor_service(checkout_root=...)` produces inspect/plan results on fixtures; missing backend → typed abstention; `assert_no_llm_surface_loaded` holds for default construction.
- Embedding query: default doctor factory checkout root stage backends capability gap

## WPD-011 Production default planner factory

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: factories
- Depends on: WPD-001, WPD-002
- Goal id: WPD-G020
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/default_planner_factory.py, external/ipfs_accelerate/test/api/test_agent_supervisor_default_planner_factory.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_default_planner_factory.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/factories
- Parallel lane: wpd-factory
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 5400
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/default_planner_factory.py, external/ipfs_accelerate/test/api/test_agent_supervisor_default_planner_factory.py
- Interfaces: DefaultPlannerFactory@1
- Conflict policy: Compose formal compiler/validator/replanner/adaptive planner.
- Preconditions: planning package modules exist.
- Effects: One factory returns compiler, validator, replanner, optional proof-carrying planner handles.
- Evidence subset: factory wiring, fail-closed missing optional prover
- Acceptance: Factory builds FormalPlanCompiler/Validator/Replanner; optional provers absent → defer_capability not silent success.
- Embedding query: default planner factory FormalPlanCompiler FormalReplanner AdaptivePlanner

## WPD-012 Worker evidence factory for planning and doctor

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: factories
- Depends on: WPD-001
- Goal id: WPD-G020
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/worker_evidence_factory.py, external/ipfs_accelerate/test/api/test_agent_supervisor_worker_evidence_factory.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_worker_evidence_factory.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/factories
- Parallel lane: wpd-factory
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 5400
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/worker_evidence_factory.py, external/ipfs_accelerate/test/api/test_agent_supervisor_worker_evidence_factory.py
- Interfaces: WorkerEvidenceFactory@1, WorkerEvidenceView@1
- Conflict policy: Prefer existing repository forest / doctor snapshot adapters.
- Preconditions: repository forest and doctor snapshot contracts available.
- Effects: Bounded exact evidence view for pre-implementation kernel.
- Evidence subset: forest binding, dirty overlay, graph/index CIDs, query coverage
- Acceptance: Evidence view is content-addressed; path escape rejected; incomplete required queries mark coverage false rather than inventing facts.
- Embedding query: worker evidence factory forest snapshot query coverage

## WPD-020 Implement PreImplementationKernel.evaluate

- Status: active
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: worker-path
- Depends on: WPD-010, WPD-011, WPD-012, WPD-002
- Goal id: WPD-G030
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/pre_implementation_kernel.py, external/ipfs_accelerate/test/api/test_agent_supervisor_pre_implementation_kernel.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_pre_implementation_kernel.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/worker
- Parallel lane: wpd-worker
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/pre_implementation_kernel.py, external/ipfs_accelerate/test/api/test_agent_supervisor_pre_implementation_kernel.py
- Interfaces: PreImplementationKernel@1
- Conflict policy: Own kernel module; factories remain separate.
- Preconditions: Default factories and disposition/packet contracts exist.
- Effects: Single evaluate() returns disposition + receipts without provider calls.
- Evidence subset: hermetic analytical close, residual authorization, abstain/defer
- Acceptance: Fixture task with unique analytical repair yields closed_deterministic and zero provider hooks; ambiguous case yields abstain_review; missing backend yields defer_capability.
- Embedding query: PreImplementationKernel evaluate disposition analytical close

## WPD-021 Hook ImplementationDaemon before provider invocation

- Status: active
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: worker-path
- Depends on: WPD-020
- Goal id: WPD-G030
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py, external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_daemon_planner_doctor_hook.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_daemon_planner_doctor_hook.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/worker
- Parallel lane: wpd-worker
- Resource class: cpu-large
- Resource stage: implementation
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py, external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_daemon_planner_doctor_hook.py
- Interfaces: ImplementationDaemon@pre_implementation_kernel
- Conflict policy: Minimal hook in _run_implementation; no parallel daemon.
- Preconditions: PreImplementationKernel exists.
- Effects: Provider path unreachable without residual_llm_authorized disposition.
- Evidence subset: event log disposition CID, provider gate unit/integration tests
- Acceptance: Monkeypatched provider asserts not called for closed_deterministic; residual path requires packet; events include kernel receipt identity.
- Embedding query: ImplementationDaemon hook provider gate disposition event

## WPD-022 Analytical close path without LLM

- Status: active
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: worker-path
- Depends on: WPD-020
- Goal id: WPD-G030
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/analytical_close_executor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_analytical_close_executor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_analytical_close_executor.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/worker
- Parallel lane: wpd-worker
- Resource class: cpu-medium
- Resource stage: implementation
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/analytical_close_executor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_analytical_close_executor.py
- Interfaces: AnalyticalCloseExecutor@1
- Conflict policy: Reuse planning transforms and doctor transaction APIs.
- Preconditions: Kernel can select closed_deterministic.
- Effects: Applies admitted analytical edits under existing lease/worktree rules.
- Evidence subset: byte change required for success, rollback on failure
- Acceptance: Success requires real byte mutation when plan expects writes; fake success without mutation rejected; no LLM import.
- Embedding query: analytical close executor deterministic transform no LLM

## WPD-023 Residual provider invocation under sealed packet only

- Status: active
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: worker-path
- Depends on: WPD-021, WPD-002
- Goal id: WPD-G030
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/residual_provider_invocation.py, external/ipfs_accelerate/test/api/test_agent_supervisor_residual_provider_invocation.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_residual_provider_invocation.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/worker
- Parallel lane: wpd-worker
- Resource class: cpu-medium
- Resource stage: implementation
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/residual_provider_invocation.py, external/ipfs_accelerate/test/api/test_agent_supervisor_residual_provider_invocation.py
- Interfaces: ResidualProviderInvocation@1
- Conflict policy: Wrap existing provider execution; do not add new providers.
- Preconditions: Residual packet contract exists; daemon hook exists.
- Effects: Provider argv/context receives only sealed residual fields.
- Evidence subset: prompt body bounds, forbidden full-task dump, path lease
- Acceptance: Oversized or path-escaping packets rejected; provider env excludes secrets; packet CID logged.
- Embedding query: residual provider invocation sealed packet only

## WPD-030 Worker Doctor bridge from validation failures

- Status: active
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: failure-bridge
- Depends on: WPD-010, WPD-021
- Goal id: WPD-G040
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/worker_doctor_bridge.py, external/ipfs_accelerate/test/api/test_agent_supervisor_worker_doctor_bridge.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_worker_doctor_bridge.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/failure
- Parallel lane: wpd-worker
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/worker_doctor_bridge.py, external/ipfs_accelerate/test/api/test_agent_supervisor_worker_doctor_bridge.py
- Interfaces: WorkerDoctorBridge@1
- Conflict policy: Map failures to DoctorOperationRequest only.
- Preconditions: Default doctor factory available.
- Effects: Validation/scope/proof failures become inspect/plan requests with exact roots.
- Evidence subset: mapping table, no network, typed abstention
- Acceptance: Known failure classes produce Doctor inspect; unknown → abstain_review; never opens LLM.
- Embedding query: worker doctor bridge validation failure inspect plan

## WPD-031 Formal replan + failure memory on retry

- Status: active
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: failure-bridge
- Depends on: WPD-011, WPD-030, WPD-002
- Goal id: WPD-G040
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/failure_replan_policy.py, external/ipfs_accelerate/test/api/test_agent_supervisor_failure_replan_residual.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_failure_replan_residual.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/failure
- Parallel lane: wpd-worker
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/failure_replan_policy.py, external/ipfs_accelerate/test/api/test_agent_supervisor_failure_replan_residual.py
- Interfaces: FailureReplanPolicy@1
- Conflict policy: Use FormalReplanner and PlanFailureMemory; bounded retries.
- Preconditions: Formal replan contracts exist.
- Effects: Retry path produces residual packet or abstain; no free re-prompt.
- Evidence subset: budgets, unchanged-failure backoff, packet seal
- Acceptance: Repeated identical failure triggers backoff; replan edits only bound records; residual packet required for LLM retry.
- Embedding query: formal replan failure memory residual packet backoff

## WPD-032 Task execution policy: ban free re-prompt after typed failure

- Status: active
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: failure-bridge
- Depends on: WPD-031, WPD-001
- Goal id: WPD-G040
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/task_execution_policy.py, external/ipfs_accelerate/test/api/test_agent_supervisor_no_free_reprompt_policy.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_no_free_reprompt_policy.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/failure
- Parallel lane: wpd-worker
- Resource class: cpu-small
- Resource stage: analysis
- Implementation timeout seconds: 3600
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/task_execution_policy.py, external/ipfs_accelerate/test/api/test_agent_supervisor_no_free_reprompt_policy.py
- Interfaces: TaskExecutionPolicy@no_free_reprompt
- Conflict policy: Additive policy checks only.
- Preconditions: Disposition and replan policy exist.
- Effects: Policy blocks provider attempts that lack residual authorization after typed failure.
- Evidence subset: policy unit tests
- Acceptance: Attempt N+1 without residual_llm_authorized after typed failure is rejected with stable reason code.
- Embedding query: task execution policy no free re-prompt residual authorized

## WPD-040 Supervisor selection uses dispositions

- Status: active
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: supervisor-control
- Depends on: WPD-021, WPD-001
- Goal id: WPD-G050
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_supervisor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_disposition_selection.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_disposition_selection.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/supervisor
- Parallel lane: wpd-supervisor
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_supervisor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_disposition_selection.py
- Interfaces: SelectionDispositionProjection@1
- Conflict policy: Minimal projection into status/selection_idle_reason.
- Preconditions: Kernel emits dispositions.
- Effects: Scheduler can prefer tasks with closed_deterministic readiness over LLM-heavy residuals under policy.
- Evidence subset: idle reason codes, priority hints
- Acceptance: selection_idle_reason includes doctor/planner disposition classes; provider_capacity_backoff remains distinct.
- Embedding query: selection idle disposition closed_deterministic residual

## WPD-041 Rescue doctor-first before model rescue

- Status: active
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: supervisor-control
- Depends on: WPD-010, WPD-030
- Goal id: WPD-G050
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/rescue_orchestrator.py, external/ipfs_accelerate/test/api/test_agent_supervisor_rescue_doctor_first.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_rescue_doctor_first.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/supervisor
- Parallel lane: wpd-supervisor
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/rescue_orchestrator.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/rescue_planner.py, external/ipfs_accelerate/test/api/test_agent_supervisor_rescue_doctor_first.py
- Interfaces: RescueDoctorFirst@1
- Conflict policy: Doctor inspect is mandatory first stage when enabled by policy.
- Preconditions: Default doctor factory works.
- Effects: Rescue receipts show doctor stage before optional model preview.
- Evidence subset: ordered stages, skip model when doctor closes
- Acceptance: Fixture recoverable by doctor never invokes model rescue path.
- Embedding query: rescue doctor first model rescue residual

## WPD-042 Refill and backlog guards for residual rules

- Status: active
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: supervisor-control
- Depends on: WPD-032, WPD-003
- Goal id: WPD-G050
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/adaptive_goal_refiner.py, external/ipfs_accelerate/test/api/test_agent_supervisor_refill_residual_guard.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_refill_residual_guard.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/supervisor
- Parallel lane: wpd-supervisor
- Resource class: cpu-small
- Resource stage: analysis
- Implementation timeout seconds: 5400
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/finding_task_source.py, external/ipfs_accelerate/test/api/test_agent_supervisor_refill_residual_guard.py
- Interfaces: RefillResidualGuard@1
- Conflict policy: Guards only; no automatic objective heap mutation of WPD control files.
- Preconditions: Authority policy exists.
- Effects: Refilled tasks inherit residual/LLM rules and cannot drop doctor preconditions.
- Evidence subset: guard unit tests
- Acceptance: Generated refill tasks require pre-implementation kernel flag and cannot mark residual_llm_authorized without packet schema.
- Embedding query: refill residual guard task source doctor precondition

## WPD-050 LLM-avoidance metrics and attempt attribution

- Status: active
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: metrics
- Depends on: WPD-001, WPD-021
- Goal id: WPD-G060
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/llm_avoidance_metrics.py, external/ipfs_accelerate/test/api/test_agent_supervisor_llm_avoidance_metrics.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_llm_avoidance_metrics.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/metrics
- Parallel lane: wpd-metrics
- Resource class: cpu-small
- Resource stage: analysis
- Implementation timeout seconds: 3600
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/llm_avoidance_metrics.py, external/ipfs_accelerate/test/api/test_agent_supervisor_llm_avoidance_metrics.py
- Interfaces: LlmAvoidanceMetrics@1
- Conflict policy: Observability only; not completion authority.
- Preconditions: Disposition events exist.
- Effects: Per-attempt counters by disposition and provider token estimates.
- Evidence subset: schema, aggregation tests
- Acceptance: Metrics reject negative counts; attribute zero provider calls for closed_deterministic; missing telemetry marked unavailable not zero-success.
- Embedding query: llm avoidance metrics disposition provider tokens

## WPD-051 Preregistered paired LLM-avoidance benchmark

- Status: active
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: metrics
- Depends on: WPD-050, WPD-022, WPD-023
- Goal id: WPD-G060
- Outputs: config/supervisor_worker_planner_doctor_benchmark.json, external/ipfs_accelerate/test/api/test_agent_supervisor_llm_avoidance_benchmark.py, external/ipfs_accelerate/test/fixtures/agent_supervisor/worker_planner_doctor_holdout/manifest.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_llm_avoidance_benchmark.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/metrics
- Parallel lane: wpd-metrics
- Resource class: cpu-large
- Resource stage: validation
- Implementation timeout seconds: 10800
- Predicted files: config/supervisor_worker_planner_doctor_benchmark.json, external/ipfs_accelerate/test/api/test_agent_supervisor_llm_avoidance_benchmark.py, external/ipfs_accelerate/test/fixtures/agent_supervisor/worker_planner_doctor_holdout/manifest.json
- Interfaces: WorkerPlannerDoctorBenchmark@1
- Conflict policy: Holdout and denominators protected after seal.
- Preconditions: Metrics module and worker paths exist.
- Effects: Baseline (provider-first mock) vs challenger (kernel-first) on fixed fixtures.
- Evidence subset: quality non-inferiority, token/call reduction, zero floors
- Acceptance: Challenger shows lower provider calls on analytical corpus; quality oracle non-inferior; safety floors zero; synthetic-only runs cannot promote.
- Embedding query: paired benchmark LLM avoidance baseline challenger holdout

## WPD-060 Adversarial residual and scope-escape suite

- Status: active
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: adversarial
- Depends on: WPD-023, WPD-032, WPD-003
- Goal id: WPD-G070
- Outputs: external/ipfs_accelerate/test/api/test_agent_supervisor_worker_planner_doctor_adversarial.py, external/ipfs_accelerate/test/fixtures/agent_supervisor/worker_planner_doctor_adversarial/
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_worker_planner_doctor_adversarial.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/release
- Parallel lane: wpd-release
- Resource class: cpu-medium
- Resource stage: validation
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/test/api/test_agent_supervisor_worker_planner_doctor_adversarial.py, external/ipfs_accelerate/test/fixtures/agent_supervisor/worker_planner_doctor_adversarial/
- Interfaces: WorkerPlannerDoctorAdversarialSuite@1
- Conflict policy: Tests and fixtures only.
- Preconditions: Residual packet and policy exist.
- Effects: Suite covering prompt injection, path escape, secret exfil attempts, free re-prompt, forged disposition.
- Evidence subset: each attack class fail-closed
- Acceptance: All adversarial fixtures fail closed with typed codes; zero writes outside lease; zero unauthorized provider calls.
- Embedding query: adversarial residual prompt injection path escape free re-prompt

## WPD-061 Staged rollout controls for kernel-first default

- Status: active
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: rollout
- Depends on: WPD-021, WPD-050
- Goal id: WPD-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/worker_planner_doctor_rollout.py, external/ipfs_accelerate/test/api/test_agent_supervisor_worker_planner_doctor_rollout.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_worker_planner_doctor_rollout.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/release
- Parallel lane: wpd-release
- Resource class: cpu-small
- Resource stage: analysis
- Implementation timeout seconds: 5400
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/worker_planner_doctor_rollout.py, external/ipfs_accelerate/test/api/test_agent_supervisor_worker_planner_doctor_rollout.py
- Interfaces: WorkerPlannerDoctorRollout@1
- Conflict policy: Align with doctor/formal planning rollout ladders.
- Preconditions: Metrics and hook exist.
- Effects: shadow → read → auto_safe promotion with kill switch.
- Evidence subset: mode transitions, rollback
- Acceptance: Default mode shadow does not change mutation authority; auto_safe requires floors and benchmark gates.
- Embedding query: worker planner doctor rollout shadow read auto_safe

## WPD-070 Terminal current-tree release gate

- Status: active
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: release
- Depends on: WPD-040, WPD-041, WPD-042, WPD-051, WPD-060, WPD-061
- Goal id: WPD-G070
- Outputs: external/ipfs_accelerate/docs/architecture/WORKER_PLANNER_DOCTOR_RELEASE.md, external/ipfs_accelerate/test/api/test_agent_supervisor_worker_planner_doctor_release.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/worker_planner_doctor_release.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_worker_planner_doctor_release.py -q
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Bundle: wpd/release
- Parallel lane: wpd-release
- Resource class: cpu-medium
- Resource stage: validation
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/docs/architecture/WORKER_PLANNER_DOCTOR_RELEASE.md, external/ipfs_accelerate/test/api/test_agent_supervisor_worker_planner_doctor_release.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/worker_planner_doctor_release.py
- Interfaces: WorkerPlannerDoctorRelease@1
- Conflict policy: Unique terminal sink; depends on all prior goals' evidence.
- Preconditions: All non-terminal WPD tasks complete with current-tree evidence.
- Effects: Single release receipt for operator promotion of kernel-first defaults.
- Evidence subset: forest, policy, floors, benchmark, adversarial, rollout
- Acceptance: Release fails if any safety floor non-zero, benchmark missing, or unauthorized LLM path remains open; receipt is content-addressed and replayable.
- Embedding query: terminal release worker planner doctor current tree gate

## WPD-071 Resolve 1 dirty backlogged worktrees blocked by unsupported_status

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: true
- Blocked reason: operator_reconciliation_required
- Priority: P1
- Track: ops
- Generated by: ipfs_accelerate_py.agent_supervisor.reconciliation-guardrail@1
- Reconciliation kind: dirty_backlogged_worktree
- Reconciliation reason: unsupported_status
- Reconciliation fingerprint: 2813508cb1969ac861e1fd9853a81a64e4deba2a
- Reconciliation discovery: /home/barberb/.local/state/ipfs_accelerate_py/worker-planner-doctor-v1/state/discovery/2026-08-06-wpd-071-reconciliation-2813508cb196.md
- Canonical board task: false
- Fingerprint: 2813508cb1969ac861e1fd9853a81a64e4deba2a
- Dedupe key: reconciliation_guardrail:dirty_backlogged_worktree:unsupported_status
- Depends on:
- Outputs: implementation_plan/docs/47-supervisor-worker-planner-doctor-integration.todo.md
- Board namespace: agent-supervisor-worker-planner-doctor-v1
- Goal id: WPD-G000
- Bundle: wpd/control
- Parallel lane: wpd-control
- Resource class: cpu-small
- Validation: test -f /home/barberb/.local/state/ipfs_accelerate_py/worker-planner-doctor-v1/state/discovery/2026-08-06-wpd-071-reconciliation-2813508cb196.md
- Acceptance: Reconciliation guardrail filed this because 1 branch or worktree cleanup candidates are blocked by unsupported_status. This task is intentionally operator-gated because unknown dirty checkout content must not be committed, stashed, or discarded automatically. Use evidence and the machine-readable reconciliation plan in /home/barberb/.local/state/ipfs_accelerate_py/worker-planner-doctor-v1/state/discovery/2026-08-06-wpd-071-reconciliation-2813508cb196.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.

## WPD-072 Resolve validation retry-budget failure for WPD-010

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: WPD-001, WPD-003
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/default_doctor_factory.py, external/ipfs_accelerate/test/api/test_agent_supervisor_default_doctor_factory.py
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_default_doctor_factory.py -q
- Parallel lane: wpd-factory
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/default_doctor_factory.py, external/ipfs_accelerate/scripts/ops/agent_supervisor/deterministic_doctor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_default_doctor_factory.py
- Conflict policy: Compose LPR stages; do not rewrite DoctorService contracts.
- Generated by: ipfs_accelerate_py.agent_supervisor.retry-budget-repair@1
- Retry repair source: WPD-010
- Retry failure kind: validation
- Retry repair discovery: /home/barberb/.local/state/ipfs_accelerate_py/worker-planner-doctor-v1/state/discovery/2026-08-06-wpd-072-wpd-010-retry-budget.md
- Canonical board task: false

- Acceptance: Retry-budget guardrail filed this from repeated validation failures in WPD-010. Use evidence in /home/barberb/.local/state/ipfs_accelerate_py/worker-planner-doctor-v1/state/discovery/2026-08-06-wpd-072-wpd-010-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release WPD-010 from strategy blocked_tasks. The declared validation target paths (external/ipfs_accelerate/test/api/test_agent_supervisor_default_doctor_factory.py) are bounded diagnostic/read-only metadata: they may be inspected and used to focus validation, but do not grant write authority. Repair edits remain limited to the source task Outputs; do not weaken correct assertions or policy.
