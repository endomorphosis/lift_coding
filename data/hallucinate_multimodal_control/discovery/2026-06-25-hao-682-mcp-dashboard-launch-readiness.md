# HAO-682 MCP Dashboard Launch Readiness

Date: 2026-06-27
Task: HAO-682
Goal id: VAIOS-G723
Track: launch
Depends on: HAO-679, HAO-681

HAO-682 aggregates the Hallucinate MCP dashboard interoperability evidence for
VAIOS-G723 and VAI-503 into one launch-readiness receipt. The packet keeps the
gate open until Hallucinate App menu navigation, the dashboard catalog, daemon
health, MCP++ telemetry, dashboard `tools/list` and `tools/call` probes,
Swissknife consumption, and Playwright pass/fail receipts all share the same
traceable session and daemon lineage.

## Receipt

```json
{
  "schema": "launch_readiness_receipt_v1",
  "task_id": "HAO-682",
  "vai_task_id": "VAI-503",
  "goal_id": "VAIOS-G723",
  "lineage_id": "VAIOS-G723:mcp-dashboard-interoperability",
  "session_id": "vaios-g723-hallucinate-mcp-dashboard-session",
  "daemon_lineage_id": "vaios-g723-daemon-lineage-ipfs-kit-datasets-accelerate",
  "evidence_term": "dashboard interoperability launch-readiness receipt",
  "gate_state": "gate_open_until_playwright_passes",
  "readiness_doc": "docs/launch/phone_desktop_glasses_readiness.md",
  "hallucinate_fixture": "hallucinate_app/test/e2e/fixtures/hao-682-mcp-dashboard-launch-readiness.json",
  "swissknife_fixture": "swissknife/test/e2e/fixtures/hao-682-mcp-dashboard-launch-readiness.json",
  "depends_on_receipts": [
    "hallucinate_app/test/e2e/fixtures/hao-679-mcp-dashboard-interoperability.json",
    "swissknife/test/e2e/fixtures/hao-681-mcp-dashboard-catalog-consumer.json"
  ],
  "playwright_specs": [
    "hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts",
    "hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts",
    "swissknife/test/e2e/mcp-dashboard.spec.ts"
  ],
  "validation_commands": [
    "npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts",
    "npm --prefix swissknife run test:e2e:mcp",
    "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_launch_readiness_gate.py -q"
  ],
  "catalog_schema": "hallucinate_app.mcp_dashboard_capability_catalog.v1",
  "required_backends": [
    "ipfs_kit_py",
    "ipfs_datasets_py",
    "ipfs_accelerate_py"
  ],
  "required_evidence": [
    "Hallucinate App menu navigation",
    "dashboard capability catalog",
    "daemon health",
    "MCP++ telemetry",
    "dashboard tools/list probes",
    "dashboard tools/call probes",
    "Swissknife consumption",
    "Playwright pass/fail receipts",
    "one traceable session",
    "shared daemon lineage"
  ],
  "session_trace": {
    "session_id": "vaios-g723-hallucinate-mcp-dashboard-session",
    "correlation_id": "corr-vaios-g723-dashboard-interop",
    "request_id": "req-hao-682-launch-readiness",
    "menu_navigation_receipt_id": "hao-682-menu-navigation-receipt",
    "catalog_receipt_id": "hao-682-dashboard-catalog-receipt",
    "daemon_lineage_id": "vaios-g723-daemon-lineage-ipfs-kit-datasets-accelerate",
    "mcpplusplus_telemetry_receipt_id": "hao-682-mcpplusplus-telemetry-receipt",
    "swissknife_consumption_receipt_id": "hao-681-swissknife-dashboard-catalog-consumer"
  },
  "dashboard_servers": [
    {
      "daemon_id": "ipfs-kit",
      "server_package": "ipfs_kit_py",
      "daemon_lineage_id": "vaios-g723-daemon-lineage-ipfs-kit-datasets-accelerate",
      "mcpplusplus_descriptor_evidence": "mcp++/profile-e-mcp-p2p",
      "tools_list_probe": {
        "operation": "tools/list",
        "receipt_id": "hao-682-ipfs-kit-tools-list"
      },
      "tools_call_probe": {
        "operation": "tools/call",
        "tool_name": "ipfs_status",
        "mutation": false,
        "receipt_id": "ipfs_kit_status_probe"
      },
      "swissknife_consumer": "Swissknife IPFS storage, pin dashboard, and backend health surfaces"
    },
    {
      "daemon_id": "ipfs-datasets",
      "server_package": "ipfs_datasets_py",
      "daemon_lineage_id": "vaios-g723-daemon-lineage-ipfs-kit-datasets-accelerate",
      "mcpplusplus_descriptor_evidence": "mcp++/descriptor:not_advertised",
      "tools_list_probe": {
        "operation": "tools/list",
        "receipt_id": "hao-682-ipfs-datasets-tools-list"
      },
      "tools_call_probe": {
        "operation": "tools/call",
        "tool_name": "datasets_list",
        "mutation": false,
        "receipt_id": "ipfs_datasets_list_probe"
      },
      "swissknife_consumer": "Swissknife dataset, content, index, provenance, and background task surfaces"
    },
    {
      "daemon_id": "ipfs-accelerate",
      "server_package": "ipfs_accelerate_py",
      "daemon_lineage_id": "vaios-g723-daemon-lineage-ipfs-kit-datasets-accelerate",
      "mcpplusplus_descriptor_evidence": "mcp++/profile-e-mcp-p2p",
      "tools_list_probe": {
        "operation": "tools/list",
        "receipt_id": "hao-682-ipfs-accelerate-tools-list"
      },
      "tools_call_probe": {
        "operation": "tools/call",
        "tool_name": "hardware_profile",
        "mutation": false,
        "receipt_id": "ipfs_accelerate_hardware_profile_probe"
      },
      "swissknife_consumer": "Swissknife hardware profile, inference job, job status, and telemetry surfaces"
    }
  ],
  "playwright_receipts": [
    {
      "command": "npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts",
      "receipt_id": "hao-682-hallucinate-playwright-pass-fail",
      "status": "required_pass"
    },
    {
      "command": "npm --prefix swissknife run test:e2e:mcp",
      "receipt_id": "hao-682-swissknife-playwright-pass-fail",
      "status": "required_pass"
    }
  ],
  "pass_together_rule": {
    "same_session_id": "vaios-g723-hallucinate-mcp-dashboard-session",
    "same_daemon_lineage_id": "vaios-g723-daemon-lineage-ipfs-kit-datasets-accelerate",
    "requires_hallucinate_app_menu_navigation": true,
    "requires_dashboard_catalog": true,
    "requires_daemon_health": true,
    "requires_mcpplusplus_telemetry": true,
    "requires_dashboard_tools_list": true,
    "requires_dashboard_tools_call": true,
    "requires_swissknife_consumption": true,
    "requires_playwright_pass_fail_receipts": true,
    "gate_state_before_all_pass": "open",
    "gate_state_after_all_pass": "launch_ready"
  },
  "failure_rule": "VAIOS-G723 cannot close until Hallucinate App menu navigation, dashboard catalog, daemon health, MCP++ telemetry, dashboard tools/list and tools/call probes, Swissknife consumption, and Playwright pass/fail receipts share one traceable session and daemon lineage."
}
```

## Gate Contract

The Hallucinate App Playwright command proves the dashboard feature exposure
spec and dashboard interoperability spec together. The Swissknife command proves
that storage, dataset, and compute applications consume the same
`hallucinate_app.mcp_dashboard_capability_catalog.v1` entries and receipt
aliases as Hallucinate App.

The aggregate launch-readiness receipt is launch-blocking for VAIOS-G723. A
dashboard-only pass is insufficient, and a Swissknife-only pass is insufficient:
both pass/fail receipts must reference
`vaios-g723-hallucinate-mcp-dashboard-session` and
`vaios-g723-daemon-lineage-ipfs-kit-datasets-accelerate`.
