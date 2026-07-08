"""Interop contract for ``external/meta-wearables-dat-android`` and ``external/ipfs_datasets``.

HAO-738 repairs the VAIOS-G710 objective validation gap by proving that the
Meta Wearables DAT Android Display/session surface can hand off glasses-side
events and display payload metadata into the ipfs_datasets dataset/IPFS storage
surface. The proof is intentionally static and deterministic: it validates
source-tree descriptors, JSON schemas, Bucket VFS interfaces, router entrypoints,
and then emits a content-addressed handoff receipt without requiring Android,
Kotlin, Kubo, DuckDB, or live network services.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

INTERFACE_CONTRACT = "interface contract external/meta-wearables-dat-android external/ipfs_datasets"
GOAL_ID = "VAIOS-G710"
GOAL_PACKET = "goal_packet/interoperability/external/6595cbbfadb9"
GOAL_PACKET_GOALS = ("VAIOS-G709", "VAIOS-G710", "VAIOS-G711")

REQUIRED_DISPLAY_ACCESS_DOC_PATH = ".cursor/rules/display-access.mdc"
REQUIRED_SESSION_LIFECYCLE_DOC_PATH = ".cursor/rules/session-lifecycle.mdc"
REQUIRED_PERMISSIONS_REGISTRATION_DOC_PATH = ".cursor/rules/permissions-registration.mdc"
REQUIRED_DISPLAY_MANIFEST_PATH = "samples/DisplayAccess/app/src/main/AndroidManifest.xml"
REQUIRED_DISPLAY_VIEW_MODEL_PATH = (
    "samples/DisplayAccess/app/src/main/java/com/meta/wearable/dat/"
    "externalsampleapps/displayaccess/display/DisplayViewModel.kt"
)

REQUIRED_DEVICE_SESSION_STATES = (
    "IDLE",
    "STARTING",
    "STARTED",
    "PAUSED",
    "STOPPING",
    "STOPPED",
)
REQUIRED_MANIFEST_METADATA_KEYS = (
    "com.meta.wearable.mwdat.APPLICATION_ID",
    "com.meta.wearable.mwdat.CLIENT_TOKEN",
)
REQUIRED_MANIFEST_PERMISSIONS = (
    "android.permission.BLUETOOTH",
    "android.permission.BLUETOOTH_CONNECT",
    "android.permission.INTERNET",
)
REQUIRED_DISPLAY_ICON_NAMES = (
    "CHECKMARK",
    "TRIANGLE_LEFT_VERTICAL_LINE",
    "TRIANGLE_RIGHT_VERTICAL_LINE",
    "VIDEO_CAMERA",
)
REQUIRED_DISPLAY_BUTTON_STYLES = ("PRIMARY", "SECONDARY")

IPFS_KIT_TOOL_ROOT = ".tools/ipfs_kit_py"
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
REQUIRED_UNIFIED_BUCKET_DEMO_PATH = ".tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py"
REQUIRED_SCHEMA_COLUMN_OPTIMIZATION_EXAMPLE_PATH = (
    ".tools/ipfs_kit_py/examples/schema_column_optimization_example.py"
)
REQUIRED_IPFS_BACKEND_ROUTER_PATH = "ipfs_datasets_py/ipfs_backend_router.py"
REQUIRED_EMBEDDINGS_ROUTER_PATH = "ipfs_datasets_py/embeddings_router.py"
REQUIRED_LLM_ROUTER_PATH = "ipfs_datasets_py/llm_router.py"

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
REQUIRED_BUCKET_TYPES = ("GENERAL", "DATASET", "KNOWLEDGE", "MEDIA", "ARCHIVE", "TEMP")
REQUIRED_VFS_STRUCTURE_TYPES = ("UNIXFS", "GRAPH", "VECTOR", "HYBRID")
REQUIRED_UNIFIED_BACKENDS = ("PARQUET", "ARROW", "S3", "SSHFS", "GDRIVE")
REQUIRED_IPFS_DATASETS_ROUTER_SYMBOLS = (
    "register_ipfs_backend",
    "add_bytes",
    "cat",
    "embed_text",
    "generate_text",
)
REQUIRED_HANDOFF_OPERATIONS = (
    "meta_wearables_dat_android.session.start",
    "meta_wearables_dat_android.display.send_content",
    "ipfs_datasets.ipfs_backend_router.add_bytes",
    "ipfs_datasets.ipfs_backend_router.cat",
    "ipfs_datasets.bucket_vfs.bucket_create",
    "ipfs_datasets.bucket_vfs.bucket_add_file",
    "ipfs_datasets.bucket_vfs.bucket_export_car",
    "ipfs_datasets.bucket_vfs.bucket_cross_query",
)


class MetaWearablesDATAndroidIPFSDatasetsInteropError(RuntimeError):
    """Raised when the meta-wearables-dat-android/ipfs_datasets contract drifts."""


@dataclass(frozen=True)
class MetaWearablesDATAndroidContract:
    """Static Display/session contract discovered from the Android DAT tree."""

    root: str
    display_access_doc_path: str
    session_lifecycle_doc_path: str
    permissions_registration_doc_path: str
    display_manifest_path: str
    display_view_model_path: str
    device_session_states: tuple[str, ...]
    manifest_metadata_keys: tuple[str, ...]
    manifest_permissions: tuple[str, ...]
    display_icon_names: tuple[str, ...]
    display_button_styles: tuple[str, ...]


@dataclass(frozen=True)
class IPFSDatasetsBucketVFSContract:
    """Static Bucket VFS/router contract discovered from the ipfs_datasets tree."""

    root: str
    ipfs_kit_tool_root: str
    deprecations_report_schema_path: str
    bucket_vfs_doc_path: str
    bucket_vfs_demo_path: str
    unified_bucket_demo_path: str
    schema_column_optimization_example_path: str
    ipfs_backend_router_path: str
    embeddings_router_path: str
    llm_router_path: str
    deprecations_report_required_keys: tuple[str, ...]
    bucket_vfs_mcp_tools: tuple[str, ...]
    bucket_vfs_cli_commands: tuple[str, ...]
    bucket_types: tuple[str, ...]
    vfs_structure_types: tuple[str, ...]
    unified_backends: tuple[str, ...]
    router_symbols: tuple[str, ...]


@dataclass(frozen=True)
class MetaWearablesDATAndroidIPFSDatasetsHandoff:
    """Deterministic receipt for routing one DAT Android display event into ipfs_datasets."""

    contract_id: str
    source_repository: str
    target_repository: str
    interface_contract: str
    goal_id: str
    goal_packet: str
    goal_packet_goals: tuple[str, ...]
    capability: str
    route: str
    dataset_bucket: str
    dataset_vfs_path: str
    content_cid: str
    payload_sha256: str
    payload_size_bytes: int
    device_session_states: tuple[str, ...]
    display_icon_names: tuple[str, ...]
    display_button_styles: tuple[str, ...]
    bucket_vfs_mcp_tools: tuple[str, ...]
    bucket_vfs_cli_commands: tuple[str, ...]
    bucket_types: tuple[str, ...]
    vfs_structure_types: tuple[str, ...]
    unified_backends: tuple[str, ...]
    required_handoff_operations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""

        return asdict(self)


def discover_meta_wearables_dat_android_contract(
    root: str | Path,
) -> MetaWearablesDATAndroidContract:
    """Discover the Meta Wearables DAT Android Display/session descriptors."""

    root_path = Path(root)
    if not root_path.exists():
        raise MetaWearablesDATAndroidIPFSDatasetsInteropError(
            f"meta-wearables-dat-android root not found: {root_path}"
        )

    display_access_doc_path = root_path / REQUIRED_DISPLAY_ACCESS_DOC_PATH
    session_lifecycle_doc_path = root_path / REQUIRED_SESSION_LIFECYCLE_DOC_PATH
    permissions_registration_doc_path = root_path / REQUIRED_PERMISSIONS_REGISTRATION_DOC_PATH
    display_manifest_path = root_path / REQUIRED_DISPLAY_MANIFEST_PATH
    display_view_model_path = root_path / REQUIRED_DISPLAY_VIEW_MODEL_PATH

    _require_files(
        "meta-wearables-dat-android Display descriptors",
        (
            display_access_doc_path,
            session_lifecycle_doc_path,
            permissions_registration_doc_path,
            display_manifest_path,
            display_view_model_path,
        ),
    )

    display_access_source = display_access_doc_path.read_text(encoding="utf-8")
    _require_symbols(
        display_access_source,
        (
            "Wearables.createSession",
            "addDisplay",
            "sendContent",
            "flexBox",
            "DisplayState.STARTED",
        ),
        "meta-wearables-dat-android display-access.mdc",
    )

    permissions_registration_source = permissions_registration_doc_path.read_text(
        encoding="utf-8"
    )
    _require_symbols(
        permissions_registration_source,
        (
            "Wearables.startRegistration",
            "checkPermissionStatus",
            "RequestPermissionContract",
            "PermissionStatus.Granted",
        ),
        "meta-wearables-dat-android permissions-registration.mdc",
    )

    session_lifecycle_source = session_lifecycle_doc_path.read_text(encoding="utf-8")
    discovered_session_states = tuple(
        sorted(set(re.findall(r"`([A-Z]+)`\s*\|", session_lifecycle_source)))
    )
    _require_subset(
        REQUIRED_DEVICE_SESSION_STATES,
        discovered_session_states,
        "meta-wearables-dat-android session-lifecycle.mdc states",
    )

    manifest_source = display_manifest_path.read_text(encoding="utf-8")
    discovered_metadata_keys = tuple(
        sorted(
            name
            for name in set(re.findall(r'android:name="([^"]+)"', manifest_source))
            if name.startswith("com.meta.wearable.mwdat.")
        )
    )
    _require_subset(
        REQUIRED_MANIFEST_METADATA_KEYS,
        discovered_metadata_keys,
        "meta-wearables-dat-android AndroidManifest.xml metadata keys",
    )

    discovered_permissions = tuple(
        sorted(set(re.findall(r'uses-permission android:name="([^"]+)"', manifest_source)))
    )
    _require_subset(
        REQUIRED_MANIFEST_PERMISSIONS,
        discovered_permissions,
        "meta-wearables-dat-android AndroidManifest.xml permissions",
    )

    view_model_source = display_view_model_path.read_text(encoding="utf-8")
    discovered_icon_names = tuple(sorted(set(re.findall(r"IconName\.([A-Z_]+)", view_model_source))))
    _require_subset(
        REQUIRED_DISPLAY_ICON_NAMES,
        discovered_icon_names,
        "meta-wearables-dat-android DisplayViewModel.kt icon names",
    )

    discovered_button_styles = tuple(
        sorted(set(re.findall(r"ButtonStyle\.([A-Z_]+)", view_model_source)))
    )
    _require_subset(
        REQUIRED_DISPLAY_BUTTON_STYLES,
        discovered_button_styles,
        "meta-wearables-dat-android DisplayViewModel.kt button styles",
    )

    return MetaWearablesDATAndroidContract(
        root=str(root_path),
        display_access_doc_path=str(display_access_doc_path),
        session_lifecycle_doc_path=str(session_lifecycle_doc_path),
        permissions_registration_doc_path=str(permissions_registration_doc_path),
        display_manifest_path=str(display_manifest_path),
        display_view_model_path=str(display_view_model_path),
        device_session_states=discovered_session_states,
        manifest_metadata_keys=discovered_metadata_keys,
        manifest_permissions=discovered_permissions,
        display_icon_names=discovered_icon_names,
        display_button_styles=discovered_button_styles,
    )


def discover_ipfs_datasets_bucket_vfs_contract(
    root: str | Path,
) -> IPFSDatasetsBucketVFSContract:
    """Discover the ipfs_datasets Bucket VFS and router descriptors."""

    root_path = Path(root)
    if not root_path.exists():
        raise MetaWearablesDATAndroidIPFSDatasetsInteropError(
            f"ipfs_datasets root not found: {root_path}"
        )

    ipfs_kit_tool_root = root_path / IPFS_KIT_TOOL_ROOT
    deprecations_report_schema_path = root_path / REQUIRED_DEPRECATIONS_REPORT_SCHEMA_PATH
    bucket_vfs_doc_path = root_path / REQUIRED_BUCKET_VFS_DOC_PATH
    bucket_vfs_demo_path, bucket_vfs_demo_source = _select_nonempty_file(
        root_path, BUCKET_VFS_DEMO_PATH_CANDIDATES
    )
    unified_bucket_demo_path = root_path / REQUIRED_UNIFIED_BUCKET_DEMO_PATH
    schema_column_optimization_example_path = (
        root_path / REQUIRED_SCHEMA_COLUMN_OPTIMIZATION_EXAMPLE_PATH
    )
    ipfs_backend_router_path = root_path / REQUIRED_IPFS_BACKEND_ROUTER_PATH
    embeddings_router_path = root_path / REQUIRED_EMBEDDINGS_ROUTER_PATH
    llm_router_path = root_path / REQUIRED_LLM_ROUTER_PATH

    _require_files(
        "ipfs_datasets Bucket VFS/router descriptors",
        (
            deprecations_report_schema_path,
            bucket_vfs_doc_path,
            bucket_vfs_demo_path,
            unified_bucket_demo_path,
            schema_column_optimization_example_path,
            ipfs_backend_router_path,
            embeddings_router_path,
            llm_router_path,
        ),
    )

    deprecations_report_schema = json.loads(
        deprecations_report_schema_path.read_text(encoding="utf-8")
    )
    discovered_required_keys = tuple(deprecations_report_schema.get("required", ()))
    _require_subset(
        REQUIRED_DEPRECATIONS_REPORT_KEYS,
        discovered_required_keys,
        "ipfs_datasets .tools/ipfs_kit_py deprecations report schema required keys",
    )

    bucket_vfs_doc_source = bucket_vfs_doc_path.read_text(encoding="utf-8")
    discovered_bucket_vfs_tools = tuple(
        sorted(set(re.findall(r"`(bucket_[a-z_]+)`", bucket_vfs_doc_source)))
    )
    _require_subset(
        REQUIRED_BUCKET_VFS_MCP_TOOLS,
        discovered_bucket_vfs_tools,
        "ipfs_datasets Bucket VFS MCP tools",
    )
    _require_symbols(
        bucket_vfs_doc_source,
        (
            "CLI Interface (`ipfs_kit_py/bucket_vfs_cli.py`)",
            "MCP API Interface (`mcp/bucket_vfs_mcp_tools.py`)",
            "Enhanced MCP Server Integration (`mcp/enhanced_integrated_mcp_server.py`)",
            "S3-like Bucket Semantics",
            "IPLD Compatibility",
            "Analytics Integration",
        ),
        "ipfs_datasets Bucket VFS implementation summary",
    )

    _require_symbols(
        bucket_vfs_demo_source,
        ("demo_cli_interface", "demo_mcp_api", "bucket_export_car", "bucket_cross_query"),
        "ipfs_datasets demo_bucket_vfs_interfaces.py",
    )

    unified_bucket_demo_source = unified_bucket_demo_path.read_text(encoding="utf-8")
    discovered_unified_backends = tuple(
        sorted(set(re.findall(r"BackendType\.([A-Z0-9_]+)", unified_bucket_demo_source)))
    )
    _require_subset(
        REQUIRED_UNIFIED_BACKENDS,
        discovered_unified_backends,
        "ipfs_datasets unified bucket backend demo",
    )

    tool_interface_source = (
        bucket_vfs_doc_source
        + "\n"
        + bucket_vfs_demo_source
        + "\n"
        + unified_bucket_demo_source
        + "\n"
        + (ipfs_kit_tool_root / "ipfs_kit_py/unified_bucket_interface.py").read_text(
            encoding="utf-8"
        )
    )
    _require_subset(
        REQUIRED_BUCKET_VFS_CLI_COMMANDS,
        tuple(sorted(set(re.findall(r"\b(create|list|delete|add-file|export|query)\b", tool_interface_source)))),
        "ipfs_datasets Bucket VFS CLI commands",
    )
    _require_subset(
        REQUIRED_BUCKET_TYPES,
        tuple(symbol for symbol in REQUIRED_BUCKET_TYPES if symbol in tool_interface_source),
        "ipfs_datasets BucketType values",
    )
    _require_subset(
        REQUIRED_VFS_STRUCTURE_TYPES,
        tuple(symbol for symbol in REQUIRED_VFS_STRUCTURE_TYPES if symbol in tool_interface_source),
        "ipfs_datasets VFSStructureType values",
    )

    router_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ipfs_backend_router_path, embeddings_router_path, llm_router_path)
    )
    discovered_router_symbols = tuple(
        symbol for symbol in REQUIRED_IPFS_DATASETS_ROUTER_SYMBOLS if symbol in router_sources
    )
    _require_subset(
        REQUIRED_IPFS_DATASETS_ROUTER_SYMBOLS,
        discovered_router_symbols,
        "ipfs_datasets router symbols",
    )

    return IPFSDatasetsBucketVFSContract(
        root=str(root_path),
        ipfs_kit_tool_root=str(ipfs_kit_tool_root),
        deprecations_report_schema_path=str(deprecations_report_schema_path),
        bucket_vfs_doc_path=str(bucket_vfs_doc_path),
        bucket_vfs_demo_path=str(bucket_vfs_demo_path),
        unified_bucket_demo_path=str(unified_bucket_demo_path),
        schema_column_optimization_example_path=str(schema_column_optimization_example_path),
        ipfs_backend_router_path=str(ipfs_backend_router_path),
        embeddings_router_path=str(embeddings_router_path),
        llm_router_path=str(llm_router_path),
        deprecations_report_required_keys=discovered_required_keys,
        bucket_vfs_mcp_tools=discovered_bucket_vfs_tools,
        bucket_vfs_cli_commands=REQUIRED_BUCKET_VFS_CLI_COMMANDS,
        bucket_types=REQUIRED_BUCKET_TYPES,
        vfs_structure_types=REQUIRED_VFS_STRUCTURE_TYPES,
        unified_backends=discovered_unified_backends,
        router_symbols=discovered_router_symbols,
    )


def build_meta_wearables_dat_android_ipfs_datasets_handoff(
    meta_wearables_dat_android_root: str | Path,
    ipfs_datasets_root: str | Path,
    *,
    capability: str = "meta_wearables_dat_android.display.ipfs_datasets_bucket_handoff",
    dataset_bucket: str = "meta-wearables-dat-android-display-events",
    dataset_vfs_path: str = "/wearables/meta/dat/android/display/events/latest.json",
    payload: bytes | str | dict[str, Any] | None = None,
) -> MetaWearablesDATAndroidIPFSDatasetsHandoff:
    """Build a deterministic Display-event to ipfs_datasets handoff receipt."""

    meta_contract = discover_meta_wearables_dat_android_contract(
        meta_wearables_dat_android_root
    )
    datasets_contract = discover_ipfs_datasets_bucket_vfs_contract(ipfs_datasets_root)

    payload_bytes = _payload_to_bytes(
        payload
        if payload is not None
        else {
            "source": "external/meta-wearables-dat-android",
            "target": "external/ipfs_datasets",
            "capability": capability,
            "route": "meta-wearables-dat-android-display-to-ipfs-datasets-bucket-vfs",
            "dataset_bucket": dataset_bucket,
            "dataset_vfs_path": dataset_vfs_path,
            "display_event": {
                "session_state": "STARTED",
                "content_kind": "flexBox",
                "icon_name": "CHECKMARK",
                "button_style": "PRIMARY",
            },
            "storage": {
                "router": "ipfs_datasets_py.ipfs_backend_router",
                "bucket_tools": list(datasets_contract.bucket_vfs_mcp_tools),
                "vfs_structure": "HYBRID",
                "backend": "IPFS",
            },
        }
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return MetaWearablesDATAndroidIPFSDatasetsHandoff(
        contract_id="external.meta-wearables-dat-android.ipfs-datasets-interop@1",
        source_repository="external/meta-wearables-dat-android",
        target_repository="external/ipfs_datasets",
        interface_contract=INTERFACE_CONTRACT,
        goal_id=GOAL_ID,
        goal_packet=GOAL_PACKET,
        goal_packet_goals=GOAL_PACKET_GOALS,
        capability=capability,
        route="meta-wearables-dat-android-display-to-ipfs-datasets-bucket-vfs",
        dataset_bucket=dataset_bucket,
        dataset_vfs_path=dataset_vfs_path,
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        device_session_states=meta_contract.device_session_states,
        display_icon_names=meta_contract.display_icon_names,
        display_button_styles=meta_contract.display_button_styles,
        bucket_vfs_mcp_tools=datasets_contract.bucket_vfs_mcp_tools,
        bucket_vfs_cli_commands=datasets_contract.bucket_vfs_cli_commands,
        bucket_types=datasets_contract.bucket_types,
        vfs_structure_types=datasets_contract.vfs_structure_types,
        unified_backends=datasets_contract.unified_backends,
        required_handoff_operations=REQUIRED_HANDOFF_OPERATIONS,
    )


def _require_files(label: str, paths: tuple[Path, ...]) -> None:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise MetaWearablesDATAndroidIPFSDatasetsInteropError(
            f"{label} missing: {missing}"
        )


def _require_symbols(source: str, symbols: tuple[str, ...], label: str) -> None:
    missing = [symbol for symbol in symbols if symbol not in source]
    if missing:
        raise MetaWearablesDATAndroidIPFSDatasetsInteropError(
            f"{label} is missing symbols: {missing}"
        )


def _require_subset(required: tuple[str, ...], discovered: tuple[Any, ...], label: str) -> None:
    normalized: set[str] = set()
    for item in discovered:
        if isinstance(item, tuple):
            normalized.update(str(part) for part in item if part)
        elif item:
            normalized.add(str(item))
    missing = set(required) - normalized
    if missing:
        raise MetaWearablesDATAndroidIPFSDatasetsInteropError(
            f"{label} missing: {sorted(missing)}"
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
