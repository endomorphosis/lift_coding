"""hallucinate_app/mobile interoperability contract regression tests for HAO-752.

HAO-752 repairs the HAO-740 / VAIOS-G707 objective validation gap recorded in
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-752-objective-gap-7edb316279e5.md`.
The gap: `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
and `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
both referenced a `mobile/src/orb/metaGlassesOrbDescriptors.js::HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT`
export that did not exist, and `interface contract hallucinate_app mobile` had no
integration test or docs proving the handoff.

These tests prove that:
1. `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
   `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` / `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`
   for `VAIOS-G707` and `interface contract hallucinate_app mobile`.
2. `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises that descriptor during
   edge capability registration (mirroring the SwissKnife/ipfs_accelerate wiring).
3. `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
   builds a normalized mobile ORB handoff envelope that matches the mobile descriptor's
   contract id, route, and control-surface contract ref.
4. `hallucinate_app/hallucinate_app/node/views/test_interface.html` carries a
   machine-readable fixture consistent with the contract.
5. `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
   and `.../scripts/create_benchmark_schema.py` agree on the receipts table name,
   routes, and artifact refs used by the JS descriptor.
6. `docs/integration/hallucinate_app-mobile.md`, the discovery evidence file, and the
   objective heap all record this objective validation repair for `VAIOS-G707`.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

MOBILE_DESCRIPTORS_PATH = "mobile/src/orb/metaGlassesOrbDescriptors.js"
MOBILE_ORB_BRIDGE_PATH = "mobile/src/orb/metaGlassesMobileOrbBridge.js"
SEARCH_INTERFACE_PATH = (
    "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
)
TEST_INTERFACE_HTML_PATH = "hallucinate_app/hallucinate_app/node/views/test_interface.html"
TIME_SERIES_SCHEMA_PATH = "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
BENCHMARK_SCHEMA_SCRIPT_PATH = (
    "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
)
DOCS_PATH = "docs/integration/hallucinate_app-mobile.md"
OBJECTIVE_GAP_PATH = (
    "data/hallucinate_multimodal_control/discovery/2026-07-08-hao-752-objective-gap-7edb316279e5.md"
)
VALIDATION_REPAIR_PATH = (
    "data/hallucinate_multimodal_control/discovery/2026-07-08-hao-752-objective-validation-repair.md"
)
OBJECTIVE_HEAP_PATH = "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"

CONTRACT_ID = "interface contract hallucinate_app mobile"
GOAL_ID = "VAIOS-G707"
CONTROL_SURFACE_CONTRACT_REF = "control_surface_contract:hallucinate-app:remote-client"
MOBILE_ORB_OPERATIONS = {
    "register_edge_capabilities",
    "publish_glasses_event",
    "bind_service",
    "invoke_service",
    "subscribe_service_updates",
    "dispatch_glasses_response",
    "revoke_binding",
}
INTEROP_ROUTES = (
    "/v1/mobile/orb/register_edge_capabilities",
    "/v1/mobile/orb/publish_glasses_event",
    "/v1/mobile/orb/bind_service",
    "/v1/mobile/orb/invoke_service",
    "/v1/mobile/orb/dispatch_glasses_response",
    "/v1/mobile/orb/diagnostics",
)
ARTIFACT_REFS = ("interaction_envelope", "policy_decision", "mediation_receipt")
RECEIPTS_TABLE = "hallucinate_app_mobile_interop_receipts"


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


_LOADER_SCRIPT = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
const requested = JSON.parse(process.argv[2]);
const callSpec = process.argv[3] ? JSON.parse(process.argv[3]) : null;
let source = fs.readFileSync(path, 'utf8');
const functionExports = [];
const classExports = [];
// Strip default exports; they are not needed for evidence checks and are not
// valid outside an ES module context when run through vm as a plain script.
source = source.replace(/export default\s+[^;]+;/g, '');
source = source.replace(/export const\s+([A-Za-z0-9_]+)\s*=/g, (_, name) => {
  return `const ${name} = exports.${name} =`;
});
source = source.replace(/export function\s+([A-Za-z0-9_]+)\s*\(/g, (_, name) => {
  functionExports.push(name);
  return `function ${name}(`;
});
source = source.replace(/export class\s+([A-Za-z0-9_]+)/g, (_, name) => {
  classExports.push(name);
  return `class ${name}`;
});
source = `${source}\n${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}\n${classExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {}, console, Date };
vm.createContext(context);
vm.runInContext(source, context, { filename: path });
const selected = {};
for (const name of requested) {
  const value = context.exports[name];
  selected[name] = typeof value === 'function' ? { __is_function__: true } : value;
}
if (callSpec) {
  const fn = context.exports[callSpec.name];
  selected.__call_result__ = fn(...callSpec.args);
}
process.stdout.write(JSON.stringify(selected));
"""


def load_js_exports(path: str, export_names: list[str], call: dict | None = None) -> dict:
    result = subprocess.run(
        [
            "node",
            "-e",
            _LOADER_SCRIPT,
            str(REPO_ROOT / path),
            json.dumps(export_names),
            json.dumps(call) if call else "",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def assert_module_is_valid_esm(path: str) -> None:
    source = _read(path)
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(source)
        temp_path = handle.name
    try:
        subprocess.run(["node", "--check", temp_path], check=True, capture_output=True, text=True)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def extract_python_string_constant(source: str, name: str) -> str:
    match = re.search(rf'{name}\s*=\s*"([^"]+)"', source)
    assert match is not None, f"Could not find constant {name}"
    return match.group(1)


def extract_python_tuple_constant(source: str, name: str) -> tuple[str, ...]:
    match = re.search(rf"{name}\s*=\s*\(([^)]*)\)", source, re.DOTALL)
    assert match is not None, f"Could not find tuple constant {name}"
    values = re.findall(r'"([^"]+)"', match.group(1))
    return tuple(values)


# ─── Descriptor exports ─────────────────────────────────────────────────────


def test_mobile_descriptor_exports_hallucinate_app_interop_contract() -> None:
    exports = load_js_exports(
        MOBILE_DESCRIPTORS_PATH,
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID",
            "HALLUCINATE_APP_MOBILE_INTEROP_RECEIPTS_TABLE",
            "HALLUCINATE_APP_MOBILE_INTEROP_ROUTES",
            "HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS",
            "MOBILE_ORB_BRIDGE_OPERATIONS",
        ],
    )

    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert exports["HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID"] == CONTRACT_ID
    assert exports["HALLUCINATE_APP_MOBILE_INTEROP_RECEIPTS_TABLE"] == RECEIPTS_TABLE
    assert tuple(exports["HALLUCINATE_APP_MOBILE_INTEROP_ROUTES"]) == INTEROP_ROUTES
    assert tuple(exports["HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS"]) == ARTIFACT_REFS

    assert interface["metadata"]["interface_contract"] == CONTRACT_ID
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert interface["metadata"]["source_surface"] == "hallucinate_app"
    assert interface["metadata"]["target_surface"] == "mobile"
    assert interface["objective_goals"] == [GOAL_ID]
    assert {method["name"] for method in interface["methods"]} == MOBILE_ORB_OPERATIONS
    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == MOBILE_ORB_OPERATIONS

    assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert {"agent", "remote_client", "mobile"}.issubset(
        set(descriptor["runtime_handoff"]["allowed_surfaces"])
    )
    assert descriptor["runtime_handoff"]["receipts_table"] == RECEIPTS_TABLE
    assert tuple(descriptor["runtime_handoff"]["receipts_routes"]) == INTEROP_ROUTES
    assert tuple(descriptor["runtime_handoff"]["required_artifacts"]) == ARTIFACT_REFS
    assert descriptor["schema_refs"]["control_surface_contract"] == CONTROL_SURFACE_CONTRACT_REF
    assert descriptor["schema_refs"]["time_series_schema"] == TIME_SERIES_SCHEMA_PATH
    assert descriptor["schema_refs"]["benchmark_schema_script"] == BENCHMARK_SCHEMA_SCRIPT_PATH
    assert descriptor["schema_refs"]["search_interface"] == SEARCH_INTERFACE_PATH
    assert descriptor["schema_refs"]["test_interface"] == TEST_INTERFACE_HTML_PATH

    assert descriptor["validation"]["task_id"] == "HAO-740"
    assert descriptor["validation"]["repair_task_id"] == "HAO-752"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["objective_gap_ref"] == OBJECTIVE_GAP_PATH
    assert descriptor["validation"]["validation_repair_ref"] == VALIDATION_REPAIR_PATH
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_orb_bridge_wires_hallucinate_app_interop_descriptor() -> None:
    assert_module_is_valid_esm(MOBILE_ORB_BRIDGE_PATH)
    source = _read(MOBILE_ORB_BRIDGE_PATH)
    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    # The descriptor must be advertised during edge capability registration,
    # alongside the pre-existing SwissKnife/ipfs_accelerate interop descriptors.
    register_fn_match = re.search(
        r"async registerEdgeCapabilities\(input = \{\}\)[\s\S]*?\n  }\n", source
    )
    assert register_fn_match is not None
    register_fn_body = register_fn_match.group(0)
    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in register_fn_body
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in register_fn_body
    # Existing SwissKnife/mobile and ipfs_accelerate/mobile wiring must remain intact.
    assert "SWISSKNIFE_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "IPFS_ACCELERATE_MOBILE_INTEROP_DESCRIPTOR" in source
    assert source.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1


# ─── Search interface handoff ───────────────────────────────────────────────


def test_search_interface_exports_matching_contract() -> None:
    exports = load_js_exports(
        SEARCH_INTERFACE_PATH,
        ["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"],
    )
    contract = exports["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"]

    assert contract["contract_id"] == CONTRACT_ID
    assert contract["source_surface"] == "hallucinate_app"
    assert contract["target_surface"] == "mobile"
    assert contract["control_surface_contract_ref"] == CONTROL_SURFACE_CONTRACT_REF
    assert contract["route"] in INTEROP_ROUTES
    assert contract["operation"] in MOBILE_ORB_OPERATIONS
    assert set(contract["required_artifacts"]) == set(ARTIFACT_REFS)


def test_search_interface_builds_normalized_mobile_handoff() -> None:
    result = load_js_exports(
        SEARCH_INTERFACE_PATH,
        [],
        call={
            "name": "buildHallucinateAppMobileSearchHandoff",
            "args": [
                "meta glasses",
                {
                    "filter": {"mimetype": "video/mp4"},
                    "issued_at": "2026-07-08T00:00:00Z",
                    "correlation_id": "hao-752-test-correlation",
                },
            ],
        },
    )
    handoff = result["__call_result__"]

    assert handoff["contract_id"] == CONTRACT_ID
    assert handoff["source_surface"] == "hallucinate_app"
    assert handoff["target_surface"] == "mobile"
    assert handoff["control_surface_contract_ref"] == CONTROL_SURFACE_CONTRACT_REF
    assert handoff["correlation_id"] == "hao-752-test-correlation"
    assert handoff["issued_at"] == "2026-07-08T00:00:00Z"
    assert handoff["payload"]["intent"] == "hallucinate_app.content_browser.search"
    assert handoff["payload"]["query"] == "meta glasses"
    assert handoff["payload"]["filter"] == {"mimetype": "video/mp4"}
    assert handoff["normalized_intent"]["method"] == "invoke_service"
    assert handoff["normalized_intent"]["confidence"] == 1.0
    assert (
        handoff["normalized_intent"]["target_ref"]
        == "handsfree.meta_glasses.mobile.mobile_orb_bridge.invoke_service"
    )


# ─── test_interface.html machine-readable fixture ───────────────────────────


def test_test_interface_html_carries_machine_readable_fixture() -> None:
    html = _read(TEST_INTERFACE_HTML_PATH)
    assert f'data-contract-id="{CONTRACT_ID}"' in html

    match = re.search(
        r'<textarea id="mobileInteropContract"[^>]*readonly>(\{.*?\})</textarea>',
        html,
        re.DOTALL,
    )
    assert match is not None, "Expected a machine-readable interop fixture in test_interface.html"
    fixture = json.loads(match.group(1))

    assert fixture["contract_id"] == CONTRACT_ID
    assert fixture["source_surface"] == "hallucinate_app"
    assert fixture["target_surface"] == "mobile"
    assert fixture["control_surface_contract_ref"] == CONTROL_SURFACE_CONTRACT_REF
    assert set(fixture["routes"]).issubset(set(INTEROP_ROUTES))
    assert set(fixture["artifacts"]) == set(ARTIFACT_REFS)
    assert "mobileInteropResults" in html


# ─── DuckDB schema / benchmark script agreement ─────────────────────────────


def test_time_series_schema_defines_hallucinate_app_mobile_interop_receipts_table() -> None:
    sql = _read(TIME_SERIES_SCHEMA_PATH)
    assert (
        "mobile/src/orb/metaGlassesOrbDescriptors.js::HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT"
        in sql
    )
    table_match = re.search(
        r"CREATE TABLE IF NOT EXISTS hallucinate_app_mobile_interop_receipts \((.*?)\);",
        sql,
        re.DOTALL,
    )
    assert table_match is not None
    table_body = table_match.group(1)
    for column in (
        "receipt_id",
        "contract_id",
        "source_surface",
        "target_surface",
        "route",
        "operation",
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
    ):
        assert column in table_body
    assert f"DEFAULT '{CONTRACT_ID}'" in table_body
    assert "DEFAULT 'hallucinate_app'" in table_body
    assert "DEFAULT 'mobile'" in table_body


def test_benchmark_schema_script_constants_match_js_descriptor() -> None:
    script = _read(BENCHMARK_SCHEMA_SCRIPT_PATH)
    assert "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT and the" in script

    contract_id = extract_python_string_constant(
        script, "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID"
    )
    table_name = extract_python_string_constant(script, "HALLUCINATE_APP_MOBILE_INTEROP_TABLE")
    routes = extract_python_tuple_constant(script, "HALLUCINATE_APP_MOBILE_INTEROP_ROUTES")
    artifacts = extract_python_tuple_constant(
        script, "HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS"
    )

    assert contract_id == CONTRACT_ID
    assert table_name == RECEIPTS_TABLE
    assert routes == INTEROP_ROUTES
    assert artifacts == ARTIFACT_REFS

    exports = load_js_exports(
        MOBILE_DESCRIPTORS_PATH,
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID",
            "HALLUCINATE_APP_MOBILE_INTEROP_RECEIPTS_TABLE",
            "HALLUCINATE_APP_MOBILE_INTEROP_ROUTES",
            "HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS",
        ],
    )
    assert exports["HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID"] == contract_id
    assert exports["HALLUCINATE_APP_MOBILE_INTEROP_RECEIPTS_TABLE"] == table_name
    assert tuple(exports["HALLUCINATE_APP_MOBILE_INTEROP_ROUTES"]) == routes
    assert tuple(exports["HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS"]) == artifacts


# ─── Docs / discovery / objective heap evidence ─────────────────────────────


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = _read(DOCS_PATH)
    discovery = _read(VALIDATION_REPAIR_PATH)
    heap = _read(OBJECTIVE_HEAP_PATH)

    required_terms = [
        "HAO-740",
        "HAO-752",
        GOAL_ID,
        "objective validation repair",
        CONTRACT_ID,
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        MOBILE_DESCRIPTORS_PATH,
        SEARCH_INTERFACE_PATH,
        TEST_INTERFACE_HTML_PATH,
        TIME_SERIES_SCHEMA_PATH,
        BENCHMARK_SCHEMA_SCRIPT_PATH,
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content, f"Expected {term!r} in content"


def test_objective_gap_fingerprint_is_tied_to_the_repair() -> None:
    gap = _read(OBJECTIVE_GAP_PATH)
    repair = _read(VALIDATION_REPAIR_PATH)

    assert "7edb316279e5" in gap
    assert "7edb316279e5" in repair
    assert GOAL_ID in gap
    assert GOAL_ID in repair
    assert "objective validation repair" in repair


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
