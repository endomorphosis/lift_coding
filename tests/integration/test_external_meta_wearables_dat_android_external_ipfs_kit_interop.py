"""HAO-739 objective validation repair for Meta Wearables DAT Android + IPFS Kit."""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path

import anyio

ROOT = Path(__file__).resolve().parents[2]
KIT_ROOT = ROOT / "external" / "ipfs_kit"
META_ROOT = ROOT / "external" / "meta-wearables-dat-android"
CONTRACT = META_ROOT / "contracts" / "ipfs_kit_wearable_handoff.json"
SCHEMA = KIT_ROOT / "data" / "deprecations_report.schema.json"
FIX_SCRIPTS = [
    KIT_ROOT / "archive" / "archive_clutter" / "fix_scripts" / "fix_mcp_schema.py",
    KIT_ROOT / "backup" / "archive_clutter" / "fix_scripts" / "fix_mcp_schema.py",
    KIT_ROOT / "backup" / "patches" / "fixes" / "fix_mcp_schema.py",
]

sys.path.insert(0, str(KIT_ROOT))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem + "_" + str(abs(hash(path))), path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_interface_contract_links_meta_dat_payload_to_ipfs_kit_schema_and_profiles():
    contract = _load_json(CONTRACT)

    assert contract["contract_id"] == "external_meta_wearables_dat_android_external_ipfs_kit"
    assert contract["source"] == "external/meta-wearables-dat-android"
    assert contract["target"] == "external/ipfs_kit"
    assert contract["objective_validation_repair"] == "HAO-739 VAIOS-G711 objective validation repair"
    assert "VAIOS-G711" in contract["packet_goals"]
    assert contract["wearable_payload"]["render_path"] == "dat-native"
    assert contract["wearable_payload"]["max_update_hz"] <= 5
    assert contract["ipfs_kit_capabilities"]["deprecations_report_schema"] == (
        "external/ipfs_kit/data/deprecations_report.schema.json"
    )
    assert "mcp++/profile-b-cid-artifacts" in contract["ipfs_kit_capabilities"]["mcp_profiles"]
    assert {"cid", "event_cid"}.issubset(contract["handoff"]["content_addressed_fields"])


def test_deprecations_report_schema_accepts_required_runtime_handoff_shape():
    schema = _load_json(SCHEMA)
    sample = {
        "report_version": "1.0.0",
        "generated_at": "2026-07-08T00:00:00Z",
        "deprecated": [
            {
                "endpoint": "pin_tools/pin_rm",
                "remove_in": None,
                "hits": 0,
                "migration": {"replacement": "pin_tools/pin_rm"},
            }
        ],
        "summary": {"count": 1, "max_hits": 0},
        "policy": {
            "hits_enforcement": {"status": "pass", "threshold": 0, "checked": 1, "violations": []},
            "migration_enforcement": {"status": "pass", "checked": 1, "violations": []},
        },
        "raw": {"objective_validation_repair": "HAO-739 VAIOS-G711"},
        "objective_validation_repair": "HAO-739 VAIOS-G711",
    }

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert set(schema["required"]).issubset(sample)
    deprecated_item = sample["deprecated"][0]
    assert set(schema["properties"]["deprecated"]["items"]["required"]).issubset(deprecated_item)
    assert deprecated_item["hits"] >= 0
    assert sample["policy"]["hits_enforcement"]["status"] in {"pass", "violation", "skipped"}


def test_fix_mcp_schema_scripts_are_importable_deterministic_and_ast_visible():
    payload = {
        "mcpServers": [
            {"name": "ipfs-kit", "command": "python", "args": ["-m", "ipfs_kit_py.mcp_server"]},
            {"command": "node", "args": ["server.js"]},
        ]
    }

    for path in FIX_SCRIPTS:
        module = _load_module(path)
        fixed = module.normalize_mcp_servers(payload)
        assert list(fixed["mcpServers"]) == ["ipfs-kit", "server-0002"]
        assert fixed["mcpServers"]["ipfs-kit"]["command"] == "python"
        assert fixed["mcpServers"]["server-0002"]["args"] == ["server.js"]
        assert module.check_high_level_api_syntax(fixed) == []

        tree = ast.parse(path.read_text())
        names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        assert {"normalize_mcp_servers", "fix_mcp_schema", "check_high_level_api_syntax"}.issubset(names)


def test_runtime_handoff_emits_mcp_plus_plus_receipt_for_wearable_ack():
    from ipfs_kit_py.mcp_server.server import MCPServer

    server = MCPServer()
    response = anyio.run(
        server.handle,
        {
            "jsonrpc": "2.0",
            "id": "wearable-pin-rm",
            "method": "tools/call",
            "params": {
                "name": "pin_tools/pin_rm",
                "arguments": {"cid": "bafyreibahao739"},
                "profile_b": True,
                "correlation_id": "meta-dat-android-display-ack",
            },
        },
    )
    result = response["result"]
    receipt = result["_mcppp"]

    assert result["status"] == "ok"
    assert result["cid"] == "bafyreibahao739"
    assert receipt["success"] is True
    assert receipt["event_cid"].startswith("bafkrei")
    assert receipt["receipt"]["correlation_id"] == "meta-dat-android-display-ack"

    frontier = anyio.run(
        server.handle,
        {"jsonrpc": "2.0", "id": "frontier", "method": "mcp++/dag/frontier"},
    )["result"]
    assert frontier["frontier"] == [receipt["event_cid"]]
