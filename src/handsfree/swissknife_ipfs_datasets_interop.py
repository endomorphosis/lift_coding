"""Interop contract between SwissKnife and ``external/ipfs_datasets``.

MGW-571 repairs the VAIOS-G702 objective validation gap that requires
`swissknife` to interoperate with `external/ipfs_datasets` through importable
contracts, interface descriptors, runtime handoff behavior, and integration
tests. This is part of the shared
`goal_packet/interoperability/swissknife/06921590135c` packet covering
VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, and
VAIOS-G706.

`external/ipfs_datasets` vendors an `ipfs_kit_py` tool surface under
``.tools/ipfs_kit_py``. The stable interoperability evidence for SwissKnife is
the deprecations report JSON Schema, the Bucket VFS implementation summary,
the dependency-light Bucket VFS CLI/MCP demo, and the unified bucket interface
demo that exercises multi-backend bucket creation, content-addressed pins,
VFS composition, and cross-backend querying. This module statically discovers
those descriptors (without importing `external/ipfs_datasets` Python) and
builds a deterministic ``SwissKnifeIPFSDatasetsHandoff`` receipt that mirrors
the TypeScript descriptor in
``swissknife/src/services/mcp/ipfs-datasets-bucket-vfs-interop-descriptor.ts``.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

INTERFACE_CONTRACT = "interface contract swissknife external/ipfs_datasets"
GOAL_ID = "VAIOS-G702"
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

IPFS_DATASETS_TOOL_ROOT = ".tools/ipfs_kit_py"
REQUIRED_DEPRECATIONS_REPORT_SCHEMA_PATH = (
    ".tools/ipfs_kit_py/data/deprecations_report.schema.json"
)
REQUIRED_BUCKET_VFS_DOC_PATH = (
    ".tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md"
)
REQUIRED_BUCKET_VFS_DEMO_PATH = ".tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py"
BUCKET_VFS_DEMO_PATH_CANDIDATES = (
    REQUIRED_BUCKET_VFS_DEMO_PATH,
    ".tools/ipfs_kit_py/examples/demos/demo_bucket_vfs_interfaces.py",
    ".tools/ipfs_kit_py/reorganization_backup_root/demo_bucket_vfs_interfaces.py",
)
REQUIRED_UNIFIED_BUCKET_DEMO_PATH = (
    ".tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py"
)

REQUIRED_DEPRECATIONS_REPORT_KEYS = (
    "report_version",
    "generated_at",
    "deprecated",
    "summary",
    "policy",
    "raw",
)

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

REQUIRED_BUCKET_VFS_CLI_COMMANDS = (
    "create",
    "list",
    "delete",
    "add-file",
    "export",
    "query",
)

REQUIRED_UNIFIED_BUCKET_CLASSES = (
    "UnifiedBucketInterface",
    "BackendType",
    "BucketType",
    "VFSStructureType",
)

REQUIRED_UNIFIED_BUCKET_METHODS = (
    "initialize",
    "create_backend_bucket",
    "add_content_pin",
    "list_backend_buckets",
    "get_vfs_composition",
    "sync_bucket_indices",
    "query_across_backends",
)

REQUIRED_UNIFIED_BUCKET_BACKENDS = (
    "PARQUET",
    "ARROW",
    "S3",
    "SSHFS",
    "GDRIVE",
)

REQUIRED_SWISSKNIFE_IPFS_DATASETS_OPERATIONS = (
    "ipfs_datasets.bucket_vfs.create_bucket",
    "ipfs_datasets.bucket_vfs.add_file",
    "ipfs_datasets.bucket_vfs.export_car",
    "ipfs_datasets.bucket_vfs.cross_query",
    "ipfs_datasets.unified_bucket.create_backend_bucket",
    "ipfs_datasets.unified_bucket.sync_indices",
    "ipfs_datasets.deprecations.validate_report",
)


class SwissKnifeIPFSDatasetsInteropError(RuntimeError):
    """Raised when either side of the swissknife/ipfs_datasets contract is missing."""


@dataclass(frozen=True)
class IPFSDatasetsBucketVFSContract:
    """Static Bucket VFS and unified-bucket contract discovered from the submodule."""

    root: str
    tool_root: str
    deprecations_report_schema_path: str
    bucket_vfs_doc_path: str
    bucket_vfs_demo_path: str
    unified_bucket_demo_path: str
    deprecations_report_required_keys: tuple[str, ...]
    bucket_vfs_mcp_tools: tuple[str, ...]
    bucket_vfs_cli_commands: tuple[str, ...]
    demo_functions: tuple[str, ...]
    demo_classes: tuple[str, ...]
    unified_bucket_imports: tuple[str, ...]
    unified_bucket_methods: tuple[str, ...]
    unified_bucket_backends: tuple[str, ...]


@dataclass(frozen=True)
class SwissKnifeIPFSDatasetsHandoff:
    """Deterministic receipt for one Bucket VFS handoff routed to SwissKnife."""

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
    bucket_vfs_cli_commands: tuple[str, ...]
    unified_bucket_backends: tuple[str, ...]
    required_swissknife_operations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""
        return asdict(self)


def discover_ipfs_datasets_bucket_vfs_contract(
    root: str | Path,
) -> IPFSDatasetsBucketVFSContract:
    """Discover the Bucket VFS and unified bucket interface contract.

    Reads (without importing) the four scanner-visible descriptors that
    `external/ipfs_datasets` ships so SwissKnife can rely on a stable,
    statically-verifiable contract:

    - ``.tools/ipfs_kit_py/data/deprecations_report.schema.json``
    - ``.tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md``
    - ``.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py``
    - ``.tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py``
    """
    root_path = Path(root)
    if not root_path.exists():
        raise SwissKnifeIPFSDatasetsInteropError(
            f"ipfs_datasets root not found: {root_path}"
        )

    paths = {
        "deprecations_report_schema": root_path / REQUIRED_DEPRECATIONS_REPORT_SCHEMA_PATH,
        "bucket_vfs_doc": root_path / REQUIRED_BUCKET_VFS_DOC_PATH,
        "unified_bucket_demo": root_path / REQUIRED_UNIFIED_BUCKET_DEMO_PATH,
    }
    bucket_vfs_demo_path, bucket_vfs_demo_source = _select_nonempty_file(
        root_path, BUCKET_VFS_DEMO_PATH_CANDIDATES
    )
    paths["bucket_vfs_demo"] = bucket_vfs_demo_path

    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise SwissKnifeIPFSDatasetsInteropError(
            f"ipfs_datasets Bucket VFS descriptors missing: {missing}"
        )

    deprecations_report_schema = json.loads(
        paths["deprecations_report_schema"].read_text(encoding="utf-8")
    )
    discovered_required_keys = tuple(deprecations_report_schema.get("required", ()))
    missing_required_keys = set(REQUIRED_DEPRECATIONS_REPORT_KEYS) - set(
        discovered_required_keys
    )
    if missing_required_keys:
        raise SwissKnifeIPFSDatasetsInteropError(
            "ipfs_datasets deprecations_report.schema.json is missing required keys: "
            f"{sorted(missing_required_keys)}"
        )

    bucket_vfs_doc_source = paths["bucket_vfs_doc"].read_text(encoding="utf-8")
    discovered_doc_tools = tuple(
        sorted(set(re.findall(r"`(bucket_[a-z_]+)`", bucket_vfs_doc_source)))
    )
    missing_doc_tools = set(REQUIRED_BUCKET_VFS_MCP_TOOLS) - set(discovered_doc_tools)
    if missing_doc_tools:
        raise SwissKnifeIPFSDatasetsInteropError(
            "ipfs_datasets BUCKET_VFS_INTERFACES_COMPLETE.md is missing tools: "
            f"{sorted(missing_doc_tools)}"
        )

    bucket_vfs_demo_tree = ast.parse(
        bucket_vfs_demo_source,
        filename=str(paths["bucket_vfs_demo"]),
    )
    demo_functions = tuple(
        sorted(
            node.name
            for node in bucket_vfs_demo_tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
    )
    demo_classes = tuple(
        sorted(node.name for node in bucket_vfs_demo_tree.body if isinstance(node, ast.ClassDef))
    )
    demo_tools = _literal_tuple_assignment_or_symbols(
        bucket_vfs_demo_tree,
        "BUCKET_VFS_MCP_TOOLS",
        REQUIRED_BUCKET_VFS_MCP_TOOLS,
        bucket_vfs_demo_source,
    )
    demo_cli_commands = _literal_tuple_assignment_or_symbols(
        bucket_vfs_demo_tree,
        "BUCKET_VFS_CLI_COMMANDS",
        REQUIRED_BUCKET_VFS_CLI_COMMANDS,
        bucket_vfs_demo_source + "\n" + bucket_vfs_doc_source,
    )
    missing_demo_cli = set(REQUIRED_BUCKET_VFS_CLI_COMMANDS) - set(demo_cli_commands)
    if missing_demo_cli:
        raise SwissKnifeIPFSDatasetsInteropError(
            "ipfs_datasets demo_bucket_vfs_interfaces.py is missing expected "
            f"cli={sorted(missing_demo_cli)}"
        )
    if {"demo_cli_interface", "demo_mcp_api"} - set(demo_functions):
        raise SwissKnifeIPFSDatasetsInteropError(
            "ipfs_datasets demo_bucket_vfs_interfaces.py is missing demo functions"
        )

    unified_bucket_demo_tree = ast.parse(
        paths["unified_bucket_demo"].read_text(encoding="utf-8"),
        filename=str(paths["unified_bucket_demo"]),
    )
    unified_imports = _imported_names_from_module(
        unified_bucket_demo_tree, "ipfs_kit_py.unified_bucket_interface"
    )
    missing_unified_imports = set(REQUIRED_UNIFIED_BUCKET_CLASSES) - set(unified_imports)
    if missing_unified_imports:
        raise SwissKnifeIPFSDatasetsInteropError(
            "ipfs_datasets demo_unified_bucket_interface.py is missing imports: "
            f"{sorted(missing_unified_imports)}"
        )

    unified_demo_source = paths["unified_bucket_demo"].read_text(encoding="utf-8")
    missing_methods = [
        method
        for method in REQUIRED_UNIFIED_BUCKET_METHODS
        if f"interface.{method}(" not in unified_demo_source
    ]
    missing_backends = [
        backend
        for backend in REQUIRED_UNIFIED_BUCKET_BACKENDS
        if f"BackendType.{backend}" not in unified_demo_source
    ]
    if missing_methods or missing_backends:
        raise SwissKnifeIPFSDatasetsInteropError(
            "ipfs_datasets demo_unified_bucket_interface.py is missing expected "
            f"methods={missing_methods} backends={missing_backends}"
        )

    return IPFSDatasetsBucketVFSContract(
        root=str(root_path),
        tool_root=str(root_path / IPFS_DATASETS_TOOL_ROOT),
        deprecations_report_schema_path=str(paths["deprecations_report_schema"]),
        bucket_vfs_doc_path=str(paths["bucket_vfs_doc"]),
        bucket_vfs_demo_path=str(paths["bucket_vfs_demo"]),
        unified_bucket_demo_path=str(paths["unified_bucket_demo"]),
        deprecations_report_required_keys=discovered_required_keys,
        bucket_vfs_mcp_tools=tuple(sorted(set(demo_tools) | set(discovered_doc_tools))),
        bucket_vfs_cli_commands=tuple(demo_cli_commands),
        demo_functions=demo_functions,
        demo_classes=demo_classes,
        unified_bucket_imports=unified_imports,
        unified_bucket_methods=REQUIRED_UNIFIED_BUCKET_METHODS,
        unified_bucket_backends=REQUIRED_UNIFIED_BUCKET_BACKENDS,
    )


def build_swissknife_ipfs_datasets_handoff(
    ipfs_datasets_root: str | Path,
    *,
    capability: str = "ipfs_datasets.bucket_vfs.unified_bucket_handoff",
    payload: bytes | str | dict[str, Any] | None = None,
) -> SwissKnifeIPFSDatasetsHandoff:
    """Build a deterministic ``external/ipfs_datasets`` to SwissKnife handoff receipt."""
    contract = discover_ipfs_datasets_bucket_vfs_contract(ipfs_datasets_root)

    payload_bytes = _payload_to_bytes(
        payload
        if payload is not None
        else {
            "source": "swissknife",
            "target": "external/ipfs_datasets",
            "capability": capability,
            "route": "swissknife-ipfs-datasets-bucket-vfs",
            "bucket_vfs_mcp_tools": list(contract.bucket_vfs_mcp_tools),
            "unified_bucket_backends": list(contract.unified_bucket_backends),
        }
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return SwissKnifeIPFSDatasetsHandoff(
        contract_id="swissknife.ipfs-datasets-bucket-vfs-interop@1",
        source_repository="swissknife",
        target_repository="external/ipfs_datasets",
        interface_contract=INTERFACE_CONTRACT,
        goal_id=GOAL_ID,
        goal_packet=GOAL_PACKET,
        capability=capability,
        route="swissknife-ipfs-datasets-bucket-vfs",
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        bucket_vfs_mcp_tools=contract.bucket_vfs_mcp_tools,
        bucket_vfs_cli_commands=contract.bucket_vfs_cli_commands,
        unified_bucket_backends=contract.unified_bucket_backends,
        required_swissknife_operations=REQUIRED_SWISSKNIFE_IPFS_DATASETS_OPERATIONS,
    )


def _payload_to_bytes(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _select_nonempty_file(root_path: Path, candidates: tuple[str, ...]) -> tuple[Path, str]:
    existing: list[tuple[Path, str]] = []
    for candidate in candidates:
        path = root_path / candidate
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        if source.strip():
            return path, source
        existing.append((path, source))

    if existing:
        return existing[0]

    return root_path / candidates[0], ""


def _literal_tuple_assignment(tree: ast.Module, name: str) -> tuple[str, ...]:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        if not isinstance(node.value, (ast.Tuple, ast.List)):
            break
        values = []
        for element in node.value.elts:
            if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
                break
            values.append(element.value)
        else:
            return tuple(values)
    raise SwissKnifeIPFSDatasetsInteropError(f"missing literal assignment for {name}")


def _literal_tuple_assignment_or_symbols(
    tree: ast.Module,
    name: str,
    candidates: tuple[str, ...],
    source: str,
) -> tuple[str, ...]:
    try:
        return _literal_tuple_assignment(tree, name)
    except SwissKnifeIPFSDatasetsInteropError:
        return tuple(symbol for symbol in candidates if symbol in source)


def _imported_names_from_module(tree: ast.Module, module: str) -> tuple[str, ...]:
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            imported_names.update(alias.name for alias in node.names)
    return tuple(sorted(imported_names))
