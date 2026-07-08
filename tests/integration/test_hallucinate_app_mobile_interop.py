"""Hallucinate App / mobile interoperability regression tests for VAI-674."""

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

from handsfree.hallucinate_app_mobile_interop import (  # noqa: E402
    REQUIRED_MOBILE_WIDGET_ACTIONS,
    REQUIRED_ROUTES,
    HallucinateAppMobileInteropError,
    build_hallucinate_app_mobile_handoff,
    discover_hallucinate_app_mobile_contract,
)

GOAL_ID = "VAIOS-G707"
HALLUCINATE_APP_ROOT = REPO_ROOT / "hallucinate_app"

MOBILE_ORB_OPERATIONS = {
    "register_edge_capabilities",
    "publish_glasses_event",
    "bind_service",
    "invoke_service",
    "subscribe_service_updates",
    "dispatch_glasses_response",
    "revoke_binding",
}
SEARCH_WIDGET_OPERATIONS = {
    "render_search_results_widget",
    "update_search_results_widget",
    "clear_search_results_widget",
    "refresh_search_metadata",
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
source = source.replace(/export class\s+([A-Za-z0-9_]+)/g, (_, name) => {
  return `class ${name}`;
});
source = source.replace(/export default\s+[A-Za-z0-9_]+;?/g, '');
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


def test_hallucinate_app_mobile_descriptors_exist_on_disk() -> None:
    expected_paths = [
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/utils/hallucinateAppSearchWidgetContract.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
    ]
    for relative_path in expected_paths:
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"


def test_discover_hallucinate_app_mobile_contract_finds_receipt_table() -> None:
    contract = discover_hallucinate_app_mobile_contract(HALLUCINATE_APP_ROOT)

    assert contract.contract_id == "interface contract hallucinate_app mobile"
    assert contract.event_name == "hallucinate-app:mobile-interop-handoff"
    assert contract.receipt_table == "hallucinate_app_mobile_interop_receipts"
    assert set(REQUIRED_ROUTES).issubset(set(contract.routes))
    assert contract.search_interface_path.endswith(
        "node/dashboard/content_browser/search_interface.js"
    )
    assert contract.test_interface_path.endswith("node/views/test_interface.html")
    assert contract.time_series_schema_path.endswith(
        "data/duckdb/db_schema/time_series_schema.sql"
    )
    assert contract.benchmark_schema_script_path.endswith(
        "data/duckdb/scripts/create_benchmark_schema.py"
    )
    assert set(contract.required_artifacts) == {
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
    }


def test_discover_hallucinate_app_mobile_contract_raises_for_missing_root(tmp_path) -> None:
    missing_root = tmp_path / "does-not-exist"
    try:
        discover_hallucinate_app_mobile_contract(missing_root)
    except HallucinateAppMobileInteropError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected HallucinateAppMobileInteropError")


def test_build_hallucinate_app_mobile_handoff_is_deterministic() -> None:
    first = build_hallucinate_app_mobile_handoff(HALLUCINATE_APP_ROOT)
    second = build_hallucinate_app_mobile_handoff(HALLUCINATE_APP_ROOT)

    assert first.as_dict() == second.as_dict()
    assert first.interface_contract == "interface contract hallucinate_app mobile"
    assert first.goal_id == GOAL_ID
    assert first.source_repository == "hallucinate_app"
    assert first.target_repository == "mobile"
    assert first.event_name == "hallucinate-app:mobile-interop-handoff"
    assert first.receipt_table == "hallucinate_app_mobile_interop_receipts"
    assert first.content_cid.startswith("sha256:")
    assert first.content_cid == f"sha256:{first.payload_sha256}"
    assert first.payload_size_bytes > 0
    assert set(first.required_mobile_widget_actions) == set(REQUIRED_MOBILE_WIDGET_ACTIONS)
    assert first.route == "/v1/mobile/orb/invoke_service"
    assert first.method == "invoke_service"


def test_build_hallucinate_app_mobile_handoff_rejects_unsupported_route() -> None:
    try:
        build_hallucinate_app_mobile_handoff(HALLUCINATE_APP_ROOT, route="/v1/mobile/orb/unknown")
    except HallucinateAppMobileInteropError as exc:
        assert "unsupported hallucinate_app mobile route" in str(exc)
    else:
        raise AssertionError("expected HallucinateAppMobileInteropError")


def test_search_interface_js_exports_mobile_interop_descriptor() -> None:
    exports = load_js_exports(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        [
            "HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        ],
    )

    contract = exports["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert contract["contract_id"] == "interface contract hallucinate_app mobile"
    assert contract["source_surface"] == "hallucinate_app"
    assert contract["target_surface"] == "mobile"
    assert descriptor["event_name"] == "hallucinate-app:mobile-interop-handoff"
    assert descriptor["receipt_table"] == "hallucinate_app_mobile_interop_receipts"
    assert descriptor["validation"]["task_id"] == "VAI-674"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_descriptor_exports_hallucinate_app_interop_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "MOBILE_ORB_BRIDGE_OPERATIONS",
            "HALLUCINATE_APP_SEARCH_WIDGET_OPERATIONS",
        ],
    )

    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert (
        interface["metadata"]["interface_contract"]
        == "interface contract hallucinate_app mobile"
    )
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert GOAL_ID in interface["objective_goals"]
    assert {method["name"] for method in interface["methods"]} == (
        MOBILE_ORB_OPERATIONS | SEARCH_WIDGET_OPERATIONS
    )
    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == MOBILE_ORB_OPERATIONS
    assert set(exports["HALLUCINATE_APP_SEARCH_WIDGET_OPERATIONS"]) == SEARCH_WIDGET_OPERATIONS
    assert descriptor["schema_refs"] == {
        "search_interface_descriptor": (
            "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
        ),
        "test_interface_fixture": (
            "hallucinate_app/hallucinate_app/node/views/test_interface.html"
        ),
        "time_series_schema": (
            "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
        ),
        "benchmark_schema_script": (
            "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
        ),
    }
    assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert descriptor["runtime_handoff"]["event_name"] == "hallucinate-app:mobile-interop-handoff"
    assert (
        descriptor["runtime_handoff"]["receipt_table"]
        == "hallucinate_app_mobile_interop_receipts"
    )
    assert set(REQUIRED_ROUTES).issubset(set(descriptor["runtime_handoff"]["routes"]))
    assert descriptor["validation"]["task_id"] == "VAI-674"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_search_widget_contract_maps_actions_to_operations_and_routes() -> None:
    exports = load_js_exports(
        "mobile/src/utils/hallucinateAppSearchWidgetContract.js",
        [
            "SEARCH_WIDGET_ACTION_IDS",
            "SEARCH_WIDGET_ORB_OPERATION_BY_ACTION_ID",
            "SEARCH_WIDGET_DAT_METHOD_BY_ACTION_ID",
            "SEARCH_WIDGET_ROUTE_BY_ACTION_ID",
            "HALLUCINATE_APP_SEARCH_WIDGET_ACTION_CONTRACT",
        ],
    )

    action_ids = set(exports["SEARCH_WIDGET_ACTION_IDS"])
    contract = exports["HALLUCINATE_APP_SEARCH_WIDGET_ACTION_CONTRACT"]

    assert action_ids == set(REQUIRED_MOBILE_WIDGET_ACTIONS)
    assert contract["producer"] == "hallucinate_app"
    assert contract["consumer"] == "mobile"
    assert contract["interface_contract"] == "interface contract hallucinate_app mobile"
    assert contract["goal_id"] == GOAL_ID
    assert contract["event_name"] == "hallucinate-app:mobile-interop-handoff"
    assert contract["receipt_table"] == "hallucinate_app_mobile_interop_receipts"
    assert set(contract["action_ids"]) == action_ids
    assert set(contract["operation_by_action_id"]) == action_ids
    assert set(contract["dat_method_by_action_id"]) == action_ids
    assert set(contract["route_by_action_id"]) == action_ids
    assert set(exports["SEARCH_WIDGET_ROUTE_BY_ACTION_ID"].values()).issubset(
        set(REQUIRED_ROUTES)
    )
    assert (
        contract["operation_by_action_id"]["mobile_render_search_results_widget"]
        == "render_search_results_widget"
    )
    assert (
        contract["dat_method_by_action_id"]["mobile_render_search_results_widget"]
        == "renderSearchResultsWidget"
    )


def test_mobile_orb_bridge_module_remains_parseable_after_contract_wiring() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert source.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1


def test_test_interface_html_carries_machine_readable_fixture() -> None:
    html = (
        REPO_ROOT / "hallucinate_app/hallucinate_app/node/views/test_interface.html"
    ).read_text(encoding="utf-8")

    assert 'data-contract-id="interface contract hallucinate_app mobile"' in html
    assert 'data-event-name="hallucinate-app:mobile-interop-handoff"' in html
    assert 'data-receipt-table="hallucinate_app_mobile_interop_receipts"' in html
    assert 'data-vai-task-id="VAI-674"' in html
    assert 'data-goal-id="VAIOS-G707"' in html


def test_duckdb_schema_and_benchmark_script_declare_receipt_table() -> None:
    schema_sql = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
    ).read_text(encoding="utf-8")
    benchmark_script = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
    ).read_text(encoding="utf-8")

    assert "hallucinate_app_mobile_interop_receipts" in schema_sql
    assert "HALLUCINATE_APP_MOBILE_INTEROP_TABLE" in benchmark_script
    assert "interface contract hallucinate_app mobile" in benchmark_script


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = (REPO_ROOT / "docs/integration/hallucinate_app-mobile.md").read_text(
        encoding="utf-8"
    )
    discovery = (
        REPO_ROOT
        / "data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-validation-repair.md"
    ).read_text(encoding="utf-8")
    heap = (
        REPO_ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")

    required_terms = [
        "VAI-674",
        GOAL_ID,
        "objective/interoperability/hallucinate_app-mobile",
        "objective validation repair",
        "interface contract hallucinate_app mobile",
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "src/handsfree/hallucinate_app_mobile_interop.py",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/utils/hallucinateAppSearchWidgetContract.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"
