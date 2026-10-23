"""Fresh authored repository and real Lean closure for Stage X, no source execution."""
import json
import os
from pathlib import Path
import subprocess
import sys

STAGE = Path(__file__).resolve().parent
ACTUAL = STAGE / "actual-public-audit-01"
os.umask(0o077)
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
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    with path.open("xb") as stream:
        stream.write(raw)

repository = ACTUAL / "repository"
repository.mkdir(mode=0o755)
sources = {
    "callee.py": b"def increment(n: int) -> int:\n    return n + 1\n",
    "caller.py": b"from callee import increment\n\ndef twice(n: int) -> int:\n    return increment(increment(n))\n",
    "dynamic.py": b"def unsupported(expression):\n    return eval(expression)\n",
}
for name, raw in sources.items():
    path = repository / name
    path.write_bytes(raw)
    path.chmod(0o644)
repository.chmod(0o755)
for args in (("init", "--quiet"), ("add", "--", *sorted(sources)),
             ("-c", "user.name=Stage X authored fixture", "-c", "user.email=fixture@example.invalid",
              "commit", "--quiet", "--no-gpg-sign", "-m", "Authored conditional caller fixture")):
    subprocess.run(["git", *args], cwd=repository, check=True, timeout=20, capture_output=True)
scheduler = _scheduler(ACTUAL / "resources.json")
connection, index = _open(ACTUAL)
try:
    prepared = index.prepare_current(repository, repository_id="authored:stage-x:conditional-caller",
        operation_id="stage-x-initial", expected_head=None, scheduler=scheduler)
    head = prepared.head
    tool_policy = seal_finite_integer_tools(python_executable=Path(sys.executable).resolve(),
        lean_executable=Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean"))
    callee = IntegerOffsetContract("callee.py", "increment", "n", 1).to_dict()
    caller = IntegerOffsetContract("caller.py", "twice", "n", 2).to_dict()
    save(ACTUAL / "prepared.json", {"head": head.to_dict(), "tool_policy": tool_policy,
        "callee_contract": callee, "caller_contract": caller, "paths": sorted(sources),
        "source_body_executed": False, "provider_calls": 0, "training_steps": 0})
    result = qualify_current_call_composition(index=index, repository=repository, expected_head=head,
        paths=sorted(sources), repository_id=head.repository_id, callee_contract=callee,
        caller_contract=caller, tool_policy=tool_policy, output=ACTUAL / "model", scheduler=scheduler)
    save(ACTUAL / "qualification-summary.json", {"result_cid": result["result_cid"],
        "head": head.to_dict(), "model_status": result["model_status"], "rows": result["metadata"]["row_count"],
        "families": result["metadata"]["family_counts"], "resources_after": scheduler.snapshot(),
        "source_body_executed": False, "provider_calls": 0, "training_steps": 0})
    print(json.dumps({"qualified": True, "model_status": result["model_status"],
        "rows": result["metadata"]["row_count"], "result_cid": result["result_cid"]}), flush=True)
finally:
    connection.close()
