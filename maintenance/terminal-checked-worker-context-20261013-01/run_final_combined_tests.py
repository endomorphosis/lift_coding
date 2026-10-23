"""Fresh focused qualification; changes no production or test source bytes."""
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

Z = Path(__file__).resolve().parent
C = Z / "checkout"
NAME = "final-combined-01"
ATTEMPT = Z / NAME
os.umask(0o077)
ATTEMPT.mkdir(mode=0o700)
TESTS = [
    "test/api/test_checked_audit_context.py",
    "test/api/test_terminal_checked_worker_budget.py",
    "test/api/test_router_checked_context_integration.py",
    "benchmarks/agent_supervisor/container_coding/test_container_worker_deployment.py",
    "test/api/test_model_input_observation_receipt.py",
    "test/api/test_router_model_input_observation.py",
    "benchmarks/agent_supervisor/container_coding/test_terminal_observer_stop.py",
    "benchmarks/agent_supervisor/container_coding/test_terminal_model_input_observation_audit.py",
    "benchmarks/agent_supervisor/container_coding/test_terminal_context_audit.py",
    "benchmarks/agent_supervisor/container_coding/test_terminal_context_audit_budget.py",
    "benchmarks/agent_supervisor/container_coding/test_terminal_nomination_context_audit.py",
    "benchmarks/agent_supervisor/container_coding/test_terminal_native_dispatch_diagnostics.py",
    "test/api/test_native_dispatch_diagnostics.py",
]
REQUIRED_COUNTS = {
    "test_checked_audit_context": 71,
    "test_terminal_checked_worker_budget": 75,
    "test_router_checked_context_integration": 24,
    "test_container_worker_deployment": 72,
    "test_model_input_observation_receipt": 55,
    "test_router_model_input_observation": 23,
}


def changed_sources():
    raw = subprocess.check_output(["git", "status", "--porcelain=v1", "-z"], cwd=C)
    paths = []
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        relative = entry[3:].decode("utf-8")
        if relative.startswith("data/aseh/"):
            continue
        if relative.endswith(".py"):
            paths.append(relative)
        else:
            raise ValueError("unexpected changed path outside generated data: " + relative)
    if len(paths) != 14 or len(set(paths)) != 14:
        raise ValueError("exact fourteen frozen changed source/test paths required")
    return sorted(paths)


def pins(paths):
    result = []
    for relative in paths:
        path = C / relative
        raw = path.read_bytes()
        result.append({"path": str(path), "relative_path": relative, "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(), "mode": oct(path.stat().st_mode & 0o777)})
    return result


def write(path, value):
    with path.open("x", encoding="utf-8") as output:
        json.dump(value, output, sort_keys=True, indent=2, ensure_ascii=False)
        output.write("\n")
    path.chmod(0o600)


paths_before = changed_sources()
before = pins(paths_before)
suite_pins_before = pins(TESTS)
write(ATTEMPT / "producer-pins-before.json", before)
write(ATTEMPT / "suite-pins-before.json", suite_pins_before)
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TIKTOKEN_CACHE_DIR="/tmp/data-gym-cache",
    IPFS_ACCELERATE_META_INDEX_DUCKDB=str(ATTEMPT / "meta.duckdb"),
    IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB=str(ATTEMPT / "seal.duckdb"),
    IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR=str(ATTEMPT / "orchestration"))
env.pop("IPFS_ACCELERATE_META_INDEX_DUCKLAKE", None)
env["PYTHONPATH"] = ":".join([
    "/home/barberb/lift_coding/maintenance/terminal-proof-cache-revision-20261012-01/pinned-host-duckdb",
    "/home/barberb/lift_coding/maintenance/terminal-token-pairing-20261012-01/pinned-host-tokenizer",
    str(C),
    "/home/barberb/lift_coding/maintenance/terminal-compact-retrieval-20261011-01/pinned-dependencies-v10/datasets",
    "/home/barberb/lift_coding/maintenance/terminal-compact-retrieval-20261011-01/pinned-dependencies-v10/kit",
    "/home/barberb/lift_coding/.venvs/terminal-bench-harbor/lib/python3.12/site-packages",
])
xml = ATTEMPT / "results.xml"
command = [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--junitxml=" + str(xml), *TESTS]
started = time.monotonic()
timeout = False
with (ATTEMPT / "pytest.log").open("xb") as output:
    try:
        completed = subprocess.run(command, cwd=C, env=env, stdout=output, stderr=subprocess.STDOUT,
            timeout=1800, check=False, preexec_fn=lambda: os.umask(0o022))
        exit_code = completed.returncode
    except subprocess.TimeoutExpired:
        exit_code, timeout = None, True
paths_after = changed_sources()
after = pins(paths_after)
suite_pins_after = pins(TESTS)
write(ATTEMPT / "producer-pins-after.json", after)
write(ATTEMPT / "suite-pins-after.json", suite_pins_after)
counts = {"tests": 0, "unique_tests": 0, "failures": 0, "errors": 0, "skips": 0}
suite_counts = collections.Counter()
case_ids = []
if xml.exists():
    root = ET.parse(xml).getroot()
    cases = list(root.iter("testcase"))
    case_ids = [(case.get("classname"), case.get("name")) for case in cases]
    counts = {"tests": len(cases), "unique_tests": len(set(case_ids)),
        "failures": len(list(root.iter("failure"))), "errors": len(list(root.iter("error"))),
        "skips": len(list(root.iter("skipped")))}
    suite_counts.update(case.get("classname").split(".")[-1] for case in cases)
required_counts_match = all(suite_counts[name] == count for name, count in REQUIRED_COUNTS.items())
qualified = (exit_code == 0 and not timeout and before == after and paths_before == paths_after
    and suite_pins_before == suite_pins_after and counts["tests"] == counts["unique_tests"]
    and counts["tests"] >= sum(REQUIRED_COUNTS.values()) and counts["failures"] == 0
    and counts["errors"] == 0 and counts["skips"] == 0 and required_counts_match
    and len(suite_counts) == len(TESTS))
record = {"schema": "terminal-checked-worker-final-combined-tests@1", "attempt": NAME,
    "cwd": str(C), "command": command, "timeout_seconds": 1800, "timed_out": timeout,
    "elapsed_seconds": time.monotonic() - started, "exit_code": exit_code,
    "fresh_metadata_and_pytest_seal_namespaces": True, "child_umask": "022",
    "test_files": TESTS, "test_counts": counts, "per_suite_test_counts": dict(suite_counts),
    "required_counts": REQUIRED_COUNTS, "required_counts_match": required_counts_match,
    "changed_source_count": len(before), "pins_before": before, "pins_after": after,
    "changed_path_population_unchanged": paths_before == paths_after,
    "producer_bytes_unchanged": before == after, "suite_bytes_unchanged": suite_pins_before == suite_pins_after,
    "qualified_combined_test_run": qualified, "provider_usage_measured": False,
    "actual_worker_origin_qualified_by_unit_tests": False, "full_supervisor_qualified_by_unit_tests": False,
    "full_task_satisfaction": False, "training_convergence_proved": False}
write(ATTEMPT / "testcase-ids.json", [list(item) for item in case_ids])
report = Z / (NAME + "-report.json")
write(report, record)
for path in ATTEMPT.iterdir():
    if path.is_file():
        path.chmod(0o600)
print(json.dumps({"report": str(report), "sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
    "bytes": report.stat().st_size, "qualified": qualified, "counts": counts,
    "producer_bytes_unchanged": before == after, "required_counts_match": required_counts_match}, sort_keys=True))
raise SystemExit(0 if qualified else 1)
