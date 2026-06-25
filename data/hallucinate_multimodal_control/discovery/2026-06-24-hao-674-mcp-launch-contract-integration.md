# HAO-674 MCP Launch Contract Integration

HAO-674 integrates Hallucinate App daemon supervision with Swissknife MCP++
control surfaces for `ipfs_accelerate_py`, `ipfs_datasets_py`, and
`ipfs_kit_py`.

## Integration Fixture

```json
{
  "task_id": "HAO-674",
  "artifact_id": "mcp_launch_contract_integration",
  "requires_physical_devices": false,
  "supervision_owner": "hallucinate_app.mcp_daemon_manager",
  "mediation_owner": "hallucinate_app.control_surface",
  "swissknife_registry": "swissknife/src/services/swissknife-mcp-capability-registry.ts",
  "before_invoke_hook": "hallucinate_app.node.control_surface_invocation.ControlSurfaceInvocationGate.beforeInvoke",
  "control_surface_route": [
    "Swissknife command intent",
    "MCP++ capability descriptor",
    "Hallucinate App interaction_envelope",
    "control_surface policy_decision",
    "mediation_receipt",
    "supervised MCP server transport"
  ],
  "servers": [
    {
      "server_package": "ipfs_kit_py",
      "daemon_id": "ipfs-kit",
      "startup_order": 10,
      "entrypoint": "python -m ipfs_kit_py.cli mcp start",
      "port": 8004,
      "rpc_path": "/mcp/tools/call",
      "swissknife_capability_family": "storage",
      "mcp_plus_plus_operations": [
        "add_content",
        "get_content",
        "pin_content",
        "list_pins",
        "backend_health"
      ],
      "sample_intent": "storage.pin_content",
      "sample_tool": "ipfs_pin_add"
    },
    {
      "server_package": "ipfs_datasets_py",
      "daemon_id": "ipfs-datasets",
      "startup_order": 20,
      "entrypoint": "python -m ipfs_datasets_py.mcp_server --http --port 3002",
      "port": 3002,
      "rpc_path": "/mcp",
      "swissknife_capability_family": "dataset",
      "mcp_plus_plus_operations": [
        "browse",
        "get",
        "index",
        "pin",
        "publish",
        "sync_status"
      ],
      "sample_intent": "dataset.browse",
      "sample_tool": "tools_dispatch"
    },
    {
      "server_package": "ipfs_accelerate_py",
      "daemon_id": "ipfs-accelerate",
      "startup_order": 30,
      "entrypoint": "python -m ipfs_accelerate_py.cli mcp start --port 3003",
      "port": 3003,
      "rpc_path": "/mcp",
      "swissknife_capability_family": "compute",
      "mcp_plus_plus_operations": [
        "hardware_profile",
        "run_inference_job",
        "job_status",
        "telemetry"
      ],
      "sample_intent": "compute.run_inference",
      "sample_tool": "tools_dispatch"
    }
  ],
  "receipt_requirements": [
    "server_package",
    "daemon_id",
    "transport",
    "tool_name",
    "swissknife_consumer",
    "interaction_envelope_id",
    "policy_decision_id",
    "mediation_receipt_id",
    "descriptor_id",
    "arguments_hash",
    "upstream_status",
    "receipt_cid"
  ],
  "assertions": [
    "Hallucinate App starts or supervises all three Python MCP server features before Swissknife invocation",
    "Swissknife advertises MCP++-compatible capability descriptors for ipfs_accelerate_py, ipfs_datasets_py, and ipfs_kit_py",
    "Every service invocation routes through the multimodal control surface before supervised MCP server transport dispatch",
    "Mediation receipts are required for launch evidence and cannot be replaced by direct daemon port calls"
  ]
}
```

The fixture is intentionally hardware-free. It proves contract alignment for the
launch path; live process health and Playwright replay coverage remain owned by
the downstream launch-readiness tasks.
