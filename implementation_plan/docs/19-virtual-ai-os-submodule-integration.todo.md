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
- Priority: P2
- Track: ops
- Depends on: none
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md, scripts/virtual_ai_os_todo_daemon.py, scripts/virtual_ai_os_todo_supervisor.py, scripts/virtual_ai_os_llm_router.py, tests/test_virtual_ai_os_todo_queue.py
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py
- Acceptance: The virtual-AI-OS backlog is daemon-parseable, exposes repo-local daemon, supervisor, and LLM-router wrappers, and can run in isolated implementation worktrees without writing supervisor state to the parent checkout.

## VAI-001 Record reviewed source topology and pin guardrails

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on: none
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery/source-topology-vai-001-2026-06-12.md
- Validation: git submodule status; rg -n "VAI-001|Pin guardrails|source-topology-vai-001" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery/source-topology-vai-001-2026-06-12.md
- Acceptance: Record the reviewed root submodule topology, current root gitlinks, case-sensitive MCP++ source guardrail, and bootstrap constraints without advancing submodule pins or rewriting root `.gitmodules`.

## VAI-002 Align root git submodule wiring with canonical upstreams

- Status: todo
- Completion: manual
- Priority: P2
- Track: ops
- Depends on: VAI-001
- Outputs: .gitmodules, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery
- Validation: git submodule status; rg -n "VAI-002|canonical upstream|submodule wiring" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
- Acceptance: Review root gitlinks against the canonical upstream map, record any mismatches with evidence, and make only intentional submodule URL or branch changes needed for the virtual AI OS integration path.

## VAI-003 Define the cross-repo capability registry

- Status: completed
- Completion: reconciled 2026-06-23: current main contains the cross-repo capability registry implementation and `PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_capability_registry.py` passes; stale branch `implementation/vai-003-attempt-1-1781233228` was not merged because it is based on an older tree and would reintroduce obsolete deletions.
- Priority: P0
- Track: integration
- Depends on: VAI-001
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, tests/test_virtual_ai_os_capability_registry.py, data/virtual_ai_os/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_capability_registry.py
- Acceptance: Define a daemon-parseable capability registry that maps SwissKnife, Hallucinate App, ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit, mobile, and Meta glasses surfaces to ownership, transport, health probe, placement constraints, and expected proof artifacts.

## VAI-004 Add the virtual runtime placement layer

- Status: completed
- Completion: reconciled 2026-06-23: current main contains `src/handsfree/ai/runtime_placement.py`, runtime-router integration, and passing placement/router tests; stale branch `implementation/vai-004-attempt-1-1781233842` was not merged because it is based on an older tree and would reintroduce obsolete deletions.
- Priority: P0
- Track: runtime
- Depends on: VAI-003
- Outputs: src/handsfree/runtime_placement.py, tests/test_virtual_ai_os_runtime_placement.py, data/virtual_ai_os/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_runtime_placement.py
- Acceptance: Add a placement policy that can decide local phone, desktop offload, browser worker, and remote peer execution from capability, latency, power, trust, and resource hints, with deterministic fallback behavior when probes fail.

## VAI-005 Integrate ipfs_datasets_py todo-daemon state into HandsFree task orchestration

- Status: completed
- Completion: reconciled 2026-06-23: current main exposes todo-daemon state through HandsFree task orchestration tests, and the preserved branch `implementation/vai-005-attempt-1-1781234570` only changed this task status.
- Priority: P1
- Track: integration
- Depends on: VAI-003
- Outputs: scripts/virtual_ai_os_todo_supervisor.py, tests/test_virtual_ai_os_todo_queue.py, data/virtual_ai_os/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py
- Acceptance: Surface ipfs_datasets_py daemon state as a first-class orchestration input so task selection can account for dataset availability, worker health, and blocked cross-repo dependencies without spawning duplicate work.

## VAI-006 Bind Swissknife into the virtual UI and ORB plane

- Status: completed
- Completion: manual
- Priority: P0
- Track: ui
- Depends on: VAI-003, VAI-004
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, tests/test_virtual_ai_os_swissknife_integration.py, data/virtual_ai_os/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_swissknife_integration.py
- Acceptance: Specify and test the SwissKnife desktop/mobile UI contract for opening tools, forwarding ORB commands, presenting remote session state, and handing capability calls to local or offloaded runtimes.

## VAI-007 Promote Hallucinate App into the operator-console plane

- Status: completed
- Completion: manual
- Priority: P0
- Track: integration
- Depends on: VAI-003, VAI-004
- Outputs: hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.todo.md, tests/test_hallucinate_multimodal_control_todo_queue.py, data/virtual_ai_os/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Treat Hallucinate App as the multimodal operator console for the virtual desktop, with explicit IDL coverage for command routing, stream control, proof capture, and error recovery between the UI and runtime planes.

## VAI-008 Route Meta glasses audio and display as remote terminal endpoints

- Status: completed
- Completion: manual
- Priority: P0
- Track: device
- Depends on: VAI-003, VAI-004, VAI-006, VAI-007
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, tests/test_meta_glasses_display_todo_queue.py, data/virtual_ai_os/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py
- Acceptance: Define and validate the Meta glasses path as a constrained terminal for mobile-hosted sessions, including audio command input, visual status output, pairing state, disconnection handling, and desktop-offload visibility.

## VAI-009 Add environment, pin, and bootstrap contracts for component repos

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: VAI-002, VAI-003
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, scripts/run_vai_mgw_hao_supervisors.py, data/virtual_ai_os/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py
- Acceptance: Document and test the repo bootstrap contract for every participating submodule, including auth assumptions, environment variables, detached worktree policy, merge cleanup defaults, and when a submodule pin may advance.

## VAI-010 Build a hardware-free end-to-end integration harness

- Status: completed
- Completion: manual
- Priority: P0
- Track: quality
- Depends on: VAI-003, VAI-004, VAI-006, VAI-007, VAI-008
- Outputs: tests/test_virtual_ai_os_end_to_end_harness.py, data/virtual_ai_os/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_end_to_end_harness.py
- Acceptance: Add a hardware-free path that simulates phone, desktop peer, SwissKnife UI, Hallucinate App command plane, and Meta glasses terminal enough to prove command dispatch, compute offload, response streaming, and recovery behavior.

## VAI-011 Add observability, policy, and rollback coverage

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: VAI-004, VAI-010
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, tests/test_virtual_ai_os_observability.py, data/virtual_ai_os/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_observability.py
- Acceptance: Capture policy decisions, placement changes, remote execution receipts, validation failures, and rollback events in stable artifacts that supervisors can use to retry or reconcile work without manual archaeology.

## VAI-012 Validate physical-device and desktop operator readiness

- Status: todo
- Completion: manual
- Priority: P1
- Track: device
- Depends on: VAI-008, VAI-010, VAI-011
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery
- Validation: rg -n "VAI-012|physical-device|desktop operator|readiness" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
- Acceptance: Produce a readiness checklist and evidence plan for an actual phone, desktop offload host, and Meta glasses session, including what remains simulator-only and what must be manually verified on devices.

## VAI-013 Resolve the canonical mcp_plus_plus upstream source

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on: VAI-001
- Outputs: .gitmodules, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery
- Validation: git submodule status Mcp-Plus-Plus; rg -n "Mcp-Plus-Plus|repository not found|distributed protocol surface" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
- Acceptance: Resolve the canonical source for the standalone MCP++ spec/docs gitlink, record the case-sensitive upstream or repository not found evidence, and keep runtime MCP++ behavior described as a distributed protocol surface unless a distinct implementation is reviewed.

## VAI-014 Investigate implementation unknowns and expand the backlog

- Status: todo
- Completion: manual
- Priority: P2
- Track: ops
- Depends on: VAI-003, VAI-004, VAI-005, VAI-006, VAI-007, VAI-008, VAI-009, VAI-010, VAI-011, VAI-012, VAI-013
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py; rg -n "VAI-014|unknowns|Discovery|discovered" implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
- Acceptance: After the initial backlog completes, investigate the cross-submodule control-plane, UI-plane, device-plane, and daemon-integration code paths for implementation unknowns. Append new daemon-parseable VAI tasks for discovered gaps, or write a dated no-new-unknowns discovery report with evidence and commands run.

## VAI-015 Refresh reviewed submodule pins and automation guardrails

- Status: todo
- Completion: manual
- Priority: P2
- Track: ops
- Depends on: VAI-002, VAI-009
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery
- Validation: git submodule status; rg -n "VAI-015|submodule pins|automation guardrails" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
- Acceptance: Reconcile the root submodule pin policy with current integration evidence and record any required pin movement as explicit, reviewed work rather than incidental daemon churn.

## VAI-016 Build the Meta Ray-Ban browser simulator shell

- Status: todo
- Completion: manual
- Priority: P1
- Track: device
- Depends on: VAI-008
- Outputs: tests/test_meta_glasses_display_todo_queue.py, data/virtual_ai_os/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py
- Acceptance: Extend the browser simulator path so the glasses display and audio surfaces can be driven by the same command/session model expected from the mobile-hosted virtual desktop.

## VAI-017 Connect simulator artifacts to mobile ORB and Web App readiness flows

- Status: todo
- Completion: manual
- Priority: P1
- Track: mobile
- Depends on: VAI-016
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery
- Validation: rg -n "VAI-017|mobile ORB|Web App readiness|simulator artifacts" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
- Acceptance: Feed simulator proofs into the mobile ORB and web app readiness checks so a glasses-terminal session can be validated before physical hardware is attached.

## VAI-018 Validate DAT MockDeviceKit parity for native mobile simulation

- Status: todo
- Completion: manual
- Priority: P1
- Track: mobile
- Depends on: VAI-017
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery
- Validation: rg -n "VAI-018|MockDeviceKit|native mobile simulation|DAT" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
- Acceptance: Compare native mobile simulator behavior with DAT MockDeviceKit assumptions and record gaps that would affect command capture, display updates, networking, or device-pairing state.

## VAI-019 Add cross-submodule virtual AI OS integration tests

- Status: todo
- Completion: manual
- Priority: P0
- Track: quality
- Depends on: VAI-003, VAI-004, VAI-006, VAI-007, VAI-008, VAI-010
- Outputs: tests/test_virtual_ai_os_end_to_end_harness.py, tests/test_virtual_ai_os_todo_queue.py, data/virtual_ai_os/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_meta_glasses_display_todo_queue.py
- Acceptance: Add integration coverage that links at least two real submodules per scenario and proves the virtual desktop can route commands, select execution placement, and collect validation artifacts across repo boundaries.

## VAI-020 Harden mobile ORB edge diagnostics and policy receipts

- Status: todo
- Completion: manual
- Priority: P1
- Track: mobile
- Depends on: VAI-004, VAI-011, VAI-017
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery
- Validation: rg -n "VAI-020|ORB edge diagnostics|policy receipts" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
- Acceptance: Record mobile ORB diagnostics and policy receipts for command routing, offload selection, permission denial, and recovery so the supervisor can distinguish implementation failure from unavailable device conditions.

## VAI-021 Resolve nested submodule hygiene for ipfs_kit recursive bootstrap

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: VAI-002, VAI-009
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery
- Validation: git submodule status --recursive; rg -n "VAI-021|nested submodule|ipfs_kit|recursive bootstrap" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
- Acceptance: Document or fix nested submodule bootstrap issues that block ipfs_kit from participating in the virtual desktop network path, with no unrelated gitlink churn.

## VAI-022 Package the browser Web App for HTTPS glasses loading

- Status: todo
- Completion: manual
- Priority: P1
- Track: ui
- Depends on: VAI-008, VAI-016
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery
- Validation: rg -n "VAI-022|HTTPS glasses loading|browser Web App" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
- Acceptance: Define the browser packaging and HTTPS loading path required for glasses-accessible UI surfaces, including local development, phone-hosted, and desktop-hosted modes.

## VAI-023 Prepare iPhone native DAT handoff and physical validation evidence

- Status: todo
- Completion: manual
- Priority: P1
- Track: mobile
- Depends on: VAI-018, VAI-020
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery
- Validation: rg -n "VAI-023|iPhone native DAT handoff|physical validation" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
- Acceptance: Prepare the iPhone handoff evidence plan and runtime contract for DAT-backed mobile sessions that can control local UI, offload compute, and expose status to Meta glasses.

## VAI-024 Add Hallucinate App and SwissKnife desktop operator E2E coverage

- Status: todo
- Completion: manual
- Priority: P0
- Track: quality
- Depends on: VAI-006, VAI-007, VAI-010
- Outputs: tests/test_virtual_ai_os_end_to_end_harness.py, data/virtual_ai_os/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_end_to_end_harness.py
- Acceptance: Prove a desktop operator path where SwissKnife presents a session, Hallucinate App routes multimodal controls, and the runtime placement layer can execute locally or hand work to a peer.

## VAI-025 Re-check canonical mcp_plus_plus source and standalone pin decision

- Status: blocked
- Completion: manual
- Blocked reason: Deferred after VAI-013 resolved the current mcp_plus_plus source evidence; repeat source-pin rechecks are not launch-critical for the virtual desktop/mobile/glasses integration run.
- Priority: P2
- Track: ops
- Depends on: VAI-013
- Outputs: .gitmodules, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery
- Validation: git submodule status Mcp-Plus-Plus; rg -n "VAI-025|mcp_plus_plus|standalone pin" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
- Acceptance: Re-check whether mcp_plus_plus is a standalone source repo or only a protocol/spec surface and keep the root pin decision consistent with the recorded upstream evidence.

## VAI-026 Supervised autonomous implementation cadence

- Status: blocked
- Completion: manual
- Blocked reason: Deferred for current virtual AI desktop/mobile/glasses integration run; historical scan or reconciliation task is not launch-critical.
- Priority: P1
- Track: ops
- Depends on: none
- Outputs: tests/test_virtual_ai_os_todo_queue.py
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py
- Acceptance: Keep the autonomous cadence resumable by proving run the daemon before the supervisor ordering, dependency ordering, and isolated worktree implementation behavior in the VAI queue tests.

## VAI-027 Resolve merge retry-budget failure for VAI-019

## VAI-028 Resolve merge retry-budget failure for VAI-020

## VAI-029 Resolve merge retry-budget failure for VAI-021

## VAI-030 Resolve merge retry-budget failure for VAI-022

## VAI-031 Resolve merge retry-budget failure for VAI-026

## VAI-032 Resolve merge retry-budget failure for VAI-028

## VAI-033 Resolve code annotation in data/hallucinate_multimodal_control/discovery/2026-05-25-hao-058-resolution.md:10

## VAI-034 Resolve code annotation in data/hallucinate_multimodal_control/discovery/2026-05-25-hao-060-objective-gap-8e0fb6e29f18.md:33

## VAI-035 Resolve code annotation in data/hallucinate_multimodal_control/discovery/2026-05-25-hao-061-objective-gap-6e4124a265a4.md:14

## VAI-036 Resolve code annotation in data/hallucinate_multimodal_control/discovery/2026-05-25-hao-061-objective-gap-6e4124a265a4.md:32

## VAI-037 Resolve code annotation in data/hallucinate_multimodal_control/discovery/2026-05-25-hao-062-objective-gap-4f0e11db46cf.md:33

## VAI-038 Replace placeholder runtime path in src/handsfree/ipfs_kit_adapters.py:147

## VAI-039 Replace placeholder runtime path in src/handsfree/ipfs_kit_adapters.py:178

## VAI-040 Replace placeholder runtime path in src/handsfree/ipfs_kit_adapters.py:186

## VAI-041 Review swallowed exception path in src/handsfree/ipfs_kit_adapters.py:194

## VAI-042 Replace placeholder runtime path in src/handsfree/ocr/stub_provider.py:38

## VAI-043 Review swallowed exception path in src/handsfree/redis_client.py:77

## VAI-044 Review swallowed exception path in src/handsfree/sessions.py:229

## VAI-045 Replace placeholder runtime path in src/handsfree/stt/stub_provider.py:42

## VAI-046 Review swallowed exception path in src/handsfree/transport/libp2p_bluetooth.py:1244

## VAI-047 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:13

## VAI-048 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:267

## VAI-049 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:355

## VAI-050 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:375

## VAI-051 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:528

## VAI-052 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:532

## VAI-053 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:604

## VAI-054 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:609

## VAI-055 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:614

## VAI-056 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:620

## VAI-057 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:621

## VAI-058 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:658

## VAI-059 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:789

## VAI-060 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:805

## VAI-061 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:807

## VAI-062 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:811

## VAI-063 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:922

## VAI-064 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:958

## VAI-065 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:975

## VAI-066 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1027

## VAI-067 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1059

## VAI-068 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1288

## VAI-069 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1293

## VAI-070 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1298

## VAI-071 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1319

## VAI-072 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1323

## VAI-073 Resolve code annotation in tests/test_meta_glasses_display_todo_queue.py:81

## VAI-074 Resolve code annotation in tests/test_meta_glasses_display_todo_queue.py:152

## VAI-075 Resolve code annotation in tests/test_meta_glasses_display_todo_queue.py:158

## VAI-076 Resolve code annotation in tests/test_meta_glasses_display_todo_queue.py:181

## VAI-077 Resolve code annotation in tests/test_meta_glasses_display_todo_queue.py:190

## VAI-078 Resolve code annotation in tests/test_virtual_ai_os_end_to_end.py:276

## VAI-079 Resolve code annotation in tests/test_virtual_ai_os_task_orchestration.py:69

## VAI-080 Resolve code annotation in tests/test_virtual_ai_os_task_orchestration.py:99

## VAI-081 Resolve code annotation in tests/test_virtual_ai_os_task_orchestration.py:111

## VAI-082 Resolve code annotation in tests/test_virtual_ai_os_todo_queue.py:12

## VAI-083 Resolve code annotation in tracking/PR-049-ios-glasses-player.md:20

## VAI-084 Resolve code annotation in tracking/PR-050-android-audio-route-monitor.md:18

## VAI-085 Resolve code annotation in tracking/PR-051-android-glasses-recorder-player.md:21

## VAI-086 Resolve code annotation in tracking/PR-052-glasses-js-integration-tts.md:26

## VAI-087 Resolve code annotation in tracking/PR-079-agent-runner-minimal.md:7

## VAI-088 Resolve code annotation in tracking/PR-081-privacy-mode-per-profile.md:7

## VAI-089 Resolve code annotation in tracking/PR-083-android-expo-glasses-audio-wav-playback.md:7

## VAI-090 Resolve code annotation in tracking/PR-090-agent-runner-docs-sync.md:1

## VAI-091 Resolve code annotation in tracking/PR-090-agent-runner-docs-sync.md:29

## VAI-092 Resolve code annotation in work/PR-046-expo-dev-client-native-glasses.md:14

## VAI-093 Resolve code annotation in work/PR-047-ios-audio-route-monitor.md:14

## VAI-094 Resolve code annotation in work/PR-048-ios-glasses-recorder-wav.md:14

## VAI-095 Resolve code annotation in work/PR-081-privacy-mode-per-profile.md:18

## VAI-096 Resolve code annotation in work/PR-090-agent-runner-docs-sync.md:1

## VAI-097 Resolve code annotation in work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md:180

## VAI-098 Resolve code annotation in hallucinate_app/MENU_STRUCTURE.md:11

## VAI-099 Resolve code annotation in hallucinate_app/docs/INDEX.md:24

## VAI-100 Resolve code annotation in hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md:3

## VAI-101 Resolve code annotation in hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/SUPPORT.md:1

## VAI-102 Resolve code annotation in hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/image-classification/models/webnn/efficientnet-lite4/config.json:490

## VAI-103 Resolve code annotation in hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/stable-diffusion-1.5/index.js:874

## VAI-104 Resolve code annotation in hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/generation_utils.js:52

## VAI-105 Resolve code annotation in hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/static/js/audioMotion-analyzer.js:1257

## VAI-106 Resolve code annotation in hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/whisper.js:232

## VAI-107 Review swallowed exception path in hallucinate_app/hallucinate_app/js_bridge/pyarrow_content_index_ws_server.py:183

## VAI-108 Resolve merge retry-budget failure for VAI-105

## VAI-109 Resolve code annotation in hallucinate_app/hallucinate_app/node/menu_generator.js:421

## VAI-110 Resolve code annotation in hallucinate_app/hallucinate_app/node/menu_generator.js:433

## VAI-111 Resolve code annotation in hallucinate_app/hallucinate_app/node/menu_generator.js:439

## VAI-112 Resolve code annotation in hallucinate_app/hallucinate_app/node/menu_generator.js:444

## VAI-113 Resolve code annotation in hallucinate_app/hallucinate_app/node/menu_generator.js:449

## VAI-114 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:301

## VAI-115 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:303

## VAI-116 Resolve code annotation in scripts/meta_glasses_display_todo_supervisor.py:302

## VAI-117 Resolve code annotation in scripts/meta_glasses_display_todo_supervisor.py:304

## VAI-118 Resolve code annotation in scripts/run_vai_mgw_hao_supervisors.sh:92

## VAI-119 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:301

## VAI-120 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:302

## VAI-121 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:304

## VAI-122 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:305

## VAI-123 Resolve code annotation in scripts/virtual_ai_os_todo_supervisor.py:161

## VAI-124 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:301

## VAI-125 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/advanced_thread_pool_manager.py:1171

## VAI-126 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/auth_keystore_integration.py:150

## VAI-127 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/auth_keystore_integration.py:376

## VAI-128 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/duckdb_ipld_kit.py:704

## VAI-129 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/duckdb_ipld_kit.py:188

## VAI-130 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/duckdb_ipld_kit.py:810

## VAI-131 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1102

## VAI-132 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1103

## VAI-133 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/github_issue_reporter.py:369

## VAI-134 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1110

## VAI-135 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1111

## VAI-136 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1118

## VAI-137 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_accelerate_server_mp.py:175

## VAI-138 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_accelerate_server_mp.py:198

## VAI-139 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1111

## VAI-140 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1112

## VAI-141 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1119

## VAI-142 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_embeddings_py/ipfs_embeddings_py.py:611

## VAI-143 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_embeddings_py/ipfs_faiss_py.py:589

## VAI-144 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1114

## VAI-145 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1115

## VAI-146 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1118

## VAI-147 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1121

## VAI-148 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_kit.py:336

## VAI-149 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_kit_server.py:329

## VAI-150 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py:283

## VAI-151 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py:338

## VAI-152 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py:454

## VAI-153 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/js_bridge/pyarrow_content_index_bridge.py:752

## VAI-154 Resolve implementation retry-budget failure for VAI-152

## VAI-155 Resolve implementation retry-budget failure for VAI-154

## VAI-156 Resolve implementation retry-budget failure for VAI-155

## VAI-157 Resolve implementation retry-budget failure for VAI-156

## VAI-158 Resolve implementation retry-budget failure for VAI-157

## VAI-159 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:304

## VAI-160 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:305

## VAI-161 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:307

## VAI-162 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:308

## VAI-163 Resolve code annotation in scripts/virtual_ai_os_todo_supervisor.py:17

## VAI-164 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_daemon.py:47

## VAI-165 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:304

## VAI-166 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:307

## VAI-167 Resolve code annotation in scripts/virtual_ai_os_todo_supervisor.py:19

## VAI-168 Resolve code annotation in scripts/virtual_ai_os_todo_supervisor.py:44

## VAI-169 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:304

## VAI-170 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:307

## VAI-171 Resolve code annotation in scripts/virtual_ai_os_todo_supervisor.py:19

## VAI-172 Resolve code annotation in scripts/virtual_ai_os_todo_supervisor.py:20

## VAI-173 Resolve code annotation in scripts/virtual_ai_os_todo_supervisor.py:169

## VAI-174 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:304

## VAI-175 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:307

## VAI-176 Resolve code annotation in scripts/virtual_ai_os_todo_supervisor.py:19

## VAI-177 Resolve code annotation in scripts/virtual_ai_os_todo_supervisor.py:168

## VAI-178 Resolve code annotation in scripts/virtual_ai_os_todo_supervisor.py:169

## VAI-179 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/pyarrow_content_index.py:846

## VAI-180 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/pyarrow_content_index.py:925

## VAI-181 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/pyarrow_content_index.py:2570

## VAI-182 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/secure_duckdb_ipld_manager.py:1249

## VAI-183 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py:269

## VAI-184 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py:376

## VAI-185 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py:378

## VAI-186 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py:380

## VAI-187 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py:389

## VAI-188 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py:390

## VAI-189 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py:462

## VAI-190 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_thread_pool_monitor.py:324

## VAI-191 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/thread_pool_integration.py:830

## VAI-192 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/thread_pool_manager.py:1029

## VAI-193 Review swallowed exception path in hallucinate_app/hallucinate_app/python/ipfs_accelerate_py.py:624

## VAI-194 Resolve merge retry-budget failure for VAI-191

## VAI-195 Review swallowed exception path in hallucinate_app/hallucinate_app/python/ipfs_accelerate_py.py:1001

## VAI-196 Review swallowed exception path in hallucinate_app/hallucinate_app/python/ucan_auth_py/ucan_auth_py/core/token.py:223

## VAI-197 Review swallowed exception path in hallucinate_app/python/hallucinate_app/control_surface_policy.py:1022

## VAI-198 Review swallowed exception path in hallucinate_app/python/hallucinate_app/control_surface_policy.py:1027

## VAI-199 Review swallowed exception path in hallucinate_app/python/hallucinate_app/control_surface_policy.py:1032

## VAI-200 Resolve dirty main checkout blocking 1 worktree merges

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Fingerprint: 223483ce405ef808ad3bb9f341d9213afb9088fe
- Dedupe key: reconciliation_guardrail:main_checkout_dirty
- Depends on:
- Outputs: data/virtual_ai_os/discovery, implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-07-vai-200-reconciliation-5705491cdbce.md
- Acceptance: Reconciliation guardrail filed this because 1 branch or worktree cleanup candidates are blocked by main_checkout_dirty. Use evidence and the machine-readable reconciliation plan in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-07-vai-200-reconciliation-5705491cdbce.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.

## VAI-201 Resolve 1 dirty backlogged worktrees blocked by content_not_in_target

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Fingerprint: 04250c7724a2c2b2ba45af5432dcf9d6fceef761
- Dedupe key: reconciliation_guardrail:dirty_backlogged_worktree:content_not_in_target
- Depends on:
- Outputs: data/virtual_ai_os/discovery, implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-07-vai-201-reconciliation-9422bd776827.md
- Acceptance: Reconciliation guardrail filed this because 1 branch or worktree cleanup candidates are blocked by content_not_in_target. Use evidence and the machine-readable reconciliation plan in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-07-vai-201-reconciliation-9422bd776827.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.

## VAI-202 Resolve 1 dirty backlogged worktrees blocked by unsupported_status

## VAI-203 Resolve 231 preflight-conflicting backlogged worktree merges

## VAI-204 Resolve dependency guardrail for VAI-200

## VAI-205 Review preserved VAI-202 dirty submodule source patches

## VAI-206 Resolve dependency guardrail for VAI-204

## VAI-207 Resolve code annotation in hallucinate_app/python/hallucinate_app/ipfs_kit_bridge.py:793

## VAI-208 Review swallowed exception path in external/ipfs_kit/.github/scripts/generate_workflow_list.py:36

## VAI-209 Review swallowed exception path in external/ipfs_kit/.github/workflows/auto-doc-maintenance.yml:120

## VAI-210 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/add_pins_monkey_patch.py:39

## VAI-211 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/advanced_filecoin.py:984

## VAI-212 Resolve implementation retry-budget failure for VAI-211

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: data/virtual_ai_os/discovery, external/ipfs_kit/archive/applied_patches/advanced_filecoin.py
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-07-vai-212-vai-211-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in VAI-211. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-07-vai-212-vai-211-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release VAI-211 from strategy blocked_tasks.

## VAI-213 Resolve validation retry-budget failure for VAI-209

## VAI-214 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/advanced_filecoin.py:1245

## VAI-215 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/direct_mcp_server.py:159

## VAI-216 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/direct_mcp_server.py:217

## VAI-217 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/enhanced_mcp_server_with_ai_ml.py:44

## VAI-218 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/enhanced_storacha_storage.py:430

## VAI-219 Resolve implementation retry-budget failure for VAI-218

## VAI-220 Resolve implementation retry-budget failure for VAI-219

## VAI-221 Resolve implementation retry-budget failure for VAI-220

## VAI-222 Resolve implementation retry-budget failure for VAI-221

## VAI-223 Resolve implementation retry-budget failure for VAI-222

## VAI-224 Resolve implementation retry-budget failure for VAI-223

## VAI-225 Resolve implementation retry-budget failure for VAI-224

## VAI-226 Resolve implementation retry-budget failure for VAI-225

## VAI-227 Resolve implementation retry-budget failure for VAI-226

## VAI-228 Resolve implementation retry-budget failure for VAI-227

## VAI-229 Resolve implementation retry-budget failure for VAI-228

## VAI-230 Resolve implementation retry-budget failure for VAI-229

## VAI-231 Resolve implementation retry-budget failure for VAI-230

## VAI-232 Resolve implementation retry-budget failure for VAI-231

## VAI-233 Resolve implementation retry-budget failure for VAI-232

## VAI-234 Resolve implementation retry-budget failure for VAI-233

## VAI-235 Resolve implementation retry-budget failure for VAI-234

## VAI-236 Resolve implementation retry-budget failure for VAI-235

## VAI-237 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/direct_mcp_server.py:255

## VAI-238 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/enhanced_storacha_storage.py:919

## VAI-239 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/enhanced_storacha_storage.py:981

## VAI-240 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/enhanced_storacha_storage.py:1037

## VAI-241 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_all_code_issues.sh:236

## VAI-242 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_all_remaining_issues.sh:204

## VAI-243 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_all_remaining_issues.sh:228

## VAI-244 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_all_storacha.py:55

## VAI-245 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_all_storacha.py:292

## VAI-246 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_code_issues.sh:229

## VAI-247 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_concise.sh:210

## VAI-248 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_concise.sh:234

## VAI-249 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_huggingface_integration.py:58

## VAI-250 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_huggingface_integration.py:318

## VAI-251 Replace placeholder runtime path in external/ipfs_kit/archive/applied_patches/fix_ipfs_model.py:210

## VAI-252 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_lassie_integration.py:59

## VAI-253 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_lassie_integration.py:273

## VAI-254 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_mcp_form_data.py:100

## VAI-255 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_mcp_server.py:163

## VAI-256 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_mcp_server.py:219

## VAI-257 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_s3_backend.py:236

## VAI-258 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_s3_backend.py:698

## VAI-259 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_s3_backend_complete.py:232

## VAI-260 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_s3_backend_complete.py:845

## VAI-261 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_storacha_backend.py:472

## VAI-262 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_storacha_backend.py:1070

## VAI-263 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/fix_storacha_backend.py:1549

## VAI-264 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/huggingface_real_init.py:44

## VAI-265 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/ipfs_dht_operations.py:279

## VAI-266 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/ipfs_ipns_operations.py:1501

## VAI-267 Review swallowed exception path in external/ipfs_kit/archive/applied_patches/lassie_mock_server.py:59

## VAI-268 Resolve code annotation in external/ipfs_kit/archive/archive_clutter/documentation_drafts/CONTRIBUTING.md:213

## VAI-269 Resolve code annotation in external/ipfs_kit/archive/archive_clutter/documentation_drafts/CONTRIBUTING.md:214

## VAI-270 Review swallowed exception path in external/ipfs_kit/archive/archive_clutter/fix_scripts/direct_fix_resource_handlers.py:249

## VAI-271 Review swallowed exception path in external/ipfs_kit/archive/archive_clutter/fix_scripts/direct_mcp_server.py:251

## VAI-272 Review swallowed exception path in external/ipfs_kit/archive/archive_clutter/fix_scripts/direct_mcp_server.py:322

## VAI-273 Review swallowed exception path in external/ipfs_kit/archive/archive_clutter/fix_scripts/direct_mcp_server_with_tools.py:185

## VAI-274 Review swallowed exception path in external/ipfs_kit/archive/archive_clutter/fix_scripts/direct_mcp_server_with_tools.py:243

## VAI-275 Review swallowed exception path in external/ipfs_kit/archive/archive_clutter/fix_scripts/fixed_mcp_test_runner.py:587

## VAI-276 Review swallowed exception path in external/ipfs_kit/archive/archive_clutter/fix_scripts/fixed_runner.py:58

## VAI-277 Review swallowed exception path in external/ipfs_kit/archive/archive_clutter/fix_scripts/patch_direct_mcp.py:31

## VAI-278 Review swallowed exception path in external/ipfs_kit/archive/archive_clutter/temp_files/working_example.py:83

## VAI-279 Review swallowed exception path in external/ipfs_kit/archive/backup_patches/fix_storage_backends.py:288

## VAI-280 Review swallowed exception path in external/ipfs_kit/archive/cli_drafts/ipfs_kit_cli_jit_optimized.py:112

## VAI-281 Review swallowed exception path in external/ipfs_kit/archive/cli_drafts/ipfs_kit_cli_ultra_fast.py:78

## VAI-282 Review swallowed exception path in external/ipfs_kit/archive/ipfs_development/ipfs_mcp_tools.py:138

## VAI-283 Review swallowed exception path in external/ipfs_kit/archive/ipfs_development/ipfs_mcp_tools.py:514

## VAI-284 Review swallowed exception path in external/ipfs_kit/archive/legacy_servers/enhanced_mcp_server_direct_ipfs.py:232

## VAI-285 Review swallowed exception path in external/ipfs_kit/archive/legacy_servers/enhanced_mcp_server_phase2.py:1667

## VAI-286 Review swallowed exception path in external/ipfs_kit/archive/legacy_servers/vscode_mcp_server.py:304

## VAI-287 Review swallowed exception path in external/ipfs_kit/archive/mcp_development/mcp_test_suite.py:109

## VAI-288 Review swallowed exception path in external/ipfs_kit/archive/mcp_development/mcp_test_suite.py:220

## VAI-289 Review swallowed exception path in external/ipfs_kit/archive/mcp_development/mcp_test_suite.py:262

## VAI-290 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/auth/persistence.py:126

## VAI-291 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/auth/service.py:286

## VAI-292 Review swallowed exception path in external/ipfs_kit/archive/mcp_development/mcp_test_suite.py:265

## VAI-293 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/auth/service.py:289

## VAI-294 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/ipfs_controller.py:1119

## VAI-295 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/ipfs_controller_anyio.py:681

## VAI-296 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/ipfs_controller_anyio.py:1465

## VAI-297 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/peer_websocket_controller.py:394

## VAI-298 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/peer_websocket_controller.py:561

## VAI-299 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/peer_websocket_controller_anyio.py:401

## VAI-300 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/peer_websocket_controller_anyio.py:568

## VAI-301 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/storage_manager_controller.py:1051

## VAI-302 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/enhanced_filecoin.py:204

## VAI-303 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/enhanced_lassie.py:49

## VAI-304 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/lassie.py:49

## VAI-305 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/metrics.py:327

## VAI-306 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/metrics.py:422

## VAI-307 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/migration.py:120

## VAI-308 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/perf.py:276

## VAI-309 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/perf.py:791

## VAI-310 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/udm.py:553

## VAI-311 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/webrtc.py:49

## VAI-312 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/perf.py:280

## VAI-313 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/webrtc.py:74

## VAI-314 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/websocket.py:52

## VAI-315 Resolve code annotation in external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/websocket.py:123

## VAI-316 Review swallowed exception path in external/ipfs_kit/archive/mcp_final_20250414_082801/ha/service.py:761

## VAI-317 Resolve merge retry-budget failure for VAI-041

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-317-vai-041-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-041. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-317-vai-041-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-041 from strategy blocked_tasks.

## VAI-318 Resolve merge retry-budget failure for VAI-045

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-318-vai-045-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-045. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-318-vai-045-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-045 from strategy blocked_tasks.

## VAI-319 Resolve merge retry-budget failure for VAI-046

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-319-vai-046-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-046. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-319-vai-046-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-046 from strategy blocked_tasks.

## VAI-320 Resolve merge retry-budget failure for VAI-107

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-320-vai-107-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-107. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-320-vai-107-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-107 from strategy blocked_tasks.

## VAI-321 Resolve merge retry-budget failure for VAI-126

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-321-vai-126-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-126. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-321-vai-126-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-126 from strategy blocked_tasks.

## VAI-322 Resolve merge retry-budget failure for VAI-155

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-322-vai-155-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-155. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-322-vai-155-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-155 from strategy blocked_tasks.

## VAI-323 Resolve merge retry-budget failure for VAI-209

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-323-vai-209-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-209. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-323-vai-209-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-209 from strategy blocked_tasks.

## VAI-324 Resolve merge retry-budget failure for VAI-214

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-324-vai-214-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-214. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-324-vai-214-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-214 from strategy blocked_tasks.

## VAI-325 Resolve merge retry-budget failure for VAI-156

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-325-vai-156-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-156. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-325-vai-156-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-156 from strategy blocked_tasks.

## VAI-326 Resolve merge retry-budget failure for VAI-212

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-326-vai-212-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-212. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-06-12-vai-326-vai-212-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-212 from strategy blocked_tasks.

## VAI-327 Resolve merge retry-budget failure for VAI-001

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, data/virtual_ai_os/discovery/source-topology-vai-001-2026-06-12.md, data/virtual_ai_os/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-12-vai-327-vai-001-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-001. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-12-vai-327-vai-001-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-001 from strategy blocked_tasks.

## VAI-328 Resolve merge retry-budget failure for VAI-002

- Status: blocked
- Completion: manual
- Blocked reason: Deferred for current virtual AI desktop/mobile/glasses integration run; historical scan or reconciliation task is not launch-critical.
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-12-vai-328-vai-002-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-002. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-12-vai-328-vai-002-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-002 from strategy blocked_tasks.

## VAI-329 Resolve merge retry-budget failure for VAI-007

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-12-vai-329-vai-007-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-007. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-12-vai-329-vai-007-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-007 from strategy blocked_tasks.

## VAI-330 Resolve merge retry-budget failure for VAI-008

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-12-vai-330-vai-008-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-008. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-12-vai-330-vai-008-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-008 from strategy blocked_tasks.

## VAI-331 Resolve implementation retry-budget failure for VAI-052

- Status: blocked
- Completion: manual
- Blocked reason: Deferred for current virtual AI desktop/mobile/glasses integration run; historical scan or reconciliation task is not launch-critical.
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-12-vai-331-vai-052-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in VAI-052. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-12-vai-331-vai-052-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release VAI-052 from strategy blocked_tasks.

## VAI-332 Resolve implementation retry-budget failure for VAI-150

- Status: blocked
- Completion: manual
- Blocked reason: Deferred for current virtual AI desktop/mobile/glasses integration run; historical scan or reconciliation task is not launch-critical.
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-13-vai-332-vai-150-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in VAI-150. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-13-vai-332-vai-150-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release VAI-150 from strategy blocked_tasks.

## VAI-333 Resolve implementation retry-budget failure for VAI-151

- Status: blocked
- Completion: manual
- Blocked reason: Deferred for current virtual AI desktop/mobile/glasses integration run; historical scan or reconciliation task is not launch-critical.
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-13-vai-333-vai-151-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in VAI-151. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-13-vai-333-vai-151-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release VAI-151 from strategy blocked_tasks.

## VAI-334 Resolve implementation retry-budget failure for VAI-141

- Status: blocked
- Completion: manual
- Blocked reason: Deferred for current virtual AI desktop/mobile/glasses integration run; historical scan or reconciliation task is not launch-critical.
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-13-vai-334-vai-141-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in VAI-141. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-13-vai-334-vai-141-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release VAI-141 from strategy blocked_tasks.

## VAI-335 Resolve implementation retry-budget failure for VAI-142

- Status: blocked
- Completion: manual
- Blocked reason: Deferred for current virtual AI desktop/mobile/glasses integration run; historical scan or reconciliation task is not launch-critical.
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-13-vai-335-vai-142-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in VAI-142. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-13-vai-335-vai-142-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release VAI-142 from strategy blocked_tasks.

## VAI-336 Resolve merge retry-budget failure for VAI-006

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/virtual_ai_os/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-13-vai-336-vai-006-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in VAI-006. Use evidence in /home/barberb/lift_coding/data/virtual_ai_os/state/discovery/2026-06-13-vai-336-vai-006-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release VAI-006 from strategy blocked_tasks.

## VAI-337 Register Meta glasses widget actions as VAI capabilities

- Status: todo
- Completion: manual
- Priority: P1
- Track: integration
- Depends on: VAI-003, VAI-006, VAI-007, VAI-008
- Outputs: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md, tests/test_virtual_ai_os_capability_registry.py
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_capability_registry.py tests/test_meta_glasses_display_todo_queue.py
- Acceptance: Add `vai.glasses_widget.render`, `vai.glasses_widget.update`, `vai.glasses_widget.confirm`, and `vai.glasses_widget.cancel` to the shared capability registry so Swissknife ORB, HandsFree mobile, Meta glasses, and Hallucinate App use one command envelope with `command_id`, `session_id`, `descriptor_cid`, `manifest_cid`, `correlation_id`, policy and placement receipts, fallback render path, and canonical `capability_receipt_cid` for virtual desktop sessions.
