#!/usr/bin/python3.12
"""Ordinary NS-028 retained-evidence check. No grants, providers, scorers, or reruns."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve()
while not (ROOT / "scripts" / "ns028_completion_guard.py").is_file():
    if ROOT.parent == ROOT:
        raise SystemExit("repository root not found")
    ROOT = ROOT.parent

TEMPLATE = ROOT / "papers/completion/neurosymbolic_supervision/qualification/operator_inputs/NS-028/pending_receipt.template.json"
ORIGINAL_NS016 = ROOT / (
    "papers/completion/neurosymbolic_supervision/pilot/recovery/"
    "pre_final_projection_history_v1/papers/completion/neurosymbolic_supervision/receipts/NS-016.json"
)
CURRENT_NS016 = ROOT / "papers/completion/neurosymbolic_supervision/receipts/NS-016.json"
FREEZE = ROOT / "papers/completion/neurosymbolic_supervision/artifacts/final_experiment_freeze.json"
HARNESS = ROOT / "papers/completion/neurosymbolic_supervision/pilot/recovery/root_native_harness_execution.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    template = json.loads(TEMPLATE.read_bytes())
    if template.get("task_id") != "NS-028":
        raise SystemExit("template task_id is not NS-028")
    if hashlib.sha256(TEMPLATE.read_bytes()).hexdigest() != (
        "f8a79dda737881b04099f37c9467cfc5ba86b11f1894ae8b9d510358e706d2ea"
    ):
        raise SystemExit("operator pending-receipt template hash changed")

    matched = 0
    for current, snapshot in template["outputs"].items():
        expected = template["artifacts"][snapshot]
        current_path = ROOT / current
        snapshot_path = ROOT / snapshot
        if sha(current_path) != expected or sha(snapshot_path) != expected:
            raise SystemExit("hash mismatch: " + current)
        matched += 1
    print("retained_output_snapshot_pairs", matched)

    spec = importlib.util.spec_from_file_location(
        "ns028_completion_guard", ROOT / "scripts/ns028_completion_guard.py"
    )
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    gate = guard.verify(ROOT, template)
    print("scientific_completion_gate", json.dumps(gate, sort_keys=True, separators=(",", ":")))
    if gate["terminal_cells"] != 24 or gate["useful_witnesses"] != {"A": 5, "B": 5}:
        raise SystemExit("unexpected retained useful-witness counts")
    if gate["new_provider_calls"] != 0 or gate["new_scorer_calls"] != 0:
        raise SystemExit("guard reported new provider or scorer calls")

    freeze = json.loads(FREEZE.read_bytes())
    if freeze.get("first_final_attempt_started") is not False:
        raise SystemExit("final attempt already started")
    if freeze.get("retained_executable_arms") != ["A", "B"]:
        raise SystemExit("retained arms are not the pre-outcome A/B design")
    if freeze.get("freeze_sha256") != "ac605b5de8b58cc41c5c3609e7752e5e4441ab627dbbe6d31f4d8d086b33732d":
        raise SystemExit("canonical freeze hash changed")
    print("freeze_file_sha256", sha(FREEZE))
    print("freeze_sha256", freeze["freeze_sha256"])
    print("planned_final_cells", len(freeze.get("planned_cells", [])))
    print("removed_arms", sorted(freeze.get("removed_arms", {})))

    original = json.loads(ORIGINAL_NS016.read_bytes())
    current = json.loads(CURRENT_NS016.read_bytes())
    print("original_ns016_sha256", sha(ORIGINAL_NS016))
    print("current_ns016_sha256", sha(CURRENT_NS016))
    if original.get("status") != "complete" or original.get("task_id") != "NS-016":
        raise SystemExit("original NS016 history is missing")
    if current.get("status") != "pending_operator_evidence_review" or current.get("template_only") is not True:
        raise SystemExit("corrective NS016 receipt is not pending")
    if current.get("correction_of", {}).get("sha256") != sha(ORIGINAL_NS016):
        raise SystemExit("corrective NS016 does not bind the original receipt")

    harness = json.loads(HARNESS.read_bytes())
    print("native_harness_sha256", sha(HARNESS))
    if harness.get("executed") is not True or harness.get("fixture") is not False:
        raise SystemExit("native harness evidence is not an actual execution")
    required = (
        "native_import",
        "admit_final_attempt",
        "missing_freeze_refused",
        "stale_freeze_refused",
        "current_source_profile",
        "consumed_replay_refused",
    )
    checks = harness.get("checks", {})
    if any(checks.get(name) is not True for name in required):
        raise SystemExit("required native harness controls are missing")
    print("native_harness_checks", json.dumps(checks, sort_keys=True, separators=(",", ":")))
    print("new_effects", "none")
    print("status", "retained_evidence_verified")
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
