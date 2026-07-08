"""external/meta-wearables-dat-android and external/ipfs_datasets interop tests."""

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

from handsfree.meta_wearables_dat_android_ipfs_datasets_interop import (  # noqa: E402
    BUCKET_VFS_DEMO_PATH_CANDIDATES,
    GOAL_ID,
    GOAL_PACKET,
    GOAL_PACKET_GOALS,
    INTERFACE_CONTRACT,
    REQUIRED_BUCKET_TYPES,
    REQUIRED_BUCKET_VFS_CLI_COMMANDS,
    REQUIRED_BUCKET_VFS_MCP_TOOLS,
    REQUIRED_DEPRECATIONS_REPORT_KEYS,
    REQUIRED_DEVICE_SESSION_STATES,
    REQUIRED_DISPLAY_BUTTON_STYLES,
    REQUIRED_DISPLAY_ICON_NAMES,
    REQUIRED_HANDOFF_OPERATIONS,
    REQUIRED_MANIFEST_METADATA_KEYS,
    REQUIRED_MANIFEST_PERMISSIONS,
    REQUIRED_UNIFIED_BACKENDS,
    REQUIRED_VFS_STRUCTURE_TYPES,
    MetaWearablesDATAndroidIPFSDatasetsInteropError,
    build_meta_wearables_dat_android_ipfs_datasets_handoff,
    discover_ipfs_datasets_bucket_vfs_contract,
    discover_meta_wearables_dat_android_contract,
)

META_WEARABLES_DAT_ANDROID_ROOT = REPO_ROOT / "external" / "meta-wearables-dat-android"
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
DISCOVERY_PATH = (
    REPO_ROOT
    / "data/hallucinate_multimodal_control/discovery/"
    "2026-07-08-hao-738-objective-gap-136ccea7b51c.md"
)
HEAP_PATH = REPO_ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
DOC_PATH = REPO_ROOT / "docs/integration/external_meta_wearables_dat_android-external_ipfs_datasets.md"
DEPRECATIONS_SCHEMA_PATH = (
    IPFS_DATASETS_ROOT / ".tools/ipfs_kit_py/data/deprecations_report.schema.json"
)
BUCKET_VFS_DEMO_PATH = (
    IPFS_DATASETS_ROOT / ".tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py"
)
BUCKET_VFS_DOC_PATH = (
    IPFS_DATASETS_ROOT
    / ".tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md"
)
BUCKET_VFS_DEMO_SUFFIXES = tuple(
    f".tools/ipfs_kit_py/{candidate.removeprefix('.tools/ipfs_kit_py/')}"
    for candidate in BUCKET_VFS_DEMO_PATH_CANDIDATES
)


def bucket_vfs_demo_path() -> Path:
    for candidate in BUCKET_VFS_DEMO_PATH_CANDIDATES:
        path = IPFS_DATASETS_ROOT / candidate
        if path.is_file() and path.read_text(encoding="utf-8").strip():
            return path
    return BUCKET_VFS_DEMO_PATH


def test_expected_external_descriptors_exist_on_disk() -> None:
    expected_paths = [
        "external/meta-wearables-dat-android/.cursor/rules/display-access.mdc",
        "external/meta-wearables-dat-android/.cursor/rules/session-lifecycle.mdc",
        "external/meta-wearables-dat-android/.cursor/rules/permissions-registration.mdc",
        "external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/AndroidManifest.xml",
        "external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/java/com/meta/"
        "wearable/dat/externalsampleapps/displayaccess/display/DisplayViewModel.kt",
        "external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json",
        (
            "external/ipfs_datasets/.tools/ipfs_kit_py/docs/implementation/"
            "BUCKET_VFS_INTERFACES_COMPLETE.md"
        ),
        "external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py",
        "external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py",
        "external/ipfs_datasets/.tools/ipfs_kit_py/examples/schema_column_optimization_example.py",
        "external/ipfs_datasets/ipfs_datasets_py/ipfs_backend_router.py",
        "external/ipfs_datasets/ipfs_datasets_py/embeddings_router.py",
        "external/ipfs_datasets/ipfs_datasets_py/llm_router.py",
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


def test_discover_ipfs_datasets_bucket_vfs_contract_finds_router_and_bucket_surface() -> None:
    contract = discover_ipfs_datasets_bucket_vfs_contract(IPFS_DATASETS_ROOT)

    assert set(REQUIRED_DEPRECATIONS_REPORT_KEYS).issubset(
        set(contract.deprecations_report_required_keys)
    )
    assert set(REQUIRED_BUCKET_VFS_MCP_TOOLS).issubset(set(contract.bucket_vfs_mcp_tools))
    assert set(REQUIRED_BUCKET_VFS_CLI_COMMANDS) == set(contract.bucket_vfs_cli_commands)
    assert set(REQUIRED_BUCKET_TYPES) == set(contract.bucket_types)
    assert set(REQUIRED_VFS_STRUCTURE_TYPES) == set(contract.vfs_structure_types)
    assert set(REQUIRED_UNIFIED_BACKENDS).issubset(set(contract.unified_backends))
    assert {
        "register_ipfs_backend",
        "add_bytes",
        "cat",
        "embed_text",
        "generate_text",
    }.issubset(set(contract.router_symbols))
    assert contract.deprecations_report_schema_path.endswith(
        ".tools/ipfs_kit_py/data/deprecations_report.schema.json"
    )
    assert contract.bucket_vfs_doc_path.endswith(
        ".tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md"
    )
    assert contract.bucket_vfs_demo_path.endswith(BUCKET_VFS_DEMO_SUFFIXES)
    assert contract.unified_bucket_demo_path.endswith(
        ".tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py"
    )


def test_contract_discovery_raises_for_missing_roots(tmp_path) -> None:
    missing_root = tmp_path / "does-not-exist"

    for discover in (
        discover_meta_wearables_dat_android_contract,
        discover_ipfs_datasets_bucket_vfs_contract,
    ):
        try:
            discover(missing_root)
        except MetaWearablesDATAndroidIPFSDatasetsInteropError as exc:
            assert "not found" in str(exc)
        else:
            raise AssertionError("expected interop error for missing root")


def test_build_handoff_is_deterministic_and_content_addressed() -> None:
    first = build_meta_wearables_dat_android_ipfs_datasets_handoff(
        META_WEARABLES_DAT_ANDROID_ROOT,
        IPFS_DATASETS_ROOT,
    )
    second = build_meta_wearables_dat_android_ipfs_datasets_handoff(
        META_WEARABLES_DAT_ANDROID_ROOT,
        IPFS_DATASETS_ROOT,
    )

    assert first.as_dict() == second.as_dict()
    assert first.interface_contract == INTERFACE_CONTRACT
    assert first.goal_id == GOAL_ID == "VAIOS-G710"
    assert first.goal_packet == GOAL_PACKET
    assert set(first.goal_packet_goals) == set(GOAL_PACKET_GOALS)
    assert first.source_repository == "external/meta-wearables-dat-android"
    assert first.target_repository == "external/ipfs_datasets"
    assert first.route == "meta-wearables-dat-android-display-to-ipfs-datasets-bucket-vfs"
    assert first.dataset_bucket == "meta-wearables-dat-android-display-events"
    assert first.dataset_vfs_path == "/wearables/meta/dat/android/display/events/latest.json"
    assert first.content_cid == f"sha256:{first.payload_sha256}"
    assert first.payload_size_bytes > 0
    assert set(REQUIRED_DEVICE_SESSION_STATES).issubset(set(first.device_session_states))
    assert set(REQUIRED_DISPLAY_ICON_NAMES).issubset(set(first.display_icon_names))
    assert set(REQUIRED_DISPLAY_BUTTON_STYLES).issubset(set(first.display_button_styles))
    assert set(REQUIRED_BUCKET_VFS_MCP_TOOLS).issubset(set(first.bucket_vfs_mcp_tools))
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
            "target": "external/ipfs_datasets",
            "interface_contract": INTERFACE_CONTRACT,
        },
    }
    Draft202012Validator(schema).validate(report)


def test_bucket_vfs_demo_is_import_safe_and_covers_cli_mcp_terms() -> None:
    demo_path = bucket_vfs_demo_path()
    py_compile.compile(str(demo_path), doraise=True)
    source = demo_path.read_text(encoding="utf-8")
    contract_source = source + "\n" + BUCKET_VFS_DOC_PATH.read_text(encoding="utf-8")

    for command in REQUIRED_BUCKET_VFS_CLI_COMMANDS:
        assert command in contract_source
    for tool_name in REQUIRED_BUCKET_VFS_MCP_TOOLS:
        assert tool_name in contract_source
    assert "demo_cli_interface" in source
    assert "demo_mcp_api" in source
    assert "bucket_export_car" in source
    assert "bucket_cross_query" in source


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    doc_source = DOC_PATH.read_text(encoding="utf-8")
    discovery_source = DISCOVERY_PATH.read_text(encoding="utf-8")
    heap_source = HEAP_PATH.read_text(encoding="utf-8")

    for source in (doc_source, discovery_source, heap_source):
        assert "HAO-738" in source
        assert GOAL_ID in source
        assert "objective validation repair" in source
        assert INTERFACE_CONTRACT in source
        assert "external/meta-wearables-dat-android" in source
        assert "external/ipfs_datasets" in source
        assert "tests/integration/test_external_meta_wearables_dat_android_external_ipfs_datasets_interop.py" in source

    assert "Status: completed" in heap_source
    assert "Completion validation: python -m pytest tests/integration -q" in heap_source
