"""Hallucinate App / mobile interoperability regression tests for MGW-579."""

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
HALLUCINATE_APP_MOBILE_OPERATIONS = {
    "content_browser_search_handoff",
    "render_mobile_result_card",
    "dispatch_glasses_response_receipt",
}


def _transform_esm_for_vm(source: str) -> str:
    exported_names: list[str] = []

    def export_const(match: re.Match[str]) -> str:
        name = match.group(1)
        exported_names.append(name)
        return f"const {name} = exports.{name} ="

    def export_function(match: re.Match[str]) -> str:
        name = match.group(1)
        exported_names.append(name)
        return f"function {name}("

    def export_class(match: re.Match[str]) -> str:
        name = match.group(1)
        exported_names.append(name)
        return f"class {name}"

    source = re.sub(r"export const\s+([A-Za-z0-9_]+)\s*=", export_const, source)
    source = re.sub(r"export function\s+([A-Za-z0-9_]+)\s*\(", export_function, source)
    source = re.sub(r"export class\s+([A-Za-z0-9_]+)", export_class, source)
    source = re.sub(r"export default\s+[A-Za-z0-9_]+;?", "", source)
    source = (
        source
        + "\n"
        + "\n".join(
            f"exports.{name} = typeof {name} !== 'undefined' ? {name} : exports.{name};"
            for name in exported_names
        )
    )
    return source


def load_js_exports(path: str, export_names: list[str], expression: str | None = None) -> dict:
    transformed = _transform_esm_for_vm((REPO_ROOT / path).read_text(encoding="utf-8"))
    script = r"""
const vm = require('vm');
const source = process.argv[1];
const requested = JSON.parse(process.argv[2]);
const expression = process.argv[3] || '';
const context = {
  exports: {},
  console,
  Date,
  setTimeout,
  clearTimeout,
};
vm.runInNewContext(source, context, { filename: 'transformed-module.js' });
const selected = {};
for (const name of requested) {
  selected[name] = context.exports[name];
}
if (expression) {
  selected.__expression_result = vm.runInNewContext(expression, context);
}
process.stdout.write(JSON.stringify(selected));
"""
    result = subprocess.run(
        ["node", "-e", script, transformed, json.dumps(export_names), expression or ""],
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


def test_search_interface_exports_mobile_handoff_descriptor_and_payload() -> None:
    exports = load_js_exports(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        [
            "HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        ],
        expression=(
            "exports.buildHallucinateAppMobileSearchHandoff('vector search', "
            "{filter: {mimetype: 'application/json'}, result_target: 'mobile_card', "
            "correlation_id: 'corr-1', issued_at: '2026-07-08T00:00:00Z'})"
        ),
    )

    contract = exports["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]
    payload = exports["__expression_result"]

    assert contract["contract_id"] == INTERFACE_CONTRACT
    assert contract["source_surface"] == "hallucinate_app"
    assert contract["target_surface"] == "mobile"
    assert contract["route"] == "/v1/mobile/orb/invoke_service"
    assert contract["operation"] == "invoke_service"
    assert contract["required_artifacts"] == [
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
    ]

    assert descriptor["descriptor_id"] == "hallucinate-app-mobile-interop@0.1.0"
    assert descriptor["runtime_handoff"]["event_name"] == (
        "hallucinate-app:mobile-interop-handoff"
    )
    assert descriptor["runtime_handoff"]["receipt_table"] == (
        "hallucinate_app_mobile_interop_receipts"
    )
    assert descriptor["validation"]["task_id"] == "MGW-579"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"

    assert payload["contract_id"] == INTERFACE_CONTRACT
    assert payload["target_surface"] == "mobile"
    assert payload["payload"]["query"] == "vector search"
    assert payload["payload"]["filter"] == {"mimetype": "application/json"}
    assert payload["normalized_intent"]["target_ref"] == (
        "handsfree.meta_glasses.mobile.mobile_orb_bridge.invoke_service"
    )
    assert payload["correlation_id"] == "corr-1"
    assert payload["issued_at"] == "2026-07-08T00:00:00Z"


def test_mobile_descriptor_exports_matching_hallucinate_app_contract() -> None:
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

    assert interface["metadata"]["interface_contract"] == INTERFACE_CONTRACT
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert interface["metadata"]["source_surface"] == "hallucinate_app"
    assert interface["metadata"]["target_surface"] == "mobile"
    assert interface["objective_goals"] == [GOAL_ID]
    assert {method["name"] for method in interface["methods"]} == (
        MOBILE_ORB_OPERATIONS | HALLUCINATE_APP_MOBILE_OPERATIONS
    )
    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == MOBILE_ORB_OPERATIONS
    assert set(exports["HALLUCINATE_APP_MOBILE_INTEROP_OPERATIONS"]) == (
        HALLUCINATE_APP_MOBILE_OPERATIONS
    )
    assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert descriptor["runtime_handoff"]["receipt_table"] == (
        "hallucinate_app_mobile_interop_receipts"
    )
    assert descriptor["validation"]["task_id"] == "MGW-579"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_orb_bridge_advertises_hallucinate_app_descriptor() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )

    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "hallucinateAppInteropInterfaceCid" in source
    assert "this.localInterfaceCids[4]" in source
    assert "interop_descriptor: HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source


def test_test_interface_fixture_and_duckdb_schema_record_receipt_contract() -> None:
    fixture = (
        REPO_ROOT / "hallucinate_app/hallucinate_app/node/views/test_interface.html"
    ).read_text(encoding="utf-8")
    schema = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
    ).read_text(encoding="utf-8")
    script = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
    ).read_text(encoding="utf-8")

    assert 'data-contract-id="interface contract hallucinate_app mobile"' in fixture
    assert "/v1/mobile/orb/register_edge_capabilities" in fixture
    assert "/v1/mobile/orb/invoke_service" in fixture
    assert "/v1/mobile/orb/dispatch_glasses_response" in fixture
    assert "interaction_envelope" in fixture
    assert "policy_decision" in fixture
    assert "mediation_receipt" in fixture

    assert "CREATE TABLE IF NOT EXISTS hallucinate_app_mobile_interop_receipts" in schema
    assert "contract_id VARCHAR NOT NULL DEFAULT 'interface contract hallucinate_app mobile'" in schema
    assert "interaction_envelope JSON" in schema
    assert "policy_decision JSON" in schema
    assert "mediation_receipt JSON" in schema

    assert (
        'HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID = "interface contract hallucinate_app mobile"'
        in script
    )
    assert 'HALLUCINATE_APP_MOBILE_INTEROP_TABLE = "hallucinate_app_mobile_interop_receipts"' in script
    assert '"/v1/mobile/orb/invoke_service"' in script


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = (REPO_ROOT / "docs/integration/hallucinate_app-mobile.md").read_text(
        encoding="utf-8"
    )
    discovery = (
        REPO_ROOT
        / "data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-validation-repair.md"
    ).read_text(encoding="utf-8")
    heap = (
        Path("/home/barberb/lift_coding/implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md")
    ).read_text(encoding="utf-8")

    for text in (docs, discovery, heap):
        assert GOAL_ID in text
        assert "objective validation repair" in text
        assert INTERFACE_CONTRACT in text
        assert "tests/integration/test_hallucinate_app_mobile_interop.py" in text
        assert "docs/integration/hallucinate_app-mobile.md" in text
        assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in text
        assert "hallucinate_app_mobile_interop_receipts" in text

    assert "No smaller child goals are needed" in heap
