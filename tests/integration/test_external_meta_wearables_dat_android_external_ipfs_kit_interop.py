"""HAO-739 interop proof for external/meta-wearables-dat-android and external/ipfs_kit."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
META_ROOT = ROOT / "external" / "meta-wearables-dat-android"
KIT_ROOT = ROOT / "external" / "ipfs_kit"
sys.path.insert(0, str(META_ROOT / "python"))
sys.path.insert(0, str(KIT_ROOT))

INTERFACE_CONTRACT = "interface contract external/meta-wearables-dat-android external/ipfs_kit"
PACKET_GOALS = ("VAIOS-G709", "VAIOS-G710", "VAIOS-G711")


def _sample_wearable_event() -> dict[str, object]:
    return {
        "device_id": "android-dat-glasses-01",
        "event_type": "display_widget_rendered",
        "sequence": 739,
        "captured_at": "2026-07-08T00:00:00Z",
        "payload": {
            "widget_id": "task-progress",
            "display_descriptor_cid": "bafybeigdyrzt",
            "battery_percent": 87,
        },
    }


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_meta_android_handoff_schema_is_scanner_visible_and_pair_specific():
    schema_path = META_ROOT / "contracts" / "ipfs_kit_handoff.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["producer"]["const"] == "external/meta-wearables-dat-android"
    assert schema["properties"]["consumer"]["const"] == "external/ipfs_kit"
    assert schema["properties"]["operation"]["enum"] == ["dag_put"]
    assert {"contract", "payload", "ipfs"}.issubset(schema["required"])


def test_runtime_handoff_builds_ipfs_kit_mcp_call_and_deterministic_cid_receipt():
    from ipfs_kit_py.meta_wearables_android_interop import (
        build_mcp_tool_call,
        consume_meta_wearables_handoff,
        dag_json_cid,
    )
    from meta_wearables_dat_android.ipfs_kit_handoff import build_ipfs_kit_handoff

    envelope = build_ipfs_kit_handoff(_sample_wearable_event(), request_id="hao-739")
    receipt = consume_meta_wearables_handoff(envelope)

    assert envelope["producer"] == "external/meta-wearables-dat-android"
    assert envelope["consumer"] == "external/ipfs_kit"
    assert receipt["schema"] == "external.ipfs_kit.meta_wearables_android.receipt.v1"
    assert receipt["cid"] == dag_json_cid(envelope["payload"])
    assert receipt["cid"].startswith("bagu")
    assert receipt["pinned"] is True
    assert receipt["source_device_id"] == "android-dat-glasses-01"
    assert receipt["sequence"] == 739

    tool_call = build_mcp_tool_call(envelope)
    assert tool_call == receipt["mcp_tool_call"]
    assert tool_call["method"] == "tools/call"
    assert tool_call["params"]["name"] == "dag_tools/dag_put"
    assert tool_call["params"]["arguments"]["object"] == envelope["payload"]


def test_required_ipfs_kit_interface_descriptor_outputs_exist_and_are_valid_json_or_text():
    required = [
        KIT_ROOT / "archive" / "archive_clutter" / "fix_scripts" / "fix_mcp_schema.py",
        KIT_ROOT / "backup" / "archive_clutter" / "fix_scripts" / "fix_mcp_schema.py",
        KIT_ROOT / "backup" / "patches" / "fixes" / "fix_mcp_schema.py",
        KIT_ROOT / "data" / "deprecations_report.schema.json",
        KIT_ROOT / "docs" / "implementation" / "BUCKET_VFS_INTERFACES_COMPLETE.md",
        KIT_ROOT / "docs" / "py-ipld-dag-pb" / "ipld_dag_pb" / "dag-pb.proto",
    ]
    for path in required:
        assert path.exists(), f"missing HAO-739 expected output: {path}"

    deprecations_schema = json.loads((KIT_ROOT / "data" / "deprecations_report.schema.json").read_text())
    assert deprecations_schema["$id"].endswith("/deprecations-report.schema.json")
    assert deprecations_schema["properties"]["source_repository"]["const"] == "external/ipfs_kit"
    assert "deprecations" in deprecations_schema["required"]

    bucket_doc = (KIT_ROOT / "docs" / "implementation" / "BUCKET_VFS_INTERFACES_COMPLETE.md").read_text()
    assert "dag_tools/dag_put" in bucket_doc
    assert "Meta Wearables DAT Android" in bucket_doc

    proto = (KIT_ROOT / "docs" / "py-ipld-dag-pb" / "ipld_dag_pb" / "dag-pb.proto").read_text()
    assert "message PBNode" in proto
    assert "message PBLink" in proto


def test_fix_mcp_schema_scripts_repair_archived_tool_descriptors():
    descriptor = {"tools": [{"name": "dag_tools/dag_put", "input_schema": {"properties": {}}}]}
    for index, script in enumerate(
        [
            KIT_ROOT / "archive" / "archive_clutter" / "fix_scripts" / "fix_mcp_schema.py",
            KIT_ROOT / "backup" / "archive_clutter" / "fix_scripts" / "fix_mcp_schema.py",
            KIT_ROOT / "backup" / "patches" / "fixes" / "fix_mcp_schema.py",
        ]
    ):
        module = _load_module(script, f"_hao739_fix_mcp_schema_{index}")
        repaired = module.repair_descriptor(descriptor)
        assert repaired["schema_repair_contract"] == "external.ipfs_kit.fix_mcp_schema.v1"
        input_schema = repaired["tools"][0]["inputSchema"]
        assert input_schema["type"] == "object"
        assert input_schema["additionalProperties"] is False
        assert module.check_high_level_api_syntax(script.read_text(encoding="utf-8")) is True


def test_docs_and_heap_carry_objective_validation_repair_terms():
    doc = (ROOT / "docs" / "integration" / "external_meta_wearables_dat_android-external_ipfs_kit.md").read_text()
    heap = (
        ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
    ).read_text()
    discovery = (
        ROOT
        / "data"
        / "hallucinate_multimodal_control"
        / "discovery"
        / "2026-07-08-hao-739-objective-validation-repair.md"
    ).read_text()

    assert INTERFACE_CONTRACT in doc
    assert "objective validation repair" in doc
    for goal in PACKET_GOALS:
        assert goal in doc
        assert goal in discovery
        assert goal in heap
    assert "HAO-739 proof" in heap
