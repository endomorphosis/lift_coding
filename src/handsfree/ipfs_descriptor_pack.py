"""SwissKnife IPFS descriptor pack for the MCP++ ORB layer.

Registers IPFS capabilities (storage, embeddings, generation, acceleration)
as routable descriptors in the SwissKnife virtual desktop ORB system.
This allows the Hallucinate App and Meta glasses surfaces to discover and
invoke IPFS operations through the unified capability routing kernel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IPFSDescriptorPackEntry:
    """One capability descriptor in the IPFS pack."""

    descriptor_id: str
    capability_id: str
    label: str
    description: str
    transport_kinds: tuple[str, ...]
    endpoint_path: str
    method: str = "POST"
    requires_body: bool = True
    tags: tuple[str, ...] = ()


# The IPFS descriptor pack - all capabilities exposed through /v1/ipfs/*
IPFS_DESCRIPTOR_PACK: tuple[IPFSDescriptorPackEntry, ...] = (
    IPFSDescriptorPackEntry(
        descriptor_id="ipfs.status",
        capability_id="ipfs_status",
        label="IPFS Status",
        description="Check health and availability of all IPFS subsystems (kit, datasets, accelerate)",
        transport_kinds=("http", "websocket", "mcp-server"),
        endpoint_path="/v1/ipfs/status",
        method="GET",
        requires_body=False,
        tags=("ipfs", "health", "diagnostics"),
    ),
    IPFSDescriptorPackEntry(
        descriptor_id="ipfs.add",
        capability_id="ipfs_add_content",
        label="IPFS Add",
        description="Add content to IPFS and get a CID back",
        transport_kinds=("http", "websocket", "mcp-server"),
        endpoint_path="/v1/ipfs/add",
        tags=("ipfs", "storage", "write"),
    ),
    IPFSDescriptorPackEntry(
        descriptor_id="ipfs.cat",
        capability_id="ipfs_cat_content",
        label="IPFS Cat",
        description="Retrieve content by CID from IPFS",
        transport_kinds=("http", "websocket", "mcp-server"),
        endpoint_path="/v1/ipfs/cat",
        tags=("ipfs", "storage", "read"),
    ),
    IPFSDescriptorPackEntry(
        descriptor_id="ipfs.pin",
        capability_id="ipfs_pin_content",
        label="IPFS Pin",
        description="Pin content by CID to ensure persistence",
        transport_kinds=("http", "websocket", "mcp-server"),
        endpoint_path="/v1/ipfs/pin",
        tags=("ipfs", "storage", "persistence"),
    ),
    IPFSDescriptorPackEntry(
        descriptor_id="ipfs.unpin",
        capability_id="ipfs_unpin_content",
        label="IPFS Unpin",
        description="Unpin content by CID",
        transport_kinds=("http", "websocket", "mcp-server"),
        endpoint_path="/v1/ipfs/unpin",
        tags=("ipfs", "storage", "persistence"),
    ),
    IPFSDescriptorPackEntry(
        descriptor_id="ipfs.resolve",
        capability_id="ipfs_resolve_cid",
        label="IPFS Resolve",
        description="Resolve CID metadata and DAG information",
        transport_kinds=("http", "websocket", "mcp-server"),
        endpoint_path="/v1/ipfs/resolve",
        tags=("ipfs", "storage", "metadata"),
    ),
    IPFSDescriptorPackEntry(
        descriptor_id="ipfs.embed",
        capability_id="ipfs_embed_texts",
        label="IPFS Embed",
        description="Generate embeddings via ipfs_datasets or ipfs_accelerate routers",
        transport_kinds=("http", "websocket", "mcp-server"),
        endpoint_path="/v1/ipfs/embed",
        tags=("ipfs", "ai", "embeddings"),
    ),
    IPFSDescriptorPackEntry(
        descriptor_id="ipfs.generate",
        capability_id="ipfs_generate_text",
        label="IPFS Generate",
        description="Generate text via LLM router (ipfs_datasets or ipfs_accelerate)",
        transport_kinds=("http", "websocket", "mcp-server"),
        endpoint_path="/v1/ipfs/generate",
        tags=("ipfs", "ai", "llm", "generation"),
    ),
    IPFSDescriptorPackEntry(
        descriptor_id="ipfs.capabilities",
        capability_id="ipfs_accelerate_capabilities",
        label="IPFS Capabilities",
        description="List accelerate hardware capabilities (GPU, WebNN, WebGPU)",
        transport_kinds=("http", "websocket", "mcp-server"),
        endpoint_path="/v1/ipfs/capabilities",
        method="GET",
        requires_body=False,
        tags=("ipfs", "ai", "accelerate", "hardware"),
    ),
)


def get_ipfs_descriptor_pack() -> tuple[IPFSDescriptorPackEntry, ...]:
    """Return the full IPFS descriptor pack for ORB registration."""
    return IPFS_DESCRIPTOR_PACK


def get_ipfs_descriptor_pack_as_dicts() -> list[dict[str, Any]]:
    """Return the descriptor pack as JSON-serializable dicts for MCP++ transport."""
    return [
        {
            "descriptor_id": entry.descriptor_id,
            "capability_id": entry.capability_id,
            "label": entry.label,
            "description": entry.description,
            "transport_kinds": list(entry.transport_kinds),
            "endpoint_path": entry.endpoint_path,
            "method": entry.method,
            "requires_body": entry.requires_body,
            "tags": list(entry.tags),
        }
        for entry in IPFS_DESCRIPTOR_PACK
    ]


def get_ipfs_capability_ids() -> tuple[str, ...]:
    """Return all capability IDs in the IPFS descriptor pack."""
    return tuple(entry.capability_id for entry in IPFS_DESCRIPTOR_PACK)


def lookup_ipfs_descriptor(capability_id: str) -> IPFSDescriptorPackEntry | None:
    """Look up a descriptor by capability_id."""
    for entry in IPFS_DESCRIPTOR_PACK:
        if entry.capability_id == capability_id:
            return entry
    return None


class IPFSMCPToolManifest(list[dict[str, Any]]):
    """MCP++ tool manifest that supports legacy dict-style metadata access."""

    def __init__(
        self,
        *,
        name: str,
        version: str,
        description: str,
        tools: list[dict[str, Any]],
    ) -> None:
        super().__init__(tools)
        self.name = name
        self.version = version
        self.description = description

    def __getitem__(self, key: int | slice | str) -> Any:
        if isinstance(key, str):
            if key == "name":
                return self.name
            if key == "version":
                return self.version
            if key == "description":
                return self.description
            if key == "tools":
                return list(self)
            raise KeyError(key)
        return super().__getitem__(key)

    def as_dict(self) -> dict[str, Any]:
        """Return the canonical MCP++ manifest envelope."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tools": list(self),
        }


# MCP++ tool manifest format for the IPFS descriptor pack
def get_ipfs_mcp_tool_manifest() -> IPFSMCPToolManifest:
    """Return the MCP++ tool manifest for IPFS operations.

    This is the format expected by the SwissKnife mcp-orb-capability-router
    for registering tools from descriptor packs.
    """
    tools = []
    for entry in IPFS_DESCRIPTOR_PACK:
        tool: dict[str, Any] = {
            "name": entry.descriptor_id.replace(".", "_"),
            "descriptor_id": entry.descriptor_id,
            "description": entry.description,
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        }
        if entry.requires_body:
            if "add" in entry.descriptor_id:
                tool["inputSchema"]["properties"] = {
                    "data_base64": {"type": "string", "description": "Base64-encoded content"},
                    "pin": {"type": "boolean", "default": True},
                }
                tool["inputSchema"]["required"] = ["data_base64"]
            elif "cat" in entry.descriptor_id or "resolve" in entry.descriptor_id:
                tool["inputSchema"]["properties"] = {
                    "cid": {"type": "string", "description": "IPFS content identifier"},
                }
                tool["inputSchema"]["required"] = ["cid"]
            elif "pin" in entry.descriptor_id or "unpin" in entry.descriptor_id:
                tool["inputSchema"]["properties"] = {
                    "cid": {"type": "string", "description": "IPFS content identifier"},
                }
                tool["inputSchema"]["required"] = ["cid"]
            elif "embed" in entry.descriptor_id:
                tool["inputSchema"]["properties"] = {
                    "texts": {"type": "array", "items": {"type": "string"}},
                    "model_name": {"type": "string", "nullable": True},
                    "provider": {"type": "string", "enum": ["datasets", "accelerate"], "nullable": True},
                }
                tool["inputSchema"]["required"] = ["texts"]
            elif "generate" in entry.descriptor_id:
                tool["inputSchema"]["properties"] = {
                    "prompt": {"type": "string"},
                    "model_name": {"type": "string", "nullable": True},
                    "provider": {"type": "string", "enum": ["datasets", "accelerate"], "nullable": True},
                }
                tool["inputSchema"]["required"] = ["prompt"]
        tools.append(tool)

    return IPFSMCPToolManifest(
        name="ipfs-integration",
        version="1.0.0",
        description="IPFS Kit, Datasets, and Accelerate integration for the Virtual AI OS",
        tools=tools,
    )
