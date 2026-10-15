"""Train no model: genuinely qualify the fresh /app conditional integer model."""
import hashlib
import json
import os
from pathlib import Path
import sys

os.umask(0o077)
ACTUAL = Path("/opt/ipfs-supervisor/state/aa-model-10")
REPOSITORY = Path("/app")
assert os.getuid() == os.geteuid() == 1000
assert not ACTUAL.exists()
ACTUAL.mkdir(mode=0o700)
os.environ["IPFS_ACCELERATE_META_INDEX_DUCKDB"] = str(ACTUAL / "meta-index.duckdb")
os.environ["IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB"] = str(ACTUAL / "pytest-seal.duckdb")
os.environ["IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR"] = str(ACTUAL / "orchestration")

from benchmarks.agent_supervisor.container_coding.terminal_codebase_finite_service_experiment import _open, _scheduler
from benchmarks.agent_supervisor.container_coding.terminal_call_ir_composition import qualify_current_call_composition
from ipfs_datasets_py.logic.software_contracts.codebase_integer_profile import IntegerOffsetContract
from ipfs_datasets_py.logic.software_contracts.codebase_finite_integer_observation import seal_finite_integer_tools


def save(path, value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode()
    with path.open("xb") as stream:
        stream.write(raw)


SOURCES = {
    "callee.py": b"def increment(n: int) -> int:\n    return n + 1\n",
    "caller.py": b"from callee import increment\n\ndef twice(n: int) -> int:\n    return increment(increment(n))\n",
    "dynamic.py": b"def unsupported(expression):\n    return eval(expression)\n",
}
for name, raw in SOURCES.items():
    assert (REPOSITORY / name).read_bytes() == raw
    assert (REPOSITORY / name).stat().st_mode & 0o777 == 0o644
assert (REPOSITORY / "build/task-instruction.txt").read_text() == "Under closed-caller-model@1, caller.py::twice(n) must return n + 2."
assert (REPOSITORY / ".git").is_dir()
scheduler = _scheduler(ACTUAL / "resources.json")
connection, index = _open(ACTUAL)
try:
    prepared = index.prepare_current(REPOSITORY, repository_id="authored:stage-aa:admitted-checked-caller",
        operation_id="stage-aa10-initial", expected_head=None, scheduler=scheduler)
    head = prepared.head
    observed = index.observe_current(REPOSITORY, expected_head=head, scheduler=scheduler)
    assert sorted(row.path for row in observed.manifest.snapshot.entries) == sorted(SOURCES)
    python = Path(sys.executable).resolve(strict=True)
    assert Path("/opt/ipfs-supervisor/venv/bin/python").resolve(strict=True) == python
    lean = Path("/opt/ipfs-supervisor/lean/bin/lean")
    tool_policy = seal_finite_integer_tools(python_executable=python, lean_executable=lean)
    callee = IntegerOffsetContract("callee.py", "increment", "n", 1).to_dict()
    caller = IntegerOffsetContract("caller.py", "twice", "n", 2).to_dict()
    save(ACTUAL / "prepared.json", {"head": head.to_dict(), "tool_policy": tool_policy,
        "callee_contract": callee, "caller_contract": caller, "paths": sorted(SOURCES),
        "repository": str(REPOSITORY), "model_state": str(ACTUAL),
        "source_inventory": {path: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
                             for path, raw in SOURCES.items()},
        "source_body_executed": False, "provider_calls": 0, "training_steps": 0})
    result = qualify_current_call_composition(index=index, repository=REPOSITORY, expected_head=head,
        paths=sorted(SOURCES), repository_id=head.repository_id, callee_contract=callee,
        caller_contract=caller, tool_policy=tool_policy, output=ACTUAL / "model", scheduler=scheduler)
    assert result["qualified"] is True and result["model_status"] == "model_proved"
    assert result["metadata"]["row_count"] == 49 and len(result["metadata"]["family_counts"]) == 20
    assert index.current(head.repository_id) == head
    for name, raw in SOURCES.items():
        assert (REPOSITORY / name).read_bytes() == raw
    resources = scheduler.snapshot()
    assert resources["active_lease_count"] == resources["waiting_request_count"] == 0
    summary = {"schema": "admitted-budget-container-model-qualification@1", "qualified": True,
        "result_cid": result["result_cid"], "head": head.to_dict(),
        "repository": str(REPOSITORY), "model_state": str(ACTUAL),
        "model_status": result["model_status"], "rows": result["metadata"]["row_count"],
        "families": result["metadata"]["family_counts"], "resources_after": resources,
        "fresh_native_Lean_processes": 3, "source_body_executed": False,
        "provider_calls": 0, "training_steps": 0, "START_called": False,
        "source_to_model_equivalence_proved": False, "convergence_proved": False,
        "full_task_satisfaction": False,
        "proof_scope": "Closed mathematical integer caller model under explicit assumptions; unsupported eval retained. This is not CPython runtime equivalence or learned convergence."}
    save(ACTUAL / "qualification-summary.json", summary)
    print(json.dumps({"qualified": True, "model_status": result["model_status"],
        "rows": result["metadata"]["row_count"], "result_cid": result["result_cid"],
        "model_state": str(ACTUAL), "repository": str(REPOSITORY)}), flush=True)
finally:
    connection.close()
