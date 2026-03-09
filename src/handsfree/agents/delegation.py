"""Helpers for normalizing delegated agent requests."""

from __future__ import annotations

from typing import Any


def enrich_delegate_trace_for_client_context(
    provider: str | None,
    trace: dict[str, Any],
    client_context: dict[str, Any] | None,
) -> tuple[str | None, dict[str, Any]]:
    """Apply client-context-specific routing hints to delegated task trace."""
    normalized_client_context = client_context or {}
    next_trace = dict(trace)
    next_trace["client_context"] = normalized_client_context

    if (
        normalized_client_context.get("feature") == "wearables_bridge"
        and normalized_client_context.get("trigger") == "target_connected"
    ):
        if provider is None:
            provider = "ipfs_accelerate_mcp"
        next_trace.update(
            {
                "created_via": "wearables_bridge",
                "wearables_bridge_trigger": "target_connected",
                "wearables_bridge_requested_workflow": "wearables_bridge_connectivity",
                "mcp_capability": "workflow",
                "mcp_preferred_execution_mode": "mcp_remote",
            }
        )

    return provider, next_trace
