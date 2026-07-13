#!/usr/bin/env python3
"""Run and publish the SVD-091 MCP++ Profiles A-G release gate.

The gate deliberately executes evidence producers instead of trusting a checked
box in a manifest.  Its published JSON contains paths and SHA-256 commitments,
but no command stdout, task payloads, raw telemetry, or delegation material.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
MCPPP = ROOT / "Mcp-Plus-Plus"
DEFAULT_OUTPUT = MCPPP / "docs" / "testing" / "profile-g-release"
SCHEMA = "mcp++/release-evidence@1"
GLASSES_SCHEMA = "mcp++/profile-g/meta-glasses-summary@1"
PUBLICATION_DATE = "2026-07-12"


@dataclass(frozen=True)
class Gate:
    gate_id: str
    title: str
    command: tuple[str, ...]
    cwd: Path
    profiles: tuple[str, ...] = ()
    transports: tuple[str, ...] = ()
    peers: int | None = None

    def public(self, passed: bool) -> dict[str, Any]:
        public_command = []
        for index, argument in enumerate(self.command):
            if index == 0 and argument == sys.executable:
                public_command.append("python")
            elif Path(argument).is_absolute() and not str(argument).startswith(str(ROOT)):
                public_command.append("<temporary-output>")
            else:
                public_command.append(argument)
        value: dict[str, Any] = {
            "id": self.gate_id,
            "title": self.title,
            "status": "pass" if passed else "fail",
            "command": " ".join(public_command),
            "profiles": list(self.profiles),
            "transports": list(self.transports),
        }
        if self.peers is not None:
            value["peer_count"] = self.peers
        return value


def gate_definitions(benchmark_output: Path) -> tuple[Gate, ...]:
    """Return the executable, fail-closed release matrix."""
    py = sys.executable
    return (
        Gate(
            "profiles-a-f-conformance", "Profiles A-F canonical conformance",
            (py, "-m", "pytest", "-q", "integration/test_conformance_vectors.py",
             "integration/test_cid_envelopes.py", "integration/test_policy_evaluation.py",
             "integration/test_event_dag.py", "integration/test_transport.py"),
            MCPPP / "tests-py", tuple("ABCDEF"), ("jsonrpc-http", "mcp+p2p"),
        ),
        Gate(
            "profile-g-codecs", "Profile G closed schemas, CIDs, and invalid vectors",
            (py, "-m", "pytest", "-q", "integration/test_profile_g_codec.py"),
            MCPPP / "tests-py", ("G",),
        ),
        Gate(
            "accelerator-profile-g-transport", "Accelerator JSON-RPC/REST/Profile E binding",
            (py, "-m", "pytest", "-q", "ipfs_accelerate_py/mcp/tests/test_profile_g_transport.py"),
            ROOT / "external" / "ipfs_accelerate", ("G",), ("jsonrpc-http", "mcp+p2p"),
        ),
        Gate(
            "datasets-profile-g-transport", "Datasets negotiation and Profile E denial binding",
            (py, "-m", "pytest", "-q", "tests/mcp_server/test_profile_g_transport.py"),
            ROOT / "external" / "ipfs_datasets", ("G",), ("jsonrpc-http", "mcp+p2p"),
        ),
        Gate(
            "kit-profile-g-transport", "Kit HTTP/Profile E semantic parity",
            (py, "-m", "pytest", "-q", "tests/test_profile_g_transport.py"),
            ROOT / "external" / "ipfs_kit", ("G",), ("jsonrpc-http", "mcp+p2p"),
        ),
        Gate(
            "profile-g-three-peer", "Three-peer conflict, takeover, and reconciliation",
            (py, "-m", "pytest", "-q", "integration/test_profile_g_three_peer.py"),
            MCPPP / "tests-py", tuple("BCDFG"), ("jsonrpc-http", "mcp+p2p"), 3,
        ),
        Gate(
            "profile-g-performance", "Throughput, fairness, starvation, and recovery thresholds",
            (py, "benchmarks/run_profile_g_benchmark.py", "--output-dir", str(benchmark_output)),
            MCPPP / "tests-py", ("G",), (), 3,
        ),
        Gate(
            "swissknife-profile-g", "Desktop connector and governed/read-only mappings",
            ("npm", "run", "test:run", "--", "test/mcp-plus-plus/profile-g-connector.test.ts"),
            ROOT / "swissknife", tuple("ABCDEFG"), ("jsonrpc-http", "mcp+p2p"),
        ),
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def source_evidence() -> list[dict[str, Any]]:
    paths = (
        "Mcp-Plus-Plus/docs/spec/mcp++-profiles-draft.md",
        "Mcp-Plus-Plus/docs/spec/risk-scheduling.md",
        "Mcp-Plus-Plus/conformance/vectors/profile_g_artifacts_valid.json",
        "Mcp-Plus-Plus/conformance/vectors/profile_g_artifacts_invalid.json",
        "Mcp-Plus-Plus/conformance/vectors/profile_g_protocol_valid.json",
        "Mcp-Plus-Plus/conformance/vectors/profile_g_protocol_invalid.json",
        "Mcp-Plus-Plus/conformance/vectors/profile_g_three_peer.json",
        "Mcp-Plus-Plus/docs/testing/profile-g-performance/results.json",
    )
    evidence = []
    for relative in paths:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"required release evidence is missing: {relative}")
        evidence.append({"path": relative, "sha256": sha256_file(path)})
    return evidence


def screenshot_evidence() -> list[dict[str, Any]]:
    paths = (
        "swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-screenshots/agent-supervisor.png",
        "swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-screenshots/mcp-plus-plus.png",
        "swissknife/test-results/virtual-desktop-ipfs-mcp-orb/glasses-screenshots/agent-supervisor-display.png",
        "swissknife/test-results/virtual-desktop-ipfs-mcp-orb/glasses-screenshots/agent-supervisor-fallback.png",
    )
    evidence = []
    for relative in paths:
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size < 1024:
            raise FileNotFoundError(f"required non-empty UI screenshot is missing: {relative}")
        evidence.append({"path": relative, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    return evidence


def validate_published_benchmark() -> dict[str, Any]:
    path = MCPPP / "docs" / "testing" / "profile-g-performance" / "results.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    checks = result.get("checks", {})
    if result.get("schema") != "mcp++/profile-g/performance-report@1":
        raise ValueError("published performance evidence has an unsupported schema")
    if result.get("peer_count", 0) < 3 or not result.get("accepted") or not checks or not all(checks.values()):
        raise ValueError("published performance evidence does not pass every three-peer threshold")
    return result


def observable_states() -> list[dict[str, str]]:
    return [
        {"state": "degraded", "surface": "backend health and transport fallback", "required_detail": "affected peer/transport and receipt"},
        {"state": "denied", "surface": "policy decision", "required_detail": "reason, decision CID, and required confirmation"},
        {"state": "conflicted", "surface": "claims and leases", "required_detail": "winning/losing claim CIDs and fencing token"},
        {"state": "expired", "surface": "claims and leases", "required_detail": "expiry, successor epoch, and takeover receipt"},
        {"state": "stale_fence", "surface": "reconciliation", "required_detail": "rejection code and current fence"},
        {"state": "partitioned", "surface": "neighborhood peers", "required_detail": "quorum failure and retry state"},
        {"state": "blocked", "surface": "task queue", "required_detail": "dependency or authority reason"},
        {"state": "unavailable", "surface": "gateway evidence", "required_detail": "capability, owner, reason, and correlation ID"},
    ]


def make_glasses_summary(evidence: dict[str, Any]) -> dict[str, Any]:
    benchmark = evidence["benchmark_summary"]
    return {
        "schema": GLASSES_SCHEMA,
        "publication_date": PUBLICATION_DATE,
        "release_decision": evidence["decision"],
        "projection": {
            "mode": "read-only",
            "surfaces": ["glasses_hud", "display_webapp", "audio-summary", "mobile-card-fallback"],
            "physical_glasses_required": False,
            "mutation_authority": False,
        },
        "summary": {
            "profiles": "A-G",
            "transports": ["jsonrpc-http", "mcp+p2p"],
            "peer_count": benchmark["peer_count"],
            "throughput_gain": benchmark["throughput_gain"],
            "policy_bypasses": benchmark["policy_bypasses"],
            "duplicate_completion_events": benchmark["duplicate_completion_events"],
            "starved_tasks": benchmark["starved_tasks"],
            "frontiers_converged": benchmark["frontiers_converged"],
        },
        "visible_states": [row["state"] for row in evidence["observable_states"]],
        "allowed_fields": [
            "release_decision", "aggregate counts", "bounded risk action", "peer DID",
            "claim/receipt/event CID", "fencing token", "expiry", "redacted reason",
        ],
        "redacted_fields": [
            "raw task input/output", "UCAN token", "policy body", "raw health telemetry",
            "unredacted risk evidence", "private peer address", "operator prompt",
        ],
        "forbidden_actions": [
            "claim", "renew", "release", "resolve", "reconcile", "select plan", "steer task",
        ],
        "handoff_rule": "Any action request leaves the glasses summary and enters the desktop/mobile confirmed Profile C/D policy path.",
    }


def build_evidence(gates: Iterable[dict[str, Any]], benchmark: dict[str, Any], screenshots: list[dict[str, Any]]) -> dict[str, Any]:
    gate_rows = list(gates)
    all_pass = bool(gate_rows) and all(row["status"] == "pass" for row in gate_rows)
    safety = benchmark["metrics"]["safety"]
    fairness = benchmark["metrics"]["fairness"]
    return {
        "schema": SCHEMA,
        "task_id": "SVD-091",
        "publication_date": PUBLICATION_DATE,
        "decision": "GO" if all_pass else "NO_GO",
        "release_rule": "Every gate must pass; missing evidence, hidden state, transport drift, stale-fence execution, policy bypass, duplicate completion, or starvation is NO_GO.",
        "profiles": list("ABCDEFG"),
        "transports": ["jsonrpc-http", "mcp+p2p"],
        "gates": gate_rows,
        "source_evidence": source_evidence(),
        "screenshots": screenshots,
        "observable_states": observable_states(),
        "benchmark_summary": {
            "peer_count": benchmark["peer_count"],
            "throughput_gain": benchmark["metrics"]["profile_g"]["throughput_gain"],
            "policy_bypasses": safety["policy_bypasses"],
            "duplicate_completion_events": safety["duplicate_completion_events"],
            "starved_tasks": fairness["starved_tasks"],
            "frontiers_converged": safety["frontiers_converged"],
        },
    }


def render_report(evidence: dict[str, Any]) -> str:
    gates = "\n".join(
        f"| `{row['id']}` | {', '.join(row['profiles']) or 'support'} | {', '.join(row['transports']) or 'n/a'} | **{row['status'].upper()}** |"
        for row in evidence["gates"]
    )
    states = "\n".join(
        f"| `{row['state']}` | {row['surface']} | {row['required_detail']} |"
        for row in evidence["observable_states"]
    )
    metrics = evidence["benchmark_summary"]
    return f"""# MCP++ Profiles A-G release evidence (SVD-091)

**Decision: {evidence['decision']}** — published {evidence['publication_date']}.

This is a fail-closed aggregation of canonical conformance, each Profile G backend transport, the durable three-peer failure harness, the pre-agreed performance workload, SwissKnife governed mappings, and virtual-desktop/glasses captures. It does not infer a pass from documentation alone.

## Gate matrix

| Gate | Profiles | Transports | Result |
| --- | --- | --- | --- |
{gates}

## Cross-transport, multi-peer result

- Both `jsonrpc-http` and `/mcp+p2p/1.0.0` retain the same Profile G method and result semantics.
- The proof uses {metrics['peer_count']} independently persisted peers; simultaneous claims, partition, expiry, takeover, stale completion, conflicting completion, replay, restart, and reconciliation are covered.
- Scheduled throughput gain is {metrics['throughput_gain']}x; policy bypasses: {metrics['policy_bypasses']}; duplicate completion events: {metrics['duplicate_completion_events']}; starved tasks: {metrics['starved_tasks']}; frontiers converged: {str(metrics['frontiers_converged']).lower()}.

## Required operator-visible states

| State | Surface | Evidence shown |
| --- | --- | --- |
{states}

The Meta glasses artifact is a bounded read-only projection. It cannot claim, renew, release, resolve, reconcile, select a plan, or steer a task; those operations move to the confirmed desktop/mobile Profile C/D flow.
"""


def write_outputs(evidence: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "report.md").write_text(render_report(evidence), encoding="utf-8")
    (output_dir / "meta-glasses-summary.json").write_text(
        json.dumps(make_glasses_summary(evidence), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--evidence-only", action="store_true", help="publish a diagnostic NO_GO matrix without executing test commands")
    args = parser.parse_args(argv)
    benchmark = validate_published_benchmark()
    screenshots = screenshot_evidence()
    with tempfile.TemporaryDirectory(prefix="mcp-profile-g-release-") as temporary:
        definitions = gate_definitions(Path(temporary) / "benchmark")
        rows: list[dict[str, Any]] = []
        for gate in definitions:
            if args.evidence_only:
                passed = False
            else:
                print(f"[{gate.gate_id}] {gate.title}", flush=True)
                completed = subprocess.run(gate.command, cwd=gate.cwd, check=False)
                passed = completed.returncode == 0
            rows.append(gate.public(passed))
            if not passed:
                # Continue to publish the complete failure matrix, but never
                # allow a later pass to mask this failure.
                print(f"FAIL: {gate.gate_id}", file=sys.stderr)
        fresh_benchmark = Path(temporary) / "benchmark" / "results.json"
        if not args.evidence_only and fresh_benchmark.is_file():
            benchmark = json.loads(fresh_benchmark.read_text(encoding="utf-8"))
        evidence = build_evidence(rows, benchmark, screenshots)
        write_outputs(evidence, args.output_dir)
    print(f"{evidence['decision']}: {args.output_dir / 'report.md'}")
    return 0 if evidence["decision"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
