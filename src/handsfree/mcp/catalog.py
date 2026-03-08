"""Shared catalog for MCP-backed IPFS providers and capabilities."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MCPProviderDescriptor:
    """Human and routing metadata for an MCP-backed provider."""

    provider_name: str
    display_name: str
    short_label: str
    aliases: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    default_capability: str = "general"
    instruction_keywords: dict[str, tuple[str, ...]] = field(default_factory=dict)


_PROVIDERS: dict[str, MCPProviderDescriptor] = {
    "ipfs_datasets_mcp": MCPProviderDescriptor(
        provider_name="ipfs_datasets_mcp",
        display_name="IPFS Datasets",
        short_label="datasets",
        aliases=("ipfs datasets", "ipfs dataset"),
        capabilities=("dataset_discovery", "dataset_processing", "embedding", "background_task"),
        default_capability="dataset_discovery",
        instruction_keywords={
            "embedding": ("embed", "embedding", "vector", "similarity", "index"),
            "dataset_processing": ("process", "transform", "convert", "analyze", "audit"),
            "dataset_discovery": ("dataset", "datasets", "find", "search", "discover", "legal"),
            "background_task": ("background", "queue", "task", "schedule"),
        },
    ),
    "ipfs_kit_mcp": MCPProviderDescriptor(
        provider_name="ipfs_kit_mcp",
        display_name="IPFS Kit",
        short_label="kit",
        aliases=("ipfs kit",),
        capabilities=("ipfs_add", "ipfs_cat", "ipfs_pin", "storage"),
        default_capability="storage",
        instruction_keywords={
            "ipfs_add": ("add", "upload", "store", "put"),
            "ipfs_cat": ("cat", "fetch", "read", "download", "get"),
            "ipfs_pin": ("pin", "unpin"),
            "storage": ("bucket", "storage", "backend", "config"),
        },
    ),
    "ipfs_accelerate_mcp": MCPProviderDescriptor(
        provider_name="ipfs_accelerate_mcp",
        display_name="IPFS Accelerate",
        short_label="accelerate",
        aliases=("ipfs accelerate",),
        capabilities=("workflow", "background_task", "p2p", "agentic_fetch"),
        default_capability="workflow",
        instruction_keywords={
            "p2p": ("peer", "p2p", "worker", "distributed"),
            "background_task": ("background", "queue", "task", "schedule"),
            "agentic_fetch": ("fetch", "crawl", "discover", "archive"),
            "workflow": ("workflow", "run", "pipeline", "orchestrate"),
        },
    ),
}


_ALIASES = {
    alias: descriptor.provider_name
    for descriptor in _PROVIDERS.values()
    for alias in descriptor.aliases
}


def get_provider_descriptor(provider_name: str) -> MCPProviderDescriptor | None:
    """Return MCP descriptor for a provider name."""
    return _PROVIDERS.get(provider_name)


def resolve_provider_alias(alias: str) -> str | None:
    """Resolve human alias text to provider name."""
    return _ALIASES.get(alias.strip().lower())


def infer_provider_capability(provider_name: str, instruction: str | None) -> str | None:
    """Infer the likely MCP capability for an instruction."""
    descriptor = get_provider_descriptor(provider_name)
    if descriptor is None:
        return None
    normalized = (instruction or "").strip().lower()
    if not normalized:
        return descriptor.default_capability

    for capability, keywords in descriptor.instruction_keywords.items():
        if any(keyword in normalized for keyword in keywords):
            return capability
    return descriptor.default_capability
