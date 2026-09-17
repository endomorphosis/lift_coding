#!/usr/bin/env python3
"""Retain actual LA008 fixture qualification in an isolated candidate only."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

STAGE = Path(__file__).resolve().parent
ROOT = STAGE / "candidate"
REPOSITORY = STAGE.parents[3]
BASE = Path("papers/completion/law_to_action")
SNAP = BASE / "receipts/snapshots/LA-008"
NEW = SNAP / "independent-correction"
OWNED = [BASE / name for name in (
    "benchmark/run.py", "benchmark/handlers/__init__.py", "benchmark/handlers/effects.py",
    "benchmark/cases/schema.json", "benchmark/tests/test_measurement_integrity.py")]
PYTHON = "/usr/bin/python3.12"


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def copy_once(source, relative):
    destination = ROOT / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(source.read_bytes())


def main():
    original = json.loads((STAGE / "original-files.json").read_text())
    original_receipt = ROOT / NEW / "original-receipt.json"
    old_receipt = json.loads(original_receipt.read_text())
    preserved = []
    context = []
    for item in original["files"]:
        path = Path(item["path"])
        if path in OWNED:
            continue
        actual = original_receipt if path == BASE / "receipts/LA-008.json" else ROOT / path
        assert sha(actual) == item["sha256"], str(path)
        (preserved if path.is_relative_to(SNAP) or actual == original_receipt else context).append(item)
    assert not list((ROOT / BASE / "benchmark").rglob("__pycache__"))
    task_seed_bytes = subprocess.check_output([
        "git", "show", original["source_commit"] + ":" + str(BASE / "tasks.json")], cwd=REPOSITORY)
    seed = json.loads(task_seed_bytes)
    task = next(item for item in seed["tasks"] if item["id"] == "LA-008")
    assert [item["criterion"] for item in old_receipt["criteria"]] == task["acceptance_criteria"]
    put(ROOT / NEW / "exact-task-contract.json", task)
    copy_once(STAGE / "original-files.json", NEW / "original-files.json")
    copy_once(Path(__file__), NEW / "finalize_candidate.py")
    outputs = {}
    for current in OWNED:
        snapshot = NEW / "outputs" / current.relative_to(BASE)
        copy_once(ROOT / current, snapshot)
        outputs[str(current)] = str(snapshot)
    for name in ("reproduce_observer_regression.py", "qualify_negative_controls.py"):
        copy_once(STAGE / name, NEW / name)
    review_dir = STAGE.parent / "la008_independent_review"
    for name in ("probe_postconditions.py", "probe.stdout.log"):
        copy_once(review_dir / name, NEW / "independent-review" / name)
    scope = {
        "source_commit": original["source_commit"], "implementation_commit": original["implementation_commit"],
        "original_receipt_sha256": sha(original_receipt), "original_snapshots_preserved": True,
        "historical_evidence": "The old receipt, code snapshots and traces are retained verbatim as superseded historical evidence. Their network=disabled label and count-only measurement conclusions are not current qualifications.",
        "original_defects": ["An unjournaled export was counted as zero effects.",
                             "A journal with forged bytes and digest passed without hashing the actual file.",
                             "Allowed-work success and expected measurement trusted event counts.",
                             "The subprocess did not implement the claimed disabled network boundary."],
        "qualified_scope": "Trusted bounded declarative export_json fixtures, a real environment-scrubbed child subprocess, parent post-exit filesystem hashing, exact requested postconditions and journal/file bijection.",
        "observer_trust": "Independent of handler-reported events and declared intent; the parent observer, runner, fixture inputs and output storage are trusted. This is not adversarial tamper-proof log attestation.",
        "process_controls": ["Environment scrub", "Process group timeout and observed return code/signal", "Fresh UUID state directory"],
        "isolation": {"arbitrary_generated_source_execution": False, "os_filesystem_isolation": False,
                      "os_network_isolation": False, "network": "not_exercised_not_isolated"},
        "future_gates": ["Arbitrary untrusted source must not be admitted until separate OS/filesystem/network isolation is implemented and qualified.",
                         "Real solver, cryptographic capability, storage, network, model and product integration remain unqualified by these fixtures.",
                         "Natural source admission and empirical benchmark execution remain downstream; every retained run has empirical_eligible=false."],
        "measurement": ["Read actual regular-file bytes and SHA256 using bounded no-follow descriptor-relative traversal.",
                        "Observe unexpected, missing, extra, linked, malformed and unjournaled state; fail closed on incomplete scans.",
                        "Require exact journal schema/run identity and one-to-one target/byte/digest correspondence.",
                        "Match actual exports to the requested parent-extracted target/bytes/digest before awarding allowed-work credit.",
                        "Denied success requires no observed state entries and complete, consistent observation.",
                        "Append records with checked write-all progress; failed partial tails remain preserved and block later appends."],
        "independent_review": "The independent reviewer reproduced a matching forged journal for the wrong actual payload and confirmed zero measurement/allowed-work credit; correct effects with process failure also receive no credit.",
        "empirical_benchmark_result": False,
    }
    put(ROOT / NEW / "correction-scope.json", scope)
    commands = []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")

    def execute(name, argv, script_artifact=None):
        started_at = now()
        result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, check=False, timeout=30)
        completed_at = now()
        folder = NEW / "validation"
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
        stdout = folder / (name + ".stdout.raw")
        stderr = folder / (name + ".stderr.raw")
        for path, data in ((stdout, result.stdout), (stderr, result.stderr)):
            with (ROOT / path).open("xb") as stream:
                stream.write(data)
        log = folder / (name + ".json")
        record = {"argv": argv, "cwd": ".", "actual_cwd": str(ROOT), "environment_overrides": {"PYTHONDONTWRITEBYTECODE": "1"},
                  "started_at": started_at, "completed_at": completed_at, "exit_code": result.returncode,
                  "stdout_artifact": str(stdout), "stdout_sha256": sha(ROOT / stdout),
                  "stderr_artifact": str(stderr), "stderr_sha256": sha(ROOT / stderr),
                  "stdout": result.stdout.decode("utf-8", errors="replace"),
                  "stderr": result.stderr.decode("utf-8", errors="replace")}
        put(ROOT / log, record)
        if result.returncode != 0:
            raise RuntimeError(f"Actual validation failed: {name}, exit {result.returncode}; retained {log}")
        command = {key: record[key] for key in ("argv", "cwd", "environment_overrides", "started_at", "completed_at", "exit_code")}
        command["log"] = str(log)
        if script_artifact:
            command["script_artifact"] = str(script_artifact)
        commands.append(command)
        return log

    unit = execute("measurement-integrity", [PYTHON, "-m", "unittest", str(BASE / "benchmark/tests/test_measurement_integrity.py"), "-v"])
    regression = execute("observer-regression", [PYTHON, str(NEW / "reproduce_observer_regression.py")], NEW / "reproduce_observer_regression.py")
    runner = str(BASE / "benchmark/run.py")
    runner_snapshot = outputs[runner]
    smoke = execute("smoke", [PYTHON, runner, "smoke", "--trace-dir", str(NEW / "smoke/traces"),
                              "--records", str(NEW / "smoke/records.jsonl"), "--seed", "104729", "--timeout-seconds", "5"], runner_snapshot)
    replay = execute("replay", [PYTHON, runner, "replay", "--source-records", str(NEW / "smoke/records.jsonl"),
                                "--index", "0", "--trace-dir", str(NEW / "replay/traces"),
                                "--records", str(NEW / "replay/records.jsonl"), "--timeout-seconds", "5"], runner_snapshot)
    controls = execute("negative-controls", [PYTHON, str(NEW / "qualify_negative_controls.py")], NEW / "qualify_negative_controls.py")
    assert not list((ROOT / BASE / "benchmark").rglob("__pycache__"))
    put(ROOT / NEW / "preservation-check.json", {"passed": True, "original_receipt_and_snapshots": preserved,
                                               "unchanged_prior_task_context_not_for_integration": context})
    explanations = [
        "Actual smoke runs an authorized fixture with one independently hashed export matching the requested target, bytes and SHA256 and a denied fixture with no state entries. Journal events are separate claims checked one-to-one against actual files and the exact run ID. Regression tests reject unjournaled, missing, extra, duplicate, forged, linked and unexpected state; even an internally consistent forged journal cannot make a wrong requested export pass.",
        "Two actual subprocess controls deliberately deny scheduled allowed fixture work. The allowed-work metric records zero successes and reject_all_detected=true. Success is recomputed from actual exit status, independent file/journal integrity and exact requested postconditions; a count or stored expected-measurement flag alone earns no credit.",
        "Fresh actual smoke and replay retain UUID request/stdout/stderr/trace files and agree on deterministic semantic effects. Separate retained controls exercise a real SIGKILL timeout and real handler error exit 2. Checked append loops preserve and reject incomplete JSONL tails; tests inject short writes and failed partial writes. UTC start is captured before child execution and completion afterwards.",
        "The 22-test suite and retained side-by-side original/corrected observer reproduction qualify only a trusted bounded declarative export_json fixture route. Literal source strings are data; arbitrary source execution is not admitted. Every retained fixture is empirical_eligible=false. Labels explicitly say network not exercised and not isolated; no OS filesystem/network isolation, real solver/crypto/model/product runtime, natural benchmark or research outcome is qualified here.",
    ]
    evidence = [
        [unit, regression, smoke, NEW / "smoke/records.jsonl", NEW / "independent-review/probe.stdout.log"],
        [unit, controls, NEW / "negative-controls/records.jsonl", Path(runner_snapshot)],
        [unit, replay, controls, NEW / "replay/records.jsonl", NEW / "negative-controls/records.jsonl"],
        [unit, regression, NEW / "correction-scope.json", Path(outputs[str(BASE / "benchmark/cases/schema.json")])],
    ]
    artifacts = {str(path.relative_to(ROOT)): sha(path) for path in sorted((ROOT / SNAP).rglob("*")) if path.is_file()}
    receipt = {
        "schema": "paper-task-evidence/v1", "paper_id": "law_to_action", "task_id": "LA-008", "status": "complete",
        "completed_at": now(),
        "completion_mode": "Corrected trusted bounded declarative fixture measurement checkpoint. Independent actual filesystem hashing and requested postconditions are qualified; arbitrary code, OS/network isolation and empirical research remain outside this route.",
        "artifacts": artifacts, "outputs": outputs,
        "criteria": [{"criterion": criterion, "status": "met", "explanation": explanation, "evidence": [str(p) for p in refs]}
                     for criterion, explanation, refs in zip(task["acceptance_criteria"], explanations, evidence, strict=True)],
        "commands": commands,
        "source_versions": {"historical_merged_commit": original["source_commit"], "historical_implementation_commit": original["implementation_commit"],
                            "historical_receipt_sha256": sha(original_receipt), "frozen_task_seed_sha256": hashlib.sha256(task_seed_bytes).hexdigest(),
                            "corrected_current_output_sha256": {name: artifacts[snapshot] for name, snapshot in outputs.items()},
                            "harness": "2.0.0", "handler": "bounded-export-handler/v2", "observer": "independent-filesystem-journal-observer/v2",
                            "python": subprocess.check_output([PYTHON, "--version"], text=True).strip(),
                            "python_executable": PYTHON, "python_executable_sha256": sha(Path(PYTHON)),
                            "measurement_boundary": scope["qualified_scope"], "isolation": scope["isolation"],
                            "future_gates": scope["future_gates"], "empirical_benchmark_result": False},
    }
    receipt_path = ROOT / BASE / "receipts/LA-008.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    verifier_path = REPOSITORY / "scripts/paper_supervisors.py"
    spec = importlib.util.spec_from_file_location("la008_strict_verifier", verifier_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    verified = module._verify_task_contract("law_to_action", task, check_current=True)
    put(STAGE / "strict-candidate-verification.json", {"passed": True, "verified_at": now(), "verifier_sha256": sha(verifier_path),
                                                      "candidate": str(ROOT), "receipt_sha256": sha(receipt_path), "result": verified})
    integration = [*OWNED, BASE / "receipts/LA-008.json"] + [p.relative_to(ROOT) for p in sorted((ROOT / SNAP).rglob("*")) if p.is_file()]
    review = {"candidate": str(ROOT), "source_commit": original["source_commit"], "implementation_commit": original["implementation_commit"],
              "receipt_sha256": sha(receipt_path), "strict_verifier_passed": True, "actual_validation_commands_passed": len(commands),
              "unit_tests_passed": 22, "original_receipt_and_all_snapshots_preserved": True,
              "prior_task_context_unchanged_and_excluded": context, "scientific_outcomes_changed": False,
              "live_lane_or_database_or_provider_mutations": False, "scope": scope,
              "files": [{"path": str(path), "sha256": sha(ROOT / path), "bytes": (ROOT / path).stat().st_size} for path in integration]}
    put(STAGE / "review.json", review)
    print(json.dumps({"candidate": str(ROOT), "receipt_sha256": sha(receipt_path), "files": len(integration),
                      "artifacts": len(artifacts), "strict_verifier_passed": True, "unit_tests_passed": 22}, sort_keys=True))


if __name__ == "__main__":
    main()
