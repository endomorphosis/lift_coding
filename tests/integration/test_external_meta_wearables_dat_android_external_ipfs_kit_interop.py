"""external/meta-wearables-dat-android and external/ipfs_kit interop tests."""

from __future__ import annotations

import json
import py_compile
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from handsfree.meta_wearables_dat_android_ipfs_kit_interop import (  # noqa: E402
    GOAL_ID,
    GOAL_PACKET,
    GOAL_PACKET_GOALS,
    INTERFACE_CONTRACT,
    REQUIRED_BUCKET_TYPES,
    REQUIRED_BUCKET_VFS_CLI_COMMANDS,
    REQUIRED_BUCKET_VFS_MCP_TOOLS,
    REQUIRED_DAG_PB_MESSAGES,
    REQUIRED_DEPRECATIONS_REPORT_KEYS,
    REQUIRED_DEVICE_SESSION_STATES,
    REQUIRED_DISPLAY_BUTTON_STYLES,
    REQUIRED_DISPLAY_ICON_NAMES,
    REQUIRED_FIX_MCP_SCHEMA_PATHS,
    REQUIRED_HANDOFF_OPERATIONS,
    REQUIRED_MANIFEST_METADATA_KEYS,
    REQUIRED_MANIFEST_PERMISSIONS,
    REQUIRED_VFS_STRUCTURE_TYPES,
    MetaWearablesDATAndroidIPFSKitInteropError,
    build_meta_wearables_dat_android_ipfs_kit_handoff,
    discover_ipfs_kit_bucket_vfs_contract,
    discover_meta_wearables_dat_android_contract,
)

META_WEARABLES_DAT_ANDROID_ROOT = REPO_ROOT / "external" / "meta-wearables-dat-android"
IPFS_KIT_ROOT = REPO_ROOT / "external" / "ipfs_kit"
DISCOVERY_PATH = (
    REPO_ROOT
    / "data/virtual_ai_os/discovery/2026-07-08-vai-670-objective-validation-repair.md"
)
GAP_PATH = (
    REPO_ROOT
    / "data/virtual_ai_os/discovery/2026-07-08-vai-670-objective-gap-853e023f8d1d.md"
)
HEAP_PATH = REPO_ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
DOC_PATH = REPO_ROOT / "docs/integration/external_meta_wearables_dat_android-external_ipfs_kit.md"
DEPRECATIONS_SCHEMA_PATH = IPFS_KIT_ROOT / "data/deprecations_report.schema.json"


def test_expected_external_descriptors_exist_on_disk() -> None:
    expected_paths = [
        "external/meta-wearables-dat-android/.cursor/rules/display-access.mdc",
        "external/meta-wearables-dat-android/.cursor/rules/session-lifecycle.mdc",
        "external/meta-wearables-dat-android/.cursor/rules/permissions-registration.mdc",
        "external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/AndroidManifest.xml",
        "external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/java/com/meta/"
        "wearable/dat/externalsampleapps/displayaccess/display/DisplayViewModel.kt",
        "external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py",
        "external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py",
        "external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py",
        "external/ipfs_kit/data/deprecations_report.schema.json",
        "external/ipfs_kit/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md",
        "external/ipfs_kit/docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto",
        "external/ipfs_kit/ipfs_kit_py/bucket_vfs_cli.py",
        "external/ipfs_kit/mcp/bucket_vfs_mcp_tools.py",
        "external/ipfs_kit/ipfs_kit_py/mcp/servers/enhanced_integrated_mcp_server.py",
        "external/ipfs_kit/ipfs_kit_py/bucket_vfs_manager.py",
        "src/handsfree/meta_wearables_dat_android_ipfs_kit_interop.py",
        "docs/integration/external_meta_wearables_dat_android-external_ipfs_kit.md",
        "data/virtual_ai_os/discovery/2026-07-08-vai-670-objective-validation-repair.md",
    ]
    for relative_path in expected_paths:
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"


def test_discover_meta_wearables_dat_android_contract_finds_display_surface() -> None:
    contract = discover_meta_wearables_dat_android_contract(META_WEARABLES_DAT_ANDROID_ROOT)

    assert set(REQUIRED_DEVICE_SESSION_STATES).issubset(set(contract.device_session_states))
    assert set(REQUIRED_MANIFEST_METADATA_KEYS).issubset(set(contract.manifest_metadata_keys))
    assert set(REQUIRED_MANIFEST_PERMISSIONS).issubset(set(contract.manifest_permissions))
    assert set(REQUIRED_DISPLAY_ICON_NAMES).issubset(set(contract.display_icon_names))
    assert set(REQUIRED_DISPLAY_BUTTON_STYLES).issubset(set(contract.display_button_styles))
    assert contract.display_access_doc_path.endswith(".cursor/rules/display-access.mdc")
    assert contract.session_lifecycle_doc_path.endswith(".cursor/rules/session-lifecycle.mdc")
    assert contract.permissions_registration_doc_path.endswith(
        ".cursor/rules/permissions-registration.mdc"
    )
    assert contract.display_manifest_path.endswith("AndroidManifest.xml")
    assert contract.display_view_model_path.endswith("display/DisplayViewModel.kt")


def test_discover_ipfs_kit_bucket_vfs_contract_finds_mcp_and_ipld_surface() -> None:
    contract = discover_ipfs_kit_bucket_vfs_contract(IPFS_KIT_ROOT)

    assert set(REQUIRED_DEPRECATIONS_REPORT_KEYS).issubset(
        set(contract.deprecations_report_required_keys)
    )
    assert set(REQUIRED_BUCKET_VFS_MCP_TOOLS).issubset(set(contract.bucket_vfs_mcp_tools))
    assert set(REQUIRED_BUCKET_VFS_CLI_COMMANDS).issubset(
        set(contract.bucket_vfs_cli_commands)
    )
    assert set(REQUIRED_BUCKET_TYPES) == set(contract.bucket_types)
    assert set(REQUIRED_VFS_STRUCTURE_TYPES) == set(contract.vfs_structure_types)
    assert set(REQUIRED_DAG_PB_MESSAGES) == set(contract.dag_pb_messages)
    for relative_path in REQUIRED_FIX_MCP_SCHEMA_PATHS:
        assert any(path.endswith(relative_path) for path in contract.fix_mcp_schema_paths)
    assert contract.deprecations_report_schema_path.endswith(
        "data/deprecations_report.schema.json"
    )
    assert contract.bucket_vfs_doc_path.endswith(
        "docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md"
    )
    assert contract.dag_pb_proto_path.endswith("docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto")
    assert contract.bucket_vfs_cli_path.endswith("ipfs_kit_py/bucket_vfs_cli.py")
    assert contract.bucket_vfs_mcp_tools_path.endswith("mcp/bucket_vfs_mcp_tools.py")
    assert contract.enhanced_mcp_server_path.endswith(
        "ipfs_kit_py/mcp/servers/enhanced_integrated_mcp_server.py"
    )


def test_contract_discovery_raises_for_missing_roots(tmp_path) -> None:
    missing_root = tmp_path / "does-not-exist"

    for discover in (
        discover_meta_wearables_dat_android_contract,
        discover_ipfs_kit_bucket_vfs_contract,
    ):
        try:
            discover(missing_root)
        except MetaWearablesDATAndroidIPFSKitInteropError as exc:
            assert "not found" in str(exc)
        else:
            raise AssertionError("expected interop error for missing root")


def test_build_handoff_is_deterministic_and_content_addressed() -> None:
    first = build_meta_wearables_dat_android_ipfs_kit_handoff(
        META_WEARABLES_DAT_ANDROID_ROOT,
        IPFS_KIT_ROOT,
    )
    second = build_meta_wearables_dat_android_ipfs_kit_handoff(
        META_WEARABLES_DAT_ANDROID_ROOT,
        IPFS_KIT_ROOT,
    )

    assert first.as_dict() == second.as_dict()
    assert first.interface_contract == INTERFACE_CONTRACT
    assert first.task_id == "VAI-670"
    assert first.goal_id == GOAL_ID == "VAIOS-G711"
    assert first.goal_packet == GOAL_PACKET
    assert set(first.goal_packet_goals) == set(GOAL_PACKET_GOALS)
    assert first.source_repository == "external/meta-wearables-dat-android"
    assert first.target_repository == "external/ipfs_kit"
    assert first.route == "meta-wearables-dat-android-display-to-ipfs-kit-bucket-vfs"
    assert first.bucket_name == "meta-wearables-dat-android-display-events"
    assert first.bucket_vfs_path == "/wearables/meta/dat/android/display/events/latest.json"
    assert first.content_cid == f"sha256:{first.payload_sha256}"
    assert first.payload_size_bytes > 0
    assert set(REQUIRED_DEVICE_SESSION_STATES).issubset(set(first.device_session_states))
    assert set(REQUIRED_DISPLAY_ICON_NAMES).issubset(set(first.display_icon_names))
    assert set(REQUIRED_DISPLAY_BUTTON_STYLES).issubset(set(first.display_button_styles))
    assert set(REQUIRED_BUCKET_VFS_MCP_TOOLS).issubset(set(first.bucket_vfs_mcp_tools))
    assert set(REQUIRED_BUCKET_VFS_CLI_COMMANDS).issubset(set(first.bucket_vfs_cli_commands))
    assert set(REQUIRED_DAG_PB_MESSAGES) == set(first.dag_pb_messages)
    assert set(REQUIRED_HANDOFF_OPERATIONS) == set(first.required_handoff_operations)


def test_deprecations_report_schema_validates_handoff_compatible_report() -> None:
    schema = json.loads(DEPRECATIONS_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)

    report = {
        "report_version": "1.0.0",
        "generated_at": "2026-07-08T00:00:00Z",
        "deprecated": [],
        "summary": {"count": 0, "max_hits": 0},
        "policy": {
            "hits_enforcement": {"status": "pass", "checked": 0, "violations": []},
            "migration_enforcement": {"status": "pass", "checked": 0, "violations": []},
        },
        "raw": {
            "source": "external/meta-wearables-dat-android",
            "target": "external/ipfs_kit",
            "interface_contract": INTERFACE_CONTRACT,
        },
    }
    Draft202012Validator(schema).validate(report)


def test_ipfs_kit_descriptor_scripts_and_sources_are_import_safe() -> None:
    for relative_path in REQUIRED_FIX_MCP_SCHEMA_PATHS:
        py_compile.compile(str(IPFS_KIT_ROOT / relative_path), doraise=True)

    cli_source = (IPFS_KIT_ROOT / "ipfs_kit_py/bucket_vfs_cli.py").read_text(
        encoding="utf-8"
    )
    mcp_source = (IPFS_KIT_ROOT / "mcp/bucket_vfs_mcp_tools.py").read_text(
        encoding="utf-8"
    )
    doc_source = (
        IPFS_KIT_ROOT / "docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md"
    ).read_text(encoding="utf-8")
    manager_source = (IPFS_KIT_ROOT / "ipfs_kit_py/bucket_vfs_manager.py").read_text(
        encoding="utf-8"
    )

    for command in REQUIRED_BUCKET_VFS_CLI_COMMANDS:
        assert f'"{command}"' in cli_source
    for tool_name in REQUIRED_BUCKET_VFS_MCP_TOOLS:
        assert tool_name in doc_source
    for implemented_tool in (
        "bucket_create",
        "bucket_list",
        "bucket_add_file",
        "bucket_export_car",
        "bucket_cross_query",
    ):
        assert implemented_tool in mcp_source or implemented_tool in cli_source
    assert "S3-like semantics" in cli_source
    assert "IPLD compatibility" in cli_source
    assert "class BucketType" in manager_source
    assert "class VFSStructureType" in manager_source


def test_docs_discovery_gap_and_heap_record_objective_validation_repair() -> None:
    doc_source = DOC_PATH.read_text(encoding="utf-8")
    discovery_source = DISCOVERY_PATH.read_text(encoding="utf-8")
    gap_source = GAP_PATH.read_text(encoding="utf-8")
    heap_source = HEAP_PATH.read_text(encoding="utf-8")

    required_terms = [
        "VAI-670",
        "VAIOS-G711",
        "VAIOS-G709",
        "VAIOS-G710",
        "goal_packet/interoperability/external/6595cbbfadb9",
        "objective validation repair",
        INTERFACE_CONTRACT,
        "tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py",
        "src/handsfree/meta_wearables_dat_android_ipfs_kit_interop.py",
        "docs/integration/external_meta_wearables_dat_android-external_ipfs_kit.md",
        "external/meta-wearables-dat-android/.cursor/rules/display-access.mdc",
        "external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py",
        "external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py",
        "external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py",
        "external/ipfs_kit/data/deprecations_report.schema.json",
        "external/ipfs_kit/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md",
        "external/ipfs_kit/docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto",
    ]
    for source in (doc_source, discovery_source, heap_source):
        for term in required_terms:
            assert term in source, f"missing {term!r}"
    for goal_id in GOAL_PACKET_GOALS:
        assert goal_id in discovery_source
        assert goal_id in heap_source
    assert "VAIOS-G711" in gap_source
    assert "Status: completed" in heap_source
    assert "Completion validation: python -m pytest tests/integration -q" in heap_source
