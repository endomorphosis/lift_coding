"""Default configuration for running handsfree inside the Hallucinate App ecosystem.

When the handsfree backend runs as part of the Hallucinate App Electron desktop,
the three IPFS MCP servers are managed by mcp_daemon_manager.js on fixed ports.
This module provides those defaults so the MCP client can connect without manual
environment configuration.
"""

from __future__ import annotations

import os

# Port assignments matching hallucinate_app/node/mcp_daemon_manager.js
HALLUCINATE_APP_IPFS_KIT_PORT = 8004
HALLUCINATE_APP_IPFS_DATASETS_PORT = 3002
HALLUCINATE_APP_IPFS_ACCELERATE_PORT = 3003
HALLUCINATE_APP_SWISSKNIFE_PORT = 8765
HALLUCINATE_APP_HANDSFREE_PORT = 8080

# Endpoint templates
HALLUCINATE_APP_IPFS_KIT_ENDPOINT = f"http://127.0.0.1:{HALLUCINATE_APP_IPFS_KIT_PORT}"
HALLUCINATE_APP_IPFS_DATASETS_ENDPOINT = f"http://127.0.0.1:{HALLUCINATE_APP_IPFS_DATASETS_PORT}"
HALLUCINATE_APP_IPFS_ACCELERATE_ENDPOINT = f"http://127.0.0.1:{HALLUCINATE_APP_IPFS_ACCELERATE_PORT}"

# Health check paths matching daemon configs
HALLUCINATE_APP_HEALTH_PATHS = {
    "ipfs_kit": "/api/mcp/status",
    "ipfs_datasets": "/health/ready",
    "ipfs_accelerate": "/api/mcp/status",
}

# RPC paths matching daemon configs
HALLUCINATE_APP_RPC_PATHS = {
    "ipfs_kit": "/mcp/tools/call",
    "ipfs_datasets": "/mcp",
    "ipfs_accelerate": "/mcp",
}

# Tool protocol paths for dashboard integration
HALLUCINATE_APP_TOOL_PROTOCOLS = {
    "ipfs_kit": {
        "tools_list": "/mcp/tools/list",
        "tools_call": "/mcp/tools/call",
    },
    "ipfs_datasets": {
        "tools_list": "/datasets/list",
        "tools_call": "/datasets/load",
    },
    "ipfs_accelerate": {
        "tools_list": "/models/list",
        "tools_call": "/inference",
    },
}


def is_hallucinate_app_environment() -> bool:
    """Detect if we are running inside the Hallucinate App Electron shell."""
    return os.getenv("HALLUCINATE_APP_MANAGED", "").lower() in {"1", "true", "yes"}


def apply_hallucinate_app_defaults() -> dict[str, str]:
    """Set MCP environment variables to hallucinate_app defaults if not already set.

    Returns a dict of the variables that were applied (for logging/diagnostics).
    """
    defaults = {
        "HANDSFREE_MCP_ENABLED": "true",
        "HANDSFREE_MCP_IPFS_KIT_URL": HALLUCINATE_APP_IPFS_KIT_ENDPOINT,
        "HANDSFREE_MCP_IPFS_KIT_RPC_PATH": HALLUCINATE_APP_RPC_PATHS["ipfs_kit"],
        "HANDSFREE_MCP_IPFS_DATASETS_URL": HALLUCINATE_APP_IPFS_DATASETS_ENDPOINT,
        "HANDSFREE_MCP_IPFS_DATASETS_RPC_PATH": HALLUCINATE_APP_RPC_PATHS["ipfs_datasets"],
        "HANDSFREE_MCP_IPFS_ACCELERATE_URL": HALLUCINATE_APP_IPFS_ACCELERATE_ENDPOINT,
        "HANDSFREE_MCP_IPFS_ACCELERATE_RPC_PATH": HALLUCINATE_APP_RPC_PATHS["ipfs_accelerate"],
    }

    applied = {}
    for key, value in defaults.items():
        if not os.getenv(key):
            os.environ[key] = value
            applied[key] = value

    return applied


def get_hallucinate_app_dashboard_catalog_entry(server_family: str) -> dict:
    """Build a dashboard capability catalog entry for a server family.

    This matches the HallucinateDashboardCapabilityServer interface defined in
    swissknife/src/services/swissknife-mcp-capability-registry.ts.
    """
    configs = {
        "ipfs_kit": {
            "daemon_id": "ipfs-kit",
            "server_package": "ipfs_kit_py",
            "endpoint": HALLUCINATE_APP_IPFS_KIT_ENDPOINT,
            "transport": "http",
            "rpc_path": HALLUCINATE_APP_RPC_PATHS["ipfs_kit"],
            "health_path": HALLUCINATE_APP_HEALTH_PATHS["ipfs_kit"],
            "menu_dashboard_url": "views/ipfs_kit_dashboard.html",
            "native_dashboard_url": None,
            "tool_protocols": HALLUCINATE_APP_TOOL_PROTOCOLS["ipfs_kit"],
            "swissknife_consumer": "Swissknife IPFS storage, pin dashboard, and backend health surfaces",
        },
        "ipfs_datasets": {
            "daemon_id": "ipfs-datasets",
            "server_package": "ipfs_datasets_py",
            "endpoint": HALLUCINATE_APP_IPFS_DATASETS_ENDPOINT,
            "transport": "http",
            "rpc_path": HALLUCINATE_APP_RPC_PATHS["ipfs_datasets"],
            "health_path": HALLUCINATE_APP_HEALTH_PATHS["ipfs_datasets"],
            "menu_dashboard_url": "views/ipfs_datasets_dashboard.html",
            "native_dashboard_url": f"http://127.0.0.1:8899/mcp",
            "tool_protocols": HALLUCINATE_APP_TOOL_PROTOCOLS["ipfs_datasets"],
            "swissknife_consumer": "Swissknife dataset, content, index, provenance, and background task surfaces",
        },
        "ipfs_accelerate": {
            "daemon_id": "ipfs-accelerate",
            "server_package": "ipfs_accelerate_py",
            "endpoint": HALLUCINATE_APP_IPFS_ACCELERATE_ENDPOINT,
            "transport": "http",
            "rpc_path": HALLUCINATE_APP_RPC_PATHS["ipfs_accelerate"],
            "health_path": HALLUCINATE_APP_HEALTH_PATHS["ipfs_accelerate"],
            "menu_dashboard_url": "views/ipfs_accelerate_dashboard.html",
            "native_dashboard_url": None,
            "tool_protocols": HALLUCINATE_APP_TOOL_PROTOCOLS["ipfs_accelerate"],
            "swissknife_consumer": "Swissknife hardware profile, inference job, job status, and telemetry surfaces",
        },
    }

    if server_family not in configs:
        raise ValueError(f"Unknown server family: {server_family}")

    return configs[server_family]
