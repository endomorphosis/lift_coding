from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "mcp_release_gate", ROOT / "scripts" / "run_mcplusplus_release_gate.py"
)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gate
SPEC.loader.exec_module(gate)


def benchmark() -> dict:
    return json.loads(
        (ROOT / "Mcp-Plus-Plus/docs/testing/profile-g-performance/results.json").read_text()
    )


def test_release_evidence_is_fail_closed_and_covers_all_profiles_transports_and_peers():
    rows = [definition.public(True) for definition in gate.gate_definitions(Path("/tmp/benchmark"))]
    evidence = gate.build_evidence(rows, benchmark(), [])
    assert evidence["decision"] == "GO"
    assert evidence["profiles"] == list("ABCDEFG")
    assert evidence["transports"] == ["jsonrpc-http", "mcp+p2p"]
    assert any(row.get("peer_count") == 3 for row in evidence["gates"])
    assert {row["state"] for row in evidence["observable_states"]} >= {
        "degraded", "denied", "conflicted", "expired", "stale_fence", "partitioned"
    }

    rows[0]["status"] = "fail"
    assert gate.build_evidence(rows, benchmark(), [])["decision"] == "NO_GO"


def test_meta_glasses_summary_is_bounded_and_has_no_mutation_authority():
    rows = [definition.public(True) for definition in gate.gate_definitions(Path("/tmp/benchmark"))]
    summary = gate.make_glasses_summary(gate.build_evidence(rows, benchmark(), []))
    assert summary["projection"]["mode"] == "read-only"
    assert summary["projection"]["mutation_authority"] is False
    assert {"claim", "renew", "resolve", "steer task"} <= set(summary["forbidden_actions"])
    assert "UCAN token" in summary["redacted_fields"]
    assert "raw task input/output" in summary["redacted_fields"]


def test_published_release_packet_is_portable_and_go():
    output = ROOT / "Mcp-Plus-Plus/docs/testing/profile-g-release"
    evidence = json.loads((output / "evidence.json").read_text())
    summary = json.loads((output / "meta-glasses-summary.json").read_text())
    assert evidence["schema"] == gate.SCHEMA
    assert evidence["decision"] == "GO"
    assert all(row["status"] == "pass" for row in evidence["gates"])
    assert all("/home/" not in row["command"] and "/tmp/" not in row["command"] for row in evidence["gates"])
    assert len(evidence["screenshots"]) >= 4
    assert summary["schema"] == gate.GLASSES_SCHEMA
    assert summary["release_decision"] == "GO"
