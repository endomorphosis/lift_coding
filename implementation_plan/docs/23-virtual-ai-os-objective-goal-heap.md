# Virtual AI OS Objective Goal Heap

This document is the objective model for supervisor-fed backlog discovery. It is
separate from the task board on purpose: the task board says what to do next,
while this heap says what the system must eventually prove.

The heap is represented as flat markdown records so the todo supervisor can parse
and refine it without a bespoke database. `Parent` forms the hierarchy, and
`Fib priority` gives the scanner a stable Fibonacci-style ordering. Lower numbers
are closer to the root objective and should be satisfied before wider refinements.

## VAIOS-G000 Virtual AI OS outcome

- Status: active
- Parent:
- Fib priority: 1
- Track: ops
- Priority: P0
- Goal: The monorepo and submodules operate as one virtualized AI operating system with Meta glasses as a remote audio/display terminal.
- Evidence: virtual AI OS, capability registry, runtime router, Meta glasses remote terminal, tests/test_virtual_ai_os_end_to_end.py
- Outputs: implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, docs, tests
- Validation: PYTHONPATH=external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -k objective_goal
- Refinement: Add child goals when a missing proof cannot be closed by one focused task.
- Gap task: Close the highest-leverage missing proof that the component stack behaves like one virtual AI OS instead of disconnected demos.

## VAIOS-G010 Objective-driven supervisor loop

- Status: active
- Parent: VAIOS-G000
- Fib priority: 2
- Track: ops
- Priority: P1
- Goal: The supervisor keeps the Codex loop fed from objective gaps, not only from TODO annotations.
- Evidence: objective_goal_scan, objective_goal_seen_fingerprints, last_objective_goal_scan_findings, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Outputs: scripts/hallucinate_multimodal_control_todo_daemon.py, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: PYTHONPATH=external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -k objective_goal
- Refinement: Split into scoring, evidence indexing, and task-generation children if the scanner becomes too broad.
- Gap task: Wire an objective-gap scanner into the supervisor loop and prove it can emit daemon-parseable tasks.

## VAIOS-G020 Capability routing kernel

- Status: active
- Parent: VAIOS-G000
- Fib priority: 3
- Track: runtime
- Priority: P1
- Goal: Stable capability ids route work across local Python, daemon tasks, MCP/MCP++, SwissKnife ORB, Hallucinate App, and mobile/glasses surfaces.
- Evidence: capability registry, runtime router, src/handsfree/capability_registry.py, tests/test_virtual_ai_os_capability_registry.py, tests/test_virtual_ai_os_runtime_router.py
- Outputs: src/handsfree, tests
- Validation: pytest tests/test_virtual_ai_os_capability_registry.py tests/test_virtual_ai_os_runtime_router.py
- Refinement: Add child goals for scheduler policy, fallback routing, and normalized error contracts.
- Gap task: Add or tighten routing evidence for any execution mode that is named in the architecture but not exercised by tests.

## VAIOS-G030 IDL, ORB, and MCP++ bridge

- Status: active
- Parent: VAIOS-G000
- Fib priority: 5
- Track: runtime
- Priority: P1
- Goal: Interface descriptor language records voice, gesture, mouse, and agent controls, then dispatches them through ORB/MCP++ with policy mediation.
- Evidence: interface descriptor language, object request broker, mcp_plus_plus, control surface, deontic logic, event calculus, frame logic
- Outputs: hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md, swissknife, external/ipfs_datasets
- Validation: PYTHONPATH=external/ipfs_datasets:hallucinate_app/python python3 hallucinate_app/python/hallucinate_app/test/test_control_surface_policy_ipfs_logic.py
- Refinement: Add child goals for each control modality when a modality lacks descriptor, policy, and dispatch evidence.
- Gap task: Close the weakest modality-to-policy-to-dispatch proof in the IDL/ORB/MCP++ bridge.

## VAIOS-G040 Operator shell and virtual desktop

- Status: active
- Parent: VAIOS-G000
- Fib priority: 8
- Track: ui
- Priority: P1
- Goal: SwissKnife and Hallucinate App provide a usable operator shell for sessions, daemon state, tools, and virtual desktop workflows.
- Evidence: SwissKnife virtual desktop, Hallucinate App operator console, daemon manager, ORB display harness, test/mcp-plus-plus/meta-glasses-display-harness.test.ts
- Outputs: swissknife, hallucinate_app, tests
- Validation: test -f hallucinate_app/docs/SWISSKNIFE_VIRTUAL_DESKTOP_MOCKUP.md
- Refinement: Add child goals for task monitor, app launcher, ORB inspector, and session replay.
- Gap task: Add missing shell evidence that connects daemon state, ORB tools, and operator-visible UI.

## VAIOS-G050 Meta glasses remote terminal

- Status: active
- Parent: VAIOS-G000
- Fib priority: 13
- Track: mobile
- Priority: P1
- Goal: Meta glasses act as a remote audio/display interface for the virtual AI OS, with simulator-first coverage before iPhone handoff.
- Evidence: Meta Ray-Ban simulator, 600x600, DAT Mock Device, mobile glasses bridge, display widget, audio routing, tests/test_meta_glasses_display_simulator.py
- Outputs: mobile, docs, tests, implementation_plan/docs/20-meta-rayban-display-interface-simulator.md
- Validation: test -f implementation_plan/docs/20-meta-rayban-display-interface-simulator.md
- Refinement: Add child goals for display, audio, action receipts, fallback rendering, and physical-device evidence.
- Gap task: Add missing simulator or bridge evidence so glasses can be treated as a terminal, not only a notification endpoint.

## VAIOS-G060 Content, provenance, and durable artifacts

- Status: active
- Parent: VAIOS-G000
- Fib priority: 21
- Track: data
- Priority: P2
- Goal: Work products, model outputs, datasets, UI descriptors, and run logs have durable IPFS provenance and can be replayed by the OS.
- Evidence: ipfs_kit, provenance, artifact manifest, content address, dataset, tests/test_virtual_ai_os_task_orchestration.py
- Outputs: external/ipfs_kit, external/ipfs_datasets, src/handsfree, tests
- Validation: pytest tests/test_virtual_ai_os_task_orchestration.py
- Refinement: Add child goals for artifact schemas, replay, pinning, and rollback.
- Gap task: Add missing artifact/provenance evidence for the highest-risk workflow.

## VAIOS-G070 Execution placement and acceleration

- Status: active
- Parent: VAIOS-G000
- Fib priority: 34
- Track: runtime
- Priority: P2
- Goal: The OS scheduler can choose local, accelerated, daemon, and remote execution paths without changing capability semantics.
- Evidence: ipfs_accelerate, execution placement, accelerated inference, scheduler, fallback mode
- Outputs: external/ipfs_accelerate, src/handsfree, tests
- Validation: rg -n "execution placement|ipfs_accelerate|fallback mode" docs implementation_plan src tests
- Refinement: Add child goals for placement policy, batching, fallback, and observability.
- Gap task: Add routing or test evidence for the weakest execution-placement path.

## VAIOS-G080 End-to-end validation lattice

- Status: active
- Parent: VAIOS-G000
- Fib priority: 55
- Track: quality
- Priority: P1
- Goal: The system has layered tests that prove planner, router, storage, UI, mobile, glasses, and daemon behavior without requiring hardware in every run.
- Evidence: tests/test_virtual_ai_os_end_to_end.py, Playwright, mobile bridge tests, SwissKnife Jest, Hallucinate App e2e, hardware-free
- Outputs: tests, mobile, swissknife, hallucinate_app
- Validation: pytest tests/test_virtual_ai_os_end_to_end.py
- Refinement: Add child goals for each untested integration path in the test matrix.
- Gap task: Add the next missing hardware-free integration test that ties at least two planes together.
