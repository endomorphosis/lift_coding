"""Hallucinate App / mobile interoperability regression tests for VAI-685."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GOAL_ID = "VAIOS-G707"
INTERFACE_CONTRACT = "interface contract hallucinate_app mobile"
SEARCH_INTERFACE = (
    "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
)
TEST_INTERFACE = "hallucinate_app/hallucinate_app/node/views/test_interface.html"
MOBILE_DESCRIPTORS = "mobile/src/orb/metaGlassesOrbDescriptors.js"
MOBILE_BRIDGE = "mobile/src/orb/metaGlassesMobileOrbBridge.js"
TIME_SERIES_SCHEMA = (
    "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
)
BENCHMARK_SCHEMA_SCRIPT = (
    "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
)

MOBILE_ORB_ROUTES = {
    "/v1/mobile/orb/register_edge_capabilities",
    "/v1/mobile/orb/invoke_service",
    "/v1/mobile/orb/dispatch_glasses_response",
    "/v1/mobile/orb/diagnostics",
}
MOBILE_ORB_OPERATIONS = {
    "register_edge_capabilities",
    "invoke_service",
    "dispatch_glasses_response",
    "diagnostics",
}
REQUIRED_ARTIFACTS = {"interaction_envelope", "policy_decision", "mediation_receipt"}


def transform_esm_for_vm(source: str) -> str:
    script = r"""
const fs = require('fs');
let source = fs.readFileSync(process.argv[1], 'utf8');
const functionExports = [];
const classExports = [];
source = source.replace(/export default\s+([A-Za-z0-9_]+);?/g, (_, name) => {
  return `exports.default = ${name};`;
});
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
source = `${source}
${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}
${classExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
process.stdout.write(source);
"""
    result = subprocess.run(
        ["node", "-e", script, str(REPO_ROOT / source)],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


def load_js_exports(path: str, export_names: list[str]) -> dict:
    script = r"""
const fs = require('fs');
const vm = require('vm');
const requested = JSON.parse(process.argv[2]);
let source = fs.readFileSync(process.argv[1], 'utf8');
const functionExports = [];
const classExports = [];
source = source.replace(/export default\s+([A-Za-z0-9_]+);?/g, (_, name) => {
  return `exports.default = ${name};`;
});
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
source = `${source}
${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}
${classExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {}, console, Date, setTimeout, clearTimeout };
vm.runInNewContext(source, context, { filename: process.argv[1] });
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


def run_search_interface_probe() -> dict:
    script = r"""
const fs = require('fs');
const vm = require('vm');
let source = fs.readFileSync(process.argv[1], 'utf8');
const functionExports = [];
const classExports = [];
source = source.replace(/export default\s+([A-Za-z0-9_]+);?/g, (_, name) => {
  return `exports.default = ${name};`;
});
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
source = `${source}
${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}
${classExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {}, console, Date, setTimeout, clearTimeout };
vm.runInNewContext(source, context, { filename: process.argv[1] });
const emitted = [];
const eventBus = { emit: (event, data) => emitted.push({ event, data }) };
const instance = new context.exports.SearchInterface({ bridge: {}, eventBus });
instance.on('mobile-handoff', (data) => emitted.push({ event: 'direct:mobile-handoff', data }));
instance.currentFilter = { mimetype: 'text/plain' };
instance.search('semantic photos');
const handoff = context.exports.buildHallucinateAppMobileSearchHandoff('semantic photos', {
  filter: { mimetype: 'text/plain' },
  correlation_id: 'vai-685-correlation',
  issued_at: '2026-07-08T00:00:00.000Z',
});
process.stdout.write(JSON.stringify({
  contract: context.exports.HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT,
  handoff,
  emitted,
}));
"""
    result = subprocess.run(
        ["node", "-e", script, str(REPO_ROOT / SEARCH_INTERFACE)],
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


def test_expected_interop_artifacts_exist() -> None:
    for relative_path in [
        SEARCH_INTERFACE,
        TEST_INTERFACE,
        MOBILE_DESCRIPTORS,
        MOBILE_BRIDGE,
        TIME_SERIES_SCHEMA,
        BENCHMARK_SCHEMA_SCRIPT,
    ]:
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"


def test_search_interface_exports_and_emits_mobile_handoff() -> None:
    probe = run_search_interface_probe()
    contract = probe["contract"]
    handoff = probe["handoff"]

    assert contract["contract_id"] == INTERFACE_CONTRACT
    assert contract["source_surface"] == "hallucinate_app"
    assert contract["target_surface"] == "mobile"
    assert contract["route"] == "/v1/mobile/orb/invoke_service"
    assert set(contract["required_artifacts"]) == REQUIRED_ARTIFACTS
    assert contract["validation"]["task_id"] == "VAI-685"
    assert contract["validation"]["goal_id"] == GOAL_ID
    assert contract["validation"]["evidence"] == "objective validation repair"

    assert handoff["contract_id"] == INTERFACE_CONTRACT
    assert handoff["correlation_id"] == "vai-685-correlation"
    assert handoff["payload"]["intent"] == "hallucinate_app.content_browser.search"
    assert handoff["payload"]["query"] == "semantic photos"
    assert handoff["payload"]["filter"] == {"mimetype": "text/plain"}
    assert handoff["normalized_intent"]["method"] == "invoke_service"
    assert handoff["normalized_intent"]["arguments"]["result_target"] == "mobile_card"

    emitted = {item["event"]: item["data"] for item in probe["emitted"]}
    assert emitted["hallucinate_app-mobile:handoff"]["contract_id"] == INTERFACE_CONTRACT
    assert emitted["hallucinate_app-mobile:handoff"]["payload"]["query"] == "semantic photos"
    assert emitted["direct:mobile-handoff"]["target_surface"] == "mobile"


def test_mobile_descriptor_exports_hallucinate_app_mobile_contract() -> None:
    exports = load_js_exports(
        MOBILE_DESCRIPTORS,
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_OPERATIONS",
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        ],
    )

    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert set(exports["HALLUCINATE_APP_MOBILE_INTEROP_OPERATIONS"]) == MOBILE_ORB_OPERATIONS
    assert interface["metadata"]["interface_contract"] == INTERFACE_CONTRACT
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert interface["metadata"]["source_surface"] == "hallucinate_app"
    assert interface["metadata"]["target_surface"] == "mobile"
    assert interface["objective_goals"] == [GOAL_ID]
    assert {method["name"] for method in interface["methods"]} == MOBILE_ORB_OPERATIONS
    assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert descriptor["runtime_handoff"]["receipt_table"] == "hallucinate_app_mobile_interop_receipts"
    assert descriptor["validation"]["task_id"] == "VAI-685"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"
    assert descriptor["schema_refs"] == {
        "search_interface": SEARCH_INTERFACE,
        "test_interface": TEST_INTERFACE,
        "time_series_schema": TIME_SERIES_SCHEMA,
        "benchmark_schema_script": BENCHMARK_SCHEMA_SCRIPT,
    }


def test_mobile_orb_bridge_advertises_hallucinate_app_descriptor() -> None:
    assert_module_is_valid_esm(MOBILE_BRIDGE)
    source = (REPO_ROOT / MOBILE_BRIDGE).read_text(encoding="utf-8")

    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "hallucinateAppMobileInteropInterfaceCid" in source
    assert "descriptorRef(\n                HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert source.count("HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR") >= 2


def test_test_interface_fixture_and_duckdb_receipts_cover_handoff() -> None:
    fixture = (REPO_ROOT / TEST_INTERFACE).read_text(encoding="utf-8")
    schema = (REPO_ROOT / TIME_SERIES_SCHEMA).read_text(encoding="utf-8")
    benchmark_script = (REPO_ROOT / BENCHMARK_SCHEMA_SCRIPT).read_text(encoding="utf-8")

    for route in MOBILE_ORB_ROUTES:
        assert route in fixture
        assert route in benchmark_script

    for artifact in REQUIRED_ARTIFACTS:
        assert artifact in fixture
        assert artifact in schema
        assert artifact in benchmark_script

    assert INTERFACE_CONTRACT in fixture
    assert INTERFACE_CONTRACT in schema
    assert INTERFACE_CONTRACT in benchmark_script
    assert "hallucinate_app_mobile_interop_receipts" in schema
    assert "hallucinate_app_mobile_interop_receipts" in benchmark_script
    assert "idx_hallucinate_app_mobile_interop_receipts_route" in schema


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = (REPO_ROOT / "docs/integration/hallucinate_app-mobile.md").read_text(
        encoding="utf-8"
    )
    discovery = (
        REPO_ROOT
        / "data/virtual_ai_os/discovery/2026-07-08-vai-685-objective-validation-repair.md"
    ).read_text(encoding="utf-8")
    gap = (
        REPO_ROOT
        / "data/virtual_ai_os/discovery/2026-07-08-vai-685-objective-gap-7edb316279e5.md"
    ).read_text(encoding="utf-8")
    heap = (
        REPO_ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")

    required_terms = [
        "VAI-685",
        GOAL_ID,
        "objective/interoperability/hallucinate_app-mobile",
        "objective validation repair",
        INTERFACE_CONTRACT,
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "docs/integration/hallucinate_app-mobile.md",
        SEARCH_INTERFACE,
        TEST_INTERFACE,
        MOBILE_DESCRIPTORS,
        MOBILE_BRIDGE,
        TIME_SERIES_SCHEMA,
        BENCHMARK_SCHEMA_SCRIPT,
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"

    assert "objective validation repair" in gap
    assert "2026-07-08-vai-685-objective-validation-repair.md" in docs
    assert "2026-07-08-vai-685-objective-validation-repair.md" in heap
