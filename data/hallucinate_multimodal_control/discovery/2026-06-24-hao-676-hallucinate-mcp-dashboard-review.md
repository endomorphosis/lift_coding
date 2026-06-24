# HAO-676 Hallucinate MCP Dashboard Review

HAO-676 reviews the Hallucinate App menu and dashboard surfaces that are meant
to exercise the `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py`
MCP servers from one operator-facing launch path.

## Review Fixture

```json
{
  "task_id": "HAO-676",
  "goal_id": "VAIOS-G723",
  "artifact_id": "hallucinate_mcp_dashboard_menu_review",
  "reviewed_at": "2026-06-24T16:30:00Z",
  "requires_physical_devices": false,
  "source_files": [
    "hallucinate_app/hallucinate_app/node/menu_config.js",
    "hallucinate_app/hallucinate_app/node/menu_generator.js",
    "hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js",
    "hallucinate_app/hallucinate_app/node/views/ipfs_kit_dashboard.html",
    "hallucinate_app/hallucinate_app/node/views/ipfs_datasets_dashboard.html",
    "hallucinate_app/hallucinate_app/node/views/ipfs_accelerate_dashboard.html",
    "hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts"
  ],
  "menu_dashboard_inventory": [
    {
      "server_package": "ipfs_kit_py",
      "daemon_id": "ipfs-kit",
      "menu_label": "IPFS Kit MCP",
      "dashboard_path": "views/ipfs_kit_dashboard.html",
      "menu_web_dashboard_url": "http://127.0.0.1:8004/dashboard",
      "launch_plan_endpoint": "http://127.0.0.1:8004",
      "health_path": "/api/mcp/status",
      "rpc_path": "/mcp/tools/call",
      "launch_order": 10
    },
    {
      "server_package": "ipfs_datasets_py",
      "daemon_id": "ipfs-datasets",
      "menu_label": "IPFS Datasets MCP",
      "dashboard_path": "views/ipfs_datasets_dashboard.html",
      "menu_web_dashboard_url": "http://127.0.0.1:8899/mcp",
      "launch_plan_endpoint": "http://127.0.0.1:3002",
      "health_path": "/health/ready",
      "rpc_path": "/datasets/load",
      "native_dashboard_catalog": "/api/hallucinate/dashboard-catalog",
      "launch_order": 20
    },
    {
      "server_package": "ipfs_accelerate_py",
      "daemon_id": "ipfs-accelerate",
      "menu_label": "IPFS Accelerate MCP",
      "dashboard_path": "views/ipfs_accelerate_dashboard.html",
      "menu_web_dashboard_url": "http://127.0.0.1:3003/dashboard",
      "launch_plan_endpoint": "http://127.0.0.1:3003",
      "health_path": "/api/mcp/status",
      "rpc_path": "/mcp",
      "mcp_plus_plus_profiles": [
        "mcp++/profile-a-idl",
        "mcp++/profile-c-ucan",
        "mcp++/profile-e-mcp-p2p"
      ],
      "launch_order": 30
    }
  ],
  "findings": [
    {
      "id": "HAO-676-F1",
      "severity": "fixed",
      "summary": "The IPFS MCP dashboard submenu included the SwissKnife entry even though SwissKnife has no dashboardPath and is a virtual desktop/tool surface, not one of the three Python MCP dashboards.",
      "evidence": [
        "menu_config.js mcpServers",
        "menu_config.js dashboards.mcpServers"
      ],
      "follow_up_task": "HAO-677"
    },
    {
      "id": "HAO-676-F2",
      "severity": "fixed",
      "summary": "The menu generator called openSwissKnifeApp for app-specific SwissKnife entries without defining the helper.",
      "evidence": [
        "menu_generator.js handleAction openSwissKnifeApp",
        "test_programmatic_menu.js SwissKnife app menu action coverage"
      ],
      "follow_up_task": "HAO-677"
    },
    {
      "id": "HAO-676-F3",
      "severity": "launch-gap",
      "summary": "There is no single dashboard capability catalog that reconciles menu_config, getLaunchPlan, native dashboard URLs, health checks, tools/list, tools/call, and MCP++ telemetry.",
      "evidence": [
        "mcp_daemon_manager.js getLaunchPlan",
        "ipfs_*_dashboard.html per-dashboard scripts",
        "mcp-feature-exposure.spec.ts"
      ],
      "follow_up_task": "HAO-677"
    },
    {
      "id": "HAO-676-F4",
      "severity": "launch-gap",
      "summary": "Datasets and Accelerate dashboards expose useful status panels, but all three dashboards still need one normalized tool invocation receipt path before they can be treated as an interoperability test console.",
      "evidence": [
        "ipfs_datasets_dashboard.html",
        "ipfs_accelerate_dashboard.html",
        "ipfs_kit_dashboard.html"
      ],
      "follow_up_task": "HAO-678"
    },
    {
      "id": "HAO-676-F5",
      "severity": "launch-gap",
      "summary": "Existing HAO-674 launch evidence still needs reconciliation against the current IPFS Kit launch-plan endpoint on port 8004.",
      "evidence": [
        "data/hallucinate_multimodal_control/discovery/2026-06-24-hao-674-mcp-launch-contract-integration.md",
        "mcp_daemon_manager.js daemonConfigs"
      ],
      "follow_up_task": "HAO-682"
    }
  ],
  "required_interoperability_tests": [
    "Open each IPFS MCP dashboard from the Dashboards menu.",
    "Open each live MCP dashboard URL from the MCP Servers menu.",
    "Read one shared capability catalog for ipfs_kit_py, ipfs_datasets_py, and ipfs_accelerate_py.",
    "Exercise tools/list and one safe tools/call-style probe per backend through the control_surface mediation path.",
    "Assert MCP++ compatibility telemetry and launch receipts are visible to Hallucinate App and Swissknife."
  ]
}
```

## Launch Interpretation

Hallucinate App already has the core menu/dashboards and Playwright coverage,
but the launch-critical gap is now narrower: the app needs one shared MCP
dashboard capability catalog, one mediated tool-call receipt path, and one
Playwright interoperability matrix that proves all three Python MCP backends can
be exercised from the same operator surface before Swissknife consumes the
backend features.
