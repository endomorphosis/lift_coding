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

## Autonomous Cadence State

Run the daemon before the supervisor for one-shot checks. The daemon writes
`data/virtual_ai_os/state/virtual_ai_os_task_state.json`,
`data/virtual_ai_os/state/virtual_ai_os_strategy.json`, and
`data/virtual_ai_os/state/virtual_ai_os_events.jsonl`. Implementation agents
should read `recommended_task_id`, `ready_task_ids`, `waiting_task_ids`,
`task_statuses`, `task_artifacts`, and `task_validation` from that state
instead of inferring the next task from the markdown order.

After VAI-015, VAI-018 is completed, VAI-019 and VAI-020 are ready, VAI-023
waits for VAI-020 and VAI-022, and VAI-026 verifies that this supervised
cadence remains parseable and resumable.

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

- Status: completed
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

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: VAI-015
- Outputs: data/virtual_ai_os/state, implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md
- Validation: PYTHONPATH=external/ipfs_datasets python3 scripts/virtual_ai_os_todo_daemon.py --once; PYTHONPATH=external/ipfs_datasets python3 scripts/virtual_ai_os_todo_supervisor.py --once; rg -n "VAI-018|VAI-019|VAI-020|VAI-023|VAI-026" implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md data/virtual_ai_os/state
- Acceptance: The ipfs_datasets_py todo daemon/supervisor can parse the expanded board, report ready work, preserve dependency order, and provide enough state for autonomous implementation agents to continue without guessing the next task.

## VAI-027 Resolve merge retry-budget failure for VAI-019

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: VAI-015, VAI-017
- Outputs: tests/test_virtual_ai_os_end_to_end.py, tests/test_virtual_ai_os_runtime_router.py, tests/test_meta_glasses_mobile_orb_bridge.py, data/virtual_ai_os/discovery
- Validation: python3 -c 'exec("import json, pathlib\nstrategy = json.loads(pathlib.Path('"'"'/home/barberb/lift_coding/data/virtual_ai_os/state/virtual_ai_os_strategy.json'"'"').read_text(encoding='"'"'utf-8'"'"'))\nassert '"'"'VAI-019'"'"' not in strategy.get('"'"'blocked_tasks'"'"', [])")'
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-019. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-027-vai-019-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then remove VAI-019 from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.

## VAI-028 Resolve merge retry-budget failure for VAI-020

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: VAI-017
- Outputs: spec/meta_glasses_mobile_orb_bridge_interface.json, src/handsfree/api.py, mobile/src/orb, mobile/src/screens/GlassesDiagnosticsScreen.js, data/virtual_ai_os/discovery
- Validation: python3 -c 'exec("import json, pathlib\nstrategy = json.loads(pathlib.Path('"'"'/home/barberb/lift_coding/data/virtual_ai_os/state/virtual_ai_os_strategy.json'"'"').read_text(encoding='"'"'utf-8'"'"'))\nassert '"'"'VAI-020'"'"' not in strategy.get('"'"'blocked_tasks'"'"', [])")'
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-020. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-028-vai-020-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then remove VAI-020 from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.

## VAI-029 Resolve merge retry-budget failure for VAI-021

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: VAI-015
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery/submodule-refresh-2026-05-23.md, data/virtual_ai_os/discovery
- Validation: python3 -c 'exec("import json, pathlib\nstrategy = json.loads(pathlib.Path('"'"'/home/barberb/lift_coding/data/virtual_ai_os/state/virtual_ai_os_strategy.json'"'"').read_text(encoding='"'"'utf-8'"'"'))\nassert '"'"'VAI-021'"'"' not in strategy.get('"'"'blocked_tasks'"'"', [])")'
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-021. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-029-vai-021-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then remove VAI-021 from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.

## VAI-030 Resolve merge retry-budget failure for VAI-022

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: VAI-017
- Outputs: dev/meta-rayban-display-simulator/webapp, docs/ios-rayban-mvp1-runbook.md, docs/ios-rayban-mvp1-demo-runbook.md, data/virtual_ai_os/discovery
- Validation: python3 -c 'exec("import json, pathlib\nstrategy = json.loads(pathlib.Path('"'"'/home/barberb/lift_coding/data/virtual_ai_os/state/virtual_ai_os_strategy.json'"'"').read_text(encoding='"'"'utf-8'"'"'))\nassert '"'"'VAI-022'"'"' not in strategy.get('"'"'blocked_tasks'"'"', [])")'
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-022. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-030-vai-022-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then remove VAI-022 from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.

## VAI-031 Resolve merge retry-budget failure for VAI-026

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: VAI-015
- Outputs: data/virtual_ai_os/state, implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md, data/virtual_ai_os/discovery
- Validation: python3 -c 'exec("import json, pathlib\nstrategy = json.loads(pathlib.Path('"'"'/home/barberb/lift_coding/data/virtual_ai_os/state/virtual_ai_os_strategy.json'"'"').read_text(encoding='"'"'utf-8'"'"'))\nassert '"'"'VAI-026'"'"' not in strategy.get('"'"'blocked_tasks'"'"', [])")'
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-026. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-031-vai-026-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then remove VAI-026 from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.

## VAI-032 Resolve merge retry-budget failure for VAI-028

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: VAI-017
- Outputs: spec/meta_glasses_mobile_orb_bridge_interface.json, src/handsfree/api.py, mobile/src/orb, mobile/src/screens/GlassesDiagnosticsScreen.js, data/virtual_ai_os/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-032-vai-028-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-028. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-032-vai-028-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-028 from strategy blocked_tasks.

## VAI-033 Resolve code annotation in data/hallucinate_multimodal_control/discovery/2026-05-25-hao-058-resolution.md:10

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/virtual_ai_os/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-058-resolution.md
- Validation: test -f data/hallucinate_multimodal_control/discovery/2026-05-25-hao-058-resolution.md
- Acceptance: Codebase scan filed this finding from data/hallucinate_multimodal_control/discovery/2026-05-25-hao-058-resolution.md:10. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-033-codebase-scan-8f7801ad8bfb.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-034 Resolve code annotation in data/hallucinate_multimodal_control/discovery/2026-05-25-hao-060-objective-gap-8e0fb6e29f18.md:33

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/virtual_ai_os/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-060-objective-gap-8e0fb6e29f18.md
- Validation: test -f data/hallucinate_multimodal_control/discovery/2026-05-25-hao-060-objective-gap-8e0fb6e29f18.md
- Acceptance: Codebase scan filed this finding from data/hallucinate_multimodal_control/discovery/2026-05-25-hao-060-objective-gap-8e0fb6e29f18.md:33. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-034-codebase-scan-1bbab731502c.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-035 Resolve code annotation in data/hallucinate_multimodal_control/discovery/2026-05-25-hao-061-objective-gap-6e4124a265a4.md:14

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/virtual_ai_os/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-061-objective-gap-6e4124a265a4.md
- Validation: test -f data/hallucinate_multimodal_control/discovery/2026-05-25-hao-061-objective-gap-6e4124a265a4.md
- Acceptance: Codebase scan filed this finding from data/hallucinate_multimodal_control/discovery/2026-05-25-hao-061-objective-gap-6e4124a265a4.md:14. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-035-codebase-scan-67a929f462fe.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-036 Resolve code annotation in data/hallucinate_multimodal_control/discovery/2026-05-25-hao-061-objective-gap-6e4124a265a4.md:32

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/virtual_ai_os/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-061-objective-gap-6e4124a265a4.md
- Validation: test -f data/hallucinate_multimodal_control/discovery/2026-05-25-hao-061-objective-gap-6e4124a265a4.md
- Acceptance: Codebase scan filed this finding from data/hallucinate_multimodal_control/discovery/2026-05-25-hao-061-objective-gap-6e4124a265a4.md:32. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-036-codebase-scan-feba566db9bd.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-037 Resolve code annotation in data/hallucinate_multimodal_control/discovery/2026-05-25-hao-062-objective-gap-4f0e11db46cf.md:33

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/virtual_ai_os/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-062-objective-gap-4f0e11db46cf.md
- Validation: test -f data/hallucinate_multimodal_control/discovery/2026-05-25-hao-062-objective-gap-4f0e11db46cf.md
- Acceptance: Codebase scan filed this finding from data/hallucinate_multimodal_control/discovery/2026-05-25-hao-062-objective-gap-4f0e11db46cf.md:33. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-037-codebase-scan-0ba39ace37d6.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-038 Replace placeholder runtime path in src/handsfree/ipfs_kit_adapters.py:147

- Status: todo
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/virtual_ai_os/discovery, src/handsfree/ipfs_kit_adapters.py
- Validation: python3 -m py_compile src/handsfree/ipfs_kit_adapters.py
- Acceptance: Codebase scan filed this finding from src/handsfree/ipfs_kit_adapters.py:147. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-038-codebase-scan-b7a1b442e24b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-039 Replace placeholder runtime path in src/handsfree/ipfs_kit_adapters.py:178

- Status: todo
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/virtual_ai_os/discovery, src/handsfree/ipfs_kit_adapters.py
- Validation: python3 -m py_compile src/handsfree/ipfs_kit_adapters.py
- Acceptance: Codebase scan filed this finding from src/handsfree/ipfs_kit_adapters.py:178. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-039-codebase-scan-5c42c881b5ec.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-040 Replace placeholder runtime path in src/handsfree/ipfs_kit_adapters.py:186

- Status: todo
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/virtual_ai_os/discovery, src/handsfree/ipfs_kit_adapters.py
- Validation: python3 -m py_compile src/handsfree/ipfs_kit_adapters.py
- Acceptance: Codebase scan filed this finding from src/handsfree/ipfs_kit_adapters.py:186. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-040-codebase-scan-5908a1fbe802.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-041 Review swallowed exception path in src/handsfree/ipfs_kit_adapters.py:194

- Status: todo
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/virtual_ai_os/discovery, src/handsfree/ipfs_kit_adapters.py
- Validation: python3 -m py_compile src/handsfree/ipfs_kit_adapters.py
- Acceptance: Codebase scan filed this finding from src/handsfree/ipfs_kit_adapters.py:194. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-041-codebase-scan-fa5c9b97278c.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-042 Replace placeholder runtime path in src/handsfree/ocr/stub_provider.py:38

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/virtual_ai_os/discovery, src/handsfree/ocr/stub_provider.py
- Validation: python3 -m py_compile src/handsfree/ocr/stub_provider.py
- Acceptance: Codebase scan filed this finding from src/handsfree/ocr/stub_provider.py:38. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-042-codebase-scan-914627da8285.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-043 Review swallowed exception path in src/handsfree/redis_client.py:77

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/virtual_ai_os/discovery, src/handsfree/redis_client.py
- Validation: python3 -m py_compile src/handsfree/redis_client.py
- Acceptance: Codebase scan filed this finding from src/handsfree/redis_client.py:77. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-043-codebase-scan-7a1ac1883655.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-044 Review swallowed exception path in src/handsfree/sessions.py:229

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/virtual_ai_os/discovery, src/handsfree/sessions.py
- Validation: python3 -m py_compile src/handsfree/sessions.py
- Acceptance: Codebase scan filed this finding from src/handsfree/sessions.py:229. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-044-codebase-scan-b1039b93eb48.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-045 Replace placeholder runtime path in src/handsfree/stt/stub_provider.py:42

- Status: todo
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/virtual_ai_os/discovery, src/handsfree/stt/stub_provider.py
- Validation: python3 -m py_compile src/handsfree/stt/stub_provider.py
- Acceptance: Codebase scan filed this finding from src/handsfree/stt/stub_provider.py:42. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-045-codebase-scan-b40c594b84b1.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-046 Review swallowed exception path in src/handsfree/transport/libp2p_bluetooth.py:1244

- Status: todo
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/virtual_ai_os/discovery, src/handsfree/transport/libp2p_bluetooth.py
- Validation: python3 -m py_compile src/handsfree/transport/libp2p_bluetooth.py
- Acceptance: Codebase scan filed this finding from src/handsfree/transport/libp2p_bluetooth.py:1244. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-046-codebase-scan-74ff113b87c6.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-047 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:13

- Status: todo
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/virtual_ai_os/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:13. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-047-codebase-scan-cfe0d4fe2a26.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-048 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:267

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/virtual_ai_os/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:267. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-048-codebase-scan-733817068892.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-049 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:355

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/virtual_ai_os/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:355. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-049-codebase-scan-bfdf8c8d6101.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-050 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:375

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/virtual_ai_os/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:375. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-050-codebase-scan-cd77c93b537e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-051 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:528

- Status: completed
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/virtual_ai_os/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:528. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-051-codebase-scan-a7e3a5ee0b9d.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-052 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:532

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/virtual_ai_os/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:532. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-052-codebase-scan-c28f9d1beee1.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-053 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:604

- Status: todo
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/virtual_ai_os/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:604. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-053-codebase-scan-ed0eacf2c1e0.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-054 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:609

- Status: todo
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/virtual_ai_os/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:609. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-054-codebase-scan-56be23fb68eb.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-055 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:614

- Status: todo
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/virtual_ai_os/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:614. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-055-codebase-scan-5a5d7575aa1d.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-056 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:620

- Status: todo
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/virtual_ai_os/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:620. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-056-codebase-scan-0857aa9175ad.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## VAI-057 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:621

- Status: todo
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/virtual_ai_os/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:621. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-057-codebase-scan-a5472eeb1373.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.
