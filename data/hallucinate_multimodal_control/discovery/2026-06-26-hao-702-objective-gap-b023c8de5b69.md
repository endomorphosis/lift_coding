# HAO-702 Objective Goal Gap

Date: 2026-06-26
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
Evidence methods: ast, exact
Embedding query: Hallucinate App daemon launch health MCP server dashboard ipfs_accelerate_py ipfs_datasets_py ipfs_kit_py Swissknife
AST query: hallucinate_app, daemon health, MCP server, MCP dashboard, ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
Conflict policy: prefer launch-critical integration evidence; use the LLM merge resolver when dashboard, daemon, or mobile control-plane edits conflict

## Goal

Hallucinate App launches and monitors the ipfs_accelerate_py, ipfs_datasets_py, and ipfs_kit_py MCP daemons, exposes their health in dashboards, and hands capability records to Swissknife.

## Missing Evidence

- launch Playwright validation gate

## Present Evidence

- Hallucinate App daemon health: dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), dev/meta-rayban-display-simulator/webapp/app.js (ast), mobile/App.js (ast)
- daemon launcher: mobile/src/screens/SettingsScreen.js (ast), Mcp-Plus-Plus/tests-ts/coverage/prettify.js (ast), external/ipfs_accelerate/ipfs_accelerate_js/src/browser/resource_pool/browser_automation.ts (ast)
- MCP server: docs/DOCUMENTATION_INDEX.md (exact), docs/planning/CODEBASE_INVENTORY.md (exact), docs/planning/DOCUMENTATION_GAP_ANALYSIS.md (exact)
- MCP dashboard: docs/launch/phone_desktop_glasses_readiness.md (exact), implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md (exact), mobile/src/screens/SettingsScreen.js (ast)
- ipfs_accelerate_py: CONFIGURATION.md (exact), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/CONFIGURATION.md (exact)
- ipfs_datasets_py: CONFIGURATION.md (exact), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/CONFIGURATION.md (exact)
- ipfs_kit_py: CONFIGURATION.md (exact), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/CONFIGURATION.md (exact)
- dashboard capability catalog: dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/launch/phone_desktop_glasses_readiness.md (exact), implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md (exact)
- Swissknife applications: dev/meta-rayban-display-simulator/webapp/app.js (ast), implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md (exact), implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md (exact)

## Suggested Handling

Run and repair the launch readiness validation gate until the phone, desktop, Swissknife, Hallucinate App, and Meta glasses Playwright checks pass.
