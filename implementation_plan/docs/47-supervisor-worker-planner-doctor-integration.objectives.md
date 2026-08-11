# Supervisor Worker Planner–Doctor Integration Objective Heap (WPD)

Machine-ingestible objective state for `ipfs_accelerate_py.agent_supervisor`.
The executable board is
`implementation_plan/docs/47-supervisor-worker-planner-doctor-integration.todo.md`
with task prefix `## WPD-`. The reviewed architecture is
`implementation_plan/docs/47-supervisor-worker-planner-doctor-integration-plan-2026-08-06.md`.

## North star

Wire the existing Planner and Deterministic Doctor into the **default live
paths** of the agent supervisor and implementation workers so deterministic
analysis, formal planning, and doctor repair close as much work as evidence
allows, and language models are used only for sealed residual packets—never as
the first or only reasoning step.

## Goal tree

```text
WPD-G000  Deterministic-first planner/doctor in live supervisor & workers
|-- WPD-G010  Contracts, authority ladder, dual-view kernel
|-- WPD-G020  Default evidence + Doctor + planner factories
|-- WPD-G030  Pre-implementation kernel on the worker path
|-- WPD-G040  Failure → doctor replan → residual packet
|-- WPD-G050  Supervisor selection, retry, rescue, refill integration
|-- WPD-G060  Metrics, paired benchmark, and LLM-avoidance proof
`-- WPD-G070  Adversarial floors, rollout, and terminal release
```

## WPD-G000 Deterministic-first planner/doctor in live supervisor & workers

- Status: active
- Parent:
- Depends on:
- Fib priority: 1
- Priority: P0
- Track: worker-planner-doctor
- Bundle: wpd/root
- Goal: Deliver a production default where implementation workers and supervisor control loops invoke planner/doctor composition before any residual LLM call, with typed dispositions, zero unauthorized model invocations, and measured reduction in provider dependence.
- Evidence: wpd/pre-implementation-kernel@1, wpd/zero-unauthorized-llm@1, wpd/llm-avoidance-benchmark@1, wpd/terminal-release@1
- Acceptance criteria: wpd/pre-implementation-kernel@1; wpd/zero-unauthorized-llm@1; wpd/llm-avoidance-benchmark@1; wpd/terminal-release@1
- Outputs: implementation_plan/docs/47-supervisor-worker-planner-doctor-integration-plan-2026-08-06.md, implementation_plan/docs/47-supervisor-worker-planner-doctor-integration.objectives.md, implementation_plan/docs/47-supervisor-worker-planner-doctor-integration.todo.md, config/supervisor_worker_planner_doctor_integration_scheduler.json
- Validation: python3 scripts/validate_supervisor_worker_planner_doctor_board.py --check-all
- Acceptance: Every child goal has current typed evidence; hermetic analytical tasks complete with zero provider calls; residual LLM only under sealed packets; safety floors remain zero; terminal release binds the current forest and policy.
- Gap task: WPD-000 through WPD-070
- Refinement: Separate contracts, factories, worker kernel, failure bridge, supervisor hooks, metrics, and release so lanes stay file-disjoint.
- Embedding query: pre-implementation kernel deterministic doctor formal planner residual LLM implementation worker supervisor
- AST query: Locate ImplementationDaemon._run_implementation, DeterministicDoctorService, FormalReplanner, ProofCarryingPlanner, AdaptivePlanner, and provider invocation sites.

## WPD-G010 Contracts, authority ladder, dual-view kernel

- Status: active
- Parent: WPD-G000
- Depends on:
- Fib priority: 2
- Priority: P0
- Track: foundation-contracts
- Bundle: wpd/contracts
- Goal: Define finite disposition, residual-packet, and authority records so planner and doctor share one kernel vocabulary and LLM residual is an explicit admitted class—not an implicit fallback.
- Evidence: wpd/implementation-disposition@1, wpd/residual-llm-packet@1, wpd/authority-ladder@1, wpd/threat-model@1
- Acceptance criteria: wpd/implementation-disposition@1; wpd/residual-llm-packet@1; wpd/authority-ladder@1; wpd/threat-model@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_disposition.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/residual_llm_packet.py, external/ipfs_accelerate/docs/architecture/agent_supervisor_worker_planner_doctor_threat_model.md
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_disposition.py external/ipfs_accelerate/test/api/test_agent_supervisor_residual_llm_packet.py -q
- Acceptance: Dispositions are closed enums; residual packets are body-bounded and path-exact; unauthorized residual is rejected; threat model lists non-compensable floors.
- Gap task: WPD-001, WPD-002, WPD-003
- Refinement: Keep schemas independent of daemon so tests can hermetic-check without providers.
- Embedding query: ImplementationDisposition residual LLM packet authority ladder doctor planner dual view
- AST query: Find FormalReplanner CodexRepairPacket schemas and DoctorOperation enums for alignment.

## WPD-G020 Default evidence + Doctor + planner factories

- Status: active
- Parent: WPD-G000
- Depends on: WPD-G010
- Fib priority: 3
- Priority: P0
- Track: production-factories
- Bundle: wpd/factories
- Goal: Provide production factories that bind live checkout evidence, Doctor stage backends, and planner compiler/validator/replanner so CLI/API defaults never ship with empty injected slots.
- Evidence: wpd/default-doctor-factory@1, wpd/default-planner-factory@1, wpd/evidence-factory@1, wpd/cold-import-hygiene@1
- Acceptance criteria: wpd/default-doctor-factory@1; wpd/default-planner-factory@1; wpd/evidence-factory@1; wpd/cold-import-hygiene@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/default_doctor_factory.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/default_planner_factory.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/worker_evidence_factory.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_default_doctor_factory.py external/ipfs_accelerate/test/api/test_agent_supervisor_default_planner_factory.py external/ipfs_accelerate/test/api/test_agent_supervisor_worker_evidence_factory.py -q
- Acceptance: Default factories build real snapshots from `--checkout-root`; missing optional backends yield typed capability gaps; cold import loads no network clients.
- Gap task: WPD-010, WPD-011, WPD-012
- Refinement: Reuse PDR/LPR stage modules; only composition is new.
- Embedding query: default doctor factory planner factory live checkout evidence snapshot capability probe
- AST query: Locate DeterministicDoctorService constructors and unbound stage Protocol fields.

## WPD-G030 Pre-implementation kernel on the worker path

- Status: active
- Parent: WPD-G000
- Depends on: WPD-G020
- Fib priority: 5
- Priority: P0
- Track: worker-path
- Bundle: wpd/worker
- Goal: Insert a mandatory pre-implementation kernel evaluation into ImplementationDaemon so every attempt records a disposition before provider invocation, and deterministic closes skip the model entirely.
- Evidence: wpd/pre-implementation-kernel@1, wpd/daemon-hook@1, wpd/analytical-close@1, wpd/provider-gate@1
- Acceptance criteria: wpd/pre-implementation-kernel@1; wpd/daemon-hook@1; wpd/analytical-close@1; wpd/provider-gate@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/pre_implementation_kernel.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py, external/ipfs_accelerate/test/api/test_agent_supervisor_pre_implementation_kernel.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_pre_implementation_kernel.py external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_daemon_planner_doctor_hook.py -q
- Acceptance: Kernel runs after claim eligibility and before provider; closed_deterministic path never calls providers; residual path requires sealed packet; events emit disposition CIDs.
- Gap task: WPD-020, WPD-021, WPD-022, WPD-023
- Refinement: Keep hook thin; logic lives in kernel + factories.
- Embedding query: pre implementation kernel ImplementationDaemon provider gate analytical close disposition
- AST query: ImplementationDaemon._run_implementation and provider command builders.

## WPD-G040 Failure → doctor replan → residual packet

- Status: active
- Parent: WPD-G000
- Depends on: WPD-G030
- Fib priority: 5
- Priority: P0
- Track: failure-bridge
- Bundle: wpd/failure
- Goal: On validation, scope, or proof failure, bridge to Doctor inspect/plan and FormalReplanner before any new free-form provider attempt; residual LLM uses only sealed packets.
- Evidence: wpd/worker-doctor-bridge@1, wpd/formal-replan-on-failure@1, wpd/retry-without-free-reprompt@1
- Acceptance criteria: wpd/worker-doctor-bridge@1; wpd/formal-replan-on-failure@1; wpd/retry-without-free-reprompt@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/worker_doctor_bridge.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/task_execution_policy.py, external/ipfs_accelerate/test/api/test_agent_supervisor_worker_doctor_bridge.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_worker_doctor_bridge.py external/ipfs_accelerate/test/api/test_agent_supervisor_failure_replan_residual.py -q
- Acceptance: Failure fixtures never re-inject full task bodies as the sole context; replan budgets and failure memory apply; unauthorized second LLM call is blocked.
- Gap task: WPD-030, WPD-031, WPD-032
- Refinement: Align with PlanFailureMemory and CodexRepairPacket existing contracts.
- Embedding query: validation failure doctor inspect formal replan residual packet no free re-prompt
- AST query: FormalReplanner, PlanFailureMemory, validation failure handlers in daemon.

## WPD-G050 Supervisor selection, retry, rescue, refill integration

- Status: active
- Parent: WPD-G000
- Depends on: WPD-G040
- Fib priority: 8
- Priority: P1
- Track: supervisor-control
- Bundle: wpd/supervisor
- Goal: Make supervisor selection, idle reasons, rescue, and refill prefer planner/doctor dispositions over blind provider retries or queue thrash.
- Evidence: wpd/selection-disposition@1, wpd/rescue-doctor-first@1, wpd/refill-guard@1
- Acceptance criteria: wpd/selection-disposition@1; wpd/rescue-doctor-first@1; wpd/refill-guard@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_supervisor.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/rescue_orchestrator.py, external/ipfs_accelerate/test/api/test_agent_supervisor_disposition_selection.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_disposition_selection.py external/ipfs_accelerate/test/api/test_agent_supervisor_rescue_doctor_first.py -q
- Acceptance: selection_idle_reason and retry policies encode doctor/planner dispositions; rescue previews call Doctor inspect before model rescue; refill cannot bypass residual rules.
- Gap task: WPD-040, WPD-041, WPD-042
- Refinement: Minimal surface changes; no second supervisor.
- Embedding query: selection idle doctor disposition rescue planner first refill guard
- AST query: implementation_supervisor selection, rescue_orchestrator, refill paths.

## WPD-G060 Metrics, paired benchmark, and LLM-avoidance proof

- Status: active
- Parent: WPD-G000
- Depends on: WPD-G030, WPD-G040
- Fib priority: 8
- Priority: P1
- Track: metrics-benchmark
- Bundle: wpd/metrics
- Goal: Attribute every attempt to disposition classes and prove on a fixed corpus that provider tokens/calls drop without safety-floor violations or quality loss.
- Evidence: wpd/llm-avoidance-metrics@1, wpd/paired-benchmark@1
- Acceptance criteria: wpd/llm-avoidance-metrics@1; wpd/paired-benchmark@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/llm_avoidance_metrics.py, external/ipfs_accelerate/test/api/test_agent_supervisor_llm_avoidance_benchmark.py, config/supervisor_worker_planner_doctor_benchmark.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_llm_avoidance_metrics.py external/ipfs_accelerate/test/api/test_agent_supervisor_llm_avoidance_benchmark.py -q
- Acceptance: Metrics distinguish closed_deterministic vs residual_llm vs abstain; benchmark is preregistered; promotion requires non-inferior quality and zero floors.
- Gap task: WPD-050, WPD-051
- Refinement: Reuse PDR benchmark patterns; protect oracles.
- Embedding query: LLM avoidance metrics tokens provider calls paired benchmark disposition
- AST query: Existing doctor/prompt workflow benchmark modules for composition.

## WPD-G070 Adversarial floors, rollout, and terminal release

- Status: active
- Parent: WPD-G000
- Depends on: WPD-G050, WPD-G060
- Fib priority: 13
- Priority: P0
- Track: release
- Bundle: wpd/release
- Goal: Prove adversarial resistance of residual boundaries and ship a staged rollout with a single terminal release gate for the worker planner–doctor default path.
- Evidence: wpd/adversarial-residual@1, wpd/rollout@1, wpd/terminal-release@1
- Acceptance criteria: wpd/adversarial-residual@1; wpd/rollout@1; wpd/terminal-release@1
- Outputs: external/ipfs_accelerate/test/api/test_agent_supervisor_worker_planner_doctor_adversarial.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/worker_planner_doctor_rollout.py, external/ipfs_accelerate/docs/architecture/WORKER_PLANNER_DOCTOR_RELEASE.md
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_worker_planner_doctor_adversarial.py external/ipfs_accelerate/test/api/test_agent_supervisor_worker_planner_doctor_release.py -q
- Acceptance: Prompt injection in residual context cannot escalate scope; shadow→read→auto_safe ladder is explicit; terminal receipt binds forest, policy, zero floors, and benchmark.
- Gap task: WPD-060, WPD-061, WPD-070
- Refinement: Align with existing formal planning and doctor rollout ladders.
- Embedding query: adversarial residual LLM scope escape rollout terminal release worker planner doctor
- AST query: formal_planning_rollout, deterministic_doctor_rollout patterns.
