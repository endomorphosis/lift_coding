"""Interop contract for ``external/meta-wearables-dat-android`` and ``external/ipfs_kit``.

VAI-670 repairs the VAIOS-G711 objective validation gap by proving that the
Meta Wearables DAT Android Display/session surface can hand glasses display
events to the ipfs_kit Bucket VFS, MCP schema, deprecations-report, and DAG-PB
surfaces. The proof is static and deterministic: it validates source-tree
descriptors and emits a content-addressed handoff receipt without requiring
Android hardware, Kubo, or a live MCP server.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

INTERFACE_CONTRACT = "interface contract external/meta-wearables-dat-android external/ipfs_kit"
TASK_ID = "VAI-670"
GOAL_ID = "VAIOS-G711"
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

REQUIRED_FIX_MCP_SCHEMA_PATHS = (
    "archive/archive_clutter/fix_scripts/fix_mcp_schema.py",
    "backup/archive_clutter/fix_scripts/fix_mcp_schema.py",
    "backup/patches/fixes/fix_mcp_schema.py",
)
REQUIRED_DEPRECATIONS_REPORT_SCHEMA_PATH = "data/deprecations_report.schema.json"
REQUIRED_BUCKET_VFS_DOC_PATH = "docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md"
REQUIRED_DAG_PB_PROTO_PATH = "docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto"
REQUIRED_BUCKET_VFS_CLI_PATH = "ipfs_kit_py/bucket_vfs_cli.py"
REQUIRED_BUCKET_VFS_MCP_TOOLS_PATH = "mcp/bucket_vfs_mcp_tools.py"
REQUIRED_ENHANCED_MCP_SERVER_PATH = "ipfs_kit_py/mcp/servers/enhanced_integrated_mcp_server.py"
REQUIRED_BUCKET_VFS_MANAGER_PATH = "ipfs_kit_py/bucket_vfs_manager.py"

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
REQUIRED_DAG_PB_MESSAGES = ("PBLink", "PBNode")

REQUIRED_HANDOFF_OPERATIONS = (
    "meta_wearables_dat_android.session.start",
    "meta_wearables_dat_android.display.send_content",
    "ipfs_kit.mcp_schema.fix_servers_schema",
    "ipfs_kit.mcp_schema.validate_deprecations_report",
    "ipfs_kit.bucket_vfs.bucket_create",
    "ipfs_kit.bucket_vfs.bucket_add_file",
    "ipfs_kit.bucket_vfs.bucket_export_car",
    "ipfs_kit.bucket_vfs.bucket_cross_query",
    "ipfs_kit.dag_pb.encode_node",
    "ipfs_kit.dag_pb.decode_node",
)


class MetaWearablesDATAndroidIPFSKitInteropError(RuntimeError):
    """Raised when either side of the DAT Android/ipfs_kit contract drifts."""


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
class IPFSKitBucketVFSContract:
    """Static Bucket VFS/MCP/DAG-PB contract discovered from ipfs_kit."""

    root: str
    fix_mcp_schema_paths: tuple[str, ...]
    deprecations_report_schema_path: str
    bucket_vfs_doc_path: str
    dag_pb_proto_path: str
    bucket_vfs_cli_path: str
    bucket_vfs_mcp_tools_path: str
    enhanced_mcp_server_path: str
    bucket_vfs_manager_path: str
    deprecations_report_required_keys: tuple[str, ...]
    bucket_vfs_mcp_tools: tuple[str, ...]
    bucket_vfs_cli_commands: tuple[str, ...]
    bucket_types: tuple[str, ...]
    vfs_structure_types: tuple[str, ...]
    dag_pb_messages: tuple[str, ...]


@dataclass(frozen=True)
class MetaWearablesDATAndroidIPFSKitHandoff:
    """Deterministic receipt for routing one Android DAT display event to ipfs_kit."""

    contract_id: str
    source_repository: str
    target_repository: str
    interface_contract: str
    task_id: str
    goal_id: str
    goal_packet: str
    goal_packet_goals: tuple[str, ...]
    capability: str
    route: str
    bucket_name: str
    bucket_vfs_path: str
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
    dag_pb_messages: tuple[str, ...]
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
        raise MetaWearablesDATAndroidIPFSKitInteropError(
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


def discover_ipfs_kit_bucket_vfs_contract(root: str | Path) -> IPFSKitBucketVFSContract:
    """Discover ipfs_kit Bucket VFS, MCP schema, deprecations, and DAG-PB descriptors."""

    root_path = Path(root)
    if not root_path.exists():
        raise MetaWearablesDATAndroidIPFSKitInteropError(
            f"ipfs_kit root not found: {root_path}"
        )

    fix_mcp_schema_paths = tuple(root_path / rel for rel in REQUIRED_FIX_MCP_SCHEMA_PATHS)
    deprecations_report_schema_path = root_path / REQUIRED_DEPRECATIONS_REPORT_SCHEMA_PATH
    bucket_vfs_doc_path = root_path / REQUIRED_BUCKET_VFS_DOC_PATH
    dag_pb_proto_path = root_path / REQUIRED_DAG_PB_PROTO_PATH
    bucket_vfs_cli_path = root_path / REQUIRED_BUCKET_VFS_CLI_PATH
    bucket_vfs_mcp_tools_path = root_path / REQUIRED_BUCKET_VFS_MCP_TOOLS_PATH
    enhanced_mcp_server_path = root_path / REQUIRED_ENHANCED_MCP_SERVER_PATH
    bucket_vfs_manager_path = root_path / REQUIRED_BUCKET_VFS_MANAGER_PATH

    _require_files(
        "ipfs_kit Bucket VFS/MCP/DAG-PB descriptors",
        (
            *fix_mcp_schema_paths,
            deprecations_report_schema_path,
            bucket_vfs_doc_path,
            dag_pb_proto_path,
            bucket_vfs_cli_path,
            bucket_vfs_mcp_tools_path,
            enhanced_mcp_server_path,
            bucket_vfs_manager_path,
        ),
    )

    for fix_script_path in fix_mcp_schema_paths:
        fix_script_source = fix_script_path.read_text(encoding="utf-8")
        _require_symbols(
            fix_script_source,
            ("def fix_mcp_schema(", "mcpServers", "json.load", "json.dump"),
            f"ipfs_kit MCP schema fix script {fix_script_path}",
        )

    deprecations_report_schema = json.loads(
        deprecations_report_schema_path.read_text(encoding="utf-8")
    )
    discovered_required_keys = tuple(deprecations_report_schema.get("required", ()))
    _require_subset(
        REQUIRED_DEPRECATIONS_REPORT_KEYS,
        discovered_required_keys,
        "ipfs_kit deprecations report schema required keys",
    )

    bucket_vfs_doc_source = bucket_vfs_doc_path.read_text(encoding="utf-8")
    discovered_bucket_vfs_tools = tuple(
        sorted(set(re.findall(r"`(bucket_[a-z_]+)`", bucket_vfs_doc_source)))
    )
    _require_subset(
        REQUIRED_BUCKET_VFS_MCP_TOOLS,
        discovered_bucket_vfs_tools,
        "ipfs_kit Bucket VFS MCP tools",
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
        "ipfs_kit Bucket VFS implementation summary",
    )

    bucket_vfs_cli_source = bucket_vfs_cli_path.read_text(encoding="utf-8")
    discovered_cli_commands = tuple(
        sorted(
            set(
                re.findall(
                    r'add_parser\(\s*"([^"]+)"',
                    bucket_vfs_cli_source,
                )
            )
        )
    )
    _require_subset(
        REQUIRED_BUCKET_VFS_CLI_COMMANDS,
        discovered_cli_commands,
        "ipfs_kit Bucket VFS CLI commands",
    )

    bucket_vfs_mcp_tools_source = bucket_vfs_mcp_tools_path.read_text(encoding="utf-8")
    _require_symbols(
        bucket_vfs_mcp_tools_source,
        (
            "create_bucket_tools",
            "handle_bucket_create",
            "handle_bucket_list",
            "handle_bucket_add_file",
            "handle_bucket_cross_query",
            "handle_bucket_export_car",
        ),
        "ipfs_kit bucket_vfs_mcp_tools.py",
    )

    enhanced_mcp_server_source = enhanced_mcp_server_path.read_text(encoding="utf-8")
    _require_symbols(
        enhanced_mcp_server_source,
        ("create_bucket_tools", "bucket_tools", "BUCKET_VFS_AVAILABLE"),
        "ipfs_kit enhanced_integrated_mcp_server.py",
    )

    bucket_vfs_manager_source = bucket_vfs_manager_path.read_text(encoding="utf-8")
    discovered_bucket_types = tuple(
        sorted(set(re.findall(r"^\s+([A-Z]+)\s*=", bucket_vfs_manager_source, flags=re.MULTILINE)))
    )
    _require_subset(
        REQUIRED_BUCKET_TYPES,
        discovered_bucket_types,
        "ipfs_kit BucketType values",
    )
    _require_subset(
        REQUIRED_VFS_STRUCTURE_TYPES,
        discovered_bucket_types,
        "ipfs_kit VFSStructureType values",
    )

    dag_pb_proto_source = dag_pb_proto_path.read_text(encoding="utf-8")
    discovered_dag_pb_messages = tuple(
        sorted(set(re.findall(r"^message\s+([A-Za-z0-9_]+)", dag_pb_proto_source, flags=re.MULTILINE)))
    )
    _require_subset(
        REQUIRED_DAG_PB_MESSAGES,
        discovered_dag_pb_messages,
        "ipfs_kit dag-pb.proto messages",
    )

    return IPFSKitBucketVFSContract(
        root=str(root_path),
        fix_mcp_schema_paths=tuple(str(path) for path in fix_mcp_schema_paths),
        deprecations_report_schema_path=str(deprecations_report_schema_path),
        bucket_vfs_doc_path=str(bucket_vfs_doc_path),
        dag_pb_proto_path=str(dag_pb_proto_path),
        bucket_vfs_cli_path=str(bucket_vfs_cli_path),
        bucket_vfs_mcp_tools_path=str(bucket_vfs_mcp_tools_path),
        enhanced_mcp_server_path=str(enhanced_mcp_server_path),
        bucket_vfs_manager_path=str(bucket_vfs_manager_path),
        deprecations_report_required_keys=discovered_required_keys,
        bucket_vfs_mcp_tools=discovered_bucket_vfs_tools,
        bucket_vfs_cli_commands=discovered_cli_commands,
        bucket_types=tuple(symbol for symbol in REQUIRED_BUCKET_TYPES if symbol in discovered_bucket_types),
        vfs_structure_types=tuple(
            symbol for symbol in REQUIRED_VFS_STRUCTURE_TYPES if symbol in discovered_bucket_types
        ),
        dag_pb_messages=discovered_dag_pb_messages,
    )


def build_meta_wearables_dat_android_ipfs_kit_handoff(
    meta_wearables_dat_android_root: str | Path,
    ipfs_kit_root: str | Path,
    *,
    capability: str = "meta_wearables_dat_android.display.ipfs_kit_bucket_vfs_handoff",
    bucket_name: str = "meta-wearables-dat-android-display-events",
    bucket_vfs_path: str = "/wearables/meta/dat/android/display/events/latest.json",
    payload: bytes | str | dict[str, Any] | None = None,
) -> MetaWearablesDATAndroidIPFSKitHandoff:
    """Build a deterministic Android DAT display-event to ipfs_kit handoff receipt."""

    meta_contract = discover_meta_wearables_dat_android_contract(
        meta_wearables_dat_android_root
    )
    ipfs_kit_contract = discover_ipfs_kit_bucket_vfs_contract(ipfs_kit_root)

    payload_bytes = _payload_to_bytes(
        payload
        if payload is not None
        else {
            "source": "external/meta-wearables-dat-android",
            "target": "external/ipfs_kit",
            "capability": capability,
            "route": "meta-wearables-dat-android-display-to-ipfs-kit-bucket-vfs",
            "bucket_name": bucket_name,
            "bucket_vfs_path": bucket_vfs_path,
            "display_event": {
                "session_state": "STARTED",
                "content_kind": "flexBox",
                "icon_name": "CHECKMARK",
                "button_style": "PRIMARY",
            },
            "ipfs_kit": {
                "mcp_schema_repair": "fix_mcp_schema",
                "bucket_tools": list(ipfs_kit_contract.bucket_vfs_mcp_tools),
                "dag_pb_messages": list(ipfs_kit_contract.dag_pb_messages),
                "vfs_structure": "HYBRID",
            },
        }
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return MetaWearablesDATAndroidIPFSKitHandoff(
        contract_id="external.meta-wearables-dat-android.ipfs-kit-interop@1",
        source_repository="external/meta-wearables-dat-android",
        target_repository="external/ipfs_kit",
        interface_contract=INTERFACE_CONTRACT,
        task_id=TASK_ID,
        goal_id=GOAL_ID,
        goal_packet=GOAL_PACKET,
        goal_packet_goals=GOAL_PACKET_GOALS,
        capability=capability,
        route="meta-wearables-dat-android-display-to-ipfs-kit-bucket-vfs",
        bucket_name=bucket_name,
        bucket_vfs_path=bucket_vfs_path,
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        device_session_states=meta_contract.device_session_states,
        display_icon_names=meta_contract.display_icon_names,
        display_button_styles=meta_contract.display_button_styles,
        bucket_vfs_mcp_tools=ipfs_kit_contract.bucket_vfs_mcp_tools,
        bucket_vfs_cli_commands=ipfs_kit_contract.bucket_vfs_cli_commands,
        bucket_types=ipfs_kit_contract.bucket_types,
        vfs_structure_types=ipfs_kit_contract.vfs_structure_types,
        dag_pb_messages=ipfs_kit_contract.dag_pb_messages,
        required_handoff_operations=REQUIRED_HANDOFF_OPERATIONS,
    )


def _require_files(label: str, paths: tuple[Path, ...]) -> None:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise MetaWearablesDATAndroidIPFSKitInteropError(f"{label} missing: {missing}")


def _require_symbols(source: str, symbols: tuple[str, ...], label: str) -> None:
    missing = [symbol for symbol in symbols if symbol not in source]
    if missing:
        raise MetaWearablesDATAndroidIPFSKitInteropError(
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
        raise MetaWearablesDATAndroidIPFSKitInteropError(
            f"{label} missing: {sorted(missing)}"
        )


def _payload_to_bytes(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
