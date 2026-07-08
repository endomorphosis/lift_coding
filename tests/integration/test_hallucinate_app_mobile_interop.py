"""Hallucinate App/mobile interoperability regression tests for MGW-579."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GOAL_ID = "VAIOS-G707"
CONTRACT_ID = "interface contract hallucinate_app mobile"
DESCRIPTOR_ID = "hallucinate-app-mobile-interop@0.1.0"
RECEIPT_TABLE = "hallucinate_app_mobile_interop_receipts"
MOBILE_ORB_OPERATIONS = {
    "register_edge_capabilities",
    "publish_glasses_event",
    "bind_service",
    "invoke_service",
    "subscribe_service_updates",
    "dispatch_glasses_response",
    "revoke_binding",
}
HALLUCINATE_APP_OPERATIONS = {
    "content_browser_search",
    "render_mobile_search_results",
    "open_mobile_content_result",
    "dispatch_glasses_response",
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
source = source.replace(/export class\s+([A-Za-z0-9_]+)/g, (_, name) => {
  classExports.push(name);
  return `class ${name}`;
});
source = source.replace(/export default\s+([A-Za-z0-9_]+);?/g, '');
source = `${source}\n${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
source = `${source}\n${classExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {}, Date };
vm.runInNewContext(source, context, { filename: path });
const selected = {};
for (const name of requested) {
  const value = context.exports[name];
  if (name === 'buildHallucinateAppMobileSearchHandoff' && typeof value === 'function') {
    selected[name] = value('vector clock', {
      correlation_id: 'test-correlation',
      issued_at: '2026-07-08T00:00:00Z',
      filter: { mimetype: 'application/json' },
      result_target: 'mobile_card',
    });
  } else if (typeof value !== 'function') {
    selected[name] = value;
  }
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


def test_hallucinate_app_search_interface_builds_mobile_handoff() -> None:
    exports = load_js_exports(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        [
            "HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "buildHallucinateAppMobileSearchHandoff",
        ],
    )

    contract = exports["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]
    handoff = exports["buildHallucinateAppMobileSearchHandoff"]

    assert contract["contract_id"] == CONTRACT_ID
    assert contract["source_surface"] == "hallucinate_app"
    assert contract["target_surface"] == "mobile"
    assert contract["route"] == "/v1/mobile/orb/invoke_service"
    assert descriptor["descriptor_id"] == DESCRIPTOR_ID
    assert descriptor["runtime_handoff"]["event_name"] == "hallucinate-app:mobile-interop-handoff"
    assert descriptor["runtime_handoff"]["receipt_table"] == RECEIPT_TABLE
    assert descriptor["validation"]["task_id"] == "MGW-579"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"
    assert handoff["contract_id"] == CONTRACT_ID
    assert handoff["descriptor_id"] == DESCRIPTOR_ID
    assert handoff["payload"]["intent"] == "hallucinate_app.content_browser.search"


def test_mobile_descriptor_exports_hallucinate_app_interop_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "HALLUCINATE_APP_MOBILE_INTEROP_OPERATIONS",
            "MOBILE_ORB_BRIDGE_OPERATIONS",
        ],
    )

    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert interface["metadata"]["interface_contract"] == CONTRACT_ID
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert interface["metadata"]["source_surface"] == "hallucinate_app"
    assert interface["metadata"]["target_surface"] == "mobile"
    assert interface["objective_goals"] == [GOAL_ID]
    assert {method["name"] for method in interface["methods"]} == (
        MOBILE_ORB_OPERATIONS | HALLUCINATE_APP_OPERATIONS
    )
    assert set(exports["HALLUCINATE_APP_MOBILE_INTEROP_OPERATIONS"]) == (
        HALLUCINATE_APP_OPERATIONS
    )
    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == MOBILE_ORB_OPERATIONS
    assert descriptor["descriptor_id"] == DESCRIPTOR_ID
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
    }
    assert descriptor["runtime_handoff"]["route"] == "/v1/mobile/orb/invoke_service"
    assert descriptor["runtime_handoff"]["receipt_table"] == RECEIPT_TABLE
    assert descriptor["validation"]["validation_repair_ref"].endswith(
        "2026-07-08-mgw-579-objective-validation-repair.md"
    )


def test_mobile_orb_bridge_advertises_hallucinate_app_descriptor() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )
    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "hallucinateAppInteropInterfaceCid" in source
    assert "interop_descriptor: HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source


def test_test_interface_html_contains_machine_readable_contract_fixture() -> None:
    html = (
        REPO_ROOT / "hallucinate_app/hallucinate_app/node/views/test_interface.html"
    ).read_text(encoding="utf-8")
    match = re.search(
        r'<textarea id="mobileInteropContract"[^>]*>(?P<payload>\{.*?\})</textarea>',
        html,
        re.DOTALL,
    )
    assert match, "missing mobileInteropContract fixture"
    fixture = json.loads(match.group("payload"))
    assert fixture["descriptor_id"] == DESCRIPTOR_ID
    assert fixture["contract_id"] == CONTRACT_ID
    assert fixture["source_surface"] == "hallucinate_app"
    assert fixture["target_surface"] == "mobile"
    assert "/v1/mobile/orb/invoke_service" in fixture["routes"]
    assert {"interaction_envelope", "policy_decision", "mediation_receipt"}.issubset(
        set(fixture["artifacts"])
    )


def test_duckdb_receipt_schema_and_benchmark_script_record_interop_evidence() -> None:
    schema = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
    ).read_text(encoding="utf-8")
    script = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
    ).read_text(encoding="utf-8")

    assert f"CREATE TABLE IF NOT EXISTS {RECEIPT_TABLE}" in schema
    assert CONTRACT_ID in schema
    assert "interaction_envelope JSON" in schema
    assert "policy_decision JSON" in schema
    assert "mediation_receipt JSON" in schema
    assert "idx_hallucinate_app_mobile_interop_receipts_route" in schema
    assert 'HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID = "interface contract hallucinate_app mobile"' in script
    assert f'HALLUCINATE_APP_MOBILE_INTEROP_TABLE = "{RECEIPT_TABLE}"' in script
    assert '"/v1/mobile/orb/invoke_service"' in script
    assert '"mediation_receipt"' in script


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = (REPO_ROOT / "docs/integration/hallucinate_app-mobile.md").read_text(
        encoding="utf-8"
    )
    discovery = (
        REPO_ROOT
        / "data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-validation-repair.md"
    ).read_text(encoding="utf-8")
    heap = (
        REPO_ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")

    for text in (docs, discovery, heap):
        assert GOAL_ID in text
        assert CONTRACT_ID in text
        assert "objective validation repair" in text
        assert "tests/integration/test_hallucinate_app_mobile_interop.py" in text
        assert "docs/integration/hallucinate_app-mobile.md" in text
        assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in text
        assert RECEIPT_TABLE in text
