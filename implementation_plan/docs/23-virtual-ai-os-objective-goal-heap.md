# Virtual AI OS Objective Goal Heap

This document is the objective model for supervisor-fed backlog discovery. It is
separate from the task board on purpose: the task board says what to do next,
while this heap says what the system must eventually prove.

The heap is represented as flat markdown records so the backlog supervisor can parse
and refine it without a bespoke database. `Parent` forms the hierarchy, and
`Fib priority` gives the scanner a stable Fibonacci-style ordering. Lower numbers
are closer to the root objective and should be satisfied before wider refinements.

## Graph And Bundling Contract

Each `VAIOS-G*` record is a node in the objective graph. `Parent` or `Parents`
creates directed refinement edges from higher-level goals to concrete subgoals.
`Fib priority` keeps root, Fibonacci-ranked goals ahead of broad refinements.
`Refinement depth` records the intended decomposition depth so the supervisor can
compare explicit design intent with the parsed graph depth.

`Evidence` terms are matched by exact text, repository paths, AST symbols, and
deterministic sentence-style token embeddings. `Embedding query` describes the
semantic search target, while `AST query` names code symbols, modules, or schema
terms that should satisfy the goal.

`Bundle` assigns generated backlog records to a conflict-reduction lane. The daemon
mirrors each generated task into the fenced shard path:
```text
data/hallucinate_multimodal_control/objective_bundles/<safe-bundle>.todo.md
```
It also updates `data/hallucinate_multimodal_control/objective_bundles/index.json`. Parallel workers should claim one bundle shard at a time.
If a shard still collides at merge time, `Conflict policy` tells the LLM merge resolver how to preserve lane intent before unblocking the source task.

## VAIOS-G000 Virtual AI OS outcome

- Status: completed
- Parent:
- Fib priority: 1
- Track: ops
- Priority: P0
- Bundle: objective/ops/root
- Parallel lane: root-operating-system
- Refinement depth: 0
- Embedding query: virtualized AI operating system Meta glasses remote audio display terminal monorepo
- AST query: capability registry, runtime router, meta_glasses_terminal_e2e_contract
- Conflict policy: protect root architecture contracts; use LLM merge resolver for semantic conflicts across docs, tests, and routing code
- Goal: The monorepo and submodules operate as one virtualized AI operating system with Meta glasses as a remote audio/display terminal.
- Evidence: virtual AI OS, capability registry, runtime router, Meta glasses remote terminal, tests/test_virtual_ai_os_end_to_end.py
- Outputs: implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, docs, tests
- Validation: test -f docs/observability_metrics.md && test -f tests/test_virtual_ai_os_end_to_end.py
- HAO-060 proof: `docs/observability_metrics.md` records the Meta glasses remote terminal evidence term outside the objective heap, and `tests/test_hallucinate_multimodal_control_todo_queue.py` verifies the scanner treats that tracked proof as covered.
- Refinement: Add child goals when a missing proof cannot be closed by one focused task.
- Gap task: Close the highest-leverage missing proof that the component stack behaves like one virtual AI OS instead of disconnected demos.
- Completed at: 2026-05-31T07:38:46.698317+00:00
- Completion evidence: virtual AI OS => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/android/termux_phone_dispatcher.py (ast); capability registry => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast); runtime router => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/reference_mobile_client.py (ast); Meta glasses remote terminal => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), docs/observability_metrics.md (exact); tests/test_virtual_ai_os_end_to_end.py => tests/test_virtual_ai_os_end_to_end.py (path), CONTRIBUTING.md (ast), agent-runner/apply_instruction.py (ast)
- Completion validation: 0

## VAIOS-G010 Objective-driven supervisor loop

- Status: completed
- Parent: VAIOS-G000
- Fib priority: 2
- Track: ops
- Priority: P1
- Bundle: objective/ops/supervisor-loop
- Parallel lane: supervisor-backlog
- Refinement depth: 1
- Embedding query: objective driven supervisor loop scans goal heap and generates daemon parseable backlog records
- AST query: record_objective_goal_findings, objective_goal_seen_fingerprints, last_objective_goal_scan_findings
- Conflict policy: keep supervisor state schema backward compatible and resolve backlog-record generation conflicts by preserving all unique HAO records
- Goal: The supervisor keeps the Codex loop fed from objective gaps, not only from inline source annotations.
- Evidence: objective_goal_scan, objective_goal_seen_fingerprints, last_objective_goal_scan_findings, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Outputs: scripts/hallucinate_multimodal_control_todo_daemon.py, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: test -f scripts/hallucinate_multimodal_control_todo_daemon.py && test -f tests/test_hallucinate_multimodal_control_todo_queue.py
- HAO-061 proof: `scripts/hallucinate_multimodal_control_todo_daemon.py` exposes `OBJECTIVE_GOAL_SCAN_EVIDENCE` for `objective_goal_scan`, `objective_goal_seen_fingerprints`, and `last_objective_goal_scan_findings`. `scripts/hallucinate_multimodal_control_todo_supervisor.py` imports that evidence contract while wiring `record_objective_goal_findings` into the supervisor refill hooks, and `tests/test_hallucinate_multimodal_control_todo_queue.py` asserts the configured objective recorder targets the shared objective heap, bundle shard directory, dataset directory, and todo-vector index.
- Refinement: Split into scoring, evidence indexing, and task-generation children if the scanner becomes too broad.
- Gap task: Wire an objective-gap scanner into the supervisor loop and prove it can emit daemon-parseable tasks.
- Completed at: 2026-05-31T07:38:46.698317+00:00
- Completion evidence: objective_goal_scan => implementation_plan/docs/12-github-cli-copilot-integration.md (ast), implementation_plan/docs/12-meta-glasses-ipfs-tool-integration.md (ast), implementation_plan/docs/12-p2p-bluetooth-libp2p.md (ast); objective_goal_seen_fingerprints => implementation_plan/docs/12-github-cli-copilot-integration.md (ast), implementation_plan/docs/12-meta-glasses-ipfs-tool-integration.md (ast), implementation_plan/docs/12-p2p-bluetooth-libp2p.md (ast); last_objective_goal_scan_findings => implementation_plan/docs/12-github-cli-copilot-integration.md (ast), implementation_plan/docs/12-meta-glasses-ipfs-tool-integration.md (ast), implementation_plan/docs/12-p2p-bluetooth-libp2p.md (ast); implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md => implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- Completion validation: 0

## VAIOS-G020 Capability routing kernel

- Status: completed
- Parent: VAIOS-G000
- Fib priority: 3
- Track: runtime
- Priority: P1
- Bundle: objective/runtime/capability-routing
- Parallel lane: runtime-routing
- Refinement depth: 1
- Embedding query: capability ids route work through local daemon MCP SwissKnife Hallucinate App mobile glasses surfaces
- AST query: CapabilityRegistry, RuntimeRouter, dispatch_task, capability_id
- Conflict policy: preserve stable capability ids and add adapters instead of renaming public routing contracts
- Goal: Stable capability ids route work across local Python, daemon tasks, MCP/MCP++, SwissKnife ORB, Hallucinate App, and mobile/glasses surfaces.
- Evidence: capability registry, runtime router, src/handsfree/capability_registry.py, tests/test_virtual_ai_os_capability_registry.py, tests/test_virtual_ai_os_runtime_router.py
- Outputs: src/handsfree, tests
- Validation: test -f tests/test_virtual_ai_os_capability_registry.py && test -f tests/test_virtual_ai_os_runtime_router.py
- HAO-062 proof: `src/handsfree/capability_registry.py` is the scanner-visible capability routing kernel. It exposes `CapabilityRegistry`, `RuntimeRouter`, and `CapabilityRoutingKernel.dispatch_task` while delegating to the existing AI registry/router and naming the local Python, daemon tasks, MCP/MCP++, SwissKnife ORB, Hallucinate App, and mobile/glasses surfaces. `tests/test_virtual_ai_os_capability_registry.py` and `tests/test_virtual_ai_os_runtime_router.py` exercise the top-level path, fallback route planning, and normalized route-planning error contract.
- Refinement: Add child goals for scheduler policy, fallback routing, and normalized error contracts.
- Gap task: Add or tighten routing evidence for any execution mode that is named in the architecture but not exercised by tests.
- Completed at: 2026-05-31T07:38:46.698317+00:00
- Completion evidence: capability registry => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast); runtime router => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/reference_mobile_client.py (ast); src/handsfree/capability_registry.py => src/handsfree/capability_registry.py (path), README.md (embedding:0.42), agent-runner/apply_instruction.py (ast); tests/test_virtual_ai_os_capability_registry.py => tests/test_virtual_ai_os_capability_registry.py (path), CONTRIBUTING.md (ast), agent-runner/apply_instruction.py (ast); tests/test_virtual_ai_os_runtime_router.py => tests/test_virtual_ai_os_runtime_router.py (path), CONTRIBUTING.md (ast), agent-runner/apply_instruction.py (ast)
- Completion validation: 0

## VAIOS-G021 Capability scheduler policy

- Status: active
- Parent: VAIOS-G020
- Fib priority: 3
- Track: runtime
- Priority: P1
- Bundle: objective/runtime/capability-routing/scheduler-policy
- Parallel lane: runtime-routing
- Refinement depth: 2
- Embedding query: capability scheduler policy priority queue placement daemon task dispatch fairness virtual AI OS
- AST query: CapabilitySchedulerPolicy, scheduler_policy, dispatch_task, priority
- Conflict policy: keep capability ids stable and make scheduler policy additive to existing route selection
- Goal: Capability dispatch plans carry scheduler policy metadata for daemon-mediated work without changing stable capability ids.
- Evidence: scheduler policy, capability scheduler, dispatch priority, tests/test_virtual_ai_os_runtime_router.py
- Outputs: src/handsfree, tests
- Validation: rg -n "scheduler policy|CapabilitySchedulerPolicy|scheduler_policy|dispatch priority" src/handsfree tests
- Refinement: Add children for per-surface capacity and fairness only after scheduler metadata lands.
- Gap task: Add scheduler-policy evidence that proves daemon task placement is a policy decision, not a hard-coded side effect.

## VAIOS-G022 Capability fallback routing

- Status: completed
- Parent: VAIOS-G020
- Fib priority: 3
- Track: runtime
- Priority: P1
- Bundle: objective/runtime/capability-routing/fallback-routing
- Parallel lane: runtime-routing
- Refinement depth: 2
- Embedding query: capability fallback routing fallback execution mode degraded surface recovery MCP direct daemon SwissKnife
- AST query: fallback_route, fallback_execution_mode, resolve_fallback_route
- Conflict policy: preserve primary route determinism and add fallback behavior through explicit route metadata
- Goal: Every capability with a fallback execution mode exposes a deterministic fallback route that clients can inspect before execution.
- Evidence: fallback routing, fallback_route, fallback_execution_mode, tests/test_virtual_ai_os_runtime_router.py
- Outputs: src/handsfree, tests
- Validation: rg -n "fallback routing|fallback_route|fallback_execution_mode|resolve_fallback_route" src/handsfree tests
- Refinement: Add children for runtime health scoring and surface-specific fallback receipts if route metadata is not enough.
- Gap task: Add fallback-routing evidence for capabilities whose backup path is named in the registry but not exercised by dispatch tests.
- Completed at: 2026-05-31T07:38:46.698317+00:00
- Completion evidence: fallback routing => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/simulator.js (ast), docs/device-smoke-checklist-ios-meta-glasses.md (embedding:0.33); fallback_route => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/simulator.js (ast), mobile/modules/expo-meta-wearables-dat/index.ts (ast); fallback_execution_mode => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/simulator.js (ast), implementation_plan/docs/12-meta-glasses-ipfs-tool-integration.md (embedding:0.36); tests/test_virtual_ai_os_runtime_router.py => tests/test_virtual_ai_os_runtime_router.py (path), CONTRIBUTING.md (ast), agent-runner/apply_instruction.py (ast)
- Completion validation: 0

## VAIOS-G023 Capability normalized error contracts

- Status: completed
- Parent: VAIOS-G020
- Fib priority: 3
- Track: runtime
- Priority: P1
- Bundle: objective/runtime/capability-routing/error-contracts
- Parallel lane: runtime-routing
- Refinement depth: 2
- Embedding query: normalized error contracts capability route failures API Hallucinate App mobile glasses MCP ORB
- AST query: CapabilityRoutingError, NORMALIZED_ERROR_CONTRACT_ID, build_error_contract
- Conflict policy: keep error envelopes backward compatible and add fields only with safe defaults
- Goal: Route planning and execution failures share one normalized error contract across API, Hallucinate App, mobile/glasses, MCP, and ORB clients.
- Evidence: normalized error contracts, CapabilityRoutingError, NORMALIZED_ERROR_CONTRACT_ID, tests/test_virtual_ai_os_runtime_router.py
- Outputs: src/handsfree, tests
- Validation: rg -n "normalized error contracts|CapabilityRoutingError|NORMALIZED_ERROR_CONTRACT_ID|build_error_contract" src/handsfree tests
- Refinement: Add children for execution-time provider errors and user-facing error rendering once route-planning errors are covered.
- Gap task: Add normalized-error evidence for the next capability failure path that still returns provider-specific strings.
- Completed at: 2026-05-31T07:38:46.698317+00:00
- Completion evidence: normalized error contracts => dev/meta-rayban-display-simulator/webapp/app.js (ast), mobile/push/examples/backend_client.ts (ast), mobile/push/examples/expo_receive_handler.ts (ast); CapabilityRoutingError => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/webapp/app.js (ast), mobile/push/examples/backend_client.ts (ast); NORMALIZED_ERROR_CONTRACT_ID => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/webapp/app.js (ast), mobile/push/examples/backend_client.ts (ast); tests/test_virtual_ai_os_runtime_router.py => tests/test_virtual_ai_os_runtime_router.py (path), CONTRIBUTING.md (ast), agent-runner/apply_instruction.py (ast)
- Completion validation: 0

## VAIOS-G030 IDL, ORB, and MCP++ bridge

- Status: completed
- Parent: VAIOS-G000
- Fib priority: 5
- Track: runtime
- Priority: P1
- Bundle: objective/runtime/idl-orb-mcp
- Parallel lane: idl-orb-bridge
- Refinement depth: 1
- Embedding query: interface descriptor language voice gesture mouse agent controls ORB MCP++ policy mediation logic
- AST query: InterfaceDescriptor, ObjectRequestBroker, mcp_plus_plus, ControlSurfacePolicy
- Conflict policy: keep descriptor schema additive and resolve modality conflicts through policy rules instead of hard-coded precedence
- Goal: Interface descriptor language records voice, gesture, mouse, and agent controls, then dispatches them through ORB/MCP++ with policy mediation.
- Evidence: interface descriptor language, object request broker, mcp_plus_plus, control surface, deontic logic, event calculus, frame logic
- Outputs: hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md, swissknife, external/ipfs_datasets
- Validation: test -f hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md
- HAO-063 proof: `hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md` now names the scanner-visible interface descriptor language proof for `VAIOS-G030`. It ties `control_surface_contract`, `interaction_envelope`, `policy_decision`, and `mediation_receipt` to the ORB/MCP++ mediation path, and records descriptor, policy, and dispatch evidence for voice, gesture, mouse, and agent modalities. Existing modality tests and `swissknife/test/mcp-plus-plus/mcp-orb-capability-router.test.ts` prove all four surfaces reach the same before-dispatch policy gate, so no modality child goals are required by this scan.
- Refinement: Add child goals for each control modality when a modality lacks descriptor, policy, and dispatch evidence.
- Gap task: Close the weakest modality-to-policy-to-dispatch proof in the IDL/ORB/MCP++ bridge.
- Completed at: 2026-05-31T07:38:46.698317+00:00
- Completion evidence: interface descriptor language => mobile/modules/expo-glasses-audio/index.ts (ast), mobile/push/examples/expo_receive_handler.ts (ast), mobile/src/push/notificationsHandler.js (ast); object request broker => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md (exact); mcp_plus_plus => dev/meta-rayban-display-simulator/webapp/app.js (exact), docs/GETTING_STARTED.md (exact), implementation_plan/docs/15-meta-wearables-dat-mcpplusplus-integration-roadmap.md (ast); control surface => dev/meta-rayban-display-simulator/styles.css (embedding:0.34), implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md (ast), implementation_plan/docs/19-virtual-ai-os-submodule-integration.md (exact); deontic logic => implementation_plan/docs/22-multimodal-control-surface-logic-idl.md (exact), mobile/push/examples/expo_receive_handler.ts (ast), mobile/src/screens/CommandScreen.js (ast); event calculus => dev/meta-rayban-display-simulator/simulator.js (ast), dev/meta-rayban-display-simulator/webapp/app.js (ast), implementation_plan/docs/22-multimodal-control-surface-logic-idl.md (exact); frame logic => dev/meta-rayban-display-simulator/simulator.js (ast), implementation_plan/docs/22-multimodal-control-surface-logic-idl.md (exact), mobile/push/examples/expo_receive_handler.ts (ast)
- Completion validation: 0

## VAIOS-G040 Operator shell and virtual desktop

- Status: completed
- Parent: VAIOS-G000
- Fib priority: 8
- Track: ui
- Priority: P1
- Bundle: objective/ui/operator-shell
- Parallel lane: operator-shell
- Refinement depth: 1
- Embedding query: SwissKnife virtual desktop Hallucinate App operator console daemon manager ORB display harness
- AST query: OperatorConsole, DaemonManager, ORBDisplayHarness, virtualDesktop
- Conflict policy: preserve user-visible operator workflows and reconcile UI conflicts by keeping the denser control surface
- Goal: SwissKnife and Hallucinate App provide a usable operator shell for sessions, daemon state, tools, and virtual desktop workflows.
- Evidence: SwissKnife virtual desktop, Hallucinate App operator console, daemon manager, ORB display harness, test/mcp-plus-plus/meta-glasses-display-harness.test.ts
- Outputs: swissknife, hallucinate_app, tests
- Validation: test -f hallucinate_app/docs/SWISSKNIFE_VIRTUAL_DESKTOP_MOCKUP.md
- HAO-064 proof: `hallucinate_app/index.js` exposes the Hallucinate App operator console evidence term in the Electron snapshot, `swissknife/test/mcp-plus-plus/meta-glasses-display-harness.test.ts` names the ORB display harness, and `hallucinate_app/docs/SWISSKNIFE_VIRTUAL_DESKTOP_MOCKUP.md` ties both terms to the desktop shell.
- Refinement: Add child goals for task monitor, app launcher, ORB inspector, and session replay.
- Gap task: Add missing shell evidence that connects daemon state, ORB tools, and operator-visible UI.
- Completed at: 2026-05-31T07:38:46.698317+00:00
- Completion evidence: SwissKnife virtual desktop => implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md (ast), implementation_plan/docs/19-virtual-ai-os-submodule-integration.md (exact), implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md (embedding:0.37); Hallucinate App operator console => dev/meta-rayban-display-simulator/webapp/app.js (ast), docs/meta-wearables-dat-display-physical-validation-checklist.md (embedding:0.42), implementation_plan/docs/19-virtual-ai-os-submodule-integration.md (embedding:0.31); daemon manager => implementation_plan/docs/19-virtual-ai-os-submodule-integration.md (exact), implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md (exact), mobile/src/screens/SettingsScreen.js (ast); ORB display harness => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/webapp/readiness.json (ast), implementation_plan/docs/21-swissknife-mobile-orb-bridge.md (embedding:0.39); test/mcp-plus-plus/meta-glasses-display-harness.test.ts => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/webapp/readiness.json (ast), docs/DOCUMENTATION_INDEX.md (embedding:0.32)
- Completion validation: 0

## VAIOS-G041 Operator shell task monitor

- Status: completed
- Parent: VAIOS-G040
- Fib priority: 8
- Track: ui
- Priority: P1
- Bundle: objective/ui/operator-shell/task-monitor
- Parallel lane: operator-shell
- Refinement depth: 2
- Embedding query: Hallucinate App operator console task monitor daemon task status pending confirmations receipts
- AST query: OperatorConsole, getControlSurfaceSnapshot, daemon:getAll
- Conflict policy: keep task state visible in the operator shell without duplicating daemon ownership
- Goal: Operators can monitor daemon-backed task status, pending confirmations, and receipt counts from the Hallucinate App desktop shell.
- Evidence: task monitor, daemon task status, pending confirmations, receipt diagnostics
- Outputs: hallucinate_app, tests
- Validation: rg -n "task monitor|daemon task status|pending confirmations|receipt diagnostics" hallucinate_app tests
- Refinement: Add child goals for per-daemon task streams if task state outgrows the current console snapshot.
- Gap task: Add missing task-monitor evidence that keeps daemon state visible to operators.
- Completed at: 2026-05-31T07:38:46.698317+00:00
- Completion evidence: task monitor => docs/planning/CODEBASE_INVENTORY.md (exact), docs/planning/DOCUMENTATION_GAP_ANALYSIS.md (exact), implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md (embedding:0.34); daemon task status => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/CONFIGURATION.md (embedding:0.32), implementation_plan/docs/15-meta-wearables-dat-mcpplusplus-integration-roadmap.md (ast); pending confirmations => implementation_plan/docs/06-command-system.md (embedding:0.38), implementation_plan/prs/PR-004-command-router-and-confirmations.md (embedding:0.33), mobile/push/examples/expo_receive_handler.ts (ast); receipt diagnostics => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/android/termux_phone_dispatcher.py (ast)
- Completion validation: 0

## VAIOS-G042 Operator shell app launcher

- Status: completed
- Parent: VAIOS-G040
- Fib priority: 8
- Track: ui
- Priority: P1
- Bundle: objective/ui/operator-shell/app-launcher
- Parallel lane: operator-shell
- Refinement depth: 2
- Embedding query: SwissKnife virtual desktop app launcher Hallucinate App desktop shell MCP tool launch
- AST query: createSwissKnifeWindow, openSwissKnifeApp, appLauncher
- Conflict policy: preserve one primary SwissKnife launch path and add app-specific launch metadata without forking the desktop shell
- Goal: Operators can launch SwissKnife virtual desktop apps and MCP tools from the Hallucinate App shell.
- Evidence: app launcher, SwissKnife virtual desktop launch, MCP tool actions
- Outputs: hallucinate_app, swissknife, tests
- Validation: rg -n "app launcher|SwissKnife virtual desktop launch|MCP tool actions" hallucinate_app swissknife tests
- Refinement: Add app-specific child goals only when a launched app needs independent policy or routing evidence.
- Gap task: Add missing app-launcher evidence that proves tools are reachable from the desktop shell.
- Completed at: 2026-05-31T07:38:46.698317+00:00
- Completion evidence: app launcher => dev/meta-rayban-display-simulator/webapp/app.js (ast), mobile/App.js (ast), mobile/modules/expo-meta-wearables-dat/app.plugin.js (ast); SwissKnife virtual desktop launch => implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md (ast), implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md (embedding:0.34), mobile/modules/expo-glasses-audio/index.ts (ast); MCP tool actions => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/simulator.js (ast), dev/meta-rayban-display-simulator/webapp/app.js (ast)
- Completion validation: 0

## VAIOS-G043 Operator shell ORB inspector

- Status: completed
- Parent: VAIOS-G040
- Fib priority: 8
- Track: ui
- Priority: P1
- Bundle: objective/ui/operator-shell/orb-inspector
- Parallel lane: operator-shell
- Refinement depth: 2
- Embedding query: ORB inspector descriptor manifest invocation receipt operator console display harness
- AST query: ORBDisplayHarness, MetaGlassesDisplayORBAdapter, getTaskMetadata, getSessionSnapshot
- Conflict policy: expose ORB diagnostics through additive inspector state and keep adapter contracts stable
- Goal: Operators can inspect ORB descriptor, manifest, invocation, receipt, and session state for display workflows.
- Evidence: ORB inspector, ORB display harness, descriptor manifest, session snapshot
- Outputs: swissknife, hallucinate_app, tests
- Validation: rg -n "ORB inspector|ORB display harness|descriptor manifest|session snapshot" swissknife hallucinate_app tests
- Refinement: Add inspector children for descriptor diffing, receipt search, and policy-denial drilldown if needed.
- Gap task: Add missing ORB-inspector evidence for display workflow diagnostics.
- Completed at: 2026-05-31T07:38:46.698317+00:00
- Completion evidence: ORB inspector => mobile/modules/expo-glasses-audio/index.ts (ast), mobile/push/examples/expo_receive_handler.ts (ast), mobile/src/push/notificationsHandler.js (ast); ORB display harness => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/webapp/readiness.json (ast), implementation_plan/docs/21-swissknife-mobile-orb-bridge.md (embedding:0.39); descriptor manifest => dev/meta-rayban-display-simulator/simulator.js (ast), dev/meta-rayban-display-simulator/webapp/app.js (ast), dev/meta-rayban-display-simulator/webapp/readiness.json (ast); session snapshot => mobile/push/examples/expo_receive_handler.ts (ast), mobile/src/hooks/usePeerChatDiagnostics.js (ast), mobile/src/orb/__tests__/metaGlassesOrbEdgeSession.test.js (exact)
- Completion validation: 0

## VAIOS-G044 Operator shell session replay

- Status: completed
- Parent: VAIOS-G040
- Fib priority: 8
- Track: ui
- Priority: P1
- Bundle: objective/ui/operator-shell/session-replay
- Parallel lane: operator-shell
- Refinement depth: 2
- Embedding query: session replay mediation receipts ORB session snapshot operator visible workflow reconstruction
- AST query: mediation_receipt, getSessionSnapshot, replay_task
- Conflict policy: preserve receipts and session snapshots as append-only replay anchors
- Goal: Operators can replay or reconstruct desktop, ORB, and mediation sessions from receipts and session snapshots.
- Evidence: session replay, mediation receipts, ORB session snapshots, replay anchors
- Outputs: hallucinate_app, swissknife, tests
- Validation: rg -n "session replay|mediation receipts|ORB session snapshots|replay anchors" hallucinate_app swissknife tests
- Refinement: Add storage/provenance children when replay artifacts need durable IPFS addressing.
- Gap task: Add missing session-replay evidence for operator-visible workflow reconstruction.
- Completed at: 2026-05-31T07:38:46.698317+00:00
- Completion evidence: session replay => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast); mediation receipts => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast); ORB session snapshots => mobile/push/examples/expo_receive_handler.ts (ast), mobile/src/hooks/usePeerChatDiagnostics.js (ast), mobile/src/orb/__tests__/metaGlassesOrbEdgeSession.test.js (embedding:0.36); replay anchors => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast)
- Completion validation: 0

## VAIOS-G050 Meta glasses remote terminal

- Status: completed
- Parent: VAIOS-G000
- Fib priority: 13
- Track: mobile
- Priority: P1
- Bundle: objective/mobile/meta-glasses-terminal
- Parallel lane: meta-glasses-terminal
- Refinement depth: 1
- Embedding query: Meta Ray-Ban Display simulator mobile bridge glasses audio display terminal iPhone handoff
- AST query: MetaGlassesDisplaySimulator, DATMockDevice, mobileGlassesBridge, displayWidget
- Conflict policy: prefer simulator-first contracts and keep physical-device assumptions behind adapter boundaries
- Goal: Meta glasses act as a remote audio/display interface for the virtual AI OS, with simulator-first coverage before iPhone handoff.
- Evidence: Meta Ray-Ban simulator, 600x600, DAT Mock Device, mobile glasses bridge, display widget, audio routing, tests/test_meta_glasses_display_simulator.py
- Outputs: mobile, docs, tests, implementation_plan/docs/20-meta-rayban-display-interface-simulator.md
- Validation: test -f implementation_plan/docs/20-meta-rayban-display-interface-simulator.md
- Refinement: Add child goals for display, audio, action receipts, fallback rendering, and physical-device evidence.
- Gap task: Add missing simulator or bridge evidence so glasses can be treated as a terminal, not only a notification endpoint.
- Completed at: 2026-05-31T07:38:46.698317+00:00
- Completion evidence: Meta Ray-Ban simulator => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/index.html (embedding:0.30), docs/plan-vs-code-gap-matrix.md (embedding:0.32); 600x600 => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/index.html (exact), dev/meta-rayban-display-simulator/simulator.js (exact); DAT Mock Device => implementation_plan/docs/19-virtual-ai-os-submodule-integration.md (exact), implementation_plan/docs/20-meta-rayban-display-interface-simulator.md (exact), implementation_plan/prs/PR-018-meta-wearables-dat-diagnostics-and-native-bridge.md (embedding:0.31); mobile glasses bridge => ARCHITECTURE.md (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/ARCHITECTURE.md (ast); display widget => config/display_webapp_readiness.meta_glasses_widget.example.json (embedding:0.32), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/webapp/app.js (embedding:0.31); audio routing => ARCHITECTURE.md (exact), GETTING_STARTED.md (exact), docs/ARCHITECTURE.md (exact); tests/test_meta_glasses_display_simulator.py => CONTRIBUTING.md (ast), GETTING_STARTED.md (embedding:0.35), README.md (embedding:0.36)
- Completion validation: 0

## VAIOS-G060 Content, provenance, and durable artifacts

- Status: completed
- Parent: VAIOS-G000
- Fib priority: 21
- Track: data
- Priority: P2
- Bundle: objective/data/provenance
- Parallel lane: durable-artifacts
- Refinement depth: 1
- Embedding query: IPFS provenance content addressed artifact manifest dataset replay rollback virtual AI OS
- AST query: ArtifactManifest, content_address, provenance, replay_task
- Conflict policy: never discard provenance metadata; merge manifests by content address and timestamped producer context
- Goal: Work products, model outputs, datasets, UI descriptors, and run logs have durable IPFS provenance and can be replayed by the OS.
- Evidence: ipfs_kit, provenance, artifact manifest, content address, dataset, tests/test_virtual_ai_os_task_orchestration.py
- Outputs: external/ipfs_kit, external/ipfs_datasets, src/handsfree, tests
- Validation: test -f tests/test_virtual_ai_os_task_orchestration.py
- Refinement: Add child goals for artifact schemas, replay, pinning, and rollback.
- Gap task: Add missing artifact/provenance evidence for the highest-risk workflow.
- Completed at: 2026-05-31T07:38:46.698317+00:00
- Completion evidence: ipfs_kit => CONFIGURATION.md (exact), docs/CONFIGURATION.md (exact), docs/GETTING_STARTED.md (exact); provenance => docs/meta-wearables-dat-display-rollout-evidence-template.md (exact), implementation_plan/docs/13-nl-prompt-to-hierarchical-tools-ipfs-datasets.md (exact), implementation_plan/docs/14-mcp-plus-plus-ipfs-server-integration.md (exact); artifact manifest => dev/meta-rayban-display-simulator/simulator.js (ast), dev/meta-rayban-display-simulator/webapp/app.js (ast), dev/meta-rayban-display-simulator/webapp/readiness.json (ast); content address => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), implementation_plan/docs/12-github-cli-copilot-integration.md (exact); dataset => ARCHITECTURE.md (exact), CONFIGURATION.md (exact), dev/meta-rayban-display-simulator/fixtures/task-progress.json (exact); tests/test_virtual_ai_os_task_orchestration.py => tests/test_virtual_ai_os_task_orchestration.py (path), CONTRIBUTING.md (ast), agent-runner/apply_instruction.py (ast)
- Completion validation: 0

## VAIOS-G070 Execution placement and acceleration

- Status: completed
- Parent: VAIOS-G000
- Fib priority: 34
- Track: runtime
- Priority: P2
- Bundle: objective/runtime/execution-placement
- Parallel lane: execution-placement
- Refinement depth: 1
- Embedding query: execution placement accelerated inference local daemon remote scheduler fallback capability semantics
- AST query: ExecutionPlacementPolicy, scheduler, fallback_mode, accelerated_inference
- Conflict policy: preserve capability semantics across placement backends and resolve scheduler conflicts with explicit fallback order
- Goal: The OS scheduler can choose local, accelerated, daemon, and remote execution paths without changing capability semantics.
- Evidence: ipfs_accelerate, execution placement, accelerated inference, scheduler, fallback mode
- Outputs: external/ipfs_accelerate, src/handsfree, tests
- Validation: rg -n "execution placement|ipfs_accelerate|fallback mode" docs implementation_plan src tests
- Refinement: Add child goals for placement policy, batching, fallback, and observability.
- Gap task: Add routing or test evidence for the weakest execution-placement path.
- Completed at: 2026-05-31T07:38:46.698317+00:00
- Completion evidence: ipfs_accelerate => CONFIGURATION.md (exact), docs/CONFIGURATION.md (exact), docs/GETTING_STARTED.md (exact); execution placement => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), implementation_plan/docs/19-virtual-ai-os-submodule-integration.md (exact), mobile/push/examples/expo_receive_handler.ts (ast); accelerated inference => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), implementation_plan/docs/15-meta-wearables-dat-mcpplusplus-integration-roadmap.md (exact); scheduler => implementation_plan/docs/19-virtual-ai-os-submodule-integration.md (exact), mobile/src/screens/SettingsScreen.js (ast), src/handsfree/capability_registry.py (exact); fallback mode => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/simulator.js (ast), implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md (embedding:0.40)
- Completion validation: 0

## VAIOS-G080 End-to-end validation lattice

- Status: completed
- Parent: VAIOS-G000
- Fib priority: 55
- Track: quality
- Priority: P1
- Bundle: objective/quality/e2e-lattice
- Parallel lane: validation-lattice
- Refinement depth: 1
- Embedding query: hardware free integration tests planner router storage UI mobile glasses daemon behavior
- AST query: test_virtual_ai_os_end_to_end, playwright, mobile_bridge_tests, hardware_free
- Conflict policy: keep layered tests independent and resolve conflicts by preserving the broadest hardware-free coverage
- Goal: The system has layered tests that prove planner, router, storage, UI, mobile, glasses, and daemon behavior without requiring hardware in every run.
- Evidence: tests/test_virtual_ai_os_end_to_end.py, Playwright, mobile bridge tests, SwissKnife Jest, Hallucinate App e2e, hardware-free
- Outputs: tests, mobile, swissknife, hallucinate_app
- Validation: test -f tests/test_virtual_ai_os_end_to_end.py
- Refinement: Add child goals for each untested integration path in the test matrix.
- Gap task: Add the next missing hardware-free integration test that ties at least two planes together.
- Completed at: 2026-05-31T07:38:46.698317+00:00
- Completion evidence: tests/test_virtual_ai_os_end_to_end.py => tests/test_virtual_ai_os_end_to_end.py (path), CONTRIBUTING.md (ast), agent-runner/apply_instruction.py (ast); Playwright => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), implementation_plan/docs/20-meta-rayban-display-interface-simulator.md (exact), mobile/modules/expo-meta-wearables-dat/app.plugin.js (ast); mobile bridge tests => ARCHITECTURE.md (ast), CONTRIBUTING.md (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast); SwissKnife Jest => implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md (ast), implementation_plan/docs/19-virtual-ai-os-submodule-integration.md (exact), mobile/package.json (ast); Hallucinate App e2e => dev/meta-rayban-display-simulator/webapp/app.js (ast), implementation_plan/docs/19-virtual-ai-os-submodule-integration.md (exact), implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md (embedding:0.43); hardware-free => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), docs/observability_metrics.md (exact)
- Completion validation: 0

## VAIOS-G081 Interoperate hallucinate_app with external/ipfs_datasets

- Status: deferred
- Deferred reason: Broad pairwise interoperability is preserved for post-gate work, but it must not outrank the phone-hosted Swissknife desktop, desktop-peer offload, Hallucinate App mediation, and Meta glasses launch-readiness gate.
- Parent: VAIOS-G000
- Fib priority: 3000
- Track: interoperability
- Priority: P1
- Bundle: objective/interoperability/hallucinate_app-external_ipfs_datasets
- Goal kind: interoperability
- Interoperability pair: hallucinate_app, external/ipfs_datasets
- Submodules: hallucinate_app, external/ipfs_datasets
- Interoperability score: 35
- Discovery sources: configured, gitlink, gitmodules
- Package manifests: external/ipfs_datasets/.tools/ipfs_kit_py/.playwright_local/package.json, external/ipfs_datasets/.tools/ipfs_kit_py/archive/fixes/requirements.txt, external/ipfs_datasets/.tools/ipfs_kit_py/backup/fixes/requirements.txt, external/ipfs_datasets/.tools/ipfs_kit_py/config/package.json, external/ipfs_datasets/.tools/ipfs_kit_py/config/pyproject.toml, external/ipfs_datasets/.tools/ipfs_kit_py/config/requirements.txt, external/ipfs_datasets/.tools/ipfs_kit_py/config/setup.cfg, external/ipfs_datasets/.tools/ipfs_kit_py/config/setup.py, external/ipfs_datasets/.tools/ipfs_kit_py/docs/py-ipld-car/pyproject.toml, external/ipfs_datasets/.tools/ipfs_kit_py/docs/py-ipld-car/requirements.txt, external/ipfs_datasets/.tools/ipfs_kit_py/docs/py-ipld-dag-pb/pyproject.toml, external/ipfs_datasets/.tools/ipfs_kit_py/docs/py-ipld-dag-pb/requirements.txt
- Interface descriptors: external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json, external/ipfs_datasets/.tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md, external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py, external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py, external/ipfs_datasets/.tools/ipfs_kit_py/examples/demos/demo_bucket_vfs_interfaces.py, external/ipfs_datasets/.tools/ipfs_kit_py/examples/schema_column_optimization_example.py, external/ipfs_datasets/.tools/ipfs_kit_py/ipfs_kit_py/arrow_ipc_daemon_interface.py, external/ipfs_datasets/.tools/ipfs_kit_py/ipfs_kit_py/backend_schemas.py, external/ipfs_datasets/.tools/ipfs_kit_py/ipfs_kit_py/cache/schema_column_optimization.py, external/ipfs_datasets/.tools/ipfs_kit_py/ipfs_kit_py/cache/zero_copy_interface.py, external/ipfs_datasets/.tools/ipfs_kit_py/ipfs_kit_py/graphql_schema.py, external/ipfs_datasets/.tools/ipfs_kit_py/ipfs_kit_py/openapi_schema.py, external/ipfs_datasets/.tools/ipfs_kit_py/ipfs_kit_py/unified_bucket_interface.py, external/ipfs_datasets/.tools/ipfs_kit_py/reorganization_backup_root/BUCKET_VFS_INTERFACES_COMPLETE.md, external/ipfs_datasets/.tools/ipfs_kit_py/reorganization_backup_root/demo_bucket_vfs_interfaces.py, external/ipfs_datasets/.tools/ipfs_kit_py/scripts/development/verify_mcp_interface.py
- MCP descriptors: external/ipfs_datasets/.github/workflows/mcp-benchmarks.yml, external/ipfs_datasets/.github/workflows/mcp-dashboard-tests.yml, external/ipfs_datasets/.github/workflows/mcp-integration-tests.yml, external/ipfs_datasets/.github/workflows/mcp-tools-monitoring-unified.yml, external/ipfs_datasets/.github/workflows/mcp-tools-monitoring.yml, external/ipfs_datasets/.github/workflows/mcp-tools-monitoring.yml.backup, external/ipfs_datasets/.tools/ipfs_kit_py/.github/workflows/enhanced-mcp-server.yml, external/ipfs_datasets/.tools/ipfs_kit_py/.github/workflows/final-mcp-server.yml, external/ipfs_datasets/.tools/ipfs_kit_py/archive/applied_patches/advanced_filecoin_mcp.py, external/ipfs_datasets/.tools/ipfs_kit_py/archive/applied_patches/direct_mcp_server.py, external/ipfs_datasets/.tools/ipfs_kit_py/archive/applied_patches/enhanced_mcp_server.py, external/ipfs_datasets/.tools/ipfs_kit_py/archive/applied_patches/enhanced_mcp_server_real.py, external/ipfs_datasets/.tools/ipfs_kit_py/archive/applied_patches/enhanced_mcp_server_with_ai_ml.py, external/ipfs_datasets/.tools/ipfs_kit_py/archive/applied_patches/filecoin_mcp_integration.py, external/ipfs_datasets/.tools/ipfs_kit_py/archive/applied_patches/fix_all_mcp.sh, external/ipfs_datasets/.tools/ipfs_kit_py/archive/applied_patches/fix_all_mcp_issues.sh
- Python import roots: Bio, PIL, Stanford, __future__, advanced_thread_pool_manager, aiohttp, analyze_workflow_failure, anyio, archive, argparse, ast, asyncio, atexit, auth, auth_keystore_integration, auth_keystore_py, base64, benchmark_symai, black, bs4, cProfile, collections, complete_mcp_discovery_test, concurrent
- Goal: Prove `hallucinate_app` interoperates with `external/ipfs_datasets` through importable contracts, interface descriptors, runtime handoff behavior, and integration tests.
- Evidence: tests/integration/test_hallucinate_app_external_ipfs_datasets_interop.py, docs/integration/hallucinate_app-external_ipfs_datasets.md, interface contract hallucinate_app external/ipfs_datasets, external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json, external/ipfs_datasets/.tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md, external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py, external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py, external/ipfs_datasets/.tools/ipfs_kit_py/examples/demos/demo_bucket_vfs_interfaces.py, external/ipfs_datasets/.tools/ipfs_kit_py/examples/schema_column_optimization_example.py
- Outputs: tests/integration/test_hallucinate_app_external_ipfs_datasets_interop.py, docs/integration/hallucinate_app-external_ipfs_datasets.md, hallucinate_app, external/ipfs_datasets, external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json, external/ipfs_datasets/.tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md, external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py, external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py
- Validation: python -m pytest tests/integration -q
- Refinement depth: 1
- Embedding query: hallucinate_app external/ipfs_datasets interoperability integration test interface descriptor Bio PIL Stanford __future__ advanced_thread_pool_manager aiohttp analyze_workflow_failure anyio archive argparse ast asyncio
- AST query: hallucinate_app, external/ipfs_datasets, interface contract, integration test, Bio, PIL, Stanford, __future__, advanced_thread_pool_manager, aiohttp, analyze_workflow_failure, anyio, archive, argparse, ast, asyncio
- Parallel lane: objective/interoperability/hallucinate_app-external_ipfs_datasets
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Gap task: Create one larger integration work item proving `hallucinate_app` and `external/ipfs_datasets` can be used together, including a test, a contract note, and any adapter code needed by the objective.

## VAIOS-G082 Interoperate hallucinate_app with external/ipfs_accelerate

- Status: deferred
- Deferred reason: Broad pairwise interoperability is preserved for post-gate work, but it must not outrank the phone-hosted Swissknife desktop, desktop-peer offload, Hallucinate App mediation, and Meta glasses launch-readiness gate.
- Parent: VAIOS-G000
- Fib priority: 3001
- Track: interoperability
- Priority: P1
- Bundle: objective/interoperability/hallucinate_app-external_ipfs_accelerate
- Goal kind: interoperability
- Interoperability pair: hallucinate_app, external/ipfs_accelerate
- Submodules: hallucinate_app, external/ipfs_accelerate
- Interoperability score: 35
- Discovery sources: configured, gitlink, gitmodules
- Package manifests: external/ipfs_accelerate/ipfs_accelerate_py/consensus_kit/Cargo.toml, external/ipfs_accelerate/ipfs_accelerate_py/mcp/requirements.txt, external/ipfs_accelerate/ipfs_accelerate_py/requirements.txt, external/ipfs_accelerate/ipfs_accelerate_py/utils/qualcomm/onnx/requirements.txt, external/ipfs_accelerate/ipfs_accelerate_py/worker/skillset/libllama/requirements.txt, external/ipfs_accelerate/pyproject.toml, external/ipfs_accelerate/requirements.txt, external/ipfs_accelerate/scripts/generators/skill_generator/setup.py, external/ipfs_accelerate/scripts/generators/test_generator/requirements.txt, external/ipfs_accelerate/setup.py, external/ipfs_accelerate/test/doc-builder-test/pyproject.toml, external/ipfs_accelerate/test/doc-builder-test/setup.cfg
- Interface descriptors: external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql, external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py, external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py, external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py, external/ipfs_accelerate/data/duckdb/utils/implement_db_schema_enhancements.py, external/ipfs_accelerate/data/duckdb/utils/onnx_db_schema_update.py, external/ipfs_accelerate/docs/development_history/VISUAL_PROOF_WORKING_INTERFACE.md, external/ipfs_accelerate/ipfs_accelerate_js/src/browser/optimizations/ipfs_accelerate_js_browser_interface.ts, external/ipfs_accelerate/ipfs_accelerate_js/src/core/interfaces.ts, external/ipfs_accelerate/ipfs_accelerate_js/src/interfaces.ts, external/ipfs_accelerate/ipfs_accelerate_js/src/utils/browser_interface.ts, external/ipfs_accelerate/ipfs_accelerate_js/src/utils/create_benchmark_schema.ts, external/ipfs_accelerate/ipfs_accelerate_js/src/utils/onnx_db_schema_update.ts, external/ipfs_accelerate/ipfs_accelerate_py/embeddings/embeddings_schema_stubs.md, external/ipfs_accelerate/ipfs_accelerate_py/embeddings/schema.py, external/ipfs_accelerate/ipfs_accelerate_py/embeddings/schema_stubs.md
- MCP descriptors: external/ipfs_accelerate/.github/workflows/mcp-transport-libp2p.yml, external/ipfs_accelerate/MCP_SERVER_UNIFICATION_PLAN.md, external/ipfs_accelerate/deployments/systemd/ipfs-accelerate-mcp.service, external/ipfs_accelerate/docs/MCP_DASHBOARD_GUIDE.md, external/ipfs_accelerate/docs/MCP_TRIO_ROADMAP.md, external/ipfs_accelerate/docs/architecture/IPFS_ACCELERATE_MCP_INTEGRATION_PLAN.md, external/ipfs_accelerate/docs/archive/implementations/CICD_MCP_VALIDATION_REPORT.md, external/ipfs_accelerate/docs/archive/implementations/CICD_MCP_VALIDATION_REPORT_2025-10-23.md, external/ipfs_accelerate/docs/archive/implementations/IMPLEMENTATION_COMPLETE_GITHUB_MCP.md, external/ipfs_accelerate/docs/development_history/MCP_ERROR_HANDLING_VERIFICATION.md, external/ipfs_accelerate/docs/features/mcp/AI_MCP_SERVER_IMPLEMENTATION.md, external/ipfs_accelerate/docs/guides/MCP_SETUP_GUIDE.md, external/ipfs_accelerate/docs/guides/QUICK_START_MCP.md, external/ipfs_accelerate/docs/guides/github/GITHUB_CLI_MCP_INTEGRATION.md, external/ipfs_accelerate/docs/guides/github/QUICK_REFERENCE_GITHUB_MCP.md, external/ipfs_accelerate/docs/guides/infrastructure/MCP_P2P_SETUP_GUIDE.md
- Python import roots: Bio, GitHub, PIL, __future__, abc, advanced_thread_pool_manager, aiohttp, anyio, api_backends, argparse, asyncio, atexit, auth, auth_keystore_integration, auth_keystore_py, base64, builtins, cli, collections, comprehensive_mcp_server, concurrent, contextlib, copilot, copy
- Goal: Prove `hallucinate_app` interoperates with `external/ipfs_accelerate` through importable contracts, interface descriptors, runtime handoff behavior, and integration tests.
- Evidence: tests/integration/test_hallucinate_app_external_ipfs_accelerate_interop.py, docs/integration/hallucinate_app-external_ipfs_accelerate.md, interface contract hallucinate_app external/ipfs_accelerate, external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql, external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py, external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py, external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py, external/ipfs_accelerate/data/duckdb/utils/implement_db_schema_enhancements.py, external/ipfs_accelerate/data/duckdb/utils/onnx_db_schema_update.py
- Outputs: tests/integration/test_hallucinate_app_external_ipfs_accelerate_interop.py, docs/integration/hallucinate_app-external_ipfs_accelerate.md, hallucinate_app, external/ipfs_accelerate, external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql, external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py, external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py, external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py
- Validation: python -m pytest tests/integration -q
- Refinement depth: 1
- Embedding query: hallucinate_app external/ipfs_accelerate interoperability integration test interface descriptor Bio GitHub PIL __future__ abc advanced_thread_pool_manager aiohttp anyio api_backends argparse asyncio atexit
- AST query: hallucinate_app, external/ipfs_accelerate, interface contract, integration test, Bio, GitHub, PIL, __future__, abc, advanced_thread_pool_manager, aiohttp, anyio, api_backends, argparse, asyncio, atexit
- Parallel lane: objective/interoperability/hallucinate_app-external_ipfs_accelerate
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Gap task: Create one larger integration work item proving `hallucinate_app` and `external/ipfs_accelerate` can be used together, including a test, a contract note, and any adapter code needed by the objective.

## VAIOS-G083 Interoperate hallucinate_app with external/ipfs_kit

- Status: deferred
- Deferred reason: Broad pairwise interoperability is preserved for post-gate work, but it must not outrank the phone-hosted Swissknife desktop, desktop-peer offload, Hallucinate App mediation, and Meta glasses launch-readiness gate.
- Parent: VAIOS-G000
- Fib priority: 3002
- Track: interoperability
- Priority: P1
- Bundle: objective/interoperability/hallucinate_app-external_ipfs_kit
- Goal kind: interoperability
- Interoperability pair: hallucinate_app, external/ipfs_kit
- Submodules: hallucinate_app, external/ipfs_kit
- Interoperability score: 35
- Discovery sources: configured, gitlink, gitmodules
- Package manifests: external/ipfs_kit/.playwright_local/package.json, external/ipfs_kit/archive/archive_clutter/temp_files/requirements.txt, external/ipfs_kit/archive/fixes/requirements.txt, external/ipfs_kit/backup/archive_clutter/temp_files/requirements.txt, external/ipfs_kit/backup/fixes/requirements.txt, external/ipfs_kit/config/package.json, external/ipfs_kit/config/pyproject.toml, external/ipfs_kit/config/requirements.txt, external/ipfs_kit/config/setup.cfg, external/ipfs_kit/config/setup.py, external/ipfs_kit/docs/py-ipld-car/pyproject.toml, external/ipfs_kit/docs/py-ipld-car/requirements.txt
- Interface descriptors: external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py, external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py, external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py, external/ipfs_kit/data/deprecations_report.schema.json, external/ipfs_kit/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md, external/ipfs_kit/docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto, external/ipfs_kit/examples/demo_bucket_vfs_interfaces.py, external/ipfs_kit/examples/demo_unified_bucket_interface.py, external/ipfs_kit/examples/demos/demo_bucket_vfs_interfaces.py, external/ipfs_kit/examples/schema_column_optimization_example.py, external/ipfs_kit/ipfs_kit_py/arrow_ipc_daemon_interface.py, external/ipfs_kit/ipfs_kit_py/backend_schemas.py, external/ipfs_kit/ipfs_kit_py/cache/schema_column_optimization.py, external/ipfs_kit/ipfs_kit_py/cache/zero_copy_interface.py, external/ipfs_kit/ipfs_kit_py/graphql_schema.py, external/ipfs_kit/ipfs_kit_py/libp2p/network/stream/net_stream_interface.py
- MCP descriptors: external/ipfs_kit/.github/workflows/enhanced-mcp-server.yml, external/ipfs_kit/.github/workflows/final-mcp-server.yml, external/ipfs_kit/archive/applied_patches/advanced_filecoin_mcp.py, external/ipfs_kit/archive/applied_patches/direct_mcp_server.py, external/ipfs_kit/archive/applied_patches/enhanced_mcp_server.py, external/ipfs_kit/archive/applied_patches/enhanced_mcp_server_real.py, external/ipfs_kit/archive/applied_patches/enhanced_mcp_server_with_ai_ml.py, external/ipfs_kit/archive/applied_patches/filecoin_mcp_integration.py, external/ipfs_kit/archive/applied_patches/fix_all_mcp.sh, external/ipfs_kit/archive/applied_patches/fix_all_mcp_issues.sh, external/ipfs_kit/archive/applied_patches/fix_mcp_batch1.sh, external/ipfs_kit/archive/applied_patches/fix_mcp_batch2.sh, external/ipfs_kit/archive/applied_patches/fix_mcp_code.py, external/ipfs_kit/archive/applied_patches/fix_mcp_errors.py, external/ipfs_kit/archive/applied_patches/fix_mcp_file.py, external/ipfs_kit/archive/applied_patches/fix_mcp_form_data.py
- Python import roots: Bio, PIL, __future__, advanced_thread_pool_manager, aiohttp, anyio, argparse, asyncio, auth, auth_keystore_integration, auth_keystore_py, base64, boto3, botocore, cbor2, collections, concurrent, contextlib, copy, create_individual_bucket_parquet, cross, cross_browser_model_sharding, cryptography, dag_cbor
- Goal: Prove `hallucinate_app` interoperates with `external/ipfs_kit` through importable contracts, interface descriptors, runtime handoff behavior, and integration tests.
- Evidence: tests/integration/test_hallucinate_app_external_ipfs_kit_interop.py, docs/integration/hallucinate_app-external_ipfs_kit.md, interface contract hallucinate_app external/ipfs_kit, external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py, external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py, external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py, external/ipfs_kit/data/deprecations_report.schema.json, external/ipfs_kit/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md, external/ipfs_kit/docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto
- Outputs: tests/integration/test_hallucinate_app_external_ipfs_kit_interop.py, docs/integration/hallucinate_app-external_ipfs_kit.md, hallucinate_app, external/ipfs_kit, external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py, external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py, external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py, external/ipfs_kit/data/deprecations_report.schema.json
- Validation: python -m pytest tests/integration -q
- Refinement depth: 1
- Embedding query: hallucinate_app external/ipfs_kit interoperability integration test interface descriptor Bio PIL __future__ advanced_thread_pool_manager aiohttp anyio argparse asyncio auth auth_keystore_integration auth_keystore_py base64
- AST query: hallucinate_app, external/ipfs_kit, interface contract, integration test, Bio, PIL, __future__, advanced_thread_pool_manager, aiohttp, anyio, argparse, asyncio, auth, auth_keystore_integration, auth_keystore_py, base64
- Parallel lane: objective/interoperability/hallucinate_app-external_ipfs_kit
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Gap task: Create one larger integration work item proving `hallucinate_app` and `external/ipfs_kit` can be used together, including a test, a contract note, and any adapter code needed by the objective.

## VAIOS-G084 Interoperate hallucinate_app with Mcp-Plus-Plus

- Status: deferred
- Deferred reason: Broad pairwise interoperability is preserved for post-gate work, but it must not outrank the phone-hosted Swissknife desktop, desktop-peer offload, Hallucinate App mediation, and Meta glasses launch-readiness gate.
- Parent: VAIOS-G000
- Fib priority: 3003
- Track: interoperability
- Priority: P1
- Bundle: objective/interoperability/hallucinate_app-mcp_plus_plus
- Goal kind: interoperability
- Interoperability pair: hallucinate_app, Mcp-Plus-Plus
- Submodules: hallucinate_app, Mcp-Plus-Plus
- Interoperability score: 35
- Discovery sources: configured, gitlink
- Package manifests: Mcp-Plus-Plus/tests-go/go.mod, Mcp-Plus-Plus/tests-py/requirements.txt, Mcp-Plus-Plus/tests-rs/Cargo.toml, Mcp-Plus-Plus/tests-ts/package.json, hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/package.json, hallucinate_app/hallucinate_app/model_collection_viewer/package.json, hallucinate_app/hallucinate_app/node/package.json, hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_embeddings_py/setup.py, hallucinate_app/hallucinate_app/python/pyproject.toml, hallucinate_app/hallucinate_app/python/requirements.txt, hallucinate_app/hallucinate_app/python/setup.py, hallucinate_app/hallucinate_app/python/ucan_auth_py/setup.py
- Interface descriptors: Mcp-Plus-Plus/tests-py/fixtures/valid/mcp_idl_descriptor.json, hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js, hallucinate_app/hallucinate_app/node/views/test_interface.html, hallucinate_app/python/hallucinate_app/control_surface_schema.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_descriptor_validation.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_schemas.py, hallucinate_app/swissknife/contracts/control_surface_contract.schema.json, hallucinate_app/swissknife/contracts/interaction_envelope.schema.json, hallucinate_app/swissknife/contracts/mediation_receipt.schema.json, hallucinate_app/swissknife/contracts/policy_decision.schema.json, hallucinate_app/swissknife/docs/ast_exports/interfaces/all_interfaces.json, hallucinate_app/swissknife/docs/mcp-plus-plus/DESCRIPTOR_AUTHORING_CLI.md, hallucinate_app/swissknife/docs/phase2/06_cross_domain_interfaces.md, hallucinate_app/swissknife/ipfs_accelerate_js/src/core/interfaces.ts, hallucinate_app/swissknife/ipfs_accelerate_js/src/interfaces.ts, hallucinate_app/swissknife/ipfs_accelerate_js/src/utils/browser_interface.ts
- MCP descriptors: Mcp-Plus-Plus/docs/spec/mcp++-profiles-draft.md, Mcp-Plus-Plus/docs/spec/mcp-idl.md, Mcp-Plus-Plus/docs/spec/transport-mcp-p2p.md, Mcp-Plus-Plus/tests-go/validators/base_mcp.go, Mcp-Plus-Plus/tests-go/validators/mcp_idl.go, Mcp-Plus-Plus/tests-py/fixtures/valid/mcp_idl_descriptor.json, Mcp-Plus-Plus/tests-py/fixtures/valid/mcp_tool_call.json, Mcp-Plus-Plus/tests-py/integration/test_base_mcp_typed.py, Mcp-Plus-Plus/tests-py/integration/test_mcp_baseline.py, Mcp-Plus-Plus/tests-py/integration/test_mcp_idl.py, Mcp-Plus-Plus/tests-py/validators/base_mcp.py, Mcp-Plus-Plus/tests-py/validators/base_mcp_typed.py, Mcp-Plus-Plus/tests-py/validators/mcp_idl.py, Mcp-Plus-Plus/tests-rs/src/validators/base_mcp.rs, Mcp-Plus-Plus/tests-rs/src/validators/mcp_idl.rs, Mcp-Plus-Plus/tests-ts/src/validators/baseMCP.ts
- Python import roots: Bio, PIL, __future__, advanced_thread_pool_manager, aiohttp, argparse, asyncio, auth, auth_keystore_integration, auth_keystore_py, base64, collections, concurrent, contextlib, copy, cross, cross_browser_model_sharding, cryptography, database_backup_manager, database_query_system, database_sync_manager, dataclasses, datasets, datetime
- Goal: Prove `hallucinate_app` interoperates with `Mcp-Plus-Plus` through importable contracts, interface descriptors, runtime handoff behavior, and integration tests.
- Evidence: tests/integration/test_hallucinate_app_mcp_plus_plus_interop.py, docs/integration/hallucinate_app-mcp_plus_plus.md, interface contract hallucinate_app Mcp-Plus-Plus, Mcp-Plus-Plus/tests-py/fixtures/valid/mcp_idl_descriptor.json, hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js, hallucinate_app/hallucinate_app/node/views/test_interface.html, hallucinate_app/python/hallucinate_app/control_surface_schema.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_descriptor_validation.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_schemas.py
- Outputs: tests/integration/test_hallucinate_app_mcp_plus_plus_interop.py, docs/integration/hallucinate_app-mcp_plus_plus.md, hallucinate_app, Mcp-Plus-Plus, Mcp-Plus-Plus/tests-py/fixtures/valid/mcp_idl_descriptor.json, hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js, hallucinate_app/hallucinate_app/node/views/test_interface.html, hallucinate_app/python/hallucinate_app/control_surface_schema.py
- Validation: python -m pytest tests/integration -q
- Refinement depth: 1
- Embedding query: hallucinate_app Mcp-Plus-Plus interoperability integration test interface descriptor Bio PIL __future__ advanced_thread_pool_manager aiohttp argparse asyncio auth auth_keystore_integration auth_keystore_py base64 collections
- AST query: hallucinate_app, Mcp-Plus-Plus, interface contract, integration test, Bio, PIL, __future__, advanced_thread_pool_manager, aiohttp, argparse, asyncio, auth, auth_keystore_integration, auth_keystore_py, base64, collections
- Parallel lane: objective/interoperability/hallucinate_app-mcp_plus_plus
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Gap task: Create one larger integration work item proving `hallucinate_app` and `Mcp-Plus-Plus` can be used together, including a test, a contract note, and any adapter code needed by the objective.

## VAIOS-G085 Interoperate hallucinate_app with swissknife

- Status: deferred
- Deferred reason: Broad pairwise interoperability is preserved for post-gate work, but it must not outrank the phone-hosted Swissknife desktop, desktop-peer offload, Hallucinate App mediation, and Meta glasses launch-readiness gate.
- Parent: VAIOS-G000
- Fib priority: 3004
- Track: interoperability
- Priority: P1
- Bundle: objective/interoperability/hallucinate_app-swissknife
- Goal kind: interoperability
- Interoperability pair: hallucinate_app, swissknife
- Submodules: hallucinate_app, swissknife
- Interoperability score: 35
- Discovery sources: configured, gitlink, gitmodules
- Package manifests: hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/package.json, hallucinate_app/hallucinate_app/model_collection_viewer/package.json, hallucinate_app/hallucinate_app/node/package.json, hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_embeddings_py/setup.py, hallucinate_app/hallucinate_app/python/pyproject.toml, hallucinate_app/hallucinate_app/python/requirements.txt, hallucinate_app/hallucinate_app/python/setup.py, hallucinate_app/hallucinate_app/python/ucan_auth_py/setup.py, hallucinate_app/package.json, hallucinate_app/python/requirements.txt, hallucinate_app/swissknife/ipfs_accelerate_js/package.json, hallucinate_app/swissknife/package.json
- Interface descriptors: hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js, hallucinate_app/hallucinate_app/node/views/test_interface.html, hallucinate_app/python/hallucinate_app/control_surface_schema.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_descriptor_validation.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_schemas.py, hallucinate_app/swissknife/contracts/control_surface_contract.schema.json, hallucinate_app/swissknife/contracts/interaction_envelope.schema.json, hallucinate_app/swissknife/contracts/mediation_receipt.schema.json, hallucinate_app/swissknife/contracts/policy_decision.schema.json, hallucinate_app/swissknife/docs/ast_exports/interfaces/all_interfaces.json, hallucinate_app/swissknife/docs/mcp-plus-plus/DESCRIPTOR_AUTHORING_CLI.md, hallucinate_app/swissknife/docs/phase2/06_cross_domain_interfaces.md, hallucinate_app/swissknife/ipfs_accelerate_js/src/core/interfaces.ts, hallucinate_app/swissknife/ipfs_accelerate_js/src/interfaces.ts, hallucinate_app/swissknife/ipfs_accelerate_js/src/utils/browser_interface.ts, hallucinate_app/swissknife/ipfs_accelerate_js/src/utils/create_benchmark_schema.ts
- MCP descriptors: hallucinate_app/.github/workflows/mcp-daemon-e2e.yml, hallucinate_app/docs/MCP_DAEMON_ARCHITECTURE.md, hallucinate_app/docs/MCP_DAEMON_IMPLEMENTATION_SUMMARY.md, hallucinate_app/docs/QUICK_START_MCP.md, hallucinate_app/hallucinate_app/cjs/orbitdb_kit_cjs/orbitdb_kit.cjs, hallucinate_app/hallucinate_app/node/dashboard/orbitdb_security_dashboard.css, hallucinate_app/hallucinate_app/node/dashboard/orbitdb_security_dashboard.js, hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js, hallucinate_app/hallucinate_app/node/orbitdb_kit.js, hallucinate_app/hallucinate_app/node/secure_orbitdb_manager.js, hallucinate_app/hallucinate_app/python/hallucinate_app/secure_orbitdb_manager.py, hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_secure_orbitdb_manager.py, hallucinate_app/swissknife/benchmark/integration/mcp-client-benchmark.ts, hallucinate_app/swissknife/cleanup-archive/analysis/mcp_direct_diagnostic.js, hallucinate_app/swissknife/cleanup-archive/analysis/mcp_server_diagnostic.py, hallucinate_app/swissknife/cleanup-archive/docs/MCP-SERVER-DIAGNOSTIC-REPORT.md
- Python import roots: Bio, PIL, __future__, advanced_thread_pool_manager, aiohttp, argparse, asyncio, auth, auth_keystore_integration, auth_keystore_py, base64, collections, concurrent, contextlib, copy, cross, cross_browser_model_sharding, cryptography, database_backup_manager, database_query_system, database_sync_manager, dataclasses, datasets, datetime
- Goal: Prove `hallucinate_app` interoperates with `swissknife` through importable contracts, interface descriptors, runtime handoff behavior, and integration tests.
- Evidence: tests/integration/test_hallucinate_app_swissknife_interop.py, docs/integration/hallucinate_app-swissknife.md, interface contract hallucinate_app swissknife, hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js, hallucinate_app/hallucinate_app/node/views/test_interface.html, hallucinate_app/python/hallucinate_app/control_surface_schema.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_descriptor_validation.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_schemas.py, hallucinate_app/swissknife/contracts/control_surface_contract.schema.json
- Outputs: tests/integration/test_hallucinate_app_swissknife_interop.py, docs/integration/hallucinate_app-swissknife.md, hallucinate_app, swissknife, hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js, hallucinate_app/hallucinate_app/node/views/test_interface.html, hallucinate_app/python/hallucinate_app/control_surface_schema.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_descriptor_validation.py
- Validation: python -m pytest tests/integration -q
- Refinement depth: 1
- Embedding query: hallucinate_app swissknife interoperability integration test interface descriptor Bio PIL __future__ advanced_thread_pool_manager aiohttp argparse asyncio auth auth_keystore_integration auth_keystore_py base64 collections
- AST query: hallucinate_app, swissknife, interface contract, integration test, Bio, PIL, __future__, advanced_thread_pool_manager, aiohttp, argparse, asyncio, auth, auth_keystore_integration, auth_keystore_py, base64, collections
- Parallel lane: objective/interoperability/hallucinate_app-swissknife
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Gap task: Create one larger integration work item proving `hallucinate_app` and `swissknife` can be used together, including a test, a contract note, and any adapter code needed by the objective.

## VAIOS-G086 Interoperate hallucinate_app with external/meta-wearables-dat-android

- Status: deferred
- Deferred reason: Broad pairwise interoperability is preserved for post-gate work, but it must not outrank the phone-hosted Swissknife desktop, desktop-peer offload, Hallucinate App mediation, and Meta glasses launch-readiness gate.
- Parent: VAIOS-G000
- Fib priority: 3005
- Track: interoperability
- Priority: P1
- Bundle: objective/interoperability/hallucinate_app-external_meta_wearables_dat_android
- Goal kind: interoperability
- Interoperability pair: hallucinate_app, external/meta-wearables-dat-android
- Submodules: hallucinate_app, external/meta-wearables-dat-android
- Interoperability score: 35
- Discovery sources: configured, gitlink, gitmodules
- Package manifests: hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/package.json, hallucinate_app/hallucinate_app/model_collection_viewer/package.json, hallucinate_app/hallucinate_app/node/package.json, hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_embeddings_py/setup.py, hallucinate_app/hallucinate_app/python/pyproject.toml, hallucinate_app/hallucinate_app/python/requirements.txt, hallucinate_app/hallucinate_app/python/setup.py, hallucinate_app/hallucinate_app/python/ucan_auth_py/setup.py, hallucinate_app/package.json, hallucinate_app/python/requirements.txt, hallucinate_app/swissknife/ipfs_accelerate_js/package.json, hallucinate_app/swissknife/package.json
- Interface descriptors: hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js, hallucinate_app/hallucinate_app/node/views/test_interface.html, hallucinate_app/python/hallucinate_app/control_surface_schema.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_descriptor_validation.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_schemas.py, hallucinate_app/swissknife/contracts/control_surface_contract.schema.json, hallucinate_app/swissknife/contracts/interaction_envelope.schema.json, hallucinate_app/swissknife/contracts/mediation_receipt.schema.json, hallucinate_app/swissknife/contracts/policy_decision.schema.json, hallucinate_app/swissknife/docs/ast_exports/interfaces/all_interfaces.json, hallucinate_app/swissknife/docs/mcp-plus-plus/DESCRIPTOR_AUTHORING_CLI.md, hallucinate_app/swissknife/docs/phase2/06_cross_domain_interfaces.md, hallucinate_app/swissknife/ipfs_accelerate_js/src/core/interfaces.ts, hallucinate_app/swissknife/ipfs_accelerate_js/src/interfaces.ts, hallucinate_app/swissknife/ipfs_accelerate_js/src/utils/browser_interface.ts, hallucinate_app/swissknife/ipfs_accelerate_js/src/utils/create_benchmark_schema.ts
- MCP descriptors: hallucinate_app/.github/workflows/mcp-daemon-e2e.yml, hallucinate_app/docs/MCP_DAEMON_ARCHITECTURE.md, hallucinate_app/docs/MCP_DAEMON_IMPLEMENTATION_SUMMARY.md, hallucinate_app/docs/QUICK_START_MCP.md, hallucinate_app/hallucinate_app/cjs/orbitdb_kit_cjs/orbitdb_kit.cjs, hallucinate_app/hallucinate_app/node/dashboard/orbitdb_security_dashboard.css, hallucinate_app/hallucinate_app/node/dashboard/orbitdb_security_dashboard.js, hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js, hallucinate_app/hallucinate_app/node/orbitdb_kit.js, hallucinate_app/hallucinate_app/node/secure_orbitdb_manager.js, hallucinate_app/hallucinate_app/python/hallucinate_app/secure_orbitdb_manager.py, hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_secure_orbitdb_manager.py, hallucinate_app/swissknife/benchmark/integration/mcp-client-benchmark.ts, hallucinate_app/swissknife/cleanup-archive/analysis/mcp_direct_diagnostic.js, hallucinate_app/swissknife/cleanup-archive/analysis/mcp_server_diagnostic.py, hallucinate_app/swissknife/cleanup-archive/docs/MCP-SERVER-DIAGNOSTIC-REPORT.md
- Python import roots: Bio, PIL, __future__, advanced_thread_pool_manager, aiohttp, argparse, asyncio, auth, auth_keystore_integration, auth_keystore_py, base64, collections, concurrent, contextlib, copy, cross, cross_browser_model_sharding, cryptography, database_backup_manager, database_query_system, database_sync_manager, dataclasses, datasets, datetime
- Goal: Prove `hallucinate_app` interoperates with `external/meta-wearables-dat-android` through importable contracts, interface descriptors, runtime handoff behavior, and integration tests.
- Evidence: tests/integration/test_hallucinate_app_external_meta_wearables_dat_android_interop.py, docs/integration/hallucinate_app-external_meta_wearables_dat_android.md, interface contract hallucinate_app external/meta-wearables-dat-android, hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js, hallucinate_app/hallucinate_app/node/views/test_interface.html, hallucinate_app/python/hallucinate_app/control_surface_schema.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_descriptor_validation.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_schemas.py, hallucinate_app/swissknife/contracts/control_surface_contract.schema.json
- Outputs: tests/integration/test_hallucinate_app_external_meta_wearables_dat_android_interop.py, docs/integration/hallucinate_app-external_meta_wearables_dat_android.md, hallucinate_app, external/meta-wearables-dat-android, hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js, hallucinate_app/hallucinate_app/node/views/test_interface.html, hallucinate_app/python/hallucinate_app/control_surface_schema.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_descriptor_validation.py
- Validation: python -m pytest tests/integration -q
- Refinement depth: 1
- Embedding query: hallucinate_app external/meta-wearables-dat-android interoperability integration test interface descriptor Bio PIL __future__ advanced_thread_pool_manager aiohttp argparse asyncio auth auth_keystore_integration auth_keystore_py base64 collections
- AST query: hallucinate_app, external/meta-wearables-dat-android, interface contract, integration test, Bio, PIL, __future__, advanced_thread_pool_manager, aiohttp, argparse, asyncio, auth, auth_keystore_integration, auth_keystore_py, base64, collections
- Parallel lane: objective/interoperability/hallucinate_app-external_meta_wearables_dat_android
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Gap task: Create one larger integration work item proving `hallucinate_app` and `external/meta-wearables-dat-android` can be used together, including a test, a contract note, and any adapter code needed by the objective.

## VAIOS-G087 Interoperate hallucinate_app with external/meta-wearables-dat-ios

- Status: deferred
- Deferred reason: Broad pairwise interoperability is preserved for post-gate work, but it must not outrank the phone-hosted Swissknife desktop, desktop-peer offload, Hallucinate App mediation, and Meta glasses launch-readiness gate.
- Parent: VAIOS-G000
- Fib priority: 3006
- Track: interoperability
- Priority: P1
- Bundle: objective/interoperability/hallucinate_app-external_meta_wearables_dat_ios
- Goal kind: interoperability
- Interoperability pair: hallucinate_app, external/meta-wearables-dat-ios
- Submodules: hallucinate_app, external/meta-wearables-dat-ios
- Interoperability score: 35
- Discovery sources: configured, gitlink, gitmodules
- Package manifests: hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/package.json, hallucinate_app/hallucinate_app/model_collection_viewer/package.json, hallucinate_app/hallucinate_app/node/package.json, hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_embeddings_py/setup.py, hallucinate_app/hallucinate_app/python/pyproject.toml, hallucinate_app/hallucinate_app/python/requirements.txt, hallucinate_app/hallucinate_app/python/setup.py, hallucinate_app/hallucinate_app/python/ucan_auth_py/setup.py, hallucinate_app/package.json, hallucinate_app/python/requirements.txt, hallucinate_app/swissknife/ipfs_accelerate_js/package.json, hallucinate_app/swissknife/package.json
- Interface descriptors: hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js, hallucinate_app/hallucinate_app/node/views/test_interface.html, hallucinate_app/python/hallucinate_app/control_surface_schema.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_descriptor_validation.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_schemas.py, hallucinate_app/swissknife/contracts/control_surface_contract.schema.json, hallucinate_app/swissknife/contracts/interaction_envelope.schema.json, hallucinate_app/swissknife/contracts/mediation_receipt.schema.json, hallucinate_app/swissknife/contracts/policy_decision.schema.json, hallucinate_app/swissknife/docs/ast_exports/interfaces/all_interfaces.json, hallucinate_app/swissknife/docs/mcp-plus-plus/DESCRIPTOR_AUTHORING_CLI.md, hallucinate_app/swissknife/docs/phase2/06_cross_domain_interfaces.md, hallucinate_app/swissknife/ipfs_accelerate_js/src/core/interfaces.ts, hallucinate_app/swissknife/ipfs_accelerate_js/src/interfaces.ts, hallucinate_app/swissknife/ipfs_accelerate_js/src/utils/browser_interface.ts, hallucinate_app/swissknife/ipfs_accelerate_js/src/utils/create_benchmark_schema.ts
- MCP descriptors: hallucinate_app/.github/workflows/mcp-daemon-e2e.yml, hallucinate_app/docs/MCP_DAEMON_ARCHITECTURE.md, hallucinate_app/docs/MCP_DAEMON_IMPLEMENTATION_SUMMARY.md, hallucinate_app/docs/QUICK_START_MCP.md, hallucinate_app/hallucinate_app/cjs/orbitdb_kit_cjs/orbitdb_kit.cjs, hallucinate_app/hallucinate_app/node/dashboard/orbitdb_security_dashboard.css, hallucinate_app/hallucinate_app/node/dashboard/orbitdb_security_dashboard.js, hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js, hallucinate_app/hallucinate_app/node/orbitdb_kit.js, hallucinate_app/hallucinate_app/node/secure_orbitdb_manager.js, hallucinate_app/hallucinate_app/python/hallucinate_app/secure_orbitdb_manager.py, hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_secure_orbitdb_manager.py, hallucinate_app/swissknife/benchmark/integration/mcp-client-benchmark.ts, hallucinate_app/swissknife/cleanup-archive/analysis/mcp_direct_diagnostic.js, hallucinate_app/swissknife/cleanup-archive/analysis/mcp_server_diagnostic.py, hallucinate_app/swissknife/cleanup-archive/docs/MCP-SERVER-DIAGNOSTIC-REPORT.md
- Python import roots: Bio, PIL, __future__, advanced_thread_pool_manager, aiohttp, argparse, asyncio, auth, auth_keystore_integration, auth_keystore_py, base64, collections, concurrent, contextlib, copy, cross, cross_browser_model_sharding, cryptography, database_backup_manager, database_query_system, database_sync_manager, dataclasses, datasets, datetime
- Goal: Prove `hallucinate_app` interoperates with `external/meta-wearables-dat-ios` through importable contracts, interface descriptors, runtime handoff behavior, and integration tests.
- Evidence: tests/integration/test_hallucinate_app_external_meta_wearables_dat_ios_interop.py, docs/integration/hallucinate_app-external_meta_wearables_dat_ios.md, interface contract hallucinate_app external/meta-wearables-dat-ios, hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js, hallucinate_app/hallucinate_app/node/views/test_interface.html, hallucinate_app/python/hallucinate_app/control_surface_schema.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_descriptor_validation.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_schemas.py, hallucinate_app/swissknife/contracts/control_surface_contract.schema.json
- Outputs: tests/integration/test_hallucinate_app_external_meta_wearables_dat_ios_interop.py, docs/integration/hallucinate_app-external_meta_wearables_dat_ios.md, hallucinate_app, external/meta-wearables-dat-ios, hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js, hallucinate_app/hallucinate_app/node/views/test_interface.html, hallucinate_app/python/hallucinate_app/control_surface_schema.py, hallucinate_app/python/hallucinate_app/test/test_control_surface_descriptor_validation.py
- Validation: python -m pytest tests/integration -q
- Refinement depth: 1
- Embedding query: hallucinate_app external/meta-wearables-dat-ios interoperability integration test interface descriptor Bio PIL __future__ advanced_thread_pool_manager aiohttp argparse asyncio auth auth_keystore_integration auth_keystore_py base64 collections
- AST query: hallucinate_app, external/meta-wearables-dat-ios, interface contract, integration test, Bio, PIL, __future__, advanced_thread_pool_manager, aiohttp, argparse, asyncio, auth, auth_keystore_integration, auth_keystore_py, base64, collections
- Parallel lane: objective/interoperability/hallucinate_app-external_meta_wearables_dat_ios
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Gap task: Create one larger integration work item proving `hallucinate_app` and `external/meta-wearables-dat-ios` can be used together, including a test, a contract note, and any adapter code needed by the objective.

## VAIOS-G689 Phone desktop glasses launch slice

- Status: completed
- Parent: VAIOS-G000
- Fib priority: 2
- Track: launch
- Priority: P0
- Bundle: objective/launch/phone-desktop-glasses
- Parallel lane: launch-vertical-slice
- Refinement depth: 1
- Embedding query: phone hosted Swissknife virtual desktop desktop peer offload Hallucinate App operator Meta glasses terminal receipts recovery
- AST query: virtual_ai_os_end_to_end_harness, meta_glasses_remote_terminal, peer_offload_policy_receipt, display_widget_intent
- Conflict policy: keep launch-slice evidence in tests, docs, and receipts; avoid broad scan or cleanup-only work unless it blocks the vertical slice
- Goal: A phone-hosted Swissknife virtual desktop can discover a desktop peer, offload compute, route operator commands through Hallucinate App, present status to Meta glasses, and recover with receipts in the hardware-free harness.
- Evidence: tests/test_virtual_ai_os_end_to_end_harness.py, src/handsfree/meta_glasses_remote_terminal.py, HAO-429 peer-offload policy receipts, HAO-430 hardware-free multimodal offload harness, MGW-269 display widget normalized intents, VAI-010 hardware-free end-to-end integration harness
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md, tests/test_virtual_ai_os_end_to_end_harness.py, src/handsfree
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_end_to_end_harness.py tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_meta_glasses_display_todo_queue.py -q
- Refinement: Add implementation tasks only when they directly improve the launch slice across phone, desktop peer, Swissknife, Hallucinate App, Meta glasses, receipts, or recovery.
- Gap task: Close the highest-leverage missing proof for the phone-to-desktop-to-glasses launch slice, not generic interoperability or repository cleanup.
- Completed at: 2026-06-23T07:45:03.060209+00:00
- Completion evidence: tests/test_virtual_ai_os_end_to_end_harness.py => tests/test_virtual_ai_os_end_to_end_harness.py (path), CONTRIBUTING.md (ast), agent-runner/apply_instruction.py (ast); src/handsfree/meta_glasses_remote_terminal.py => src/handsfree/meta_glasses_remote_terminal.py (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast); HAO-429 peer-offload policy receipts => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast); HAO-430 hardware-free multimodal offload harness => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md (embedding:0.35); MGW-269 display widget normalized intents => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/webapp/readiness.json (ast), implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md (embedding:0.30); VAI-010 hardware-free end-to-end integration harness => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), docs/implementation/IMPLEMENTATION_SUMMARY_NOTIFICATIONS.md (ast)
- Completion validation: 0

## VAIOS-G690 Phone-hosted Swissknife session

- Status: completed
- Parent: VAIOS-G689
- Fib priority: 2
- Track: launch
- Priority: P0
- Bundle: objective/launch/phone-session
- Parallel lane: launch-phone-session
- Refinement depth: 2
- Embedding query: phone hosted Swissknife virtual desktop mobile ORB session command dispatch Hallucinate App control plane
- AST query: phone_session, swissknife_virtual_desktop, normalized_intent, control_surface_dispatch
- Conflict policy: preserve one command envelope from mobile UI through Swissknife and Hallucinate App
- Goal: The mobile/phone side can host a virtual desktop session, expose Swissknife UI state, and send normalized operator intents into the Hallucinate App command plane.
- Evidence: VAI-006 Swissknife virtual UI binding, VAI-007 operator-console plane, MGW-269 display widget normalized intents, tests/test_virtual_ai_os_end_to_end_harness.py
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, tests/test_virtual_ai_os_end_to_end_harness.py, tests/test_meta_glasses_display_todo_queue.py
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_end_to_end_harness.py tests/test_meta_glasses_display_todo_queue.py -q
- Refinement: Split only if phone session state, command envelope, or operator-intent routing needs a separate proof.
- Gap task: Prove the phone-hosted virtual desktop session can launch, route commands, and expose state without assuming a desktop-only UI.
- Completed at: 2026-06-23T07:45:03.060209+00:00
- Completion evidence: VAI-006 Swissknife virtual UI binding => dev/meta-rayban-display-simulator/webapp/app.js (ast), implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md (ast), implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md (embedding:0.32); VAI-007 operator-console plane => implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md (embedding:0.37), mobile/modules/expo-glasses-audio/index.ts (ast), mobile/push/examples/expo_receive_handler.ts (ast); MGW-269 display widget normalized intents => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/webapp/readiness.json (ast), implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md (embedding:0.30); tests/test_virtual_ai_os_end_to_end_harness.py => tests/test_virtual_ai_os_end_to_end_harness.py (path), CONTRIBUTING.md (ast), agent-runner/apply_instruction.py (ast)
- Completion validation: 0

## VAIOS-G691 Desktop peer offload and receipts

- Status: completed
- Parent: VAIOS-G689
- Fib priority: 2
- Track: launch
- Priority: P0
- Bundle: objective/launch/desktop-offload
- Parallel lane: launch-peer-offload
- Refinement depth: 2
- Embedding query: desktop peer offload capability placement policy receipts recovery phone compute handoff
- AST query: peer_offload_policy_receipt, placement_policy, recovery_state, desktop_peer
- Conflict policy: keep policy receipts deterministic and make unavailable hardware a recoverable state
- Goal: The runtime can choose a desktop peer for compute offload from phone-originated work, emit placement/policy receipts, and recover deterministically when the peer is unavailable.
- Evidence: HAO-429 peer-offload policy receipts, HAO-430 hardware-free multimodal offload harness, capability scheduler policy, tests/test_virtual_ai_os_end_to_end_harness.py
- Outputs: hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, tests/test_virtual_ai_os_end_to_end_harness.py
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_end_to_end_harness.py tests/test_hallucinate_multimodal_control_todo_queue.py -q
- Refinement: Split only if placement policy, receipt schema, or recovery behavior needs a separate failing test.
- Gap task: Prove phone-originated work can be offloaded to a desktop peer with receipts and recovery instead of local-only execution.
- Completed at: 2026-06-23T07:45:03.060209+00:00
- Completion evidence: HAO-429 peer-offload policy receipts => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast); HAO-430 hardware-free multimodal offload harness => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md (embedding:0.35); capability scheduler policy => dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), mobile/push/examples/expo_receive_handler.ts (ast), mobile/src/screens/CommandScreen.js (ast); tests/test_virtual_ai_os_end_to_end_harness.py => tests/test_virtual_ai_os_end_to_end_harness.py (path), CONTRIBUTING.md (ast), agent-runner/apply_instruction.py (ast)
- Completion validation: 0

## VAIOS-G692 Meta glasses terminal readiness

- Status: completed
- Parent: VAIOS-G689
- Fib priority: 2
- Track: launch
- Priority: P0
- Bundle: objective/launch/meta-glasses-terminal
- Parallel lane: launch-glasses-terminal
- Refinement depth: 2
- Embedding query: Meta glasses remote terminal phone audio display status offload visibility pairing disconnection recovery
- AST query: meta_glasses_remote_terminal, glasses_audio_command, glasses_display_status, offload_visibility
- Conflict policy: keep hardware-free simulator evidence separate from physical-device readiness evidence
- Goal: Meta glasses act as a constrained phone terminal for audio commands, visual status, pairing state, offload visibility, and disconnection recovery.
- Evidence: VAI-008 Meta glasses remote terminal, src/handsfree/meta_glasses_remote_terminal.py, VAI-016 browser simulator shell, VAI-012 physical-device readiness plan, tests/test_virtual_ai_os_end_to_end_harness.py
- Outputs: src/handsfree/meta_glasses_remote_terminal.py, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, tests/test_virtual_ai_os_end_to_end_harness.py
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_end_to_end_harness.py tests/test_virtual_ai_os_todo_queue.py -q
- Refinement: Split simulator, phone pairing, and physical-device evidence only when one of those blocks launch readiness.
- Gap task: Prove Meta glasses can operate as the mobile terminal for the virtual desktop and can report desktop-offload state.
- Completed at: 2026-06-23T07:45:03.060209+00:00
- Completion evidence: VAI-008 Meta glasses remote terminal => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), implementation_plan/docs/19-virtual-ai-os-submodule-integration.md (exact); src/handsfree/meta_glasses_remote_terminal.py => src/handsfree/meta_glasses_remote_terminal.py (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast); VAI-016 browser simulator shell => mobile/modules/expo-glasses-audio/index.ts (ast), mobile/push/examples/expo_receive_handler.ts (ast), mobile/src/native/glassesAudio.js (ast); VAI-012 physical-device readiness plan => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast); tests/test_virtual_ai_os_end_to_end_harness.py => tests/test_virtual_ai_os_end_to_end_harness.py (path), CONTRIBUTING.md (ast), agent-runner/apply_instruction.py (ast)
- Completion validation: 0

## VAIOS-G693 Shared launch evidence packet

- Status: completed
- Parent: VAIOS-G689
- Fib priority: 1
- Track: launch
- Priority: P0
- Bundle: objective/launch/shared-evidence-packet
- Parallel lane: launch-shared-evidence
- Refinement depth: 2
- Embedding query: shared launch evidence packet phone desktop Swissknife Hallucinate App Meta glasses offload capability mediation placement recovery receipts
- AST query: launch_alignment, capability_receipt, mediation_receipt, placement_receipt, meta_glasses_status_receipt
- Conflict policy: keep evidence packet edits scoped to launch docs, deterministic fixtures, and focused tests
- Goal: A shared launch evidence packet ties phone-hosted Swissknife virtual desktop commands, Hallucinate App mediation, desktop peer offload, Meta glasses display status, and recovery receipts to one session and command identity.
- Evidence: VAI-338 launch alignment map, HAO-434 launch replay receipts, MGW-272 glasses launch capability receipts
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md, data/virtual_ai_os/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_meta_glasses_display_todo_queue.py -q
- Refinement: Split only if the shared packet needs a separate proof for capability, mediation, placement, recovery, or render receipts.
- Gap task: Connect the completed launch slice into one cross-board evidence packet that the supervisor can validate before physical-device rehearsal.
- Completed at: 2026-06-23T13:16:26.749131+00:00
- Completion evidence: VAI-338 launch alignment map => implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md (embedding:0.43), implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md (embedding:0.48), mobile/push/examples/expo_receive_handler.ts (ast); HAO-434 launch replay receipts => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast); MGW-272 glasses launch capability receipts => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast)
- Completion validation: 0

## VAIOS-G694 Phone-hosted physical rehearsal inputs

- Status: completed
- Parent: VAIOS-G693
- Fib priority: 1
- Track: launch
- Priority: P0
- Bundle: objective/launch/phone-physical-rehearsal
- Parallel lane: launch-phone-rehearsal
- Refinement depth: 3
- Embedding query: physical phone rehearsal mobile hosted Swissknife virtual desktop Hallucinate App commands Meta glasses interface fallback receipts
- AST query: phone_hosted_session, physical_device_readiness, mobile_orb, display_webapp
- Conflict policy: keep physical-device assumptions explicit and preserve simulator fallback evidence
- Goal: The phone-hosted session has a rehearsal packet for launching Swissknife, routing commands through Hallucinate App, exposing fallback UI, and preparing Meta glasses as the phone interface.
- Evidence: VAI-023 iPhone native DAT handoff, VAI-338 launch alignment map, MGW-273 physical-device rehearsal packet
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md, data/meta_glasses_display_widgets/discovery
- Validation: rg -n "physical-device rehearsal|phone-hosted|Swissknife|Hallucinate App|Meta glasses|receipt" implementation_plan/docs data
- Refinement: Split only if phone pairing, native DAT, Web App fallback, or manual evidence capture needs a distinct blocker task.
- Gap task: Prepare the phone-side physical rehearsal inputs without requiring hardware in the autonomous run.
- Completed at: 2026-06-23T13:16:26.749131+00:00
- Completion evidence: VAI-023 iPhone native DAT handoff => docs/meta-wearables-dat-display-physical-validation-checklist.md (embedding:0.43), docs/meta-wearables-dat-display-rollout-evidence-template.md (embedding:0.41), implementation_plan/docs/19-virtual-ai-os-submodule-integration.md (exact); VAI-338 launch alignment map => implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md (embedding:0.43), implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md (embedding:0.48), mobile/push/examples/expo_receive_handler.ts (ast); MGW-273 physical-device rehearsal packet => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast)
- Completion validation: 0

## VAIOS-G695 Desktop-peer offload recovery rehearsal

- Status: completed
- Parent: VAIOS-G693
- Fib priority: 1
- Track: launch
- Priority: P0
- Bundle: objective/launch/desktop-peer-recovery
- Parallel lane: launch-desktop-recovery
- Refinement depth: 3
- Embedding query: desktop peer offload recovery rehearsal timeout denial retry cancellation fallback phone Swissknife Hallucinate App Meta glasses receipts
- AST query: desktop_peer, offload_failure, retry_exhausted, fallback_to_phone, recovery_receipt
- Conflict policy: keep recovery-state vocabulary owned by Hallucinate App and visible to phone, Swissknife, and glasses surfaces
- Goal: Desktop-peer timeout, denial, retry exhaustion, cancellation, and fallback-to-phone outcomes are rehearsed with one Hallucinate App recovery state rendered by phone UI, Swissknife, and Meta glasses.
- Evidence: HAO-435 operator recovery rehearsal, VAI-339 launch replay gate, HAO-432 launch-slice replay receipts
- Outputs: hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md, tests/test_virtual_ai_os_end_to_end_harness.py, data/hallucinate_multimodal_control/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_end_to_end_harness.py tests/test_hallucinate_multimodal_control_todo_queue.py -q
- Refinement: Split only if a recovery outcome lacks deterministic replay coverage.
- Gap task: Prove desktop offload failure handling is launch-ready instead of optimistic-only.
- Completed at: 2026-06-23T13:16:26.749131+00:00
- Completion evidence: HAO-435 operator recovery rehearsal => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast); VAI-339 launch replay gate => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast); HAO-432 launch-slice replay receipts => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast)
- Completion validation: 0

## VAIOS-G696 Meta glasses physical terminal handoff

- Status: completed
- Parent: VAIOS-G693
- Fib priority: 1
- Track: launch
- Priority: P0
- Bundle: objective/launch/glasses-terminal-handoff
- Parallel lane: launch-glasses-handoff
- Refinement depth: 3
- Embedding query: Meta glasses physical terminal handoff phone interface pairing display fallback offload visibility Hallucinate App receipts Swissknife
- AST query: meta_glasses_remote_terminal, pairing, display_fallback, offload_visibility, terminal_handoff
- Conflict policy: keep physical glasses readiness separate from simulator proofs while using the same command and receipt contract
- Goal: Meta glasses can be rehearsed as the phone interface to the virtual desktop with pairing gates, display fallback, desktop-offload visibility, and Hallucinate App receipt inspection.
- Evidence: MGW-273 physical-device rehearsal packet, VAI-012 physical-device readiness, VAI-339 launch replay gate
- Outputs: implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/meta_glasses_display_widgets/discovery
- Validation: rg -n "Meta glasses|physical-device rehearsal|phone interface|desktop peer|display fallback|receipt" implementation_plan/docs data
- Refinement: Split only if pairing, display fallback, or manual receipt inspection blocks the first hardware run.
- Gap task: Prepare the Meta glasses handoff path for physical validation without inventing a second command surface.
- Completed at: 2026-06-23T13:16:26.749131+00:00
- Completion evidence: MGW-273 physical-device rehearsal packet => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast); VAI-012 physical-device readiness => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast); VAI-339 launch replay gate => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast)
- Completion validation: 0

## VAIOS-G697 Production launch readiness gate

- Status: completed
- Parent: VAIOS-G689
- Fib priority: 1
- Track: launch
- Priority: P0
- Bundle: objective/launch/production-readiness-gate
- Parallel lane: launch-readiness-gate
- Refinement depth: 2
- Embedding query: production launch gate phone hosted Swissknife virtual desktop desktop peer offload Meta glasses terminal physical validation receipts Playwright e2e
- AST query: LaunchReadinessGate, launch_readiness_receipt_v1, phone_desktop_glasses_readiness, playwright, meta-glasses-virtual-os, multimodal-control-surface
- Conflict policy: keep launch readiness evidence in explicit receipts and tests; do not accept generic AST or documentation matches as sufficient proof
- Goal: The supervisor must keep the phone-hosted Swissknife virtual desktop, desktop-peer offload, Hallucinate App mediation, and Meta glasses terminal path open until a launch-readiness receipt proves every product-critical hop.
- Evidence: tests/test_virtual_ai_os_launch_readiness_gate.py, docs/launch/phone_desktop_glasses_readiness.md, launch_readiness_receipt_v1, swissknife/test/e2e/meta-glasses-virtual-os.spec.ts, hallucinate_app/test/e2e/multimodal-control-surface.spec.ts, Playwright launch replay
- Outputs: tests/test_virtual_ai_os_launch_readiness_gate.py, docs/launch/phone_desktop_glasses_readiness.md, data/virtual_ai_os/discovery, data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q && npm --prefix swissknife run test:e2e:meta-glasses && npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
- Refinement: Split only if the gate needs a separate child for physical phone, desktop peer, or Meta glasses evidence capture.
- Gap task: Add a launch-readiness gate that prevents the objective heap from treating weak scanner matches as proof that the product slice is production ready.
- Gate evidence: VAI-340 launch readiness gate => data/virtual_ai_os/discovery/2026-06-23-vai-340-launch-readiness-gate.md; MGW-274 launch readiness gate => data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-274-launch-readiness-gate.md; HAO-436 launch readiness gate => data/hallucinate_multimodal_control/discovery/2026-06-23-hao-436-launch-readiness-gate.md; HAO-440 physical readiness aggregate => data/hallucinate_multimodal_control/discovery/2026-06-23-hao-440-launch-readiness-physical-aggregate.md; launch Playwright validation gate => tests/test_virtual_ai_os_launch_readiness_gate.py, docs/launch/phone_desktop_glasses_readiness.md, swissknife/build-tools/configs/playwright.meta-glasses.config.ts, hallucinate_app/scripts/run_playwright_test.mjs
- Active gate reason: Keep this goal open until a single launch-readiness receipt proves the phone, desktop-peer offload, Hallucinate App mediation, Meta glasses render path, and Playwright launch replay together.
- Active HAO child tasks: HAO-437 physical phone ingress rehearsal receipt; HAO-438 desktop-peer offload smoke receipt; HAO-439 Meta glasses terminal receipt capture; HAO-440 aggregate physical-readiness evidence into the launch gate; HAO-441 MCP server feature inventory; HAO-442 Hallucinate App Python MCP daemon launch; HAO-443 Swissknife MCP capability registry; HAO-444 Swissknife app MCP feature invocation; HAO-445 Mcp-Plus-Plus compatibility; HAO-446 HAO/Swissknife MCP Playwright coverage; HAO-447 aggregate MCP evidence into launch readiness.
- Completed at: 2026-06-23T22:58:56.778153+00:00
- Completion evidence: tests/test_virtual_ai_os_launch_readiness_gate.py => tests/test_virtual_ai_os_launch_readiness_gate.py (path), CONTRIBUTING.md (ast), agent-runner/apply_instruction.py (ast); docs/launch/phone_desktop_glasses_readiness.md => docs/launch/phone_desktop_glasses_readiness.md (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast); launch_readiness_receipt_v1 => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast); swissknife/test/e2e/meta-glasses-virtual-os.spec.ts => swissknife/test/e2e/meta-glasses-virtual-os.spec.ts (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast); hallucinate_app/test/e2e/multimodal-control-surface.spec.ts => hallucinate_app/test/e2e/multimodal-control-surface.spec.ts (path), dev/meta-rayban-display-simulator/webapp/app.js (ast), docs/launch/phone_desktop_glasses_readiness.md (exact); Playwright launch replay => agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast)
- Completion validation: 0

## VAIOS-G698 Supervisor objective and task janitor

- Status: completed
- Parent: VAIOS-G010
- Fib priority: 1
- Track: ops
- Priority: P0
- Bundle: objective/ops/task-janitor
- Parallel lane: supervisor-backlog
- Refinement depth: 2
- Embedding query: supervisor objective task janitor retire stale goals archive orphaned tasks remove useless work fibonacci heap dynamic reconciliation
- AST query: ObjectiveTaskJanitor, objective_task_janitor, retired_task_reason, heap_goal_retirement_receipt
- Conflict policy: make task retirement explicit and reversible; preserve audit receipts for every generated goal or task that is archived, deprioritized, or reopened
- Goal: The daemon continuously reconciles goals, subgoals, tasks, subtasks, and heap priorities so stale or off-mission work is archived or deprioritized while launch-blocking gaps are reopened.
- Evidence: tests/test_supervisor_objective_task_janitor.py, objective_task_janitor, retired_task_reason, heap_goal_retirement_receipt
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor, tests/test_supervisor_objective_task_janitor.py
- Validation: PYTHONPATH=external/ipfs_accelerate pytest tests/test_supervisor_objective_task_janitor.py -q
- Refinement: Add child goals for task archival, heap-goal reopening, and stale blocked-task summarization only after the janitor contract lands.
- Gap task: Implement an objective/task janitor that can dynamically add, remove, archive, reopen, and reprioritize daemon work against the launch objective.
- Completed at: 2026-06-23T14:20:50+00:00
- Completion evidence: objective_task_janitor strategy reconciler, retired_task_reason receipts, heap_goal_retirement_receipt strategy output, supervisor objective_task_janitor phase, and tests/test_supervisor_objective_task_janitor.py.
- Completion validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_supervisor_objective_task_janitor.py tests/test_virtual_ai_os_todo_queue.py tests/test_meta_glasses_display_todo_queue.py tests/test_hallucinate_multimodal_control_todo_queue.py -q => 96 passed, 1 warning.

## VAIOS-G699 Merge-lock retry and duplicate-attempt suppression

- Status: completed
- Parent: VAIOS-G010
- Fib priority: 1
- Track: ops
- Priority: P0
- Bundle: objective/ops/merge-reconciliation
- Parallel lane: supervisor-backlog
- Refinement depth: 2
- Embedding query: merge lock retry queue duplicate attempt suppression worktree cleanup automatic failed validation retry supervisor daemon
- AST query: merge_lock_retry_queue, duplicate_attempt_suppression, transient_merge_lock, validation_auto_repair
- Conflict policy: distinguish transient merge-lock deferrals from real merge conflicts, and preserve validated implementation commits before spawning replacement attempts
- Goal: A validated implementation whose merge was deferred by a transient lock is retried and cleaned up automatically instead of being blocked, duplicated, or stranded in an orphaned worktree.
- Evidence: tests/test_implementation_daemon_merge_lock_retry.py, merge_lock_retry_queue, duplicate_attempt_suppression, transient_merge_lock
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py, tests/test_implementation_daemon_merge_lock_retry.py
- Validation: PYTHONPATH=external/ipfs_accelerate pytest tests/test_implementation_daemon_merge_lock_retry.py -q
- Refinement: Split validation auto-repair into a child goal if lock retry lands but failed-validation retry remains ad hoc.
- Gap task: Teach the daemon to retry transient merge-lock failures, suppress duplicate attempts for already-validated work, and clean merged worktrees without manual intervention.
- Completed at: 2026-06-23T14:20:50+00:00
- Completion evidence: transient_merge_lock classification, merge_lock_retry_queue candidate selection, duplicate_attempt_suppression waiting state, reconciliation todo completion, and tests/test_implementation_daemon_merge_lock_retry.py.
- Completion validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_implementation_daemon_merge_lock_retry.py tests/test_supervisor_objective_task_janitor.py tests/test_virtual_ai_os_todo_queue.py tests/test_meta_glasses_display_todo_queue.py tests/test_hallucinate_multimodal_control_todo_queue.py -q => 99 passed, 1 warning.

