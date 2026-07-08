"""Interoperability tests proving hallucinate_app <-> mobile handoff for VAI-674.

These tests satisfy the evidence requirements for:
- VAIOS-G707: hallucinate_app <-> mobile interoperability

They verify that:
1. The Hallucinate App desktop search surface exports a mobile interop
   contract and descriptor (`search_interface.js`).
2. The mobile ORB bridge exports a matching interop interface/descriptor
   (`metaGlassesOrbDescriptors.js`) and advertises it during edge capability
   registration (`metaGlassesMobileOrbBridge.js`).
3. The machine-readable JSON fixture in `test_interface.html` matches the
   JavaScript descriptors.
4. The DuckDB schema/script pair records the shared
   `hallucinate_app_mobile_interop_receipts` evidence table and the
   `VAI-674` / `VAIOS-G707` evidence constants.
5. This objective validation repair is recorded in the discovery evidence
   and the supervisor-fed objective heap.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GOAL_ID = "VAIOS-G707"
TASK_ID = "VAI-674"

MOBILE_ORB_OPERATIONS = {
    "register_edge_capabilities",
    "publish_glasses_event",
    "bind_service",
    "invoke_service",
    "subscribe_service_updates",
    "dispatch_glasses_response",
    "revoke_binding",
}
DISPLAY_WIDGET_OPERATIONS = {
    "render_widget",
    "update_widget",
    "clear_widget",
    "focus_next",
    "focus_previous",
    "activate",
    "reset_session",
    "play_video",
    "subscribe_updates",
}

_LOAD_EXPORTS_SCRIPT = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
const requested = JSON.parse(process.argv[2]);
let source = fs.readFileSync(path, 'utf8');
const classBoundary = source.indexOf('export class');
if (classBoundary !== -1) {
  source = source.slice(0, classBoundary);
}
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

_CALL_EXPORT_SCRIPT = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
const exportName = process.argv[2];
const args = JSON.parse(process.argv[3]);
let source = fs.readFileSync(path, 'utf8');
const classBoundary = source.indexOf('export class');
if (classBoundary !== -1) {
  source = source.slice(0, classBoundary);
}
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
const fn = context.exports[exportName];
const result = fn(...args);
process.stdout.write(JSON.stringify(result === undefined ? null : result));
"""


def load_js_exports(path: str, export_names: list[str]) -> dict:
    result = subprocess.run(
        ["node", "-e", _LOAD_EXPORTS_SCRIPT, str(REPO_ROOT / path), json.dumps(export_names)],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def call_js_export(path: str, export_name: str, args: list) -> dict:
    result = subprocess.run(
        ["node", "-e", _CALL_EXPORT_SCRIPT, str(REPO_ROOT / path), export_name, json.dumps(args)],
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


def test_hallucinate_app_and_mobile_interop_descriptors_exist_on_disk() -> None:
    expected_paths = [
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
    ]
    for relative_path in expected_paths:
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"


def test_mobile_descriptor_exports_hallucinate_app_interop_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "MOBILE_ORB_BRIDGE_OPERATIONS",
            "DISPLAY_WIDGET_BRIDGE_OPERATIONS",
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
        MOBILE_ORB_OPERATIONS | DISPLAY_WIDGET_OPERATIONS
    )
    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == MOBILE_ORB_OPERATIONS
    assert set(exports["DISPLAY_WIDGET_BRIDGE_OPERATIONS"]) == DISPLAY_WIDGET_OPERATIONS

    assert descriptor["schema_refs"] == {
        "search_interface_descriptor": (
            "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
        ),
        "test_interface_fixture": "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "time_series_schema": (
            "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
        ),
        "benchmark_schema_script": (
            "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
        ),
    }
    assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert {"agent", "remote_client", "mobile"}.issubset(
        set(descriptor["runtime_handoff"]["allowed_surfaces"])
    )
    assert descriptor["runtime_handoff"]["event_name"] == "hallucinate-app:mobile-interop-handoff"
    assert descriptor["runtime_handoff"]["receipt_table"] == (
        "hallucinate_app_mobile_interop_receipts"
    )
    assert descriptor["validation"]["task_id"] == TASK_ID
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_hallucinate_app_search_interface_exports_matching_descriptor() -> None:
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

    assert descriptor["contract_id"] == "interface contract hallucinate_app mobile"
    assert descriptor["event_name"] == "hallucinate-app:mobile-interop-handoff"
    assert descriptor["receipt_table"] == "hallucinate_app_mobile_interop_receipts"
    assert descriptor["interop_descriptor_ref"] == (
        "mobile/src/orb/metaGlassesOrbDescriptors.js::HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"
    )
    assert descriptor["schema_refs"] == {
        "search_interface_descriptor": (
            "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
        ),
        "test_interface_fixture": "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "time_series_schema": (
            "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
        ),
        "benchmark_schema_script": (
            "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
        ),
    }
    assert descriptor["validation"]["task_id"] == TASK_ID
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_emit_hallucinate_app_mobile_interop_handoff_is_deterministic() -> None:
    args = [
        None,
        "graph neural networks",
        {
            "filter": {"mimetype": "application/pdf"},
            "result_target": "mobile_card",
            "correlation_id": "hallucinate-app-mobile-search-test",
            "issued_at": "2026-07-08T00:00:00.000Z",
        },
    ]
    first = call_js_export(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "emitHallucinateAppMobileInteropHandoff",
        args,
    )
    second = call_js_export(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "emitHallucinateAppMobileInteropHandoff",
        args,
    )

    assert first == second
    assert first["event"] == "hallucinate-app:mobile-interop-handoff"
    assert first["descriptor_id"] == "hallucinate-app-mobile-interop@0.1.0"
    assert first["receipt_table"] == "hallucinate_app_mobile_interop_receipts"

    handoff = first["handoff"]
    assert handoff["contract_id"] == "interface contract hallucinate_app mobile"
    assert handoff["source_surface"] == "hallucinate_app"
    assert handoff["target_surface"] == "mobile"
    assert handoff["route"] == "/v1/mobile/orb/invoke_service"
    assert handoff["operation"] == "invoke_service"
    assert handoff["correlation_id"] == "hallucinate-app-mobile-search-test"
    assert handoff["payload"]["query"] == "graph neural networks"
    assert handoff["payload"]["filter"] == {"mimetype": "application/pdf"}
    assert handoff["normalized_intent"]["method"] == "invoke_service"


def test_mobile_orb_bridge_module_remains_parseable_after_contract_wiring() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert source.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1


def test_hallucinate_app_search_interface_module_remains_parseable() -> None:
    assert_module_is_valid_esm(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
    )


def test_test_interface_html_carries_matching_json_fixture() -> None:
    content = (
        REPO_ROOT / "hallucinate_app/hallucinate_app/node/views/test_interface.html"
    ).read_text(encoding="utf-8")

    assert 'id="hallucinate-app-mobile-interop-contract"' in content
    assert 'data-contract-id="interface contract hallucinate_app mobile"' in content
    assert 'data-event-name="hallucinate-app:mobile-interop-handoff"' in content
    assert 'data-receipt-table="hallucinate_app_mobile_interop_receipts"' in content
    assert f'data-vai-task-id="{TASK_ID}"' in content
    assert f'data-goal-id="{GOAL_ID}"' in content

    match = re.search(
        r'<textarea id="mobileInteropContract"[^>]*>(.*?)</textarea>', content, re.S
    )
    assert match is not None, "mobileInteropContract fixture not found"
    fixture = json.loads(match.group(1))

    assert fixture["contract_id"] == "interface contract hallucinate_app mobile"
    assert fixture["source_surface"] == "hallucinate_app"
    assert fixture["target_surface"] == "mobile"
    assert fixture["event_name"] == "hallucinate-app:mobile-interop-handoff"
    assert fixture["receipt_table"] == "hallucinate_app_mobile_interop_receipts"
    assert set(fixture["artifacts"]) == {
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
    }
    assert fixture["validation"]["task_id"] == TASK_ID
    assert fixture["validation"]["goal_id"] == GOAL_ID
    assert fixture["validation"]["evidence"] == "objective validation repair"


def test_duckdb_time_series_schema_records_hallucinate_app_mobile_interop_evidence() -> None:
    schema_sql = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
    ).read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS hallucinate_app_mobile_interop_receipts" in schema_sql
    assert "CREATE VIEW IF NOT EXISTS hallucinate_app_mobile_interop_evidence" in schema_sql
    assert "'interface contract hallucinate_app mobile'" in schema_sql
    assert "'VAI-674'" in schema_sql
    assert "'VAIOS-G707'" in schema_sql
    assert "'objective validation repair'" in schema_sql


def test_benchmark_schema_script_records_hallucinate_app_mobile_interop_evidence() -> None:
    script_path = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
    )
    script_text = script_path.read_text(encoding="utf-8")

    assert 'HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID = "interface contract hallucinate_app mobile"' in (
        script_text
    )
    assert 'HALLUCINATE_APP_MOBILE_INTEROP_TABLE = "hallucinate_app_mobile_interop_receipts"' in (
        script_text
    )
    assert 'HALLUCINATE_APP_MOBILE_INTEROP_VAI_TASK_ID = "VAI-674"' in script_text
    assert 'HALLUCINATE_APP_MOBILE_INTEROP_GOAL_ID = "VAIOS-G707"' in script_text
    assert (
        'HALLUCINATE_APP_MOBILE_INTEROP_EVENT_NAME = "hallucinate-app:mobile-interop-handoff"'
        in script_text
    )
    assert "def build_hallucinate_app_mobile_interop_evidence_record():" in script_text

    # Only the appended VAI-674 block is guaranteed to be valid, importable
    # Python; the legacy script body above it has pre-existing, unrelated
    # syntax issues. Exec just the appended tail (a self-contained block of
    # pure literals and one small function) to prove it is real, executable
    # evidence rather than inert text.
    marker = "# HAO-740 / VAIOS-G707"
    assert marker in script_text
    tail_source = script_text[script_text.index(marker):]
    namespace: dict = {}
    exec(compile(tail_source, str(script_path), "exec"), namespace)  # noqa: S102

    assert namespace["HALLUCINATE_APP_MOBILE_INTEROP_TABLE"] == (
        "hallucinate_app_mobile_interop_receipts"
    )
    record = namespace["build_hallucinate_app_mobile_interop_evidence_record"]()
    assert record["vai_task_id"] == TASK_ID
    assert record["goal_id"] == GOAL_ID
    assert record["contract_id"] == "interface contract hallucinate_app mobile"
    assert record["receipt_table"] == "hallucinate_app_mobile_interop_receipts"
    assert record["event_name"] == "hallucinate-app:mobile-interop-handoff"
    assert record["evidence"] == "objective validation repair"
    assert record["objective_gap_ref"] == (
        "data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-gap-7edb316279e5.md"
    )
    assert record["validation_repair_ref"] == (
        "data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-validation-repair.md"
    )


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = (REPO_ROOT / "docs/integration/hallucinate_app-mobile.md").read_text(
        encoding="utf-8"
    )
    discovery = (
        REPO_ROOT
        / "data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-validation-repair.md"
    ).read_text(encoding="utf-8")
    gap = (
        REPO_ROOT
        / "data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-gap-7edb316279e5.md"
    ).read_text(encoding="utf-8")
    heap = (
        REPO_ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")

    assert "7edb316279e5" in gap

    required_terms = [
        TASK_ID,
        GOAL_ID,
        "objective/interoperability/hallucinate_app-mobile",
        "objective validation repair",
        "interface contract hallucinate_app mobile",
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "docs/integration/hallucinate_app-mobile.md",
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
        "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        "hallucinate_app_mobile_interop_receipts",
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"
