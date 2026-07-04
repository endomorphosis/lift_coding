# VAI-641 Objective Goal Gap

Date: 2026-07-04
Fingerprint: b023c8de5b69b85e7de6de9bcd13d89350974c98
Goal id: VAIOS-G728
Goal title: Hallucinate App daemon launch orchestration
Objective heap: implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
Priority: P0
Track: launch
Parent goals: VAIOS-G000
Graph depth: 1
Bundle: objective/launch/hallucinate-daemon-launch-orchestration
Parallel lane: objective/launch/hallucinate-daemon-launch-orchestration
Bundle strategy: explicit
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Goal packet role: packet_member
Goal packet goals: VAIOS-G724, VAIOS-G728
Goal packet task count: 2
Goal packet work item count: 2
Evidence methods: ast, embedding, exact, path
Embedding query: Hallucinate App daemon launch health MCP server dashboard ipfs_accelerate_py ipfs_datasets_py ipfs_kit_py Swissknife
AST query: hallucinate_app, daemon health, MCP server, MCP dashboard, ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
Conflict policy: prefer launch-critical integration evidence; use the LLM merge resolver when dashboard, daemon, or mobile control-plane edits conflict

## Goal

Hallucinate App launches and monitors the ipfs_accelerate_py, ipfs_datasets_py, and ipfs_kit_py MCP daemons, exposes their health in dashboards, and hands capability records to Swissknife.

## Missing Evidence

- launch Playwright validation gate

## Present Evidence

- Hallucinate App daemon health: dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/webapp/app.js (ast), docs/launch/phone_desktop_glasses_readiness.md (exact)
- daemon launcher: docs/launch/phone_desktop_glasses_readiness.md (exact), mobile/src/screens/SettingsScreen.js (ast), Mcp-Plus-Plus/tests-ts/coverage/prettify.js (ast)
- MCP server: docs/DOCUMENTATION_INDEX.md (exact), docs/launch/phone_desktop_glasses_readiness.md (exact), docs/planning/CODEBASE_INVENTORY.md (exact)
- MCP dashboard: docs/launch/phone_desktop_glasses_readiness.md (exact), mobile/src/screens/SettingsScreen.js (ast), scripts/hallucinate_multimodal_control_todo_supervisor.py (exact)
- ipfs_accelerate_py: CONFIGURATION.md (exact), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/CONFIGURATION.md (exact)
- ipfs_datasets_py: CONFIGURATION.md (exact), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/CONFIGURATION.md (exact)
- ipfs_kit_py: CONFIGURATION.md (exact), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/CONFIGURATION.md (exact)
- dashboard capability catalog: dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/launch/phone_desktop_glasses_readiness.md (exact), mobile/push/examples/expo_receive_handler.ts (ast)
- Swissknife applications: dev/meta-rayban-display-simulator/webapp/app.js (ast), docs/launch/phone_desktop_glasses_readiness.md (exact), implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md (exact)
- launch Playwright validation gate: dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/simulator.js (ast), docs/launch/phone_desktop_glasses_readiness.md (exact)
- data/virtual_ai_os/discovery/2026-06-26-vai-517-mcp-dashboard-launch-readiness.md: data/virtual_ai_os/discovery/2026-06-26-vai-517-mcp-dashboard-launch-readiness.md (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- hallucinate_app/test/e2e/fixtures/vai-517-mcp-dashboard-launch-readiness.json: hallucinate_app/test/e2e/fixtures/vai-517-mcp-dashboard-launch-readiness.json (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- data/virtual_ai_os/discovery/2026-06-26-vai-519-daemon-launch-health-gate.md: data/virtual_ai_os/discovery/2026-06-26-vai-519-daemon-launch-health-gate.md (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- hallucinate_app/test/e2e/fixtures/vai-519-daemon-launch-health-gate.json: hallucinate_app/test/e2e/fixtures/vai-519-daemon-launch-health-gate.json (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- data/virtual_ai_os/discovery/2026-06-27-vai-530-daemon-launch-health-gate.md: data/virtual_ai_os/discovery/2026-06-27-vai-530-daemon-launch-health-gate.md (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- hallucinate_app/test/e2e/fixtures/vai-530-daemon-launch-health-gate.json: hallucinate_app/test/e2e/fixtures/vai-530-daemon-launch-health-gate.json (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- data/virtual_ai_os/discovery/2026-06-28-vai-536-daemon-launch-health-gate.md: data/virtual_ai_os/discovery/2026-06-28-vai-536-daemon-launch-health-gate.md (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- hallucinate_app/test/e2e/fixtures/vai-536-daemon-launch-health-gate.json: hallucinate_app/test/e2e/fixtures/vai-536-daemon-launch-health-gate.json (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- data/virtual_ai_os/discovery/2026-06-28-vai-538-daemon-launch-health-gate.md: data/virtual_ai_os/discovery/2026-06-28-vai-538-daemon-launch-health-gate.md (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- hallucinate_app/test/e2e/fixtures/vai-538-daemon-launch-health-gate.json: hallucinate_app/test/e2e/fixtures/vai-538-daemon-launch-health-gate.json (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- data/virtual_ai_os/discovery/2026-06-28-vai-540-daemon-launch-health-gate.md: data/virtual_ai_os/discovery/2026-06-28-vai-540-daemon-launch-health-gate.md (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- hallucinate_app/test/e2e/fixtures/vai-540-daemon-launch-health-gate.json: hallucinate_app/test/e2e/fixtures/vai-540-daemon-launch-health-gate.json (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- data/virtual_ai_os/discovery/2026-07-02-vai-549-daemon-launch-health-gate.md: data/virtual_ai_os/discovery/2026-07-02-vai-549-daemon-launch-health-gate.md (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- hallucinate_app/test/e2e/fixtures/vai-549-daemon-launch-health-gate.json: hallucinate_app/test/e2e/fixtures/vai-549-daemon-launch-health-gate.json (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- data/virtual_ai_os/discovery/2026-07-04-vai-568-daemon-launch-health-gate.md: data/virtual_ai_os/discovery/2026-07-04-vai-568-daemon-launch-health-gate.md (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- hallucinate_app/test/e2e/fixtures/vai-568-daemon-launch-health-gate.json: hallucinate_app/test/e2e/fixtures/vai-568-daemon-launch-health-gate.json (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- data/virtual_ai_os/discovery/2026-07-04-vai-574-daemon-launch-health-gate.md: data/virtual_ai_os/discovery/2026-07-04-vai-574-daemon-launch-health-gate.md (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- hallucinate_app/test/e2e/fixtures/vai-574-daemon-launch-health-gate.json: hallucinate_app/test/e2e/fixtures/vai-574-daemon-launch-health-gate.json (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-535-daemon-launch-health-gate.md: data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-535-daemon-launch-health-gate.md (path), config/display_webapp_readiness.meta_glasses_widget.example.json (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast)
- data/meta_glasses_display_widgets/discovery/2026-06-28-mgw-551-daemon-launch-health-gate.md: data/meta_glasses_display_widgets/discovery/2026-06-28-mgw-551-daemon-launch-health-gate.md (path), config/display_webapp_readiness.meta_glasses_widget.example.json (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast)
- data/meta_glasses_display_widgets/discovery/2026-07-02-mgw-565-daemon-launch-health-gate.md: config/display_webapp_readiness.meta_glasses_widget.example.json (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/webapp/readiness.json (ast)
- data/hallucinate_multimodal_control/discovery/2026-06-27-hao-713-daemon-launch-health-gate.md: data/hallucinate_multimodal_control/discovery/2026-06-27-hao-713-daemon-launch-health-gate.md (path), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/launch/phone_desktop_glasses_readiness.md (embedding:0.58)
- data/hallucinate_multimodal_control/discovery/2026-06-28-hao-719-daemon-launch-health-gate.md: data/hallucinate_multimodal_control/discovery/2026-06-28-hao-719-daemon-launch-health-gate.md (path), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/launch/phone_desktop_glasses_readiness.md (embedding:0.60)
- data/hallucinate_multimodal_control/discovery/2026-06-28-hao-721-daemon-launch-health-gate.md: data/hallucinate_multimodal_control/discovery/2026-06-28-hao-721-daemon-launch-health-gate.md (path), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/launch/phone_desktop_glasses_readiness.md (embedding:0.60)
- data/hallucinate_multimodal_control/discovery/2026-06-28-hao-726-hao-724-merge-retry-budget.md: data/hallucinate_multimodal_control/discovery/2026-06-28-hao-726-hao-724-merge-retry-budget.md (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- hallucinate_app/test/e2e/daemon-launch-health.spec.ts: hallucinate_app/test/e2e/daemon-launch-health.spec.ts (path), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/webapp/app.js (ast)
- hallucinate_app/test/e2e/fixtures/mgw-535-daemon-launch-health-gate.json: hallucinate_app/test/e2e/fixtures/mgw-535-daemon-launch-health-gate.json (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- hallucinate_app/test/e2e/fixtures/mgw-551-daemon-launch-health-gate.json: hallucinate_app/test/e2e/fixtures/mgw-551-daemon-launch-health-gate.json (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- hallucinate_app/test/e2e/fixtures/mgw-565-daemon-launch-health-gate.json: agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast), dev/android/termux_github_dispatcher.py (ast)
- hallucinate_app/test/e2e/fixtures/hao-713-daemon-launch-health-gate.json: hallucinate_app/test/e2e/fixtures/hao-713-daemon-launch-health-gate.json (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- hallucinate_app/test/e2e/fixtures/hao-719-daemon-launch-health-gate.json: hallucinate_app/test/e2e/fixtures/hao-719-daemon-launch-health-gate.json (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- hallucinate_app/test/e2e/fixtures/hao-721-daemon-launch-health-gate.json: hallucinate_app/test/e2e/fixtures/hao-721-daemon-launch-health-gate.json (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)

## Suggested Handling

Run and repair the launch readiness validation gate until the phone, desktop, Swissknife, Hallucinate App, and Meta glasses Playwright checks pass.
