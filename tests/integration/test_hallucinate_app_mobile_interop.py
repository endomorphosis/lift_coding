"""Hallucinate App/mobile interoperability contract regression tests for HAO-740."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GOAL_ID = "VAIOS-G707"
CONTRACT_ID = "interface contract hallucinate_app mobile"
DISCOVERY_REPAIR = (
    "data/hallucinate_multimodal_control/discovery/"
    "2026-07-08-hao-740-objective-validation-repair.md"
)

MOBILE_ORB_OPERATIONS = {
    "register_edge_capabilities",
    "publish_glasses_event",
    "bind_service",
    "invoke_service",
    "subscribe_service_updates",
    "dispatch_glasses_response",
    "revoke_binding",
}


def load_js_exports(path: str, export_names: list[str]) -> dict:
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
source = source.replace(/export class\s+([A-Za-z0-9_]+)\s*/g, (_, name) => {
  classExports.push(name);
  return `class ${name} `;
});
source = source.replace(/export default\s+[A-Za-z0-9_]+;?/g, '');
source = `${source}\n${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
source = `${source}\n${classExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const emitted = [];
const context = {
  exports: {},
  console,
  Date,
  localStorage: undefined,
};
vm.runInNewContext(source, context, { filename: path });
const selected = {};
for (const name of requested) {
  selected[name] = context.exports[name];
}
if (selected.buildHallucinateAppMobileSearchHandoff) {
  selected.buildHallucinateAppMobileSearchHandoff =
    selected.buildHallucinateAppMobileSearchHandoff('latency regression', {
      filter: { mimetype: 'application/json' },
      result_target: 'mobile_card',
      correlation_id: 'hallucinate-app-mobile-search-test',
      issued_at: '2026-07-08T00:00:00.000Z',
    });
}
delete selected.SearchInterface;
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


def test_search_interface_exports_hallucinate_app_mobile_contract_and_handoff() -> None:
    exports = load_js_exports(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        [
            "HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT",
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "buildHallucinateAppMobileSearchHandoff",
        ],
    )

    contract = exports["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"]
    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert contract["contract_id"] == CONTRACT_ID
    assert contract["source_surface"] == "hallucinate_app"
    assert contract["target_surface"] == "mobile"
    assert contract["operation"] == "invoke_service"
    assert interface["metadata"]["interface_contract"] == CONTRACT_ID
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert interface["metadata"]["evidence"] == "objective validation repair"
    assert GOAL_ID in interface["objective_goals"]
    assert descriptor["descriptor_id"] == "hallucinate-app-mobile-interop@0.1.0"
    assert descriptor["validation"] == {
        "task_id": "HAO-740",
        "goal_id": GOAL_ID,
        "objective_gap_ref": (
            "data/hallucinate_multimodal_control/discovery/"
            "2026-07-08-hao-740-objective-gap-7edb316279e5.md"
        ),
        "validation_repair_ref": DISCOVERY_REPAIR,
        "evidence": "objective validation repair",
    }
    assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert descriptor["runtime_handoff"]["receipt_table"] == (
        "hallucinate_app_mobile_interop_receipts"
    )

    handoff = exports["buildHallucinateAppMobileSearchHandoff"]
    assert handoff["contract_id"] == CONTRACT_ID
    assert handoff["descriptor_id"] == descriptor["descriptor_id"]
    assert handoff["correlation_id"] == "hallucinate-app-mobile-search-test"
    assert handoff["issued_at"] == "2026-07-08T00:00:00.000Z"
    assert handoff["payload"]["intent"] == "hallucinate_app.content_browser.search"
    assert handoff["normalized_intent"]["target_ref"] == (
        "handsfree.meta_glasses.mobile.mobile_orb_bridge.invoke_service"
    )
    assert handoff["schema_refs"] == descriptor["schema_refs"]

    source = (
        REPO_ROOT
        / "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
    ).read_text(encoding="utf-8")
    assert "this.eventBus.emit('hallucinate-app:mobile-interop-handoff', mobileHandoff)" in source
    assert "this.eventBus.emit('hallucinate_app-mobile:handoff', mobileHandoff)" in source


def test_mobile_descriptor_exports_matching_hallucinate_app_mobile_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "MOBILE_ORB_BRIDGE_OPERATIONS",
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        ],
    )

    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == MOBILE_ORB_OPERATIONS
    assert interface["metadata"]["interface_contract"] == CONTRACT_ID
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert interface["objective_goals"] == [GOAL_ID]
    assert MOBILE_ORB_OPERATIONS.issubset({method["name"] for method in interface["methods"]})
    assert descriptor["interface"]["metadata"]["interface_contract"] == CONTRACT_ID
    assert descriptor["schema_refs"] == {
        "app_search_interface": (
            "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
        ),
        "app_test_interface": "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "time_series_schema": (
            "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/"
            "time_series_schema.sql"
        ),
        "benchmark_schema_script": (
            "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/"
            "create_benchmark_schema.py"
        ),
        "mobile_orb_descriptor": "mobile/src/orb/metaGlassesOrbDescriptors.js",
    }
    assert descriptor["runtime_handoff"]["event_names"] == [
        "hallucinate-app:mobile-interop-handoff",
        "hallucinate_app-mobile:handoff",
    ]
    assert descriptor["validation"]["task_id"] == "HAO-740"
    assert descriptor["validation"]["validation_repair_ref"] == DISCOVERY_REPAIR
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_orb_bridge_advertises_hallucinate_app_descriptor() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )

    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "hallucinateAppInteropInterfaceCid" in source
    assert "interop_descriptor: HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source


def test_test_interface_html_exposes_machine_readable_contract_fixture() -> None:
    html = (
        REPO_ROOT / "hallucinate_app/hallucinate_app/node/views/test_interface.html"
    ).read_text(encoding="utf-8")

    assert 'id="hallucinate-app-mobile-interop-contract"' in html
    assert f'data-contract-id="{CONTRACT_ID}"' in html
    match = re.search(
        r'<textarea id="mobileInteropContract"[^>]*>(.*?)</textarea>',
        html,
        flags=re.DOTALL,
    )
    assert match, "missing mobileInteropContract fixture"
    fixture = json.loads(match.group(1))
    assert fixture["contract_id"] == CONTRACT_ID
    assert fixture["source_surface"] == "hallucinate_app"
    assert fixture["target_surface"] == "mobile"
    assert "/v1/mobile/orb/invoke_service" in fixture["routes"]
    assert fixture["artifacts"] == ["interaction_envelope", "policy_decision", "mediation_receipt"]


def test_duckdb_schema_and_builder_record_mobile_interop_receipts() -> None:
    schema = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
    ).read_text(encoding="utf-8")
    builder = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
    ).read_text(encoding="utf-8")

    required_schema_terms = [
        "HAO-740 / VAIOS-G707",
        "hallucinate_app_mobile_interop_receipts",
        CONTRACT_ID,
        "interaction_envelope JSON",
        "policy_decision JSON",
        "mediation_receipt JSON",
        "idx_hallucinate_app_mobile_interop_receipts_route",
    ]
    for term in required_schema_terms:
        assert term in schema

    required_builder_terms = [
        "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID",
        "HALLUCINATE_APP_MOBILE_INTEROP_TABLE",
        "HALLUCINATE_APP_MOBILE_INTEROP_ROUTES",
        "HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS",
        CONTRACT_ID,
        "hallucinate_app_mobile_interop_receipts",
        "/v1/mobile/orb/invoke_service",
    ]
    for term in required_builder_terms:
        assert term in builder


def test_docs_discovery_and_heap_record_hao_740_objective_validation_repair() -> None:
    docs = (REPO_ROOT / "docs/integration/hallucinate_app-mobile.md").read_text(
        encoding="utf-8"
    )
    discovery = (REPO_ROOT / DISCOVERY_REPAIR).read_text(encoding="utf-8")
    heap = (
        REPO_ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")

    required_terms = [
        "HAO-740",
        "7edb316279e5a093e45d963b421d143361ec8d50",
        GOAL_ID,
        "objective validation repair",
        CONTRACT_ID,
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "docs/integration/hallucinate_app-mobile.md",
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
        DISCOVERY_REPAIR,
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content

    assert "No smaller child goals are required" in discovery
    assert "No smaller child goals are required" in heap
