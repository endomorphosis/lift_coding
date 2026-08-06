"""Hallucinate App / mobile interoperability regression tests for VAI-684."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from handsfree.hallucinate_app_mobile_interop import (  # noqa: E402
    REQUIRED_HANDOFF_ARTIFACTS,
    REQUIRED_MOBILE_ORB_ROUTES,
    REQUIRED_RECEIPT_TABLE,
    HallucinateAppMobileInteropError,
    build_mobile_search_handoff,
    discover_hallucinate_app_search_contract,
)

GOAL_ID = "VAIOS-G707"
HALLUCINATE_APP_ROOT = REPO_ROOT / "hallucinate_app"

# Nested submodule path historically used by hallucinate_app descriptors.
NESTED_TIME_SERIES_SCHEMA = (
    "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
)
NESTED_BENCHMARK_SCHEMA_SCRIPT = (
    "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
)
# Monorepo-pinned accelerate tree (CI does not initialize nested submodules).
PINNED_TIME_SERIES_SCHEMA = (
    "external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql"
)
PINNED_BENCHMARK_SCHEMA_SCRIPT = (
    "external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py"
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


def _first_existing_repo_path(*relative_paths: str) -> Path:
    """Return the first monorepo-relative path that exists as a file."""
    for relative_path in relative_paths:
        candidate = REPO_ROOT / relative_path
        if candidate.is_file():
            return candidate
    raise AssertionError(
        "missing required artifact; tried: " + ", ".join(relative_paths)
    )


def resolve_time_series_schema_path() -> Path:
    """Prefer nested accelerate schema; fall back to monorepo pin."""
    return _first_existing_repo_path(NESTED_TIME_SERIES_SCHEMA, PINNED_TIME_SERIES_SCHEMA)


def resolve_benchmark_schema_script_path() -> Path:
    """Prefer nested accelerate script; fall back to monorepo pin."""
    return _first_existing_repo_path(
        NESTED_BENCHMARK_SCHEMA_SCRIPT, PINNED_BENCHMARK_SCHEMA_SCRIPT
    )


@pytest.fixture(scope="module")
def hallucinate_app_interop_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Composite hallucinate_app root with nested accelerate schema materialised.

    Production discovery still looks under ``hallucinate_app/ipfs_accelerate_py``.
    CI checkouts leave that nested submodule empty, but the monorepo pin at
    ``external/ipfs_accelerate`` carries the interop receipt table and
    constants. Mount the pin (or reuse a populated nested tree) so discovery
    exercises the real contract without weakening assertions.
    """
    nested_accelerate = HALLUCINATE_APP_ROOT / "ipfs_accelerate_py"
    nested_schema = nested_accelerate / "data/duckdb/db_schema/time_series_schema.sql"
    if nested_schema.is_file():
        return HALLUCINATE_APP_ROOT

    pinned_accelerate = REPO_ROOT / "external" / "ipfs_accelerate"
    pinned_schema = pinned_accelerate / "data/duckdb/db_schema/time_series_schema.sql"
    assert pinned_schema.is_file(), (
        f"monorepo-pinned accelerate schema missing: {pinned_schema}"
    )

    root = tmp_path_factory.mktemp("hallucinate_app_interop")
    product_surface = HALLUCINATE_APP_ROOT / "hallucinate_app"
    assert product_surface.is_dir(), f"missing product surface: {product_surface}"
    os.symlink(product_surface, root / "hallucinate_app")
    os.symlink(pinned_accelerate, root / "ipfs_accelerate_py")
    return root


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
  functionExports.push(name);
  return `class ${name}`;
});
source = source.replace(/export default\s+[^;]+;?/g, '');
source = `${source}\n${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {} };
vm.runInNewContext(source, context, { filename: path });
const selected = {};
for (const name of requested) {
  const value = context.exports[name];
  selected[name] = typeof value === 'function' ? `__function__:${value.name || name}` : value;
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
    ]
    for relative_path in expected_paths:
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"

    # Nested accelerate schema is optional on CI; monorepo pin must carry the
    # receipt table evidence (same contract content).
    schema_path = resolve_time_series_schema_path()
    script_path = resolve_benchmark_schema_script_path()
    assert schema_path.is_file(), "missing accelerate time_series_schema.sql"
    assert script_path.is_file(), "missing accelerate create_benchmark_schema.py"


def test_discover_hallucinate_app_search_contract_finds_receipt_table(
    hallucinate_app_interop_root: Path,
) -> None:
    contract = discover_hallucinate_app_search_contract(hallucinate_app_interop_root)

    assert contract.contract_id == "interface contract hallucinate_app mobile"
    assert contract.source_surface == "hallucinate_app"
    assert contract.target_surface == "mobile"
    assert contract.control_surface_contract_ref == (
        "control_surface_contract:hallucinate-app:remote-client"
    )
    assert contract.route == "/v1/mobile/orb/invoke_service"
    assert contract.operation == "invoke_service"
    assert set(REQUIRED_HANDOFF_ARTIFACTS).issubset(set(contract.required_artifacts))
    assert contract.receipt_table == REQUIRED_RECEIPT_TABLE
    assert contract.search_interface_path.endswith(
        "hallucinate_app/node/dashboard/content_browser/search_interface.js"
    )
    assert contract.test_interface_path.endswith("hallucinate_app/node/views/test_interface.html")
    assert contract.time_series_schema_path.endswith("data/duckdb/db_schema/time_series_schema.sql")


def test_discover_hallucinate_app_search_contract_raises_for_missing_root(tmp_path) -> None:
    missing_root = tmp_path / "does-not-exist"
    try:
        discover_hallucinate_app_search_contract(missing_root)
    except HallucinateAppMobileInteropError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected HallucinateAppMobileInteropError")


def test_build_mobile_search_handoff_is_deterministic(
    hallucinate_app_interop_root: Path,
) -> None:
    first = build_mobile_search_handoff(hallucinate_app_interop_root, "pyarrow content index")
    second = build_mobile_search_handoff(hallucinate_app_interop_root, "pyarrow content index")

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
    assert first.query == "pyarrow content index"
    assert set(REQUIRED_HANDOFF_ARTIFACTS).issubset(set(first.required_artifacts))
    assert first.receipt_table == REQUIRED_RECEIPT_TABLE

    third = build_mobile_search_handoff(hallucinate_app_interop_root, "a different query")
    assert third.payload_sha256 != first.payload_sha256


def test_mobile_descriptor_exports_hallucinate_app_interop_contract() -> None:
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

    assert (
        interface["metadata"]["interface_contract"] == "interface contract hallucinate_app mobile"
    )
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert interface["metadata"]["source_surface"] == "hallucinate_app"
    assert interface["metadata"]["target_surface"] == "mobile"
    assert GOAL_ID in interface["objective_goals"]
    assert {method["name"] for method in interface["methods"]} == MOBILE_ORB_OPERATIONS
    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == MOBILE_ORB_OPERATIONS

    # Descriptor schema_refs remain the logical nested contract paths (stable
    # interface identifiers). Live CI content is resolved from the monorepo pin.
    assert descriptor["schema_refs"] == {
        "search_interface": (
            "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
        ),
        "test_interface": "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "time_series_schema": NESTED_TIME_SERIES_SCHEMA,
        "benchmark_schema_script": NESTED_BENCHMARK_SCHEMA_SCRIPT,
    }
    assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert descriptor["runtime_handoff"]["route"] == "/v1/mobile/orb/invoke_service"
    assert descriptor["runtime_handoff"]["receipt_table"] == REQUIRED_RECEIPT_TABLE
    assert set(REQUIRED_HANDOFF_ARTIFACTS).issubset(
        set(descriptor["runtime_handoff"]["required_artifacts"])
    )
    assert descriptor["validation"]["task_id"] == "VAI-684"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_orb_bridge_module_remains_parseable_after_contract_wiring() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert source.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1


def test_search_interface_module_remains_parseable_and_exports_handoff_builder() -> None:
    assert_module_is_valid_esm(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
    )
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
    assert contract["route"] in REQUIRED_MOBILE_ORB_ROUTES
    assert set(REQUIRED_HANDOFF_ARTIFACTS).issubset(set(contract["required_artifacts"]))
    assert exports["buildHallucinateAppMobileSearchHandoff"] == (
        "__function__:buildHallucinateAppMobileSearchHandoff"
    )


def test_test_interface_html_carries_mobile_interop_fixture() -> None:
    source = (
        REPO_ROOT / "hallucinate_app/hallucinate_app/node/views/test_interface.html"
    ).read_text(encoding="utf-8")
    assert "interface contract hallucinate_app mobile" in source
    assert 'data-contract-id="interface contract hallucinate_app mobile"' in source
    assert "mobileInteropContract" in source
    assert "mobileInteropResults" in source


def test_time_series_schema_declares_hallucinate_app_mobile_interop_receipts_table() -> None:
    source = resolve_time_series_schema_path().read_text(encoding="utf-8")
    assert REQUIRED_RECEIPT_TABLE in source
    assert "interface contract hallucinate_app mobile" in source
    assert f"idx_{REQUIRED_RECEIPT_TABLE}_route" in source


def test_create_benchmark_schema_records_hallucinate_app_mobile_interop_constants() -> None:
    source = resolve_benchmark_schema_script_path().read_text(encoding="utf-8")
    assert "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID" in source
    assert "interface contract hallucinate_app mobile" in source
    assert REQUIRED_RECEIPT_TABLE in source


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = (REPO_ROOT / "docs/integration/hallucinate_app-mobile.md").read_text(encoding="utf-8")
    discovery = (
        REPO_ROOT / "data/virtual_ai_os/discovery/2026-07-09-vai-684-objective-validation-repair.md"
    ).read_text(encoding="utf-8")
    heap = (
        REPO_ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")

    # Docs + discovery own full path evidence. Heap historically records the
    # suite/docs/contract surfaces without restating every source module path.
    shared_terms = [
        "VAI-684",
        GOAL_ID,
        "objective/interoperability/hallucinate_app-mobile",
        "objective validation repair",
        "interface contract hallucinate_app mobile",
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "time_series_schema.sql",
        "create_benchmark_schema.py",
    ]
    path_evidence_terms = [
        "src/handsfree/hallucinate_app_mobile_interop.py",
    ]
    for content in (docs, discovery):
        for term in (*shared_terms, *path_evidence_terms):
            assert term in content, f"missing {term!r}"
    for term in shared_terms:
        assert term in heap, f"missing {term!r} in heap"

    discovery_record = (
        "data/virtual_ai_os/discovery/2026-07-09-vai-684-objective-validation-repair.md"
    )
    assert discovery_record in docs
    # Heap may cite VAI-684 / interop objective without the exact discovery path.
    assert "VAI-684" in heap or discovery_record in heap
    assert (REPO_ROOT / discovery_record).is_file()
