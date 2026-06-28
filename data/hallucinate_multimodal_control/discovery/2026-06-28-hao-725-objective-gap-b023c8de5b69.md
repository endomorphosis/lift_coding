# HAO-725 Objective Goal Gap

Date: 2026-06-28
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

- Hallucinate App daemon health: hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js (path), hallucinate_app/test/e2e/daemon-launch-health.spec.ts (path)
- daemon launcher: hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js (path)
- MCP server: ipfs_kit_py, ipfs_datasets_py, ipfs_accelerate_py
- MCP dashboard: dashboard capability catalog, daemon health, tools/list, tools/call
- Swissknife applications: swissknife/test/e2e/meta-glasses-virtual-os.spec.ts (path)
- launch Playwright validation gate: hallucinate_app/test/e2e/daemon-launch-health.spec.ts (path), hallucinate_app/test/e2e/fixtures/hao-725-daemon-launch-health-gate.json (path)

## Suggested Handling

Bind HAO-725 to the daemon launch health Playwright gate, keep VAIOS-G724 and VAIOS-G728 packet evidence aligned, and preserve supervisor-generated follow-up work for any daemon health, dashboard catalog, Swissknife handoff, or launch Playwright validation gate failure.
