"""Execute the existing original-source vertical slice; retain all failures.

This is fixture qualification, not historical repair, held-out synthesis,
validated deployment, or measured model-call savings against a baseline.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
SOURCE = ROOT / ".worktrees/proof-carrying-procedure-compiler-v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x") as out:
        json.dump(value, out, indent=2, sort_keys=True)
        out.write("\n")


def main():
    global SOURCE
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=SOURCE)
    args = parser.parse_args()
    SOURCE = args.source.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True)
    (out / "runner_snapshot.py").write_bytes(Path(__file__).read_bytes())
    module = SOURCE / "ipfs_accelerate_py/agent_supervisor/validation/compositional_verification_vertical.py"
    child = """import hashlib,json,sys,time
from pathlib import Path
from ipfs_accelerate_py.agent_supervisor.validation.compositional_verification_vertical import run_compositional_verification_vertical_slice
started=time.perf_counter()
result=run_compositional_verification_vertical_slice(output_path=Path(sys.argv[1]),keep_workdir=True)
source=Path(sys.argv[2]).resolve()
files={}
for mod in tuple(sys.modules.values()):
    p=getattr(mod,'__file__',None)
    if p and Path(p).is_file() and Path(p).resolve().is_relative_to(source):
        files[str(Path(p).resolve())]=hashlib.sha256(Path(p).read_bytes()).hexdigest()
Path(sys.argv[3]).write_text(json.dumps(files,indent=2,sort_keys=True)+'\\n')
print(json.dumps({'status':result['status'],'route_elapsed_seconds':time.perf_counter()-started,'artifact_valid':result['artifact_verification']['valid']}))
"""
    (out / "child.py").write_text(child)
    env = os.environ.copy()
    env.update(PYTHONPATH=os.pathsep.join([str(SOURCE), str(SOURCE / "ipfs_datasets_py")]),
               IPFS_ACCEL_SKIP_CORE="1", PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    command = [sys.executable, "-B", str(out / "child.py"), str(out / "native_result.json"),
               str(SOURCE), str(out / "loaded_sources.json")]
    write(out / "protocol.json", {
        "schema": "ns-native-compositional-qualification/v1", "case_count": 1,
        "source": str(SOURCE), "entry_sha256": sha(module), "runner_sha256": sha(Path(__file__)),
        "child_sha256": sha(out / "child.py"), "command": command, "timeout_seconds": 360,
        "source_git_head": subprocess.check_output(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip(),
        "datasets_git_head": subprocess.check_output(["git", "-C", str(SOURCE / "ipfs_datasets_py"), "rev-parse", "HEAD"], text=True).strip(),
        "expected": ["baseline composition proved", "fault refuted", "counterexample localized",
                     "repair independently replayed", "selected and full tests passed"],
        "limits": ["Existing constructed fixture with prescribed fault 30 and expected repair 10",
                   "Internal benchmark estimates are not new token or compute savings",
                   "No new claim of production authority or general Python correctness"]})
    start = time.monotonic()
    with (out / "stdout.log").open("wb") as stdout, (out / "stderr.log").open("wb") as stderr:
        proc = subprocess.Popen(command, cwd=SOURCE, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        write(out / "process.json", {"pid": proc.pid, "command": command})
        timeout = False
        try:
            rc = proc.wait(timeout=360)
        except subprocess.TimeoutExpired:
            timeout = True
            os.killpg(proc.pid, signal.SIGKILL)
            rc = proc.wait()
    summary = {"schema": "ns-native-compositional-observation/v1", "returncode": rc,
               "timed_out": timeout, "host_elapsed_seconds": time.monotonic() - start,
               "status": "completed" if rc == 0 else "failed", "model_token_savings": None,
               "stdout_sha256": sha(out / "stdout.log"), "stderr_sha256": sha(out / "stderr.log")}
    if rc == 0:
        r = json.loads((out / "native_result.json").read_text())
        summary.update(baseline_disposition=r["baseline"]["discharge"]["disposition"],
                       fault_disposition=r["fault"]["discharge"]["disposition"],
                       final_disposition=r["final"]["discharge"]["disposition"],
                       artifact_verification=r["artifact_verification"],
                       selected_tests_status=r["final"]["selected_tests"]["status"],
                       full_tests_status=r["final"]["full_tests"]["status"],
                       native_result_sha256=sha(out / "native_result.json"))
    write(out / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
