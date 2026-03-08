"""Environment-driven configuration for MCP++ servers."""

from __future__ import annotations

import os

from .models import MCPServerConfig

_SERVER_ENV_PREFIX = {
    "ipfs_datasets": "HANDSFREE_MCP_IPFS_DATASETS",
    "ipfs_kit": "HANDSFREE_MCP_IPFS_KIT",
    "ipfs_accelerate": "HANDSFREE_MCP_IPFS_ACCELERATE",
}

_PROVIDER_ENABLE_ENV = {
    "ipfs_datasets_mcp": "HANDSFREE_AGENT_ENABLE_IPFS_DATASETS_MCP",
    "ipfs_kit_mcp": "HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP",
    "ipfs_accelerate_mcp": "HANDSFREE_AGENT_ENABLE_IPFS_ACCELERATE_MCP",
}

_DEFAULT_TOOL_NAME = {
    "ipfs_datasets": "tools_dispatch",
    "ipfs_kit": "",
    "ipfs_accelerate": "tools_dispatch",
}


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_mcp_globally_enabled() -> bool:
    """Return whether MCP integrations are globally enabled."""
    return _env_flag("HANDSFREE_MCP_ENABLED", True)


def is_mcp_provider_enabled(provider_name: str) -> bool:
    """Return whether the named MCP provider is enabled."""
    if not is_mcp_globally_enabled():
        return False

    env_name = _PROVIDER_ENABLE_ENV.get(provider_name)
    if env_name is None:
        return False
    return _env_flag(env_name, True)


def get_mcp_server_config(server_family: str) -> MCPServerConfig:
    """Build MCP server config for the given server family from environment."""
    if server_family not in _SERVER_ENV_PREFIX:
        raise ValueError(f"Unknown MCP server family: {server_family}")

    prefix = _SERVER_ENV_PREFIX[server_family]
    timeout_s = float(os.getenv("HANDSFREE_MCP_DEFAULT_TIMEOUT_S", "30"))
    poll_interval_s = float(os.getenv("HANDSFREE_MCP_DEFAULT_POLL_INTERVAL_S", "2"))

    return MCPServerConfig(
        server_family=server_family,
        endpoint=os.getenv(f"{prefix}_URL", "").strip(),
        auth_secret=os.getenv(f"{prefix}_AUTH_SECRET"),
        timeout_s=timeout_s,
        poll_interval_s=poll_interval_s,
        enabled=True,
        tool_name=(os.getenv(f"{prefix}_TOOL_NAME", _DEFAULT_TOOL_NAME[server_family]).strip() or None),
        rpc_path=os.getenv(f"{prefix}_RPC_PATH", os.getenv("HANDSFREE_MCP_RPC_PATH", "/mcp")),
        protocol_version=os.getenv(
            "HANDSFREE_MCP_PROTOCOL_VERSION",
            "2024-11-05",
        ),
        client_name=os.getenv(
            "HANDSFREE_MCP_CLIENT_NAME",
            "handsfree-dev-companion",
        ),
        client_version=os.getenv(
            "HANDSFREE_MCP_CLIENT_VERSION",
            "0.0.0",
        ),
        transport=os.getenv(
            f"{prefix}_TRANSPORT",
            os.getenv("HANDSFREE_MCP_TRANSPORT", "http"),
        ).strip().lower(),
        command=os.getenv(f"{prefix}_COMMAND"),
        args=[
            part
            for part in os.getenv(f"{prefix}_ARGS", "").split(" ")
            if part.strip()
        ],
        task_category=(os.getenv(f"{prefix}_TASK_CATEGORY", "").strip() or None),
        task_create_tool=(os.getenv(f"{prefix}_TASK_CREATE_TOOL", "").strip() or None),
        task_status_tool=(os.getenv(f"{prefix}_TASK_STATUS_TOOL", "").strip() or None),
        task_cancel_tool=(os.getenv(f"{prefix}_TASK_CANCEL_TOOL", "").strip() or None),
    )
