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

## VAI-015 Refresh reviewed submodule pins and automation guardrails

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: VAI-014
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md, data/virtual_ai_os/discovery/submodule-refresh-2026-05-23.md
- Validation: git submodule status; git status --short --ignore-submodules=none; rg -n "2026-05-23 submodule refresh findings|ipfs_datasets|hallucinate_app|swissknife|recursive" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md
- Acceptance: The roadmap and daemon backlog reflect the live reviewed pins, explicitly call out the `external/ipfs_datasets` gitlink drift, preserve the dirty `swissknife` worktree, and record the recursive `ipfs_kit` nested-submodule blocker instead of assuming a clean recursive bootstrap.

## VAI-016 Build the Meta Ray-Ban browser simulator shell

- Status: completed
- Completion: manual
- Priority: P1
- Track: mobile
- Depends on: VAI-014
- Outputs: dev/meta-rayban-display-simulator, implementation_plan/docs/20-meta-rayban-display-interface-simulator.md, tests/test_meta_rayban_display_simulator.py
- Validation: PYTHONPATH=./src pytest tests/test_meta_rayban_display_simulator.py; rg -n "600x600|focus_order|render_widget|ArrowUp|ArrowDown|Enter" dev/meta-rayban-display-simulator implementation_plan/docs/20-meta-rayban-display-interface-simulator.md
- Acceptance: A browser-first 600x600 simulator exists for Meta Ray-Ban display flows, supports D-pad style focus navigation, emits bridge-compatible action traces, and does not claim to be an official Meta native display emulator.

## VAI-017 Connect simulator artifacts to mobile ORB and Web App readiness flows

- Status: completed
- Completion: manual
- Priority: P1
- Track: quality
- Depends on: VAI-016
- Outputs: mobile/src/orb, config/display_webapp_readiness.example.json, scripts/lint_display_webapp_readiness.py, implementation_plan/docs/20-meta-rayban-display-interface-simulator.md
- Validation: cd mobile && npm test -- --runInBand src/orb/__tests__/metaGlassesMobileOrbBridge.test.js; PYTHONPATH=./src pytest tests/test_meta_glasses_mobile_orb_runtime.py tests/test_meta_rayban_display_simulator.py; rg -n "MockDevice|Web App mode|readiness.json|trace.json|mobile_fixture" implementation_plan/docs/20-meta-rayban-display-interface-simulator.md mobile/src/orb config scripts
- Acceptance: Simulator fixtures round-trip into the mobile ORB/display bridge, Web App readiness artifacts are exported and lintable, and the pre-iPhone validation path uses one manifest/trace contract across browser, mobile, and backend tests.

## VAI-018 Validate DAT MockDeviceKit parity for native mobile simulation

- Status: completed
- Completion: manual
- Priority: P1
- Track: mobile
- Depends on: VAI-017
- Outputs: mobile/modules/expo-meta-wearables-dat, mobile/src/native/__tests__, docs/meta-wearables-dat-display-integration.md
- Validation: cd mobile && npm test -- --runInBand src/native/__tests__/wearablesBridge.test.js; rg -n "MockDevice|MockDeviceKit|permission|configuration|phone camera|DAT" docs mobile external/meta-wearables-dat-ios external/meta-wearables-dat-android
- Acceptance: The native mobile simulation path documents exactly what Meta MockDeviceKit can validate, what remains browser-only for display rendering, and which mobile bridge tests mirror device/session/media/permission states before iPhone hardware testing.

## VAI-019 Add cross-submodule virtual AI OS integration tests

- Status: todo
- Completion: manual
- Priority: P1
- Track: quality
- Depends on: VAI-015, VAI-017
- Outputs: tests/test_virtual_ai_os_end_to_end.py, tests/test_virtual_ai_os_runtime_router.py, tests/test_meta_glasses_mobile_orb_bridge.py
- Validation: PYTHONPATH=./src pytest tests/test_virtual_ai_os_end_to_end.py tests/test_virtual_ai_os_runtime_router.py tests/test_meta_glasses_mobile_orb_bridge.py
- Acceptance: Tests exercise one full task flow across todo-daemon state, capability routing, SwissKnife ORB descriptor binding, IPFS artifact/provenance metadata, backend policy, mobile bridge dispatch, and Meta glasses display/audio fallback metadata.

## VAI-020 Harden mobile ORB edge diagnostics and policy receipts

- Status: todo
- Completion: manual
- Priority: P1
- Track: backend
- Depends on: VAI-017
- Outputs: spec/meta_glasses_mobile_orb_bridge_interface.json, src/handsfree/api.py, mobile/src/orb, mobile/src/screens/GlassesDiagnosticsScreen.js
- Validation: PYTHONPATH=./src pytest tests/test_meta_glasses_mobile_orb_bridge.py tests/test_meta_glasses_mobile_orb_runtime.py; cd mobile && npm test -- --runInBand src/orb/__tests__/metaGlassesMobileOrbBridge.test.js src/orb/__tests__/metaGlassesMobileOrbRuntime.test.js src/orb/__tests__/metaGlassesMobileOrbApiBackend.test.js
- Acceptance: Mobile edge sessions expose backend capability counts, descriptor CIDs, policy CIDs, binding state, receipt CIDs, and fallback reasons in one diagnostics contract that works in simulator and physical-device modes.

## VAI-021 Resolve nested submodule hygiene for ipfs_kit recursive bootstrap

- Status: todo
- Completion: manual
- Priority: P2
- Track: ops
- Depends on: VAI-015
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery/submodule-refresh-2026-05-23.md
- Validation: git -C external/ipfs_kit submodule status; git submodule status --recursive
- Acceptance: Either upstream `external/ipfs_kit` metadata is repaired/pinned so recursive submodule status succeeds, or the monorepo bootstrap scripts explicitly avoid recursive traversal there and document the local-safe replacement command.

## VAI-022 Package the browser Web App for HTTPS glasses loading

- Status: todo
- Completion: manual
- Priority: P1
- Track: mobile
- Depends on: VAI-017
- Outputs: dev/meta-rayban-display-simulator/webapp, docs/ios-rayban-mvp1-runbook.md, docs/ios-rayban-mvp1-demo-runbook.md
- Validation: PYTHONPATH=./src pytest tests/test_meta_rayban_display_simulator.py; rg -n "publicly available HTTPS|QR|Meta AI app|Web apps|readiness.json" dev/meta-rayban-display-simulator docs implementation_plan/docs/20-meta-rayban-display-interface-simulator.md
- Acceptance: The Web App simulator export has deployable static files, readiness metadata, and a runbook for hosting over HTTPS and adding it to Meta AI App Web Apps before native iPhone DAT migration.

## VAI-023 Prepare iPhone native DAT handoff and physical validation evidence

- Status: todo
- Completion: manual
- Priority: P1
- Track: mobile
- Depends on: VAI-018, VAI-020, VAI-022
- Outputs: docs/device-smoke-checklist-ios-meta-glasses.md, docs/meta-wearables-dat-display-physical-validation-checklist.md, docs/meta-wearables-dat-display-rollout-evidence-template.md
- Validation: rg -n "iPhone|DAT|DisplayAccess|firmware|Meta AI app|evidence|rollback" docs mobile/modules/expo-meta-wearables-dat
- Acceptance: iPhone migration has a concrete smoke-test sequence, expected simulator trace parity, native DAT display fallback criteria, rollback switches, and evidence templates for real glasses runs.

## VAI-024 Add Hallucinate App and SwissKnife desktop operator E2E coverage

- Status: todo
- Completion: manual
- Priority: P2
- Track: ui
- Depends on: VAI-019, VAI-020
- Outputs: hallucinate_app/test, swissknife/test/mcp-plus-plus, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md
- Validation: cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-display-harness.test.ts test/mcp-plus-plus/meta-glasses-mobile-orb-bridge.test.ts --config=config/jest/jest.config.cjs --runInBand; rg -n "operator|daemon|desktop|SwissKnife|Meta glasses" hallucinate_app/test swissknife/test implementation_plan/docs/19-virtual-ai-os-submodule-integration.md
- Acceptance: Operator console tests prove a daemon task can be inspected, routed, rendered, and recovered through SwissKnife/Hallucinate surfaces without paired glasses hardware.

## VAI-025 Re-check canonical mcp_plus_plus source and standalone pin decision

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on: VAI-015
- Outputs: data/virtual_ai_os/discovery, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, .gitmodules
- Validation: git ls-remote https://github.com/endomorphosis/mcp_plus_plus HEAD refs/heads/main refs/heads/master || true; rg -n "mcp_plus_plus|distributed protocol surface|Repository not found" data/virtual_ai_os/discovery implementation_plan/docs/19-virtual-ai-os-submodule-integration.md
- Acceptance: The team has fresh evidence for either adding a standalone `mcp_plus_plus` submodule or continuing to keep MCP++ as an interface/protocol surface distributed across SwissKnife, ipfs_datasets_py, and ipfs_accelerate_py.

## VAI-026 Supervised autonomous implementation cadence

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: VAI-015
- Outputs: data/virtual_ai_os/state, implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md
- Validation: PYTHONPATH=external/ipfs_datasets python3 scripts/virtual_ai_os_todo_daemon.py --once; PYTHONPATH=external/ipfs_datasets python3 scripts/virtual_ai_os_todo_supervisor.py --once; rg -n "VAI-018|VAI-019|VAI-020|VAI-023|VAI-026" implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md data/virtual_ai_os/state
- Acceptance: The ipfs_datasets_py todo daemon/supervisor can parse the expanded board, report ready work, preserve dependency order, and provide enough state for autonomous implementation agents to continue without guessing the next task.
