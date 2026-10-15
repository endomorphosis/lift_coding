"""Run one reviewed local pytest group with isolated admission state."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--repo", choices=("accelerate", "datasets", "kit"), default="accelerate")
    parser.add_argument("--tests", required=True)
    args = parser.parse_args()
    campaign = Path(__file__).resolve().parent
    workspace = Path("/home/barberb/lift_coding_worktrees")
    roots = {name: workspace / f"merge-all-{name}-20261014" for name in ("accelerate", "datasets", "kit")}
    paths = Path(args.tests).read_text().splitlines()
    assert paths and all(path.strip() == path and path for path in paths)
    env = dict(os.environ)
    env.update({
        "PYTHONPATH": ":".join(map(str, roots.values())) + ":/home/barberb/.local/lib/python3.12/site-packages:/home/barberb/lift_coding/.venvs/terminal-bench-harbor/lib/python3.12/site-packages",
        "PYTHONNOUSERSITE": "1",
        "PYTHONOPTIMIZE": "0",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB": f"/tmp/merge-all-{args.name}-20261014-tests.duckdb",
        "IPFS_DATASETS_RESOURCE_SCHEDULER_PATH": str(campaign / f"{args.name}-test-resources.json"),
        "IPFS_DATASETS_RESOURCE_CPU_SLOTS": "1",
        "IPFS_KIT_DISABLE": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
    })
    command = [sys.executable, "-m", "pytest", "-q", "-o", "addopts=", "-o", "log_cli=false", "--color=no", *paths, "--junitxml=" + str(campaign / f"{args.name}-tests.xml")]
    with tempfile.TemporaryDirectory(prefix="merge-all-bytecode-") as bytecode, (campaign / f"{args.name}-tests.log").open("w") as log:
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPYCACHEPREFIX"] = bytecode
        return subprocess.run(command, cwd=roots[args.repo], env=env, stdout=log, stderr=subprocess.STDOUT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
