#!/usr/bin/env python3
"""Run no-provider import/custody prerequisites for a future integrated caller."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MODULES = [
    "ipfs_accelerate_py.agent_supervisor.semantic_state.harness",
    "ipfs_accelerate_py.agent_supervisor.semantic_state.context_pack",
    "ipfs_accelerate_py.agent_supervisor.semantic_state.session",
    "ipfs_accelerate_py.agent_supervisor.autonomous_repair.formal_assurance_cegis",
    "ipfs_accelerate_py.agent_supervisor.procedure_compiler.cegis",
    "ipfs_accelerate_py.agent_supervisor.procedure_compiler.registry",
    "ipfs_accelerate_py.agent_supervisor.validation.compositional_verification_vertical",
    "ipfs_datasets_py.logic.software_contracts.semantic_state",
    "ipfs_datasets_py.logic.software_contracts.compositional",
    "ipfs_datasets_py.proof_context.context_pack",
    "ipfs_kit_py.proof_context.state_store",
    "ipfs_datasets_py.logic.zkp.incremental_sealing",
]
CHILD = """import hashlib,importlib,json,sys
out={}
for name in json.loads(sys.argv[1]):
 try:
  module=importlib.import_module(name);p=module.__file__
  out[name]={'imported':True,'path':p,'sha256':hashlib.sha256(open(p,'rb').read()).hexdigest()}
 except Exception as exc:out[name]={'imported':False,'error_type':type(exc).__name__,'error':str(exc)[:500]}
print(json.dumps(out))
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=HERE / "next_stage_prerequisites.json")
    args = parser.parse_args()
    if args.output.exists(): raise SystemExit("receipt exists; choose a fresh --output path")
    aseh = ROOT / ".worktrees/agent-supervisor-efficiency-and-state-hardening-v1"
    procedure = ROOT / ".worktrees/proof-carrying-procedure-compiler-v1"
    profiles = {"root_external": [ROOT / "external/ipfs_accelerate", ROOT / "external/ipfs_datasets", ROOT / "external/ipfs_kit"], "complete_aseh": [aseh, aseh / "ipfs_datasets_py", aseh / "ipfs_kit_py"], "original_procedure": [procedure, procedure / "ipfs_datasets_py", procedure / "ipfs_kit_py"]}
    observations = {}
    for name, paths in profiles.items():
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(map(str, paths)), PYTHONDONTWRITEBYTECODE="1", IPFS_ACCEL_SKIP_CORE="1")
        command = [sys.executable, "-B", "-c", CHILD, json.dumps(MODULES)]
        process = subprocess.run(command, cwd="/tmp", env=env, capture_output=True, text=True, timeout=40)
        observations[name] = {"source_roots": list(map(str, paths)), "returncode": process.returncode, "module_results": json.loads(process.stdout) if process.returncode == 0 else None, "stderr": process.stderr[-2000:]}
    registry_path = HERE / "next_stage_candidate_registry.json"
    registry = json.loads(registry_path.read_text())
    hashes_valid = all((ROOT / p).is_file() and hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == expected for p, expected in registry["input_bindings"].items())
    result = {"schema": "ns-next-stage-prerequisite-observation/v1", "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "registry_sha256": hashlib.sha256(registry_path.read_bytes()).hexdigest(), "registry_input_hashes_match": hashes_valid, "profiles": observations, "integrated_caller_exists": (HERE / "integrated_v1/run.py").is_file(), "integrated_freeze_exists": (HERE / "integrated_v1/freeze.json").is_file(), "ready_for_live_dispatch": False, "readiness_reason": "Separate import successes do not qualify one materializing caller, signed trust profile, complete usage ledger, source-expansion/recovery behavior or newly frozen trajectory/scorer corpus.", "provider_calls": 0, "oracle_or_reference_patch_payload_reads": False}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"registry_input_hashes_match": hashes_valid, "profile_import_counts": {k: sum(v["imported"] for v in p["module_results"].values()) if p["module_results"] else None for k, p in observations.items()}, "integrated_caller_exists": result["integrated_caller_exists"], "ready_for_live_dispatch": False, "provider_calls": 0}, indent=2))


if __name__ == "__main__": main()
