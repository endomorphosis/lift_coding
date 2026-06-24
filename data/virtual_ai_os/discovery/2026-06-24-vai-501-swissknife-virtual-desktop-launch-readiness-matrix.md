# VAI-501 Swissknife Virtual Desktop Launch Readiness Matrix

Task: VAI-501
Priority: P0
Track: integration
Depends on: VAI-003, VAI-004, VAI-006, VAI-007, VAI-010, VAI-019

This daemon-readable matrix turns the Swissknife virtual desktop launch slice
into one prioritized launch gate. The gate stays open until the desktop/mobile
UI, Hallucinate App mediation, IPFS MCP servers, desktop peer offload, Meta
glasses terminal IO, IPFS/libp2p transport, MCP++ compatibility, and Playwright
evidence all point at concrete owners and commands.

## SwissknifeVirtualDesktopLaunchReadinessMatrix

```json
{
  "schema": "swissknife_virtual_desktop_launch_readiness_matrix_v1",
  "task_id": "VAI-501",
  "launch_gate_id": "VAI-501:Swissknife virtual desktop:launch-readiness",
  "priority": "P0",
  "track": "integration",
  "depends_on": [
    "VAI-003",
    "VAI-004",
    "VAI-006",
    "VAI-007",
    "VAI-010",
    "VAI-019"
  ],
  "gate_state": "open_until_all_required_validations_pass",
  "gate_owner": "virtual-ai-os launch integration owner",
  "lineage_id": "VAIOS-G697:launch-readiness:phone-desktop-glasses",
  "required_terms": [
    "Swissknife virtual desktop",
    "desktop peer offload",
    "MCP++",
    "Playwright"
  ],
  "required_validation_commands": [
    "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py",
    "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q",
    "npm --prefix swissknife run test:e2e:meta-glasses",
    "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts",
    "rg -n \"VAI-501|Swissknife virtual desktop|desktop peer offload|MCP\\\\+\\\\+|Playwright\" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery"
  ],
  "launch_ready_requires": [
    "all matrix rows have owner, priority, validation_commands, evidence_refs, and blocks_launch=true",
    "VAI-340 launch_readiness_receipt_v1 remains the receipt lineage anchor",
    "VAI-339 deterministic replay preserves command, session, correlation, and request identity",
    "hardware-free Playwright evidence remains explicit and does not replace required physical follow-up receipts"
  ],
  "owners": {
    "swissknife_desktop_mobile_ui": "Swissknife UI/ORB owner",
    "hallucinate_app_mediation": "Hallucinate App control-plane owner",
    "ipfs_accelerate_mcp_server": "ipfs_accelerate_py placement/MCP owner",
    "ipfs_datasets_mcp_server": "ipfs_datasets_py routing/MCP owner",
    "ipfs_kit_mcp_server": "ipfs_kit_py provenance/MCP owner",
    "desktop_peer_offload": "runtime placement owner",
    "meta_glasses_terminal_io": "Meta glasses terminal owner",
    "ipfs_libp2p_transport": "IPFS/libp2p transport owner",
    "mcp_plus_plus_compatibility": "MCP++ compatibility owner",
    "playwright_evidence_lineage": "launch validation owner"
  },
  "matrix": [
    {
      "priority_order": 1,
      "surface": "swissknife_desktop_mobile_ui",
      "owner": "Swissknife UI/ORB owner",
      "readiness_requirement": "Swissknife virtual desktop and mobile ORB surfaces can open the launch session and render every operator desktop app through the Meta glasses template.",
      "validation_commands": [
        "npm --prefix swissknife run test:e2e:meta-glasses",
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q"
      ],
      "evidence_refs": [
        "swissknife/test/e2e/meta-glasses-virtual-os.spec.ts",
        "data/virtual_ai_os/discovery/2026-06-23-vai-340-launch-readiness-gate.md"
      ],
      "blocks_launch": true
    },
    {
      "priority_order": 2,
      "surface": "hallucinate_app_mediation",
      "owner": "Hallucinate App control-plane owner",
      "readiness_requirement": "Hallucinate App mediation accepts the phone-originated interaction envelope, records policy decision receipts, and dispatches only approved control-plane commands.",
      "validation_commands": [
        "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts",
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q"
      ],
      "evidence_refs": [
        "hallucinate_app/test/e2e/multimodal-control-surface.spec.ts",
        "data/virtual_ai_os/discovery/2026-06-23-vai-339-launch-replay-gate.md"
      ],
      "blocks_launch": true
    },
    {
      "priority_order": 3,
      "surface": "ipfs_accelerate_mcp_server",
      "owner": "ipfs_accelerate_py placement/MCP owner",
      "readiness_requirement": "ipfs_accelerate_py MCP server exposes placement and acceleration capabilities used by desktop peer offload and phone-local recovery.",
      "validation_commands": [
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_ipfs_accelerate_adapters.py tests/test_virtual_ai_os_runtime_placement.py -q"
      ],
      "evidence_refs": [
        "external/ipfs_accelerate",
        "tests/test_virtual_ai_os_runtime_placement.py",
        "data/virtual_ai_os/discovery/2026-06-23-vai-019-cross-submodule-integration-tests.md"
      ],
      "blocks_launch": true
    },
    {
      "priority_order": 4,
      "surface": "ipfs_datasets_mcp_server",
      "owner": "ipfs_datasets_py routing/MCP owner",
      "readiness_requirement": "ipfs_datasets_py MCP server keeps semantic routing and backlog orchestration addressable for the shared capability envelope.",
      "validation_commands": [
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_ipfs_datasets_routers.py tests/test_virtual_ai_os_task_orchestration.py -q"
      ],
      "evidence_refs": [
        "external/ipfs_datasets",
        "tests/test_virtual_ai_os_task_orchestration.py",
        "data/virtual_ai_os/discovery/2026-06-23-vai-019-cross-submodule-integration-tests.md"
      ],
      "blocks_launch": true
    },
    {
      "priority_order": 5,
      "surface": "ipfs_kit_mcp_server",
      "owner": "ipfs_kit_py provenance/MCP owner",
      "readiness_requirement": "ipfs_kit_py MCP server keeps IPFS content addressing, artifact pinning, and receipt provenance available to launch receipts.",
      "validation_commands": [
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_ipfs_kit_adapters.py tests/test_mcp_ipfs_provider.py -q"
      ],
      "evidence_refs": [
        "external/ipfs_kit",
        "tests/test_mcp_ipfs_provider.py",
        "data/virtual_ai_os/discovery/2026-06-23-vai-019-cross-submodule-integration-tests.md"
      ],
      "blocks_launch": true
    },
    {
      "priority_order": 6,
      "surface": "desktop_peer_offload",
      "owner": "runtime placement owner",
      "readiness_requirement": "desktop peer offload is selected when policy allows desktop:peer execution and records phone_local recovery for the same command lineage.",
      "validation_commands": [
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_runtime_placement.py tests/test_virtual_ai_os_launch_readiness_gate.py -q"
      ],
      "evidence_refs": [
        "data/virtual_ai_os/discovery/2026-06-23-vai-339-launch-replay-gate.md",
        "data/hallucinate_multimodal_control/discovery/2026-06-23-hao-438-desktop-peer-offload-smoke.md"
      ],
      "blocks_launch": true
    },
    {
      "priority_order": 7,
      "surface": "meta_glasses_terminal_io",
      "owner": "Meta glasses terminal owner",
      "readiness_requirement": "Meta glasses terminal IO renders status output, preserves confirmation/cancel actions, and records display-widget receipts for the launch session.",
      "validation_commands": [
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_meta_glasses_remote_terminal.py tests/test_virtual_ai_os_launch_readiness_gate.py -q"
      ],
      "evidence_refs": [
        "data/hallucinate_multimodal_control/discovery/2026-06-23-hao-439-meta-glasses-terminal-receipt.md",
        "data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-274-launch-readiness-gate.md"
      ],
      "blocks_launch": true
    },
    {
      "priority_order": 8,
      "surface": "ipfs_libp2p_transport",
      "owner": "IPFS/libp2p transport owner",
      "readiness_requirement": "IPFS/libp2p transport can carry content-addressed launch receipts, widget descriptors, and peer-routing metadata without breaking receipt provenance.",
      "validation_commands": [
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_transport_providers.py tests/test_mcp_result_envelope.py -q"
      ],
      "evidence_refs": [
        "tests/test_transport_providers.py",
        "tests/test_mcp_result_envelope.py",
        "data/virtual_ai_os/discovery/2026-06-23-vai-339-launch-replay-gate.md"
      ],
      "blocks_launch": true
    },
    {
      "priority_order": 9,
      "surface": "mcp_plus_plus_compatibility",
      "owner": "MCP++ compatibility owner",
      "readiness_requirement": "MCP++ compatibility remains a distributed protocol surface across Swissknife, ipfs_accelerate_py, and ipfs_datasets_py with Mcp-Plus-Plus as the spec/docs source.",
      "validation_commands": [
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_capability_registry.py tests/test_mcp_catalog.py -q",
        "rg -n \"MCP\\\\+\\\\+|Mcp-Plus-Plus\" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery"
      ],
      "evidence_refs": [
        "Mcp-Plus-Plus",
        "data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-vai-013-2026-06-23.md",
        "data/virtual_ai_os/discovery/source-topology-vai-001-2026-06-12.md"
      ],
      "blocks_launch": true
    },
    {
      "priority_order": 10,
      "surface": "playwright_evidence_lineage",
      "owner": "launch validation owner",
      "readiness_requirement": "Playwright evidence for Swissknife and Hallucinate App shares the VAIOS-G697 receipt lineage and is tied to the Python readiness gate.",
      "validation_commands": [
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q",
        "npm --prefix swissknife run test:e2e:meta-glasses",
        "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
      ],
      "evidence_refs": [
        "data/virtual_ai_os/discovery/2026-06-23-vai-340-launch-readiness-gate.md",
        "swissknife/test/e2e/meta-glasses-virtual-os.spec.ts",
        "hallucinate_app/test/e2e/multimodal-control-surface.spec.ts"
      ],
      "blocks_launch": true
    }
  ]
}
```

## Validation

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q
npm --prefix swissknife run test:e2e:meta-glasses
npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
rg -n "VAI-501|Swissknife virtual desktop|desktop peer offload|MCP\\+\\+|Playwright" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
```
