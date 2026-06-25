# HAO-677 Dashboard Capability Catalog

HAO-677 promotes the Hallucinate App MCP dashboard integration from menu-only
coverage to a daemon-owned capability catalog. The catalog gives the app,
Playwright tests, Swissknife consumers, and the supervisor the same launch
contract for `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py`.

This also reconciles the older HAO-674 IPFS Kit evidence with the current launch
truth: IPFS Kit runs on port 8004, not the historical 3001 port.

## Catalog Fixture

```json
{
  "schema": "hallucinate_app.mcp_dashboard_capability_catalog.v1",
  "task_id": "HAO-677",
  "goal_id": "VAIOS-G723",
  "generated_by": "hallucinate_app.node.mcp_daemon_manager",
  "control_surface_route": [
    "Hallucinate App dashboard action",
    "dashboard capability catalog",
    "interaction_envelope",
    "policy_decision",
    "mediation_receipt",
    "supervised MCP server transport"
  ],
  "servers": [
    {
      "daemon_id": "ipfs-kit",
      "server_package": "ipfs_kit_py",
      "display_name": "IPFS Kit",
      "port": 8004,
      "endpoint": "http://127.0.0.1:8004",
      "transport": "http",
      "rpc_path": "/mcp/tools/call",
      "health_path": "/api/mcp/status",
      "health_url": "http://127.0.0.1:8004/api/mcp/status",
      "menu_dashboard_path": "views/ipfs_kit_dashboard.html",
      "menu_dashboard_url": "http://127.0.0.1:8004/dashboard",
      "native_dashboard_url": null,
      "native_dashboard_catalog_url": null,
      "tool_protocols": {
        "tools_list": {
          "operation": "tools/list",
          "method": "GET",
          "url": "http://127.0.0.1:8004/mcp/tools/list"
        },
        "tools_call": {
          "operation": "tools/call",
          "method": "POST",
          "url": "http://127.0.0.1:8004/mcp/tools/call",
          "safeProbe": {
            "tool_name": "ipfs_status",
            "arguments": {},
            "mutation": false,
            "expected_receipt": "ipfs_kit_status_probe"
          }
        }
      },
      "mcpplusplus": {
        "available": false,
        "mode": "not_advertised",
        "profiles": []
      },
      "swissknife_consumer": "Swissknife IPFS storage, pin dashboard, and backend health surfaces",
      "control_surface_mediation_contract": "control_surface_contract:mcp-daemon:ipfs-kit",
      "control_surface_receipt_requirements": [
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
        "daemon_id",
        "server_package",
        "tool_protocol",
        "safe_probe",
        "receipt_cid"
      ]
    },
    {
      "daemon_id": "ipfs-datasets",
      "server_package": "ipfs_datasets_py",
      "display_name": "IPFS Datasets",
      "port": 3002,
      "endpoint": "http://127.0.0.1:3002",
      "transport": "http",
      "rpc_path": "/datasets/load",
      "health_path": "/health/ready",
      "health_url": "http://127.0.0.1:3002/health/ready",
      "menu_dashboard_path": "views/ipfs_datasets_dashboard.html",
      "menu_dashboard_url": "http://127.0.0.1:8899/mcp",
      "native_dashboard_url": "http://127.0.0.1:8899/mcp",
      "native_dashboard_catalog_url": "http://127.0.0.1:8899/api/hallucinate/dashboard-catalog",
      "tool_protocols": {
        "tools_list": {
          "operation": "tools/list",
          "method": "GET",
          "url": "http://127.0.0.1:3002/datasets/list"
        },
        "tools_call": {
          "operation": "tools/call",
          "method": "POST",
          "url": "http://127.0.0.1:3002/datasets/load",
          "safeProbe": {
            "tool_name": "datasets_list",
            "arguments": {
              "limit": 1
            },
            "mutation": false,
            "expected_receipt": "ipfs_datasets_list_probe"
          }
        }
      },
      "mcpplusplus": {
        "provider": "ipfs_datasets_py.mcp_server.mcplusplus",
        "bridge_to": "ipfs_accelerate_py.mcplusplus_module",
        "supports_profile_negotiation": false,
        "mode": "optional_bridge",
        "profiles": []
      },
      "swissknife_consumer": "Swissknife dataset, content, index, provenance, and background task surfaces",
      "control_surface_mediation_contract": "control_surface_contract:mcp-daemon:ipfs-datasets",
      "control_surface_receipt_requirements": [
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
        "daemon_id",
        "server_package",
        "tool_protocol",
        "safe_probe",
        "receipt_cid"
      ]
    },
    {
      "daemon_id": "ipfs-accelerate",
      "server_package": "ipfs_accelerate_py",
      "display_name": "IPFS Accelerate",
      "port": 3003,
      "endpoint": "http://127.0.0.1:3003",
      "transport": "http",
      "rpc_path": "/mcp",
      "health_path": "/api/mcp/status",
      "health_url": "http://127.0.0.1:3003/api/mcp/status",
      "menu_dashboard_path": "views/ipfs_accelerate_dashboard.html",
      "menu_dashboard_url": "http://127.0.0.1:3003/dashboard",
      "native_dashboard_url": null,
      "native_dashboard_catalog_url": null,
      "tool_protocols": {
        "tools_list": {
          "operation": "tools/list",
          "method": "GET",
          "url": "http://127.0.0.1:3003/models/list"
        },
        "tools_call": {
          "operation": "tools/call",
          "method": "POST",
          "url": "http://127.0.0.1:3003/inference",
          "safeProbe": {
            "tool_name": "hardware_profile",
            "arguments": {
              "dry_run": true
            },
            "mutation": false,
            "expected_receipt": "ipfs_accelerate_hardware_profile_probe"
          }
        }
      },
      "mcpplusplus": {
        "available": true,
        "supports_profile_negotiation": true,
        "mode": "optional_additive",
        "profiles": [
          "mcp++/profile-a-idl",
          "mcp++/profile-b-cid-artifacts",
          "mcp++/profile-c-ucan",
          "mcp++/profile-d-temporal-policy",
          "mcp++/profile-e-mcp-p2p"
        ]
      },
      "swissknife_consumer": "Swissknife hardware profile, inference job, job status, and telemetry surfaces",
      "control_surface_mediation_contract": "control_surface_contract:mcp-daemon:ipfs-accelerate",
      "control_surface_receipt_requirements": [
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
        "daemon_id",
        "server_package",
        "tool_protocol",
        "safe_probe",
        "receipt_cid"
      ]
    }
  ]
}
```

## Supervisor Guidance

The next useful generated tasks should attach to HAO-678 through HAO-683, not to
historical broad scans. Useful follow-up work includes dashboard UI wiring,
hardware-free tools/list and safe tools/call probes, MCP++ receipt capture,
Swissknife catalog consumption, and launch-readiness aggregation.
