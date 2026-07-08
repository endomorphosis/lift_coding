"""Hallucinate App / mobile interoperability contract regression tests for HAO-740.

These tests prove `hallucinate_app` interoperates with `mobile` through
importable contracts, interface descriptors, runtime handoff behavior, and
integration tests, satisfying the evidence requirements for VAIOS-G707
(`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`).

They verify that:
1. The Hallucinate App desktop search surface
   (`hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`)
   advertises `interface contract hallucinate_app mobile` and builds a
   normalized handoff envelope destined for the mobile ORB bridge.
2. The mobile ORB descriptor module
   (`mobile/src/orb/metaGlassesOrbDescriptors.js`) exports a matching
   `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE`/`_DESCRIPTOR` pair that names
   the same contract id, routes, and schema references.
3. The mobile ORB bridge
   (`mobile/src/orb/metaGlassesMobileOrbBridge.js`) advertises that
   descriptor during edge capability registration.
4. `hallucinate_app/hallucinate_app/node/views/test_interface.html` carries a
   machine-readable fixture of the same contract for manual/desktop probing.
5. The DuckDB schema/script pair
   (`hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
   and
   `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`)
   records `hallucinate_app_mobile_interop_receipts` time-series evidence for
   the handoff.
6. The discovery record and objective heap stay aligned with the objective
   validation repair for VAIOS-G707.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CONTRACT_ID = "interface contract hallucinate_app mobile"
GOAL_ID = "VAIOS-G707"

SEARCH_INTERFACE_PATH = (
    "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
)
TEST_INTERFACE_HTML_PATH = "hallucinate_app/hallucinate_app/node/views/test_interface.html"
TIME_SERIES_SCHEMA_PATH = (
    "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
)
BENCHMARK_SCHEMA_SCRIPT_PATH = (
    "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
)
MOBILE_ORB_DESCRIPTORS_PATH = "mobile/src/orb/metaGlassesOrbDescriptors.js"
MOBILE_ORB_BRIDGE_PATH = "mobile/src/orb/metaGlassesMobileOrbBridge.js"
DOCS_PATH = "docs/integration/hallucinate_app-mobile.md"
DISCOVERY_GAP_PATH = (
    "data/hallucinate_multimodal_control/discovery/"
    "2026-07-08-hao-740-objective-gap-7edb316279e5.md"
)
DISCOVERY_REPAIR_PATH = (
    "data/hallucinate_multimodal_control/discovery/"
    "2026-07-08-hao-740-objective-validation-repair.md"
)
HEAP_DOC_PATH = "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"


def read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def load_js_exports(path: str, export_names: list[str]) -> dict:
    """Load specific named exports (const/function) from an ES module by
    rewriting `export` statements into CommonJS-style assignments and running
    the result in a fresh V8 context via Node's `vm` module. Handles
    `export const`, `export function`, `export class`, and `export default`
    declarations so it is safe to use against modules that mix contract
    constants with class definitions.
    """
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
const requested = JSON.parse(process.argv[2]);
let source = fs.readFileSync(path, 'utf8');
const functionExports = [];
const classExports = [];
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
source = source.replace(/export default\s+[A-Za-z0-9_]+\s*;?/g, '');
source = `${source}\n${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
source = `${source}\n${classExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {}, module: { exports: {} }, console, require };
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


def call_js_function(
    path: str, function_name: str, args_json: list, extra_exports: list[str] | None = None
) -> dict:
    """Load an exported function from an ES module and invoke it with the
    given JSON-serializable arguments, returning the JSON-serialized result.
    """
    extra_exports = extra_exports or []
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
const functionName = process.argv[2];
const args = JSON.parse(process.argv[3]);
let source = fs.readFileSync(path, 'utf8');
const functionExports = [];
source = source.replace(/export const\s+([A-Za-z0-9_]+)\s*=/g, (_, name) => {
  return `const ${name} = exports.${name} =`;
});
source = source.replace(/export function\s+([A-Za-z0-9_]+)\s*\(/g, (_, name) => {
  functionExports.push(name);
  return `function ${name}(`;
});
source = source.replace(/export class\s+([A-Za-z0-9_]+)/g, (_, name) => `class ${name}`);
source = source.replace(/export default\s+[A-Za-z0-9_]+\s*;?/g, '');
source = `${source}\n${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {}, module: { exports: {} }, console, require, Date };
vm.runInNewContext(source, context, { filename: path });
const fn = context.exports[functionName];
const result = fn(...args);
process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run(
        ["node", "-e", script, str(REPO_ROOT / path), function_name, json.dumps(args_json)],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def assert_module_is_valid_esm(path: str) -> None:
    source = read_text(path)
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(source)
        temp_path = handle.name
    try:
        subprocess.run(["node", "--check", temp_path], check=True, capture_output=True, text=True)
    finally:
        Path(temp_path).unlink(missing_ok=True)


# ─── search_interface.js: Hallucinate App desktop -> mobile ORB handoff ────


def test_search_interface_module_is_valid_esm() -> None:
    assert_module_is_valid_esm(SEARCH_INTERFACE_PATH)


def test_search_interface_advertises_interop_contract() -> None:
    exports = load_js_exports(
        SEARCH_INTERFACE_PATH,
        ["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"],
    )
    contract = exports["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"]
    assert contract["contract_id"] == CONTRACT_ID
    assert contract["source_surface"] == "hallucinate_app"
    assert contract["target_surface"] == "mobile"
    assert contract["route"] == "/v1/mobile/orb/invoke_service"
    assert contract["operation"] == "invoke_service"
    assert contract["descriptor_path"] == SEARCH_INTERFACE_PATH
    assert set(contract["required_artifacts"]) == {
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
    }


def test_search_interface_builds_normalized_mobile_handoff() -> None:
    handoff = call_js_function(
        SEARCH_INTERFACE_PATH,
        "buildHallucinateAppMobileSearchHandoff",
        ["ipfs benchmark models", {"filter": {"mimetype": "model"}, "issued_at": "2026-07-08T00:00:00Z"}],
    )
    assert handoff["contract_id"] == CONTRACT_ID
    assert handoff["source_surface"] == "hallucinate_app"
    assert handoff["target_surface"] == "mobile"
    assert handoff["route"] == "/v1/mobile/orb/invoke_service"
    assert handoff["operation"] == "invoke_service"
    assert handoff["payload"]["query"] == "ipfs benchmark models"
    assert handoff["payload"]["filter"] == {"mimetype": "model"}
    assert handoff["normalized_intent"]["method"] == "invoke_service"
    assert handoff["normalized_intent"]["target_ref"] == (
        "handsfree.meta_glasses.mobile.mobile_orb_bridge.invoke_service"
    )
    assert handoff["normalized_intent"]["arguments"]["query"] == "ipfs benchmark models"
    assert handoff["issued_at"] == "2026-07-08T00:00:00Z"


def test_search_flow_wires_mobile_handoff_events() -> None:
    """The `search()` method must build and emit the mobile handoff so a
    live desktop search request reaches the mobile ORB bridge."""
    source = read_text(SEARCH_INTERFACE_PATH)
    search_method_match = re.search(r"\n  search\(query\) \{(.*?)\n  \}\n", source, re.S)
    assert search_method_match is not None, "search(query) method not found"
    body = search_method_match.group(1)
    assert "buildHallucinateAppMobileSearchHandoff(" in body
    assert "hallucinate_app-mobile:handoff" in body
    assert "this.emit('mobile-handoff', mobileHandoff)" in body


# ─── mobile/src/orb/metaGlassesOrbDescriptors.js: matching mobile descriptor ─


def test_mobile_descriptor_exports_hallucinate_app_interop_contract() -> None:
    exports = load_js_exports(
        MOBILE_ORB_DESCRIPTORS_PATH,
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "MOBILE_ORB_BRIDGE_OPERATIONS",
        ],
    )
    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]
    mobile_orb_operations = set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"])

    assert interface["metadata"]["interface_contract"] == CONTRACT_ID
    assert interface["metadata"]["source_surface"] == "hallucinate_app"
    assert interface["metadata"]["target_surface"] == "mobile"
    assert interface["objective_goals"] == [GOAL_ID]
    assert {method["name"] for method in interface["methods"]} == mobile_orb_operations

    assert descriptor["interface"]["metadata"]["interface_contract"] == CONTRACT_ID
    assert descriptor["schema_refs"]["time_series_schema"] == TIME_SERIES_SCHEMA_PATH
    assert descriptor["schema_refs"]["benchmark_schema_script"] == BENCHMARK_SCHEMA_SCRIPT_PATH
    assert descriptor["schema_refs"]["search_interface"] == SEARCH_INTERFACE_PATH
    assert descriptor["schema_refs"]["test_interface"] == TEST_INTERFACE_HTML_PATH
    assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert descriptor["runtime_handoff"]["route"] == "/v1/mobile/orb/invoke_service"
    assert descriptor["runtime_handoff"]["operation"] == "invoke_service"
    assert descriptor["runtime_handoff"]["interop_table"] == "hallucinate_app_mobile_interop_receipts"
    assert {"agent", "remote_client", "mobile"}.issubset(
        set(descriptor["runtime_handoff"]["allowed_surfaces"])
    )
    assert descriptor["validation"]["task_id"] == "HAO-740"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["objective_gap_ref"] == DISCOVERY_GAP_PATH
    assert descriptor["validation"]["validation_repair_ref"] == DISCOVERY_REPAIR_PATH
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_orb_bridge_registers_hallucinate_app_interop_descriptor() -> None:
    assert_module_is_valid_esm(MOBILE_ORB_BRIDGE_PATH)
    source = read_text(MOBILE_ORB_BRIDGE_PATH)
    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    # Registered alongside the existing swissknife/ipfs_accelerate interop
    # descriptors during edge capability registration.
    assert "localInterfaceCids[4]" in source
    assert source.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1


# ─── test_interface.html: machine-readable fixture for manual probing ─────


def test_interface_html_carries_matching_contract_fixture() -> None:
    html = read_text(TEST_INTERFACE_HTML_PATH)
    assert f'data-contract-id="{CONTRACT_ID}"' in html
    match = re.search(
        r'<textarea id="mobileInteropContract"[^>]*readonly>(\{.*?\})</textarea>', html, re.S
    )
    assert match is not None, "mobileInteropContract fixture textarea not found"
    fixture = json.loads(match.group(1))
    assert fixture["contract_id"] == CONTRACT_ID
    assert fixture["source_surface"] == "hallucinate_app"
    assert fixture["target_surface"] == "mobile"
    assert "/v1/mobile/orb/invoke_service" in fixture["routes"]
    assert set(fixture["artifacts"]) == {
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
    }


# ─── DuckDB schema + benchmark script: time-series evidence for receipts ──


def test_time_series_schema_declares_interop_receipts_table() -> None:
    sql = read_text(TIME_SERIES_SCHEMA_PATH)
    assert "CREATE TABLE IF NOT EXISTS hallucinate_app_mobile_interop_receipts" in sql
    assert f"DEFAULT '{CONTRACT_ID}'" in sql
    assert "idx_hallucinate_app_mobile_interop_receipts_route" in sql
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
        "receipt_cid",
    ):
        assert column in sql


def test_benchmark_schema_script_mirrors_interop_contract() -> None:
    script = read_text(BENCHMARK_SCHEMA_SCRIPT_PATH)
    assert f'HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID = "{CONTRACT_ID}"' in script
    assert 'HALLUCINATE_APP_MOBILE_INTEROP_TABLE = "hallucinate_app_mobile_interop_receipts"' in script
    assert "/v1/mobile/orb/invoke_service" in script
    assert "HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS" in script


def test_benchmark_script_routes_are_subset_of_mobile_orb_routes() -> None:
    """The routes recorded for benchmark schema evidence must stay within the
    routes advertised by the desktop fixture and mobile ORB bridge, so the
    time-series receipts stay consistent with the live contract."""
    script = read_text(BENCHMARK_SCHEMA_SCRIPT_PATH)
    route_match = re.search(
        r"HALLUCINATE_APP_MOBILE_INTEROP_ROUTES = \((.*?)\)", script, re.S
    )
    assert route_match is not None
    script_routes = set(re.findall(r'"(/v1/mobile/orb/[a-z_]+)"', route_match.group(1)))

    html = read_text(TEST_INTERFACE_HTML_PATH)
    html_match = re.search(r'"routes":\s*\[(.*?)\]', html, re.S)
    assert html_match is not None
    html_routes = set(re.findall(r'"(/v1/mobile/orb/[a-z_]+)"', html_match.group(1)))

    assert html_routes.issubset(script_routes)
    assert "/v1/mobile/orb/invoke_service" in script_routes
    assert "/v1/mobile/orb/register_edge_capabilities" in script_routes


# ─── Docs, discovery, and objective heap alignment ────────────────────────


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = read_text(DOCS_PATH)
    gap = read_text(DISCOVERY_GAP_PATH)
    repair = read_text(DISCOVERY_REPAIR_PATH)
    heap = read_text(HEAP_DOC_PATH)

    required_terms = [
        "HAO-740",
        GOAL_ID,
        "7edb316279e5",
        "objective validation repair",
        CONTRACT_ID,
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        DOCS_PATH,
        SEARCH_INTERFACE_PATH,
        TEST_INTERFACE_HTML_PATH,
        TIME_SERIES_SCHEMA_PATH,
        BENCHMARK_SCHEMA_SCRIPT_PATH,
        MOBILE_ORB_DESCRIPTORS_PATH,
    ]
    for content in (docs, repair, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"

    assert "HAO-740" in gap
    assert GOAL_ID in gap
    assert "7edb316279e5" in gap
    assert DISCOVERY_REPAIR_PATH in heap
