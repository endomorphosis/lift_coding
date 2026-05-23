# Virtual AI OS Submodule Integration Todo Board

This is the machine-readable backlog for the ipfs_datasets_py todo supervisor/daemon.
It operationalizes `implementation_plan/docs/19-virtual-ai-os-submodule-integration.md`.

Run from the repository root:

```bash
python3 scripts/virtual_ai_os_todo_daemon.py --once
python3 scripts/virtual_ai_os_todo_supervisor.py --once
python3 scripts/virtual_ai_os_llm_router.py --task-id VAI-003
```

To allow autonomous implementation in isolated worktrees, pass `--implement` to the supervisor or daemon and provide an implementation command if the default Codex/Copilot fallback is not desired.

## VAI-000 Bootstrap supervised virtual-AI-OS backlog processing

- Status: completed
- Completion: manual
- Priority: P0
- Track: ops
- Depends on:
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md, scripts/virtual_ai_os_todo_daemon.py, scripts/virtual_ai_os_todo_supervisor.py, scripts/virtual_ai_os_llm_router.py, tests/test_virtual_ai_os_todo_queue.py
- Validation: PYTHONPATH=external/ipfs_datasets python3 scripts/virtual_ai_os_todo_daemon.py --once; PYTHONPATH=external/ipfs_datasets python3 scripts/virtual_ai_os_todo_supervisor.py --once; PYTHONPATH=external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py
- Acceptance: The virtual-AI-OS roadmap is available as a daemon-parseable VAI task board with repository-local wrappers and parser tests.

## VAI-001 Record reviewed source topology and pin guardrails

- Status: completed
- Completion: manual
- Priority: P0
- Track: ops
- Depends on: VAI-000
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, .gitmodules
- Validation: rg -n "ipfs_datasets_py|ipfs_accelerate_py|ipfs_kit_py|hallucinate_app|mcp_plus_plus|Meta glasses" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md .gitmodules
- Acceptance: The roadmap records the reviewed component revisions, root submodule topology, canonical upstream URLs for tracked repos, Meta glasses role, and the unresolved canonical source blocker for `mcp_plus_plus`.

## VAI-002 Align root git submodule wiring with canonical upstreams

- Status: completed
- Completion: manual
- Priority: P0
- Track: ops
- Depends on: VAI-001
- Outputs: .gitmodules
- Validation: git config --file .gitmodules --get-regexp '^submodule\..*\.(path|url)$' | rg 'ipfs_datasets_py|ipfs_accelerate_py|ipfs_kit_py|hallucinate_app'
- Acceptance: Root git metadata points the tracked component submodules at the canonical reviewed upstream repositories without overwriting dirty nested worktrees.

## VAI-003 Define the cross-repo capability registry

- Status: completed
- Completion: manual
- Priority: P0
- Track: runtime
- Depends on: VAI-002
- Outputs: src/handsfree/ai/capability_registry.py, src/handsfree/models.py, tests/test_virtual_ai_os_capability_registry.py, implementation_plan/docs/16-phase-1-capability-registry-execution-matrix.md
- Validation: PYTHONPATH=./src pytest tests/test_virtual_ai_os_capability_registry.py
- Acceptance: One typed registry maps capabilities to owner repo, execution mode, fallback mode, confirmation policy, artifact shape, display summary shape, and integration-test coverage.

## VAI-004 Add the virtual runtime placement layer

- Status: completed
- Completion: manual
- Priority: P0
- Track: runtime
- Depends on: VAI-003
- Outputs: src/handsfree/ai/runtime_router.py, src/handsfree/ipfs_accelerate_adapters.py, src/handsfree/ipfs_kit_adapters.py, tests/test_virtual_ai_os_runtime_router.py
- Validation: PYTHONPATH=./src pytest tests/test_virtual_ai_os_runtime_router.py
- Acceptance: HandsFree can deterministically choose direct import, local CLI, daemon-mediated, Swissknife ORB, or MCP-backed execution for each capability without duplicating routing logic across components.

## VAI-005 Integrate ipfs_datasets_py todo-daemon state into HandsFree task orchestration

- Status: completed
- Completion: manual
- Priority: P0
- Track: backend
- Depends on: VAI-003, VAI-004
- Outputs: src/handsfree/agents/service.py, src/handsfree/agent_providers.py, tests/test_virtual_ai_os_task_orchestration.py
- Validation: PYTHONPATH=./src pytest tests/test_virtual_ai_os_task_orchestration.py
- Acceptance: HandsFree can observe, summarize, and resume daemon-backed task progress using one normalized task-state contract.

## VAI-006 Bind Swissknife into the virtual UI and ORB plane

- Status: completed
- Completion: manual
- Priority: P0
- Track: ui
- Depends on: VAI-003, VAI-004
- Outputs: swissknife/src/services/mcp-orb-capability-router.ts, swissknife/src/services/meta-glasses-display-orb-adapter.ts, swissknife/test/mcp-plus-plus/meta-glasses-display-harness.test.ts, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md
- Validation: cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-display-harness.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Swissknife exposes reviewed ORB/UI capabilities as part of the shared runtime registry and can render operator-safe progress and action surfaces for remote clients.

## VAI-007 Promote Hallucinate App into the operator-console plane

- Status: completed
- Completion: manual
- Priority: P0
- Track: ui
- Depends on: VAI-003, VAI-005, VAI-006
- Outputs: hallucinate_app/README.md, hallucinate_app/test/README.md, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md
- Validation: rg -n "daemon manager|SwissKnife|virtual desktop|operator" hallucinate_app/README.md hallucinate_app/test/README.md implementation_plan/docs/19-virtual-ai-os-submodule-integration.md
- Acceptance: Hallucinate App is documented and wired as the GUI shell and daemon-management console for the virtual AI OS rather than an optional side project.

## VAI-008 Route Meta glasses audio and display as remote terminal endpoints

- Status: completed
- Completion: manual
- Priority: P0
- Track: mobile
- Depends on: VAI-004, VAI-005, VAI-006
- Outputs: src/handsfree/agent_providers.py, mobile/src/utils/agentActions.js, tests/test_meta_glasses_display_widget_harness.py, implementation_plan/docs/15-meta-wearables-dat-mcpplusplus-integration-roadmap.md
- Validation: PYTHONPATH=./src pytest tests/test_meta_glasses_display_widget_harness.py; cd mobile && npm test -- --runInBand src/utils/__tests__/agentActions.test.js
- Acceptance: The runtime can emit remote-terminal audio/display actions and progress summaries for Meta glasses with safe mobile/web fallbacks when native display is unavailable.

## VAI-009 Add environment, pin, and bootstrap contracts for component repos

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: VAI-002, VAI-004
- Outputs: docs/CONFIGURATION.md, docs/GETTING_STARTED.md, scripts/virtual_ai_os_todo_supervisor.py, tests/test_virtual_ai_os_todo_queue.py
- Validation: PYTHONPATH=external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py; rg -n "virtual AI OS|submodule|bootstrap|worktree" docs implementation_plan/docs scripts
- Acceptance: Operators have one documented bootstrap contract for submodule init, env configuration, daemon worktrees, and rollback-safe pin updates.

## VAI-010 Build a hardware-free end-to-end integration harness

- Status: completed
- Completion: manual
- Priority: P1
- Track: quality
- Depends on: VAI-005, VAI-006, VAI-008
- Outputs: tests/test_virtual_ai_os_end_to_end.py, mobile/src/utils/__tests__/displayWidgetHarness.test.js, hallucinate_app/test/e2e/README.md
- Validation: PYTHONPATH=./src pytest tests/test_virtual_ai_os_end_to_end.py; cd mobile && npm test -- --runInBand src/utils/__tests__/displayWidgetHarness.test.js
- Acceptance: The full workflow from daemon task state to UI emission to mobile/glasses fallback rendering can be exercised without requiring paired hardware.

## VAI-011 Add observability, policy, and rollback coverage

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: VAI-004, VAI-005, VAI-008, VAI-010
- Outputs: docs/observability_metrics.md, src/handsfree/config.py, tests/test_virtual_ai_os_config.py
- Validation: PYTHONPATH=./src pytest tests/test_virtual_ai_os_config.py; rg -n "virtual AI OS|rollback|metrics|policy" docs src tests
- Acceptance: The system exposes feature flags, metrics, policy decisions, and rollback-safe pinning/transport guards for every cross-repo execution path.

## VAI-012 Validate physical-device and desktop operator readiness

- Status: completed
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: VAI-007, VAI-008, VAI-010, VAI-011
- Outputs: docs/meta-wearables-dat-display-physical-validation-checklist.md, docs/mvp1-demo-checklist.md, hallucinate_app/test/e2e/README.md
- Validation: rg -n "physical|desktop|operator|display" docs/meta-wearables-dat-display-physical-validation-checklist.md docs/mvp1-demo-checklist.md hallucinate_app/test/e2e/README.md
- Acceptance: Physical-device and desktop-console readiness evidence exists for operator workflows, remote display behavior, rollback, and degraded-mode handling.

## VAI-013 Resolve the canonical mcp_plus_plus upstream source

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: VAI-001
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, .gitmodules, data/virtual_ai_os/discovery
- Validation: rg -n "mcp_plus_plus|MCP\+\+|canonical source|Repository not found" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md
- Acceptance: The team either records the valid canonical source repository and integrates it safely as a tracked source, or records evidence-backed rationale for continuing to treat MCP++ as a distributed protocol surface across existing repos.

## VAI-014 Investigate implementation unknowns and expand the backlog

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on: VAI-003, VAI-004, VAI-005, VAI-006, VAI-007, VAI-008, VAI-009, VAI-010, VAI-011, VAI-012, VAI-013
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery
- Validation: PYTHONPATH=external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py; rg -n "VAI-014|unknowns|discovery|canonical source" implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md implementation_plan/docs/19-virtual-ai-os-submodule-integration.md
- Acceptance: After the initial backlog completes, inspect the control-plane, UI-plane, device-plane, and daemon-integration code paths for missed work; append new daemon-parseable VAI tasks or record a dated no-new-unknowns discovery report with evidence.