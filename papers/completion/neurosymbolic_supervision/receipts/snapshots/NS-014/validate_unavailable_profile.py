"""Structural audit for NS-014's unavailable native-proof closure.

This program does not invoke prove, verify, setup, pytest, or any fallback.
It records only the native CLI help/capability boundary and verifies that the
published unavailable record cannot be mistaken for a proof result.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[6]
PROFILE = ROOT / "papers/completion/neurosymbolic_supervision/qualification/native_profile.json"
RESULTS = ROOT / "papers/completion/neurosymbolic_supervision/qualification/native_results.jsonl"
SCOPE = ROOT / "papers/completion/neurosymbolic_supervision/qualification/native_scope_decision.md"
SNAPSHOT_ROOT = ROOT / "papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-014/qualification"
BINARY = ROOT / "external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/bin/linux-aarch64/groth16"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines() if line]

    assert profile["qualification_status"] == "unavailable"
    assert profile["candidate_backend"]["native_binary_reported_version"] is None
    assert profile["candidate_circuit_and_relation"]["statement_to_public_input_binding_verified"] is False
    assert profile["key_and_setup"]["verification_key_verified"] is False
    assert profile["candidate_backend"]["native_executable"]["sha256"] == digest(BINARY)
    assert len(rows) == 1
    row = rows[0]
    assert row["result_class"] == "unavailable_native_proving"
    assert row["retained_native_result"] is False
    assert row["proof_payload"]["present"] is False
    assert row["statement_and_public_inputs"]["binding_verified"] is False
    assert row["measurements"]["generation"]["elapsed_ms"] is None
    assert row["measurements"]["verification"]["elapsed_ms"] is None
    assert row["native_probe"]["proof_generation_invoked"] is False
    assert row["native_probe"]["verification_invoked"] is False
    assert row["native_probe"]["setup_invoked"] is False
    assert len(row["boundary_case_dispositions"]) == 5
    assert row["semantic_scope"]["horn_fragment_only"] is True
    assert "arbitrary CPython execution" in row["semantic_scope"]["does_not_establish"]
    assert "full temporal semantics" in row["semantic_scope"]["does_not_establish"]
    assert digest(PROFILE) == digest(SNAPSHOT_ROOT / "native_profile.json")
    assert digest(RESULTS) == digest(SNAPSHOT_ROOT / "native_results.jsonl")
    assert digest(SCOPE) == digest(SNAPSHOT_ROOT / "native_scope_decision.md")

    # This is deliberately a capability observation, not a proof operation.
    native_help = subprocess.run([str(BINARY), "--help"], check=True, text=True, capture_output=True)
    assert "Groth16 ZKP Prover/Verifier" in native_help.stdout
    assert "prove" in native_help.stdout and "verify" in native_help.stdout
    print("NS-014 unavailable native-profile closure: OK")
    print("native_cli_help_exit_code=0; prove=not_invoked; verify=not_invoked; setup=not_invoked")


if __name__ == "__main__":
    main()
