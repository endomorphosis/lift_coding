"""Meta Wearables DAT Android / external/ipfs_accelerate interop tests for MGW-576."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from handsfree.meta_wearables_dat_android_ipfs_accelerate_interop import (  # noqa: E402
    DAT_ANDROID_TABLE_BY_METHOD,
    GOAL_ID,
    GOAL_PACKET,
    GOAL_PACKET_GOALS,
    INTERFACE_CONTRACT,
    REQUIRED_BENCHMARK_SCHEMA_FUNCTIONS,
    REQUIRED_CHECK_SCHEMA_FUNCTIONS,
    REQUIRED_DAT_ANDROID_METHODS,
    REQUIRED_TIME_SERIES_TABLES,
    MetaWearablesDatAndroidIPFSAccelerateInteropError,
    build_meta_wearables_dat_android_ipfs_accelerate_handoff,
    discover_ipfs_accelerate_duckdb_contract,
    discover_meta_wearables_dat_android_contract,
)

META_WEARABLES_DAT_ANDROID_ROOT = REPO_ROOT / "external" / "meta-wearables-dat-android"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
DISCOVERY_REPAIR = (
    REPO_ROOT
    / "data"
    / "meta_glasses_display_widgets"
    / "discovery"
    / "2026-07-08-mgw-576-objective-validation-repair.md"
)


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_expected_interop_artifacts_exist_on_disk() -> None:
    expected_paths = [
        "external/meta-wearables-dat-android/samples/DisplayAccess/README.md",
        "external/meta-wearables-dat-android/samples/DisplayAccess/app/build.gradle.kts",
        (
            "external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/java/"
            "com/meta/wearable/dat/externalsampleapps/displayaccess/display/DisplayViewModel.kt"
        ),
        "external/meta-wearables-dat-android/.cursor/rules/display-access.mdc",
        "external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql",
        "external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py",
        "external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py",
        "external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py",
        "docs/integration/external_meta_wearables_dat_android-external_ipfs_accelerate.md",
        "data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-576-objective-validation-repair.md",
    ]
    for relative_path in expected_paths:
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"


def test_discover_ipfs_accelerate_duckdb_contract_finds_schema_surface() -> None:
    contract = discover_ipfs_accelerate_duckdb_contract(IPFS_ACCELERATE_ROOT)

    assert set(REQUIRED_TIME_SERIES_TABLES).issubset(set(contract.time_series_tables))
    assert set(REQUIRED_BENCHMARK_SCHEMA_FUNCTIONS).issubset(
        set(contract.benchmark_schema_functions)
    )
    assert set(REQUIRED_CHECK_SCHEMA_FUNCTIONS).issubset(set(contract.check_schema_functions))
    assert contract.time_series_schema_path.endswith(
        "data/duckdb/db_schema/time_series_schema.sql"
    )
    assert contract.benchmark_schema_script_path.endswith(
        "data/duckdb/scripts/create_benchmark_schema.py"
    )
    assert contract.check_database_schema_path.endswith(
        "data/duckdb/utils/check_database_schema.py"
    )
    assert contract.check_db_schema_path.endswith("data/duckdb/utils/check_db_schema.py")


def test_discover_meta_wearables_dat_android_contract_validates_descriptor() -> None:
    contract = discover_meta_wearables_dat_android_contract(META_WEARABLES_DAT_ANDROID_ROOT)

    assert contract.interface_contract == INTERFACE_CONTRACT
    assert contract.task_id == "MGW-576"
    assert contract.goal_id == GOAL_ID == "VAIOS-G709"
    assert contract.goal_packet == GOAL_PACKET
    assert set(GOAL_PACKET_GOALS).issubset(set(contract.goal_packet_goals))
    assert contract.producer == "external/ipfs_accelerate"
    assert contract.consumer == "external/meta-wearables-dat-android"
    assert set(REQUIRED_DAT_ANDROID_METHODS).issubset(set(contract.dat_display_methods))
    assert contract.table_by_method == DAT_ANDROID_TABLE_BY_METHOD
    assert any(path.endswith("samples/DisplayAccess/README.md") for path in contract.descriptor_paths)
    assert any(path.endswith(".cursor/rules/display-access.mdc") for path in contract.descriptor_paths)
    assert contract.schema_refs == {
        "time_series_schema": (
            "external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql"
        ),
        "benchmark_schema_script": (
            "external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py"
        ),
        "check_database_schema": (
            "external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py"
        ),
        "check_db_schema": "external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py",
    }


def test_discovery_raises_for_missing_roots(tmp_path) -> None:
    missing_root = tmp_path / "does-not-exist"

    for discover in (
        discover_ipfs_accelerate_duckdb_contract,
        discover_meta_wearables_dat_android_contract,
    ):
        try:
            discover(missing_root)
        except MetaWearablesDatAndroidIPFSAccelerateInteropError as exc:
            assert "not found" in str(exc)
        else:
            raise AssertionError("expected MetaWearablesDatAndroidIPFSAccelerateInteropError")


def test_build_meta_wearables_dat_android_ipfs_accelerate_handoff_is_deterministic() -> None:
    first = build_meta_wearables_dat_android_ipfs_accelerate_handoff(
        META_WEARABLES_DAT_ANDROID_ROOT,
        IPFS_ACCELERATE_ROOT,
    )
    second = build_meta_wearables_dat_android_ipfs_accelerate_handoff(
        META_WEARABLES_DAT_ANDROID_ROOT,
        IPFS_ACCELERATE_ROOT,
    )

    assert first.as_dict() == second.as_dict()
    assert first.interface_contract == INTERFACE_CONTRACT
    assert first.task_id == "MGW-576"
    assert first.goal_id == GOAL_ID
    assert first.goal_packet == GOAL_PACKET
    assert set(first.goal_packet_goals) == set(GOAL_PACKET_GOALS)
    assert first.source_repository == "external/ipfs_accelerate"
    assert first.target_repository == "external/meta-wearables-dat-android"
    assert first.capability == "dat.android.display.performance_benchmark"
    assert first.route == "ipfs-accelerate-benchmark-to-meta-wearables-dat-android"
    assert first.content_cid.startswith("sha256:")
    assert first.content_cid == f"sha256:{first.payload_sha256}"
    assert first.payload_size_bytes > 0
    assert set(REQUIRED_TIME_SERIES_TABLES).issubset(set(first.time_series_tables))
    assert set(REQUIRED_DAT_ANDROID_METHODS).issubset(set(first.dat_display_methods))
    assert first.table_by_method == DAT_ANDROID_TABLE_BY_METHOD
    assert set(REQUIRED_BENCHMARK_SCHEMA_FUNCTIONS).issubset(
        set(first.benchmark_schema_functions)
    )
    assert set(REQUIRED_CHECK_SCHEMA_FUNCTIONS).issubset(set(first.check_schema_functions))


def test_dat_android_display_access_sources_support_benchmark_widget_handoff() -> None:
    readme = read_text(META_WEARABLES_DAT_ANDROID_ROOT / "samples/DisplayAccess/README.md")
    display_rule = read_text(META_WEARABLES_DAT_ANDROID_ROOT / ".cursor/rules/display-access.mdc")
    view_model = read_text(
        META_WEARABLES_DAT_ANDROID_ROOT
        / "samples/DisplayAccess/app/src/main/java/com/meta/wearable/dat/"
        / "externalsampleapps/displayaccess/display/DisplayViewModel.kt"
    )
    build_gradle = read_text(
        META_WEARABLES_DAT_ANDROID_ROOT / "samples/DisplayAccess/app/build.gradle.kts"
    )

    assert "display-capable Meta AI glasses" in readme
    assert "mwdat-display" in display_rule
    assert "addDisplay" in display_rule
    assert "sendContent" in display_rule
    assert "implementation(libs.mwdat.display)" in build_gradle
    assert "DisplayState.STARTED" in view_model
    assert "DeviceSessionError.DAT_APP_ON_THE_GLASSES_UPDATE_REQUIRED" in view_model
    assert DAT_ANDROID_TABLE_BY_METHOD == {
        "renderPerformanceBenchmarkWidget": "performance_baselines",
        "updatePerformanceBenchmarkWidget": "performance_trends",
        "clearPerformanceBenchmarkWidget": "regression_notifications",
        "refreshPerformanceBenchmarkMetrics": "performance_regressions",
    }


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = read_text(
        REPO_ROOT
        / "docs"
        / "integration"
        / "external_meta_wearables_dat_android-external_ipfs_accelerate.md"
    )
    discovery = read_text(DISCOVERY_REPAIR)
    heap = read_text(
        REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    )

    required_terms = [
        "MGW-576",
        "VAIOS-G709",
        "VAIOS-G710",
        "VAIOS-G711",
        "goal_packet/interoperability/external/6595cbbfadb9",
        "objective validation repair",
        INTERFACE_CONTRACT,
        "tests/integration/test_external_meta_wearables_dat_android_external_ipfs_accelerate_interop.py",
        "docs/integration/external_meta_wearables_dat_android-external_ipfs_accelerate.md",
        "external/meta-wearables-dat-android/samples/DisplayAccess/README.md",
        "external/meta-wearables-dat-android/.cursor/rules/display-access.mdc",
        "external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql",
        "external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py",
        "external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py",
        "external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py",
    ]
    for term in required_terms:
        assert term in docs
        assert term in discovery
        assert term in heap
