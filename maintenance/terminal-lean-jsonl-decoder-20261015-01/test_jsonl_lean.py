"""Replay actual native evidence and mutate only public in-memory receipts.

The main experiment must complete before this test module executes.  Missing
artifacts are errors, never skips.  These tests launch neither Lean nor source
code from the repository under test.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

import jsonl_lean as lean
from file_model_bridge import BUCKET_PATHS
from observed_files import FILE_PATHS, decode_file
from strict_jsonl import parse_jsonl, validate_jsonl_report

ROOT = Path(__file__).resolve().parent
EXPERIMENT = ROOT / "experiment-01"
OUTPUT = EXPERIMENT / "lean"


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resign(report):
    report.pop("report_sha256", None)
    report["report_sha256"] = hashlib.sha256(lean._wire(report)).hexdigest()


def _assert_unchanged(originals):
    assert all(_hash(path) == digest for path, digest in originals.items())


@pytest.fixture(scope="module")
def actual_evidence():
    report = json.loads((OUTPUT / "report.json").read_bytes())
    theory = json.loads((EXPERIMENT / "lean-theory.json").read_bytes())
    filecases = json.loads((EXPERIMENT / "file-case-report.json").read_bytes())
    assert lean.validate_constraint_lean_evidence(report, theory=theory, output=OUTPUT) is report
    assert report["positive_compiles"] == 1 and report["false_controls_rejected"] == 4
    assert len(lean.GENERIC_THEOREMS) == 10
    assert len(report["proved_theorems"]) == 17
    assert report["proved_theorems"] == theory["theorems"]
    assert filecases["counts"]["accepted"] == 7
    assert filecases["counts"]["model_refusal"] == 9
    assert filecases["counts"]["derived_cases"] == 16
    paths = [OUTPUT / "report.json", EXPERIMENT / "lean-theory.json",
             EXPERIMENT / "file-case-report.json"]
    for label in lean.LEAN_LABELS:
        paths.extend([OUTPUT / (label + ".lean"), OUTPUT / (label + "-process.json")])
    for entry in filecases["entries"]:
        paths.extend(Path(entry["after"]["root"]) / name for name in FILE_PATHS)
    originals = {path: _hash(path) for path in paths}
    yield report, theory, filecases, originals
    _assert_unchanged(originals)


def _memory_receipts(monkeypatch, report):
    """Override only retained report bytes; compiler/source files stay physical."""
    original_read = lean._read

    def read(path, maximum=64 * 1024**2):
        if path == OUTPUT / "report.json":
            return lean._wire(report)
        for check in report["checks"]:
            if path == OUTPUT / (check["label"] + "-process.json"):
                return lean._wire(check)
        return original_read(path, maximum)

    monkeypatch.setattr(lean, "_read", read)


def test_actual_seventeen_kernel_theorems_and_four_false_controls(actual_evidence):
    report, theory, _, _ = actual_evidence
    assert theory["theorems"] == list(lean.GENERIC_THEOREMS) + [
        "authored_case_" + str(index) + "_accepted" for index in range(7)]
    assert [check["label"] for check in report["checks"]] == list(lean.LEAN_LABELS)
    assert all(check["backend_executed"] is True
               and check["native_lifecycle"]["cleanup_confirmed"] is True
               and check["workspace_cleaned"] is True for check in report["checks"])
    assert all(check["limits"]["resident_memory_bytes"] == 1024 * 1024**2
               and check["child_resource_request"]["memory_mb"] == 1024
               for check in report["checks"])
    positive = report["checks"][0]
    assert "sorryAx" not in positive["stdout"]
    assert all("SchedulerConstraint." + name in positive["stdout"] for name in theory["theorems"])
    assert [check["status"] for check in report["checks"]] == ["passed"] + ["rejected"] * 4
    assert report["proof_scope"] == "defined_authored_finite_model_only_not_source_semantics_or_IntentIR_equivalence"
    assert all(report[key] is False for key in lean.AUTHORITY)
    assert theory["native_fol_lean_correspondence"] == "unproved"


def test_every_lean_case_is_derived_from_complete_observed_file_bytes(actual_evidence):
    _, theory, filecases, _ = actual_evidence
    derived = []
    for entry in filecases["entries"]:
        model = entry["model"]
        if model is None:
            assert entry["outcome"] == "file_refusal"
            continue
        assert entry["outcome"] in {"accepted", "model_refusal"}
        expected_pass = entry["outcome"] == "accepted"
        assert model["evaluation"]["evaluation_passed"] is expected_pass
        assert model["case"]["case_id"] == entry["spec"]["case_id"]
        assert len(model["case"]["buckets"]) == 2
        for bucket in model["case"]["buckets"]:
            bucket_id = bucket["bucket_id"]
            request_path = BUCKET_PATHS[bucket_id]["requests"]
            before_raw = decode_file(entry["before"], request_path)
            after_raw = decode_file(entry["after"], request_path)
            assert bucket["input_before"].encode("utf-8") == before_raw
            assert bucket["input_after"].encode("utf-8") == after_raw
            assert before_raw == after_raw
            for kind, field in (("requests", "requests"), ("plan", "plan")):
                path = BUCKET_PATHS[bucket_id][kind]
                for phase in ("before", "after"):
                    raw = decode_file(entry[phase], path)
                    parsed = parse_jsonl(raw, kind=kind)
                    assert validate_jsonl_report(model["projections"][phase][path],
                                                 raw=raw, kind=kind) == parsed
                    assert bucket[field] == parsed["rows"]
                assert model["file_bindings"][path]["row_source"] == "after_raw_utf8_bytes"
            assert bucket["metrics"] == entry["spec"]["metrics"][str(bucket_id)]
        derived.append({"case": deepcopy(model["case"]), "expected_pass": expected_pass,
                        "intended_violation_ids": list(entry["spec"]["intended_violation_ids"])})
    assert len(derived) == 16
    assert sum(item["expected_pass"] for item in derived) == 7
    assert derived == filecases["derived_cases"] == theory["cases"]
    assert theory["cases_sha256"] == hashlib.sha256(lean._wire(derived)).hexdigest()
    assert theory["accepted_case_ids"] == [item["case"]["case_id"] for item in derived if item["expected_pass"]]


@pytest.mark.parametrize("mutation", (
    "drop-proved-name", "extra-proved-name", "missing-printed-name", "sorry-axiom-stdout",
    "proof-scope-promotion", "original-task-promotion", "unknown-fulltask-promotion",
    "theory-sha", "missing-false-control", "false-counter-bool-alias",
    "child-cpu-bool-alias", "child-memory-bool-alias", "limit-cpu-bool-alias", "rss-bound",
    "actual-argv", "requested-argv", "home-assignment", "cleanup-false", "workspace-retained",
    "remaining-group-member", "parent-custody-mismatch", "readers-unjoined",
    "kernel-containment-promotion", "pid-bool-alias", "pid-mismatch", "birth-bool-alias",
    "duplicate-birth", "unknown-process-field"))
def test_resigned_native_receipt_mutations_refuse_without_file_edits(actual_evidence, monkeypatch, mutation):
    original, theory, _, originals = actual_evidence
    changed = deepcopy(original)
    check = changed["checks"][0]
    if mutation == "drop-proved-name":
        changed["proved_theorems"].pop()
    elif mutation == "extra-proved-name":
        changed["proved_theorems"].append("fabricated_theorem")
    elif mutation == "missing-printed-name":
        name = theory["theorems"][0]
        check["stdout"] = "\n".join(line for line in check["stdout"].splitlines()
                                      if "SchedulerConstraint." + name not in line)
    elif mutation == "sorry-axiom-stdout":
        check["stdout"] += "\n[propext, sorryAx]\n"
    elif mutation == "proof-scope-promotion":
        changed["proof_scope"] = "complete_original_source_and_task_proof"
    elif mutation == "original-task-promotion":
        changed["original_task_satisfaction"] = True
    elif mutation == "unknown-fulltask-promotion":
        changed["full_task_satisfaction_proved"] = True
    elif mutation == "theory-sha":
        changed["theory_sha256"] = "0" * 64
    elif mutation == "missing-false-control":
        changed["checks"].pop()
    elif mutation == "false-counter-bool-alias":
        changed["false_controls_rejected"] = True
    elif mutation == "child-cpu-bool-alias":
        check["child_resource_request"]["cpu_slots"] = True
    elif mutation == "child-memory-bool-alias":
        check["child_resource_request"]["memory_mb"] = True
    elif mutation == "limit-cpu-bool-alias":
        check["limits"]["cpu_seconds"] = True
    elif mutation == "rss-bound":
        check["limits"]["resident_memory_bytes"] *= 2
    elif mutation == "actual-argv":
        check["actual_invocation_command"][-1] = "Forged.lean"
    elif mutation == "requested-argv":
        check["requested_command"][-1] = "Forged.lean"
    elif mutation == "home-assignment":
        check["environment"]["HOME"] = "/tmp/fabricated"
    elif mutation == "cleanup-false":
        check["native_lifecycle"]["cleanup_confirmed"] = False
    elif mutation == "workspace-retained":
        check["native_lifecycle"]["workspace"]["removed"] = False
    elif mutation == "remaining-group-member":
        check["native_lifecycle"]["remaining_group_members"] = [deepcopy(check["native_lifecycle"]["leader"])]
    elif mutation == "parent-custody-mismatch":
        check["native_lifecycle"]["parent"]["pid"] += 1
    elif mutation == "readers-unjoined":
        check["native_lifecycle"]["readers"]["joined"] = 1
    elif mutation == "kernel-containment-promotion":
        check["native_lifecycle"]["kernel_containment_attested"] = True
    elif mutation == "pid-bool-alias":
        check["pid"] = True
    elif mutation == "pid-mismatch":
        check["pid"] += 1
    elif mutation == "birth-bool-alias":
        check["native_lifecycle"]["leader"]["birth_ticks"] = True
    elif mutation == "duplicate-birth":
        other = changed["checks"][1]
        other["pid"] = check["pid"]
        other["native_lifecycle"]["leader"] = deepcopy(check["native_lifecycle"]["leader"])
    else:
        check["fabricated_proof_authority"] = True
    _resign(changed)
    _memory_receipts(monkeypatch, changed)
    with pytest.raises(ValueError):
        lean.validate_constraint_lean_evidence(changed, theory=theory, output=OUTPUT)
    _assert_unchanged(originals)


@pytest.mark.parametrize("mutation", ("source", "omit-control", "case-sha", "changed-file-derived-row",
                                      "changed-observed-bytes", "drop-refused-case", "extra-theorem",
                                      "source-equivalence-promotion", "parser-proof-promotion"))
def test_resigned_theory_mutations_cannot_replace_file_derived_cases(actual_evidence, monkeypatch, mutation):
    original_report, original_theory, _, originals = actual_evidence
    theory = deepcopy(original_theory)
    if mutation == "source":
        theory["sources"][0]["source"] += "\naxiom fabricated : False\n"
    elif mutation == "omit-control":
        theory["sources"].pop()
    elif mutation == "case-sha":
        theory["cases_sha256"] = "0" * 64
    elif mutation == "changed-file-derived-row":
        theory["cases"][0]["case"]["buckets"][0]["requests"][0]["gen_len"] += 1
    elif mutation == "changed-observed-bytes":
        theory["cases"][0]["case"]["buckets"][0]["input_before"] += " "
    elif mutation == "drop-refused-case":
        index = next(index for index, case in enumerate(theory["cases"]) if case["expected_pass"] is False)
        theory["cases"].pop(index)
    elif mutation == "extra-theorem":
        theory["theorems"].append("fabricated")
    elif mutation == "source-equivalence-promotion":
        theory["source_model_equivalence_proved"] = True
    else:
        theory["formal_parser_correctness_proved"] = True
    _resign(theory)
    changed = deepcopy(original_report)
    changed["theory_sha256"] = hashlib.sha256(lean._wire(theory)).hexdigest()
    _resign(changed)
    _memory_receipts(monkeypatch, changed)
    with pytest.raises(ValueError):
        lean.validate_constraint_lean_evidence(changed, theory=theory, output=OUTPUT)
    _assert_unchanged(originals)


def test_false_controls_contradict_actual_model_predicates(actual_evidence):
    _, theory, _, _ = actual_evidence
    controls = {row["label"]: row["source"] for row in theory["sources"][1:]}
    assert "coverageCheck controlRequests [row1, row1] = true" in controls["false-duplicate-missing-ids"]
    assert "globalCapCheck (nineShapeRows.take 5) (nineShapeRows.drop 5) = true" in controls["false-nine-global-shapes"]
    assert "batchCheck [row1, row2] = true" in controls["false-inconsistent-batch"]
    assert "prompt := 65" in controls["false-insufficient-alignment"]
    assert "seq := 64" in controls["false-insufficient-alignment"]
    for source in controls.values():
        assert "theorem deliberate_false_control" in source
        assert ":= by decide" in source
