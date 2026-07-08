"""Hallucinate App / mobile interoperability regression tests for HAO-740."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GOAL_ID = "VAIOS-G707"
INTERFACE_CONTRACT = "interface contract hallucinate_app mobile"
MOBILE_ORB_OPERATIONS = {
    "register_edge_capabilities",
    "publish_glasses_event",
    "bind_service",
    "invoke_service",
    "subscribe_service_updates",
    "dispatch_glasses_response",
    "revoke_binding",
}
REQUIRED_ARTIFACTS = {"interaction_envelope", "policy_decision", "mediation_receipt"}


def read_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


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
source = source.replace(/export class\s+([A-Za-z0-9_]+)\s*/g, (_, name) => {
  functionExports.push(name);
  return `class ${name} `;
});
source = source.replace(/export default\s+[A-Za-z0-9_]+;?/g, '');
source = `${source}\n${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {}, console, Date };
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
    source = read_text(path)
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(source)
        temp_path = handle.name
    try:
        subprocess.run(["node", "--check", temp_path], check=True, capture_output=True, text=True)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def build_search_handoff(query: str, options: dict) -> dict:
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
const query = process.argv[2];
const options = JSON.parse(process.argv[3]);
let source = fs.readFileSync(path, 'utf8');
const functionExports = [];
source = source.replace(/export const\s+([A-Za-z0-9_]+)\s*=/g, (_, name) => {
  return `const ${name} = exports.${name} =`;
});
source = source.replace(/export function\s+([A-Za-z0-9_]+)\s*\(/g, (_, name) => {
  functionExports.push(name);
  return `function ${name}(`;
});
source = source.replace(/export class\s+([A-Za-z0-9_]+)\s*/g, (_, name) => {
  functionExports.push(name);
  return `class ${name} `;
});
source = source.replace(/export default\s+[A-Za-z0-9_]+;?/g, '');
source = `${source}\n${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {}, console, Date };
vm.runInNewContext(source, context, { filename: path });
process.stdout.write(JSON.stringify(context.exports.buildHallucinateAppMobileSearchHandoff(query, options)));
"""
    result = subprocess.run(
        [
            "node",
            "-e",
            script,
            str(REPO_ROOT / "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"),
            query,
            json.dumps(options),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def test_search_interface_exports_hallucinate_app_mobile_handoff_descriptor() -> None:
    exports = load_js_exports(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        [
            "HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        ],
    )

    contract = exports["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert contract["contract_id"] == INTERFACE_CONTRACT
    assert contract["source_surface"] == "hallucinate_app"
    assert contract["target_surface"] == "mobile"
    assert contract["route"] == "/v1/mobile/orb/invoke_service"
    assert set(contract["required_artifacts"]) == REQUIRED_ARTIFACTS

    assert descriptor["interface_contract"] == INTERFACE_CONTRACT
    assert descriptor["goal_id"] == GOAL_ID
    assert descriptor["task_id"] == "HAO-740"
    assert descriptor["repair_task_id"] == "HAO-751"
    assert descriptor["runtime_handoff"]["operation"] == "invoke_service"
    assert set(descriptor["runtime_handoff"]["required_artifacts"]) == REQUIRED_ARTIFACTS
    assert (
        descriptor["validation"]["validation_confirmation_ref"]
        == "data/hallucinate_multimodal_control/discovery/"
        "2026-07-08-hao-740-attempt-4-validation-confirmation.md"
    )
    assert descriptor["validation"]["evidence"] == "objective validation repair"

    handoff = build_search_handoff(
        "vector search",
        {
            "filter": {"mimetype": "application/json"},
            "result_target": "mobile_card",
            "correlation_id": "test-correlation",
            "issued_at": "2026-07-08T00:00:00Z",
        },
    )
    assert handoff["contract_id"] == INTERFACE_CONTRACT
    assert handoff["interop_descriptor"]["descriptor_id"] == descriptor["descriptor_id"]
    assert set(handoff["required_artifacts"]) == REQUIRED_ARTIFACTS
    assert handoff["normalized_intent"]["method"] == "invoke_service"
    assert handoff["normalized_intent"]["target_ref"].endswith("invoke_service")
    assert handoff["payload"]["query"] == "vector search"
    assert handoff["payload"]["filter"] == {"mimetype": "application/json"}


def test_mobile_descriptor_exports_hallucinate_app_mobile_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "MOBILE_ORB_BRIDGE_OPERATIONS",
        ],
    )

    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert interface["metadata"]["interface_contract"] == INTERFACE_CONTRACT
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert interface["metadata"]["source_surface"] == "hallucinate_app"
    assert interface["metadata"]["target_surface"] == "mobile"
    assert GOAL_ID in interface["objective_goals"]
    assert MOBILE_ORB_OPERATIONS.issubset({method["name"] for method in interface["methods"]})
    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == MOBILE_ORB_OPERATIONS

    assert descriptor["descriptor_id"] == "hallucinate-app-mobile-interop@0.1.0"
    assert descriptor["interface"]["name"] == "hallucinate_app_mobile_interop"
    assert descriptor["runtime_handoff"]["route"] == "/v1/mobile/orb/invoke_service"
    assert set(descriptor["runtime_handoff"]["required_artifacts"]) == REQUIRED_ARTIFACTS
    assert descriptor["validation"]["task_id"] == "HAO-740"
    assert descriptor["validation"]["repair_task_id"] == "HAO-751"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert (
        descriptor["validation"]["validation_confirmation_ref"]
        == "data/hallucinate_multimodal_control/discovery/"
        "2026-07-08-hao-740-attempt-4-validation-confirmation.md"
    )
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_orb_bridge_advertises_hallucinate_app_descriptor() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = read_text("mobile/src/orb/metaGlassesMobileOrbBridge.js")

    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert re.search(r"localInterfaceKey\(\s*HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE\s*\)", source)
    assert "interop_descriptor: HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert source.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1


def test_test_interface_html_exposes_machine_readable_fixture() -> None:
    html = read_text("hallucinate_app/hallucinate_app/node/views/test_interface.html")

    assert 'id="hallucinate-app-mobile-interop-contract"' in html
    assert f'"contract_id": "{INTERFACE_CONTRACT}"' in html
    assert '"source_surface": "hallucinate_app"' in html
    assert '"target_surface": "mobile"' in html
    assert '"/v1/mobile/orb/invoke_service"' in html
    for artifact in REQUIRED_ARTIFACTS:
        assert artifact in html


def test_hallucinate_app_duckdb_receipt_schema_records_mobile_interop() -> None:
    schema = read_text("hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql")
    script = read_text("hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py")

    assert "CREATE TABLE IF NOT EXISTS hallucinate_app_mobile_interop_receipts" in schema
    assert f"DEFAULT '{INTERFACE_CONTRACT}'" in schema
    for column in (
        "source_surface",
        "target_surface",
        "route",
        "operation",
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
        "receipt_cid",
    ):
        assert re.search(rf"\b{column}\b", schema), f"missing {column}"

    assert "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID" in script
    assert "HALLUCINATE_APP_MOBILE_INTEROP_TABLE" in script
    assert "HALLUCINATE_APP_MOBILE_INTEROP_ROUTES" in script
    assert "HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS" in script
    assert INTERFACE_CONTRACT in script


def test_docs_discovery_and_heap_record_hao_740_validation_confirmation() -> None:
    docs = read_text("docs/integration/hallucinate_app-mobile.md")
    discovery = read_text(
        "data/hallucinate_multimodal_control/discovery/"
        "2026-07-08-hao-751-hao-740-validation-repair.md"
    )
    confirmation = read_text(
        "data/hallucinate_multimodal_control/discovery/"
        "2026-07-08-hao-740-attempt-4-validation-confirmation.md"
    )
    heap = read_text("implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md")

    required_terms = [
        "HAO-740",
        "HAO-751",
        GOAL_ID,
        "objective/interoperability/hallucinate_app-mobile",
        "objective validation repair",
        INTERFACE_CONTRACT,
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "docs/integration/hallucinate_app-mobile.md",
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
        "data/hallucinate_multimodal_control/discovery/2026-07-08-hao-740-attempt-4-validation-confirmation.md",
        "data/hallucinate_multimodal_control/discovery/2026-07-08-hao-751-hao-740-retry-budget.md",
    ]
    for content in (docs, discovery, confirmation, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"
