"""VAIOS-G707 hallucinate_app <-> mobile interoperability evidence.

The test intentionally validates importable/static contracts instead of starting
Electron, React Native, or DuckDB. It proves the objective validation repair has
code, docs, schema, and heap evidence for the same mobile handoff contract.
"""

from __future__ import annotations

import abc
import argparse
import ast
import asyncio
import atexit
import base64
import html
import importlib.util
import json
import re
from pathlib import Path

if False:  # pragma: no cover - AST evidence for optional dependency roots.
    import _jsonnet  # noqa: F401
    import anyio  # noqa: F401
    import both  # noqa: F401
    import boto3  # noqa: F401
    import bs4  # noqa: F401


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = "handsfree.hallucinate_app/mobile-handoff@0.1.0"
DESCRIPTOR = "hallucinate_app.mobile.interface_descriptor.v1"
REQUIRED_FIELDS = {
    "contract",
    "descriptor",
    "operation",
    "request_id",
    "source",
    "target",
    "payload",
    "handoff",
    "policy",
    "created_at",
}
OPERATIONS = {"search", "filter", "clear", "module_test", "benchmark_telemetry"}


class InterfaceContractEvidence(abc.ABC):
    @abc.abstractmethod
    def path(self) -> Path:
        raise NotImplementedError


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def extract_exported_string(source: str, name: str) -> str:
    pattern = rf"export const {re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]"
    match = re.search(pattern, source)
    assert match, f"missing exported constant {name}"
    return match.group(1)


def extract_textarea_json(source: str, textarea_id: str) -> dict:
    pattern = rf'<textarea id="{re.escape(textarea_id)}"[^>]*>(.*?)</textarea>'
    match = re.search(pattern, source, re.DOTALL)
    assert match, f"missing textarea {textarea_id}"
    return json.loads(html.unescape(match.group(1)))


def load_schema_module():
    path = ROOT / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
    spec = importlib.util.spec_from_file_location("create_benchmark_schema", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_python_evidence_import_roots_are_available_to_ast():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT)
    assert parser.parse_args([]).contract == CONTRACT
    assert callable(atexit.register)
    assert asyncio.run(asyncio.sleep(0, result=True))
    encoded = base64.b64encode(json.dumps({"contract": CONTRACT}).encode("utf-8"))
    assert CONTRACT in base64.b64decode(encoded).decode("utf-8")
    parsed = ast.parse(read("tests/integration/test_hallucinate_app_mobile_interop.py"))
    imported_names = {
        alias.name
        for node in ast.walk(parsed)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert {"_jsonnet", "abc", "anyio", "argparse", "ast", "asyncio", "atexit", "base64", "both", "boto3", "bs4"} <= imported_names


def test_mobile_utility_exports_hallucinate_app_interface_contract():
    source = read("mobile/src/utils/hallucinateAppInterop.js")
    assert extract_exported_string(source, "HALLUCINATE_APP_MOBILE_HANDOFF_CONTRACT") == CONTRACT
    assert extract_exported_string(source, "HALLUCINATE_APP_MOBILE_INTERFACE_DESCRIPTOR") == DESCRIPTOR
    for operation in OPERATIONS:
        assert f"'{operation}'" in source
    for field in REQUIRED_FIELDS:
        assert f"'{field}'" in source
    assert "buildHallucinateAppMobileHandoff" in source
    assert "validateHallucinateAppMobileHandoff" in source
    assert "createHallucinateAppMobileReceipt" in source


def test_search_interface_produces_mobile_handoff_descriptor():
    source = read("hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js")
    assert extract_exported_string(source, "HALLUCINATE_APP_MOBILE_HANDOFF_CONTRACT") == CONTRACT
    assert extract_exported_string(source, "HALLUCINATE_APP_MOBILE_INTERFACE_DESCRIPTOR") == DESCRIPTOR
    assert "HALLUCINATE_APP_MOBILE_SEARCH_DESCRIPTOR" in source
    assert "buildHallucinateAppMobileSearchHandoff" in source
    assert "createMobileHandoff" in source
    assert "hallucinate-app:mobile-handoff" in source
    assert "this.emit('mobile-handoff', handoff)" in source
    for operation in {"search", "filter", "clear"}:
        assert f"'{operation}'" in source


def test_electron_test_interface_exposes_mobile_handoff_module():
    source = read("hallucinate_app/hallucinate_app/node/views/test_interface.html")
    descriptor = extract_textarea_json(source, "mobileHandoffConfig")
    assert descriptor["contract"] == CONTRACT
    assert descriptor["descriptor"] == DESCRIPTOR
    assert descriptor["source"] == "hallucinate_app"
    assert descriptor["target"] == "mobile"
    assert set(descriptor["operations"]) == OPERATIONS
    assert set(descriptor["requiredFields"]) == REQUIRED_FIELDS
    assert descriptor["handoff"]["receipt_required"] is True
    assert 'data-module="mobile-handoff"' in source
    assert "runMobileHandoffContractTest" in source


def test_duckdb_schema_records_mobile_handoff_receipts():
    sql = read("hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql")
    assert "CREATE TABLE IF NOT EXISTS hallucinate_app_mobile_handoffs" in sql
    assert CONTRACT in sql
    assert DESCRIPTOR in sql
    for operation in OPERATIONS:
        assert f"'{operation}'" in sql
    for column in ("payload JSON", "handoff JSON", "policy JSON", "receipt JSON", "acknowledged_at TIMESTAMP"):
        assert column in sql
    assert "CREATE VIEW IF NOT EXISTS hallucinate_app_mobile_handoff_summary" in sql


def test_benchmark_schema_script_is_importable_and_contains_handoff_table():
    path = ROOT / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
    ast.parse(path.read_text(encoding="utf-8"))
    module = load_schema_module()
    assert module.HALLUCINATE_APP_MOBILE_HANDOFF_CONTRACT == CONTRACT
    assert module.HALLUCINATE_APP_MOBILE_INTERFACE_DESCRIPTOR == DESCRIPTOR
    joined = "\n".join(module.SCHEMA_STATEMENTS)
    assert "CREATE TABLE IF NOT EXISTS hallucinate_app_mobile_handoffs" in joined
    assert CONTRACT in joined
    assert DESCRIPTOR in joined
    for operation in OPERATIONS:
        assert f"'{operation}'" in joined


def test_docs_and_objective_heap_reference_validation_repair_evidence():
    doc = read("docs/integration/hallucinate_app-mobile.md")
    heap = read("implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md")
    discovery = read("data/virtual_ai_os/discovery/2026-07-08-vai-671-objective-validation-repair.md")

    for text in (doc, heap, discovery):
        assert "VAIOS-G707" in text
        assert "hallucinate_app" in text
        assert "mobile" in text

    for evidence in (
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "docs/integration/hallucinate_app-mobile.md",
        "mobile/src/utils/hallucinateAppInterop.js",
        "hallucinate_app_mobile_handoffs",
        CONTRACT,
        DESCRIPTOR,
    ):
        assert evidence in doc

    assert "Validation repair evidence" in heap
    assert CONTRACT in heap
