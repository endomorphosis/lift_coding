"""Diagnostic: reproduce the steering bridge worker's seed exactly
(Supervisor.open on external/ipfs_accelerate + run with the bridge's
default seed prompt), printing the full traceback of any failure.
Run with the bridge worker's own environment (cwd = superproject root,
PYTHONPATH = kit:datasets:accelerate, lift_coding .venv python)."""
import os
import sys
import traceback

sys.path.insert(0, "/home/hatch/workspace/lift_coding/external/ipfs_accelerate")
sys.path.insert(0, "/home/hatch/workspace/lift_coding/external/ipfs_datasets")
sys.path.insert(0, "/home/hatch/workspace/lift_coding/external/ipfs_kit")

from ipfs_accelerate_py.agent_supervisor.entrypoints.facade import Supervisor

DEFAULT_SEED_PROMPT = (
    "Maintain the ipfs_accelerate_py verification backlog: keep MCP++ "
    "Profile G conformance evidence current for the supervisor console."
)

repo = os.environ.get(
    "IPFS_ACCELERATE_AGENT_REPOSITORY",
    "/home/hatch/workspace/lift_coding/external/ipfs_accelerate",
)
print("repository:", repo)
supervisor = Supervisor.open(repository=repo)
print("open OK, composition_cid:", supervisor.composition_cid)
try:
    run = supervisor.run(os.environ.get("IPFS_ACCELERATE_SUPERVISOR_SEED_PROMPT") or DEFAULT_SEED_PROMPT)
    print("RUN OK:", run.run_id, run.state)
except Exception:
    traceback.print_exc()
