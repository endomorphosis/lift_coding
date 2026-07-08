"""Mobile / external/ipfs_accelerate interoperability regression tests for VAI-672."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from handsfree.mobile_ipfs_accelerate_interop import (  # noqa: E402
    REQUIRED_MOBILE_WIDGET_ACTIONS,
    REQUIRED_TIME_SERIES_TABLES,
    MobileIPFSAccelerateInteropError,
    build_mobile_benchmark_widget_handoff,
    discover_ipfs_accelerate_duckdb_contract,
)

GOAL_ID = "VAIOS-G719"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

MOBILE_ORB_OPERATIONS = {
    "register_edge_capabilities",
    "publish_glasses_event",
    "bind_service",
    "invoke_service",
    "subscribe_service_updates",
    "dispatch_glasses_response",
    "revoke_binding",
}
BENCHMARK_WIDGET_OPERATIONS = {
    "render_performance_benchmark_widget",
    "update_performance_benchmark_widget",
    "clear_performance_benchmark_widget",
    "refresh_performance_benchmark_metrics",
}


def load_js_exports(path: str, export_names: list[str]) -> dict:
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
const requested = JSON.parse(process.argv[2]);
let source = fs.readFileSync(path, 'utf8');
const functionExports = [];
source = source.replace(/export const\s+([A-Za-z0-9_]+)\s*=/g, (_, name) => {
  return `const ${name} = exports.${name} =`;
});
source = source.replace(/export function\s+([A-Za-z0-9_]+)\s*\(/g, (_, name) => {
  functionExports.push(name);
  return `function ${name}(`;
});
source = `${source}\n${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {} };
vm.runInNewContext(source, context, { filename: path });
const selected = {};
for (const name of requested) {
  selected[name] = context.exports[name];
}
process.stdout.write(JSON.stringify(selected));
"""
    result = subprocess.run(
        ["node", "-e", script, str(REPO_ROOT / path), json.dumps(export_names)],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def assert_module_is_valid_esm(path: str) -> None:
    source = (REPO_ROOT / path).read_text(encoding="utf-8")
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(source)
        temp_path = handle.name
    try:
        subprocess.run(["node", "--check", temp_path], check=True, capture_output=True, text=True)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_ipfs_accelerate_duckdb_schema_descriptors_exist_on_disk() -> None:
    expected_paths = [
        "external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql",
        "external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py",
        "external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py",
        "external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py",
    ]
    for relative_path in expected_paths:
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"


def test_discover_ipfs_accelerate_duckdb_contract_finds_time_series_tables() -> None:
    contract = discover_ipfs_accelerate_duckdb_contract(IPFS_ACCELERATE_ROOT)

    assert set(REQUIRED_TIME_SERIES_TABLES).issubset(set(contract.time_series_tables))
    assert "create_performance_tables" in contract.benchmark_schema_functions
    assert {"check_schema", "get_all_tables", "get_performance_results"}.issubset(
        set(contract.check_schema_functions)
    )
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


def test_discover_ipfs_accelerate_duckdb_contract_raises_for_missing_root(tmp_path) -> None:
    missing_root = tmp_path / "does-not-exist"
    try:
        discover_ipfs_accelerate_duckdb_contract(missing_root)
    except MobileIPFSAccelerateInteropError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected MobileIPFSAccelerateInteropError")


def test_build_mobile_benchmark_widget_handoff_is_deterministic() -> None:
    first = build_mobile_benchmark_widget_handoff(IPFS_ACCELERATE_ROOT)
    second = build_mobile_benchmark_widget_handoff(IPFS_ACCELERATE_ROOT)

    assert first.as_dict() == second.as_dict()
    assert first.interface_contract == "interface contract mobile external/ipfs_accelerate"
    assert first.goal_id == GOAL_ID
    assert first.source_repository == "external/ipfs_accelerate"
    assert first.target_repository == "mobile"
    assert first.content_cid.startswith("sha256:")
    assert first.content_cid == f"sha256:{first.payload_sha256}"
    assert first.payload_size_bytes > 0
    assert set(REQUIRED_TIME_SERIES_TABLES).issubset(set(first.time_series_tables))
    assert set(first.required_mobile_widget_actions) == set(REQUIRED_MOBILE_WIDGET_ACTIONS)
    assert first.endpoint_path == "/v1/ipfs/capabilities"
    assert first.method == "GET"


def test_mobile_descriptor_exports_ipfs_accelerate_interop_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "IPFS_ACCELERATE_MOBILE_INTEROP_INTERFACE",
            "IPFS_ACCELERATE_MOBILE_INTEROP_DESCRIPTOR",
            "MOBILE_ORB_BRIDGE_OPERATIONS",
            "IPFS_ACCELERATE_BENCHMARK_WIDGET_OPERATIONS",
        ],
    )

    interface = exports["IPFS_ACCELERATE_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["IPFS_ACCELERATE_MOBILE_INTEROP_DESCRIPTOR"]

    assert (
        interface["metadata"]["interface_contract"]
        == "interface contract mobile external/ipfs_accelerate"
    )
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert GOAL_ID in interface["objective_goals"]
    assert {method["name"] for method in interface["methods"]} == (
        MOBILE_ORB_OPERATIONS | BENCHMARK_WIDGET_OPERATIONS
    )
    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == MOBILE_ORB_OPERATIONS
    assert set(exports["IPFS_ACCELERATE_BENCHMARK_WIDGET_OPERATIONS"]) == (
        BENCHMARK_WIDGET_OPERATIONS
    )
    assert descriptor["schema_refs"] == {
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
        "benchmark_widget_contract": (
            "mobile/src/utils/ipfsAccelerateBenchmarkWidgetContract.js"
        ),
    }
    assert descriptor["runtime_handoff"]["source_surface"] == "external/ipfs_accelerate"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert set(REQUIRED_TIME_SERIES_TABLES).issubset(
        set(descriptor["runtime_handoff"]["time_series_tables"])
    )
    assert descriptor["validation"]["task_id"] == "VAI-672"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_benchmark_widget_contract_maps_actions_to_dat_methods_and_tables() -> None:
    exports = load_js_exports(
        "mobile/src/utils/ipfsAccelerateBenchmarkWidgetContract.js",
        [
            "BENCHMARK_WIDGET_ACTION_IDS",
            "BENCHMARK_WIDGET_ORB_OPERATION_BY_ACTION_ID",
            "BENCHMARK_WIDGET_DAT_METHOD_BY_ACTION_ID",
            "BENCHMARK_WIDGET_TIME_SERIES_TABLE_BY_ACTION_ID",
            "IPFS_ACCELERATE_BENCHMARK_WIDGET_ACTION_CONTRACT",
        ],
    )

    action_ids = set(exports["BENCHMARK_WIDGET_ACTION_IDS"])
    contract = exports["IPFS_ACCELERATE_BENCHMARK_WIDGET_ACTION_CONTRACT"]

    assert action_ids == set(REQUIRED_MOBILE_WIDGET_ACTIONS)
    assert contract["producer"] == "external/ipfs_accelerate"
    assert contract["consumer"] == "mobile"
    assert contract["interface_contract"] == "interface contract mobile external/ipfs_accelerate"
    assert contract["goal_id"] == GOAL_ID
    assert set(contract["action_ids"]) == action_ids
    assert set(contract["operation_by_action_id"]) == action_ids
    assert set(contract["dat_method_by_action_id"]) == action_ids
    assert set(contract["time_series_table_by_action_id"]) == action_ids
    assert set(contract["time_series_table_by_action_id"].values()).issubset(
        set(REQUIRED_TIME_SERIES_TABLES)
    )
    assert (
        contract["operation_by_action_id"]["mobile_render_performance_benchmark_widget"]
        == "render_performance_benchmark_widget"
    )
    assert (
        contract["dat_method_by_action_id"]["mobile_render_performance_benchmark_widget"]
        == "renderPerformanceBenchmarkWidget"
    )


def test_mobile_orb_bridge_module_remains_parseable_after_contract_wiring() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )
    assert "IPFS_ACCELERATE_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "IPFS_ACCELERATE_MOBILE_INTEROP_INTERFACE" in source
    assert source.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = (
        REPO_ROOT / "docs/integration/mobile-external_ipfs_accelerate.md"
    ).read_text(encoding="utf-8")
    discovery = (
        REPO_ROOT
        / "data/virtual_ai_os/discovery/2026-07-08-vai-672-objective-validation-repair.md"
    ).read_text(encoding="utf-8")
    attempt_four = (
        REPO_ROOT
        / "data/virtual_ai_os/discovery/2026-07-08-vai-672-attempt-4-validation-confirmation.md"
    ).read_text(encoding="utf-8")
    attempt_five = (
        REPO_ROOT
        / "data/virtual_ai_os/discovery/2026-07-08-vai-672-attempt-5-validation-confirmation.md"
    ).read_text(encoding="utf-8")
    attempt_six = (
        REPO_ROOT
        / "data/virtual_ai_os/discovery/2026-07-08-vai-672-attempt-6-validation-confirmation.md"
    ).read_text(encoding="utf-8")
    attempt_seven = (
        REPO_ROOT
        / "data/virtual_ai_os/discovery/2026-07-08-vai-672-attempt-7-validation-confirmation.md"
    ).read_text(encoding="utf-8")
    heap = (
        REPO_ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")

    required_terms = [
        "VAI-672",
        GOAL_ID,
        "objective/interoperability/mobile-external_ipfs_accelerate",
        "objective validation repair",
        "interface contract mobile external/ipfs_accelerate",
        "tests/integration/test_mobile_external_ipfs_accelerate_interop.py",
        "src/handsfree/mobile_ipfs_accelerate_interop.py",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/utils/ipfsAccelerateBenchmarkWidgetContract.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql",
        "external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py",
        "external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py",
        "external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py",
    ]
    for content in (docs, discovery, attempt_four, attempt_five, attempt_six, attempt_seven, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"

    attempt_six_record = (
        "data/virtual_ai_os/discovery/"
        "2026-07-08-vai-672-attempt-6-validation-confirmation.md"
    )
    attempt_seven_record = (
        "data/virtual_ai_os/discovery/"
        "2026-07-08-vai-672-attempt-7-validation-confirmation.md"
    )
    assert attempt_six_record in docs
    assert attempt_six_record in heap
    assert attempt_seven_record in docs
    assert attempt_seven_record in heap
