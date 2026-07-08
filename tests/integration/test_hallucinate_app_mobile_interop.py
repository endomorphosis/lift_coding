"""Hallucinate App / mobile interoperability regression tests for HAO-740."""

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
    INTEROP_RECEIPTS_TABLE,
    REQUIRED_ARTIFACTS,
    REQUIRED_ROUTES,
    HallucinateAppMobileInteropError,
    build_hallucinate_app_mobile_search_handoff,
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
HALLUCINATE_APP_HANDOFF_OPERATIONS = {
    "register_edge_capabilities",
    "invoke_service",
    "dispatch_glasses_response",
    "diagnostics",
}
HALLUCINATE_APP_SEARCH_ACTION_IDS = {
    "mobile_dispatch_hallucinate_app_search_query",
    "mobile_render_hallucinate_app_search_results",
    "mobile_update_hallucinate_app_search_results",
    "mobile_clear_hallucinate_app_search_results",
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


def test_hallucinate_app_mobile_interop_descriptors_exist_on_disk() -> None:
    expected_paths = [
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
    ]
    for relative_path in expected_paths:
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"


def test_discover_hallucinate_app_mobile_contract_finds_required_routes() -> None:
    contract = discover_hallucinate_app_mobile_contract(HALLUCINATE_APP_ROOT)

    assert contract.contract_id == "interface contract hallucinate_app mobile"
    assert set(REQUIRED_ROUTES).issubset(set(contract.required_routes))
    assert set(REQUIRED_ARTIFACTS) == set(contract.required_artifacts)
    assert contract.interop_receipts_table == INTEROP_RECEIPTS_TABLE
    assert contract.search_interface_path.endswith(
        "hallucinate_app/node/dashboard/content_browser/search_interface.js"
    )
    assert contract.test_interface_path.endswith("hallucinate_app/node/views/test_interface.html")
    assert contract.time_series_schema_path.endswith(
        "ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
    )
    assert contract.benchmark_schema_script_path.endswith(
        "ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
    )


def test_discover_hallucinate_app_mobile_contract_raises_for_missing_root(tmp_path) -> None:
    missing_root = tmp_path / "does-not-exist"
    try:
        discover_hallucinate_app_mobile_contract(missing_root)
    except HallucinateAppMobileInteropError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected HallucinateAppMobileInteropError")


def test_discover_hallucinate_app_mobile_contract_raises_for_missing_descriptors(tmp_path) -> None:
    incomplete_root = tmp_path / "hallucinate_app"
    (incomplete_root / "hallucinate_app" / "node" / "dashboard" / "content_browser").mkdir(
        parents=True
    )
    try:
        discover_hallucinate_app_mobile_contract(incomplete_root)
    except HallucinateAppMobileInteropError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("expected HallucinateAppMobileInteropError")


def test_build_hallucinate_app_mobile_search_handoff_is_deterministic() -> None:
    first = build_hallucinate_app_mobile_search_handoff(HALLUCINATE_APP_ROOT)
    second = build_hallucinate_app_mobile_search_handoff(HALLUCINATE_APP_ROOT)

    assert first.as_dict() == second.as_dict()
    assert first.interface_contract == "interface contract hallucinate_app mobile"
    assert first.goal_id == GOAL_ID
    assert first.source_repository == "hallucinate_app"
    assert first.target_repository == "mobile"
    assert first.content_cid.startswith("sha256:")
    assert first.content_cid == f"sha256:{first.payload_sha256}"
    assert first.payload_size_bytes > 0
    assert first.route == "/v1/mobile/orb/invoke_service"
    assert first.operation == "invoke_service"
    assert set(REQUIRED_ROUTES).issubset(set(first.required_routes))
    assert set(first.required_artifacts) == set(REQUIRED_ARTIFACTS)
    assert first.interop_receipts_table == INTEROP_RECEIPTS_TABLE


def test_build_hallucinate_app_mobile_search_handoff_with_custom_payload() -> None:
    handoff = build_hallucinate_app_mobile_search_handoff(
        HALLUCINATE_APP_ROOT,
        capability="content_browser.search_handoff",
        payload={"query": "stable diffusion", "filter": {"mimetype": "model"}},
    )
    other = build_hallucinate_app_mobile_search_handoff(
        HALLUCINATE_APP_ROOT,
        capability="content_browser.search_handoff",
        payload={"query": "llama", "filter": {}},
    )
    assert handoff.payload_sha256 != other.payload_sha256
    assert handoff.content_cid != other.content_cid


def test_search_interface_js_exports_mobile_search_handoff_contract() -> None:
    exports = load_js_exports(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        [
            "HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT",
            "buildHallucinateAppMobileSearchHandoff",
        ],
    )
    contract = exports["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"]
    assert contract["contract_id"] == "interface contract hallucinate_app mobile"
    assert contract["source_surface"] == "hallucinate_app"
    assert contract["target_surface"] == "mobile"
    assert contract["route"] == "/v1/mobile/orb/invoke_service"
    assert contract["operation"] == "invoke_service"
    assert set(contract["required_artifacts"]) == set(REQUIRED_ARTIFACTS)


def test_mobile_descriptor_exports_hallucinate_app_interop_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "MOBILE_ORB_BRIDGE_OPERATIONS",
            "HALLUCINATE_APP_MOBILE_HANDOFF_OPERATIONS",
        ],
    )

    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert interface["metadata"]["interface_contract"] == "interface contract hallucinate_app mobile"
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert interface["metadata"]["source_surface"] == "hallucinate_app"
    assert interface["metadata"]["target_surface"] == "mobile"
    assert GOAL_ID in interface["objective_goals"]
    assert {method["name"] for method in interface["methods"]} == (
        HALLUCINATE_APP_HANDOFF_OPERATIONS
    )
    assert set(exports["HALLUCINATE_APP_MOBILE_HANDOFF_OPERATIONS"]) == (
        HALLUCINATE_APP_HANDOFF_OPERATIONS
    )
    assert set(HALLUCINATE_APP_HANDOFF_OPERATIONS) <= (
        MOBILE_ORB_OPERATIONS | {"diagnostics"}
    )
    assert descriptor["schema_refs"] == {
        "search_interface": (
            "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
        ),
        "test_interface": "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "time_series_schema": (
            "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
        ),
        "benchmark_schema_script": (
            "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
        ),
        "mobile_search_contract": "mobile/src/utils/hallucinateAppMobileSearchContract.js",
    }
    assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert set(REQUIRED_ROUTES).issubset(set(descriptor["runtime_handoff"]["routes"]))
    assert descriptor["runtime_handoff"]["interop_receipts_table"] == INTEROP_RECEIPTS_TABLE
    assert descriptor["validation"]["task_id"] == "HAO-740"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_search_contract_maps_actions_to_dat_methods_and_routes() -> None:
    exports = load_js_exports(
        "mobile/src/utils/hallucinateAppMobileSearchContract.js",
        [
            "HALLUCINATE_APP_SEARCH_ACTION_IDS",
            "HALLUCINATE_APP_SEARCH_ORB_OPERATION_BY_ACTION_ID",
            "HALLUCINATE_APP_SEARCH_DAT_METHOD_BY_ACTION_ID",
            "HALLUCINATE_APP_SEARCH_ROUTE_BY_ACTION_ID",
            "HALLUCINATE_APP_MOBILE_SEARCH_ACTION_CONTRACT",
        ],
    )

    action_ids = set(exports["HALLUCINATE_APP_SEARCH_ACTION_IDS"])
    contract = exports["HALLUCINATE_APP_MOBILE_SEARCH_ACTION_CONTRACT"]

    assert action_ids == HALLUCINATE_APP_SEARCH_ACTION_IDS
    assert contract["producer"] == "hallucinate_app"
    assert contract["consumer"] == "mobile"
    assert contract["interface_contract"] == "interface contract hallucinate_app mobile"
    assert contract["goal_id"] == GOAL_ID
    assert set(contract["action_ids"]) == action_ids
    assert set(contract["operation_by_action_id"]) == action_ids
    assert set(contract["dat_method_by_action_id"]) == action_ids
    assert set(contract["route_by_action_id"]) == action_ids
    assert set(contract["route_by_action_id"].values()).issubset(set(REQUIRED_ROUTES))
    assert (
        contract["operation_by_action_id"]["mobile_dispatch_hallucinate_app_search_query"]
        == "invoke_service"
    )
    assert (
        contract["dat_method_by_action_id"]["mobile_dispatch_hallucinate_app_search_query"]
        == "dispatchHallucinateAppSearchQuery"
    )


def test_mobile_orb_bridge_module_remains_parseable_after_contract_wiring() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert source.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1


def test_test_interface_html_embeds_the_interop_descriptor_fixture() -> None:
    source = (
        REPO_ROOT / "hallucinate_app/hallucinate_app/node/views/test_interface.html"
    ).read_text(encoding="utf-8")
    assert 'data-contract-id="interface contract hallucinate_app mobile"' in source
    for route in REQUIRED_ROUTES:
        assert route in source


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = (REPO_ROOT / "docs/integration/hallucinate_app-mobile.md").read_text(encoding="utf-8")
    discovery = (
        REPO_ROOT
        / "data/hallucinate_multimodal_control/discovery/2026-07-08-hao-740-objective-validation-repair.md"
    ).read_text(encoding="utf-8")
    attempt_three = (
        REPO_ROOT
        / "data/hallucinate_multimodal_control/discovery/2026-07-08-hao-740-attempt-3-validation-confirmation.md"
    ).read_text(encoding="utf-8")
    heap = (
        REPO_ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")

    required_terms = [
        "HAO-740",
        GOAL_ID,
        "objective/interoperability/hallucinate_app-mobile",
        "objective validation repair",
        "interface contract hallucinate_app mobile",
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "src/handsfree/hallucinate_app_mobile_interop.py",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/utils/hallucinateAppMobileSearchContract.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
    ]
    for content in (docs, discovery, attempt_three, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"

    attempt_three_record = (
        "data/hallucinate_multimodal_control/discovery/"
        "2026-07-08-hao-740-attempt-3-validation-confirmation.md"
    )
    assert attempt_three_record in docs
    assert attempt_three_record in heap
