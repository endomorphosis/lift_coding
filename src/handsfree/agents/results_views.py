"""Shared saved views and preset resolution for agent result queries."""

from __future__ import annotations

from typing import Any

RESULT_PRESETS: dict[str, dict[str, str]] = {
    "dataset_discoveries": {
        "provider": "ipfs_datasets_mcp",
        "capability": "dataset_discovery",
    },
    "ipfs_results": {
        "provider": "ipfs_kit_mcp",
    },
    "agentic_fetches": {
        "provider": "ipfs_accelerate_mcp",
        "capability": "agentic_fetch",
    },
}

RESULT_VIEWS: dict[str, dict[str, Any]] = {
    "overview": {
        "latest_only": True,
        "sort": "updated_at",
        "direction": "desc",
    },
    "datasets": {
        "preset": "dataset_discoveries",
        "latest_only": True,
    },
    "ipfs": {
        "preset": "ipfs_results",
        "latest_only": True,
    },
    "fetches": {
        "preset": "agentic_fetches",
        "latest_only": True,
    },
}


def supported_result_views() -> tuple[str, ...]:
    """Return supported result view aliases."""
    return tuple(RESULT_VIEWS.keys())


def supported_result_presets() -> tuple[str, ...]:
    """Return supported result preset names."""
    return tuple(RESULT_PRESETS.keys())


def resolve_result_query(
    *,
    view: str | None = None,
    provider: str | None = None,
    capability: str | None = None,
    preset: str | None = None,
    latest_only: bool = False,
    sort: str = "updated_at",
    direction: str = "desc",
) -> dict[str, Any]:
    """Resolve view/preset aliases into a concrete result query."""
    if view:
        view_config = RESULT_VIEWS.get(view)
        if view_config is None:
            raise ValueError(
                f"view must be one of: {', '.join(supported_result_views())}"
            )
        preset = preset or view_config.get("preset")
        latest_only = latest_only or bool(view_config.get("latest_only"))
        if sort == "updated_at":
            sort = str(view_config.get("sort", sort))
        if direction == "desc":
            direction = str(view_config.get("direction", direction))

    if preset:
        preset_config = RESULT_PRESETS.get(preset)
        if preset_config is None:
            raise ValueError(
                f"preset must be one of: {', '.join(supported_result_presets())}"
            )
        provider = provider or preset_config.get("provider")
        capability = capability or preset_config.get("capability")

    return {
        "view": view,
        "provider": provider,
        "capability": capability,
        "preset": preset,
        "latest_only": latest_only,
        "sort": sort,
        "direction": direction,
    }
