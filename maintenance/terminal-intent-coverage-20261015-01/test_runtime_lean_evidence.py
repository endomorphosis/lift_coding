"""Mutate actual accepted main02 receipts in memory, without new children.

These tests require the selected main02 run to finish before regression. There
is no synthetic passing receipt and no fallback or skip for a missing run.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

import logic_projections as logic

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "experiment-02" / "lean"


@pytest.fixture(scope="module")
def accepted_native_evidence():
    report = json.loads((OUTPUT / "report.json").read_bytes())
    projections = json.loads((OUTPUT.parent / "logic-projections.json").read_bytes())
    assert logic.validate_lean_evidence(report, projections=projections, output=OUTPUT) is report
    assert report["positive_compiles"] == 4
    assert report["false_type_controls_rejected"] == 1
    assert report["qualified"] is True
    paths = [OUTPUT / "report.json"]
    for row in report["checks"]:
        paths += [OUTPUT / (row["label"] + "-process.json"), OUTPUT / (row["label"] + ".lean")]
    originals = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    return report, projections, originals


def _resign(report):
    report.pop("report_sha256", None)
    report["report_sha256"] = hashlib.sha256(logic._wire(report)).hexdigest()


def _mutable_receipts(monkeypatch, changed):
    original_read = logic._read
    def read(path, maximum=64 * 1024**2):
        if path == OUTPUT / "report.json":
            return logic._wire(changed)
        for check in changed["checks"]:
            if path == OUTPUT / (check["label"] + "-process.json"):
                return logic._wire(check)
        return original_read(path, maximum)
    monkeypatch.setattr(logic, "_read", read)


def test_retained_actual_lean_processes_are_qualified(accepted_native_evidence):
    report, _, _ = accepted_native_evidence
    assert all(row["backend_executed"] is True and row["native_lifecycle"]["cleanup_confirmed"] is True
        for row in report["checks"])
    assert all(row["limits"]["resident_memory_bytes"] == 1024 * 1024**2
        and row["child_resource_request"]["memory_mb"] == 1024 for row in report["checks"])
    assert report["theorems_proved"] == []


@pytest.mark.parametrize("mutation", (
    "root-proof", "root-training", "root-provider-alias", "old-profile", "false-count-alias", "unknown-root",
    "drop-rss", "change-rss", "change-child-memory", "cpu-bool-alias", "elapsed-bool-alias",
    "returncode-bool-alias", "threads-bool-alias", "pid-bool-alias", "actual-argv", "home-assignment",
    "inherited-environment", "resource-failure", "birth-bool-alias", "writer-bool-alias", "cleanup-false",
    "kernel-claim", "unknown-lifecycle", "process-proof", "source-pin", "executable-pin",
    "missing-control", "duplicate-birth", "unknown-process"))
def test_resigned_mutations_of_real_native_evidence_refuse(accepted_native_evidence, monkeypatch, mutation):
    original, projections, originals = accepted_native_evidence
    changed = deepcopy(original)
    check = changed["checks"][0]
    if mutation == "root-proof":
        changed["proof_authority"] = True
    elif mutation == "root-training":
        changed["training_steps"] = 1
    elif mutation == "root-provider-alias":
        changed["provider_calls"] = False
    elif mutation == "old-profile":
        changed["profile"] = "direct-installed-lean-native-generated-declarations-single-thread@1"
    elif mutation == "false-count-alias":
        changed["false_type_controls_rejected"] = True
    elif mutation == "unknown-root":
        changed["formal_equivalence"] = True
    elif mutation == "drop-rss":
        check["limits"].pop("resident_memory_bytes")
    elif mutation == "change-rss":
        check["limits"]["resident_memory_bytes"] *= 2
    elif mutation == "change-child-memory":
        check["child_resource_request"]["memory_mb"] = 256
    elif mutation == "cpu-bool-alias":
        check["child_resource_request"]["cpu_slots"] = True
    elif mutation == "elapsed-bool-alias":
        check["elapsed_seconds"] = False
    elif mutation == "returncode-bool-alias":
        check["returncode"] = False
    elif mutation == "threads-bool-alias":
        check["lean_threads"] = True
    elif mutation == "pid-bool-alias":
        check["pid"] = True
    elif mutation == "actual-argv":
        check["actual_invocation_command"][-1] = "Other.lean"
    elif mutation == "home-assignment":
        check["environment"]["HOME"] = "/tmp/invented"
    elif mutation == "inherited-environment":
        check["inherited_environment"] = True
    elif mutation == "resource-failure":
        check["resource_exhausted"] = True
    elif mutation == "birth-bool-alias":
        check["native_lifecycle"]["leader"]["birth_ticks"] = True
    elif mutation == "writer-bool-alias":
        check["native_lifecycle"]["stdin_writer"]["started"] = False
    elif mutation == "cleanup-false":
        check["native_lifecycle"]["cleanup_confirmed"] = False
    elif mutation == "kernel-claim":
        check["native_lifecycle"]["kernel_containment_attested"] = True
    elif mutation == "unknown-lifecycle":
        check["native_lifecycle"]["proved_current_authority"] = True
    elif mutation == "process-proof":
        check["proof_authority"] = True
    elif mutation == "source-pin":
        check["source"]["sha256"] = "0" * 64
    elif mutation == "executable-pin":
        check["executable"]["sha256"] = "0" * 64
    elif mutation == "missing-control":
        changed["checks"].pop()
    elif mutation == "duplicate-birth":
        other = changed["checks"][1]
        other["pid"] = check["pid"]
        other["native_lifecycle"]["leader"] = deepcopy(check["native_lifecycle"]["leader"])
    else:
        check["new_authority"] = True
    _resign(changed)
    _mutable_receipts(monkeypatch, changed)
    with pytest.raises(ValueError):
        logic.validate_lean_evidence(changed, projections=projections, output=OUTPUT)
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in originals.items())
