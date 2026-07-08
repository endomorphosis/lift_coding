"""Interop contract between SwissKnife and ``external/ipfs_kit``.

MGW-572 repairs the VAIOS-G703 objective validation gap that requires
`swissknife` to interoperate with `external/ipfs_kit` through importable
contracts, interface descriptors, runtime handoff behavior, and integration
tests. This is part of the shared
`goal_packet/interoperability/swissknife/06921590135c` packet covering
VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, and
VAIOS-G706.

`external/ipfs_kit` ships three MCP-settings-schema repair scripts
(``archive/archive_clutter/fix_scripts/fix_mcp_schema.py``,
``backup/archive_clutter/fix_scripts/fix_mcp_schema.py``,
``backup/patches/fixes/fix_mcp_schema.py``), a JSON Schema for its
deprecations report (``data/deprecations_report.schema.json``), a Bucket VFS
CLI/MCP interface summary
(``docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md``) documenting its
``bucket_*`` MCP tool surface, and a DAG-PB protobuf schema
(``docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto``) describing the
``PBLink``/``PBNode`` MerkleDAG wire format. This module statically
discovers those five descriptors (without importing `external/ipfs_kit`
Python) and builds a deterministic ``SwissKnifeIPFSKitHandoff`` receipt that
mirrors the
``swissknife/src/services/mcp/ipfs-kit-mcp-schema-interop-descriptor.ts``
runtime handoff descriptor on the SwissKnife side.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

INTERFACE_CONTRACT = "interface contract swissknife external/ipfs_kit"
GOAL_ID = "VAIOS-G703"
GOAL_PACKET = "goal_packet/interoperability/swissknife/06921590135c"
GOAL_PACKET_GOALS = (
    "VAIOS-G700",
    "VAIOS-G701",
    "VAIOS-G702",
    "VAIOS-G703",
    "VAIOS-G704",
    "VAIOS-G705",
    "VAIOS-G706",
)

#: The three ``fix_mcp_schema.py`` copies `external/ipfs_kit` ships that
#: normalize a ``mcpServers`` settings block from an (invalid) JSON array
#: back into an object keyed by server name.
REQUIRED_FIX_MCP_SCHEMA_PATHS = (
    "archive/archive_clutter/fix_scripts/fix_mcp_schema.py",
    "backup/archive_clutter/fix_scripts/fix_mcp_schema.py",
    "backup/patches/fixes/fix_mcp_schema.py",
)

REQUIRED_DEPRECATIONS_REPORT_SCHEMA_PATH = "data/deprecations_report.schema.json"
REQUIRED_BUCKET_VFS_DOC_PATH = "docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md"
REQUIRED_DAG_PB_PROTO_PATH = "docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto"

#: Top-level keys the deprecations report JSON Schema must require.
REQUIRED_DEPRECATIONS_REPORT_KEYS = (
    "report_version",
    "generated_at",
    "deprecated",
    "summary",
    "policy",
    "raw",
)

#: Bucket VFS MCP tool names documented by
#: ``BUCKET_VFS_INTERFACES_COMPLETE.md`` that SwissKnife's bucket-vfs
#: control surface can route to.
REQUIRED_BUCKET_VFS_MCP_TOOLS = (
    "bucket_create",
    "bucket_list",
    "bucket_delete",
    "bucket_add_file",
    "bucket_export_car",
    "bucket_cross_query",
    "bucket_get_info",
    "bucket_status",
)

#: DAG-PB protobuf messages the MerkleDAG wire format defines.
REQUIRED_DAG_PB_MESSAGES = ("PBLink", "PBNode")

#: SwissKnife-side MCP-IDL operations the handoff must support; kept in sync
#: with ``IPFS_KIT_MCP_SCHEMA_INTEROP_OPERATIONS`` in
#: ``swissknife/src/services/mcp/ipfs-kit-mcp-schema-interop-descriptor.ts``.
REQUIRED_SWISSKNIFE_IPFS_KIT_OPERATIONS = (
    "ipfs_kit.mcp_schema.fix_servers_schema",
    "ipfs_kit.mcp_schema.validate_deprecations_report",
    "ipfs_kit.bucket_vfs.export_car",
    "ipfs_kit.bucket_vfs.cross_query",
    "ipfs_kit.dag_pb.encode_node",
    "ipfs_kit.dag_pb.decode_node",
)


class SwissKnifeIPFSKitInteropError(RuntimeError):
    """Raised when either side of the swissknife/ipfs_kit contract is missing."""


@dataclass(frozen=True)
class IPFSKitMCPSchemaContract:
    """Static MCP-schema/bucket-VFS/DAG-PB contract discovered from the submodule."""

    root: str
    fix_mcp_schema_paths: tuple[str, ...]
    deprecations_report_schema_path: str
    bucket_vfs_doc_path: str
    dag_pb_proto_path: str
    bucket_vfs_mcp_tools: tuple[str, ...]
    dag_pb_messages: tuple[str, ...]
    deprecations_report_required_keys: tuple[str, ...]


@dataclass(frozen=True)
class SwissKnifeIPFSKitHandoff:
    """Deterministic receipt for one MCP-schema/bucket-VFS handoff routed to SwissKnife."""

    contract_id: str
    source_repository: str
    target_repository: str
    interface_contract: str
    goal_id: str
    goal_packet: str
    capability: str
    route: str
    content_cid: str
    payload_sha256: str
    payload_size_bytes: int
    bucket_vfs_mcp_tools: tuple[str, ...]
    dag_pb_messages: tuple[str, ...]
    required_swissknife_operations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""
        return asdict(self)


def discover_ipfs_kit_mcp_schema_contract(root: str | Path) -> IPFSKitMCPSchemaContract:
    """Discover the MCP-schema/bucket-VFS/DAG-PB contract.

    Reads (without importing) the descriptors that `external/ipfs_kit` ships
    so SwissKnife can rely on a stable, statically-verifiable contract:

    - ``archive/archive_clutter/fix_scripts/fix_mcp_schema.py``
    - ``backup/archive_clutter/fix_scripts/fix_mcp_schema.py``
    - ``backup/patches/fixes/fix_mcp_schema.py``
    - ``data/deprecations_report.schema.json``
    - ``docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md``
    - ``docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto``
    """
    root_path = Path(root)
    if not root_path.exists():
        raise SwissKnifeIPFSKitInteropError(f"ipfs_kit root not found: {root_path}")

    fix_mcp_schema_full_paths = tuple(root_path / rel for rel in REQUIRED_FIX_MCP_SCHEMA_PATHS)
    deprecations_report_schema_path = root_path / REQUIRED_DEPRECATIONS_REPORT_SCHEMA_PATH
    bucket_vfs_doc_path = root_path / REQUIRED_BUCKET_VFS_DOC_PATH
    dag_pb_proto_path = root_path / REQUIRED_DAG_PB_PROTO_PATH

    missing = [
        str(path)
        for path in (
            *fix_mcp_schema_full_paths,
            deprecations_report_schema_path,
            bucket_vfs_doc_path,
            dag_pb_proto_path,
        )
        if not path.exists()
    ]
    if missing:
        raise SwissKnifeIPFSKitInteropError(
            f"ipfs_kit MCP-schema/bucket-VFS/DAG-PB descriptors missing: {missing}"
        )

    for fix_script_path in fix_mcp_schema_full_paths:
        fix_script_source = fix_script_path.read_text(encoding="utf-8")
        if "def fix_mcp_schema(" not in fix_script_source:
            raise SwissKnifeIPFSKitInteropError(
                f"ipfs_kit MCP schema fix script is missing fix_mcp_schema(): {fix_script_path}"
            )
        if "mcpServers" not in fix_script_source:
            raise SwissKnifeIPFSKitInteropError(
                f"ipfs_kit MCP schema fix script does not reference mcpServers: {fix_script_path}"
            )

    deprecations_report_schema = json.loads(
        deprecations_report_schema_path.read_text(encoding="utf-8")
    )
    discovered_required_keys = tuple(deprecations_report_schema.get("required", ()))
    missing_required_keys = set(REQUIRED_DEPRECATIONS_REPORT_KEYS) - set(discovered_required_keys)
    if missing_required_keys:
        raise SwissKnifeIPFSKitInteropError(
            f"ipfs_kit deprecations_report.schema.json is missing required keys: "
            f"{sorted(missing_required_keys)}"
        )

    bucket_vfs_doc_source = bucket_vfs_doc_path.read_text(encoding="utf-8")
    discovered_bucket_vfs_tools = tuple(
        sorted(set(re.findall(r"`(bucket_[a-z_]+)`", bucket_vfs_doc_source)))
    )
    missing_bucket_vfs_tools = set(REQUIRED_BUCKET_VFS_MCP_TOOLS) - set(discovered_bucket_vfs_tools)
    if missing_bucket_vfs_tools:
        raise SwissKnifeIPFSKitInteropError(
            f"ipfs_kit BUCKET_VFS_INTERFACES_COMPLETE.md is missing tools: "
            f"{sorted(missing_bucket_vfs_tools)}"
        )

    dag_pb_proto_source = dag_pb_proto_path.read_text(encoding="utf-8")
    discovered_dag_pb_messages = tuple(
        sorted(set(re.findall(r"^message\s+([A-Za-z0-9_]+)", dag_pb_proto_source, flags=re.MULTILINE)))
    )
    missing_dag_pb_messages = set(REQUIRED_DAG_PB_MESSAGES) - set(discovered_dag_pb_messages)
    if missing_dag_pb_messages:
        raise SwissKnifeIPFSKitInteropError(
            f"ipfs_kit dag-pb.proto is missing messages: {sorted(missing_dag_pb_messages)}"
        )

    return IPFSKitMCPSchemaContract(
        root=str(root_path),
        fix_mcp_schema_paths=tuple(str(path) for path in fix_mcp_schema_full_paths),
        deprecations_report_schema_path=str(deprecations_report_schema_path),
        bucket_vfs_doc_path=str(bucket_vfs_doc_path),
        dag_pb_proto_path=str(dag_pb_proto_path),
        bucket_vfs_mcp_tools=discovered_bucket_vfs_tools,
        dag_pb_messages=discovered_dag_pb_messages,
        deprecations_report_required_keys=discovered_required_keys,
    )


def build_swissknife_ipfs_kit_handoff(
    ipfs_kit_root: str | Path,
    *,
    capability: str = "ipfs_kit.mcp_schema.bucket_vfs_handoff",
    payload: bytes | str | dict[str, Any] | None = None,
) -> SwissKnifeIPFSKitHandoff:
    """Build a deterministic ``external/ipfs_kit`` to SwissKnife handoff receipt."""
    contract = discover_ipfs_kit_mcp_schema_contract(ipfs_kit_root)

    payload_bytes = _payload_to_bytes(
        payload
        if payload is not None
        else {
            "source": "swissknife",
            "target": "external/ipfs_kit",
            "capability": capability,
            "route": "swissknife-ipfs-kit-mcp-schema-bucket-vfs",
            "bucket_vfs_mcp_tools": list(contract.bucket_vfs_mcp_tools),
            "dag_pb_messages": list(contract.dag_pb_messages),
        }
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return SwissKnifeIPFSKitHandoff(
        contract_id="swissknife.ipfs-kit-mcp-schema-interop@1",
        source_repository="swissknife",
        target_repository="external/ipfs_kit",
        interface_contract=INTERFACE_CONTRACT,
        goal_id=GOAL_ID,
        goal_packet=GOAL_PACKET,
        capability=capability,
        route="swissknife-ipfs-kit-mcp-schema-bucket-vfs",
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        bucket_vfs_mcp_tools=contract.bucket_vfs_mcp_tools,
        dag_pb_messages=contract.dag_pb_messages,
        required_swissknife_operations=REQUIRED_SWISSKNIFE_IPFS_KIT_OPERATIONS,
    )


def _payload_to_bytes(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
